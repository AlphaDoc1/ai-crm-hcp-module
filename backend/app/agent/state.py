"""
app/agent/state.py
─────────────────────────────────────────────────────────────────────────────
Defines the shared state object that flows through every node of the
LangGraph StateGraph. The `messages` list uses `add_messages` as its
reducer so new messages are appended rather than overwritten on each step.
─────────────────────────────────────────────────────────────────────────────
"""
from typing import Annotated, Optional, Any, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    # Conversation history — add_messages reducer appends, never overwrites
    messages: Annotated[list[BaseMessage], add_messages]

    # Raw user input (echoed into state so tool nodes can inspect it directly)
    user_input: str

    # Structured result returned by the last-executed tool
    tool_result: Optional[dict[str, Any]]

    # Name of the tool that was most recently invoked (for debugging / tracing)
    active_tool: Optional[str]
