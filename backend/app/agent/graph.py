"""
app/agent/graph.py
─────────────────────────────────────────────────────────────────────────────
LangGraph StateGraph — the core orchestration layer of the HCP CRM agent.

Architecture
────────────
  START
    │
    ▼
  [router] ──────────────────────────────────────────────────────┐
    │ (LLM with 5 bound tools decides which tool to call)         │
    │                                                             │
    ▼ if tool_calls present                                       │
  [tool_executor]  ←── ToolNode runs the selected tool           │
    │                                                             │
    ▼ loop back                                                   │
  [router]  ──── no more tool_calls ──────────────────────────► END

Nodes:
  • router        — ChatGroq (openai/gpt-oss-20b, reasoning_effort=low) with 5 tools bound via .bind_tools()
                    Emits an AIMessage; if that message contains tool_calls,
                    the graph routes to tool_executor.
  • tool_executor — langgraph.prebuilt.ToolNode; invokes the selected tool
                    and appends a ToolMessage to the state.

Conditional Edges:
  • tools_condition() from langgraph.prebuilt checks the last message:
      - If tool_calls   → "tools"  (tool_executor)
      - If no tool_calls → END

The graph is compiled once at module load and cached as `hcp_agent`.
─────────────────────────────────────────────────────────────────────────────
"""

import logging
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from app.core.config import get_settings
from app.agent.state import AgentState
from app.agent.tools import ALL_TOOLS
from app.agent.prompts import ROUTER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)
settings = get_settings()


# ─────────────────────────────────────────────────────────────────────────────
# Build the LLM with all 5 tools bound
# ─────────────────────────────────────────────────────────────────────────────

def _build_llm_with_tools() -> ChatGroq:
    """
    Create a ChatGroq instance for the router node using the primary model
    (openai/gpt-oss-20b) with all 5 tools bound via .bind_tools().
    The LLM will emit tool_calls when it determines a tool should be invoked.

    reasoning_effort="low" is passed via model_kwargs (the correct path for
    langchain_groq 0.2.x, which does not expose reasoning_effort as a direct
    constructor kwarg). Low effort is sufficient for routing — deciding *which*
    tool to call doesn't need deep reasoning, and speed is important since this
    runs on every conversation turn.
    """
    llm = ChatGroq(
        model=settings.primary_model,   # "openai/gpt-oss-20b"
        api_key=settings.groq_api_key,
        temperature=1,                  # reasoning models require temperature=1
        max_tokens=4096,
        model_kwargs={"reasoning_effort": "low"},  # via model_kwargs (not a direct param)
    )
    return llm.bind_tools(ALL_TOOLS)


# ─────────────────────────────────────────────────────────────────────────────
# Router node function
# ─────────────────────────────────────────────────────────────────────────────

def router_node(state: AgentState) -> dict:
    """
    The router node is the brain of the agent.

    It prepends the system prompt (explaining all 5 tools) to the conversation
    history and invokes the LLM. The LLM either:
      a) Emits tool_calls → graph routes to tool_executor for execution
      b) Responds directly → graph routes to END

    The system message is injected at the start of every invocation so the
    LLM always knows the full tool manifest, even mid-conversation.
    """
    llm_with_tools = _build_llm_with_tools()

    system_msg = SystemMessage(content=ROUTER_SYSTEM_PROMPT)
    messages_to_send = [system_msg] + state["messages"]

    try:
        response = llm_with_tools.invoke(messages_to_send)
        logger.info(
            f"[router] Response type: {'tool_call' if response.tool_calls else 'direct'} "
            f"| tools: {[tc['name'] for tc in response.tool_calls] if response.tool_calls else []}"
        )
        return {"messages": [response]}
    except Exception as e:
        logger.error(f"[router] LLM invocation error: {e}", exc_info=True)
        # Return a graceful error message rather than crashing the graph
        from langchain_core.messages import AIMessage
        return {
            "messages": [
                AIMessage(
                    content=f"I encountered an error while processing your request: {str(e)}. "
                            f"Please try again or rephrase your message."
                )
            ]
        }


# ─────────────────────────────────────────────────────────────────────────────
# Build and compile the StateGraph
# ─────────────────────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """
    Assemble the LangGraph StateGraph with:
      - router node (LLM-based orchestrator)
      - tool_executor node (ToolNode running all 5 tools)
      - Conditional edge from router: tool_calls → tools, else → END
      - Edge from tool_executor back to router (enables multi-step reasoning)
    """
    graph_builder = StateGraph(AgentState)

    # ── Add nodes ─────────────────────────────────────────────────────────────
    graph_builder.add_node("router", router_node)
    graph_builder.add_node("tools", ToolNode(tools=ALL_TOOLS))

    # ── Define edges ──────────────────────────────────────────────────────────

    # Entry point
    graph_builder.add_edge(START, "router")

    # Conditional: if last AIMessage has tool_calls → tools; else → END
    graph_builder.add_conditional_edges(
        "router",
        tools_condition,         # built-in condition from langgraph.prebuilt
    )

    # After tool execution, loop back to router so it can:
    #   a) process the tool result and respond to user, OR
    #   b) call another tool if needed (multi-step)
    graph_builder.add_edge("tools", "router")

    return graph_builder


# ─────────────────────────────────────────────────────────────────────────────
# Compiled graph — singleton, imported by routers/chat.py
# ─────────────────────────────────────────────────────────────────────────────

def get_compiled_graph():
    """
    Build and compile the LangGraph agent graph.
    Called lazily so that settings (GROQ_API_KEY) are loaded before compile.
    """
    graph = build_graph()
    compiled = graph.compile()
    logger.info("[graph] HCP Agent StateGraph compiled successfully.")
    return compiled


# Module-level singleton — compiled once when this module is first imported
hcp_agent = None


def get_hcp_agent():
    """
    Lazy-load the compiled graph. Called from FastAPI startup.
    Avoids issues with settings not yet loaded at import time.
    """
    global hcp_agent
    if hcp_agent is None:
        hcp_agent = get_compiled_graph()
    return hcp_agent
