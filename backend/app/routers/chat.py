"""
app/routers/chat.py
FastAPI router for the AI chat endpoint — routes messages through the LangGraph agent.
"""
import logging
from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage, AIMessage

from app.schemas import ChatRequest, ChatResponse
from app.agent.graph import get_hcp_agent

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["AI Chat"])


@router.post("", response_model=ChatResponse, summary="Send a message to the HCP LangGraph agent")
async def chat(payload: ChatRequest):
    """
    Routes the user's message through the LangGraph StateGraph agent.

    Flow:
    1. Reconstruct conversation history as LangChain messages.
    2. Append the new user message.
    3. Invoke the compiled LangGraph agent (router → tool_executor loop).
    4. Extract the final AI response and any tool metadata from the state.
    5. Return a structured ChatResponse with the reply, tool used, and
       any interaction data or follow-up suggestions surfaced by the tools.

    The agent will automatically:
    - Call log_interaction if the message describes a new HCP visit
    - Call edit_interaction if an interaction ID + change is mentioned
    - Call search_hcp for HCP lookup queries
    - Call suggest_followups for follow-up generation requests
    - Call summarize_interaction for preview/summary requests
    """
    try:
        agent = get_hcp_agent()

        # ── Build initial message list ────────────────────────────────────────
        messages = []
        for msg in (payload.conversation_history or []):
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                messages.append(AIMessage(content=msg.content))

        # Append the current user message
        messages.append(HumanMessage(content=payload.message))

        # ── Invoke the LangGraph agent ────────────────────────────────────────
        result_state = agent.invoke(
            {
                "messages": messages,
                "user_input": payload.message,
                "tool_result": None,
                "active_tool": None,
            }
        )

        # ── Extract the final AI reply ────────────────────────────────────────
        all_messages = result_state.get("messages", [])

        # Walk backwards to find the last AIMessage that is NOT a tool call
        reply_text = "I processed your request."
        for msg in reversed(all_messages):
            if isinstance(msg, AIMessage) and not msg.tool_calls:
                reply_text = msg.content
                break

        # ── Extract tool metadata ─────────────────────────────────────────────
        tool_used = None
        tool_result = None
        interaction_data = None
        suggestions = None

        # Find the last ToolMessage to surface structured data to the frontend
        from langchain_core.messages import ToolMessage
        import json

        for msg in reversed(all_messages):
            if isinstance(msg, ToolMessage):
                tool_used = msg.name if hasattr(msg, "name") else None
                try:
                    tool_result = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                except (json.JSONDecodeError, TypeError):
                    tool_result = {"raw": str(msg.content)}

                # Surface interaction data for form hydration
                if tool_result and isinstance(tool_result, dict):
                    if "saved_interaction" in tool_result:
                        interaction_data = tool_result["saved_interaction"]
                    if "suggestions" in tool_result:
                        suggestions = tool_result["suggestions"]
                    if "summary" in tool_result:
                        interaction_data = tool_result["summary"]
                break

        logger.info(f"[chat] Replied to: '{payload.message[:60]}...' | tool_used={tool_used}")

        return ChatResponse(
            reply=reply_text,
            tool_used=tool_used,
            tool_result=tool_result,
            interaction_data=interaction_data,
            suggestions=suggestions,
            success=True,
        )

    except Exception as e:
        logger.error(f"[chat] Agent invocation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Agent error: {str(e)}",
        )
