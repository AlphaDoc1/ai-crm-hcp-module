"""
app/schemas.py
Pydantic v2 request/response schemas for all FastAPI endpoints.
"""
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator
from enum import Enum


# ── Enums ─────────────────────────────────────────────────────────────────────

class SentimentEnum(str, Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"


class InteractionTypeEnum(str, Enum):
    meeting = "Meeting"
    call = "Call"
    email = "Email"
    conference = "Conference"


class FollowUpStatusEnum(str, Enum):
    pending = "pending"
    done = "done"


# ── HCP schemas ────────────────────────────────────────────────────────────────

class HCPBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    specialty: Optional[str] = None
    hospital: Optional[str] = None
    contact_info: Optional[str] = None


class HCPCreate(HCPBase):
    pass


class HCPResponse(HCPBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class HCPSearchResult(BaseModel):
    id: int
    name: str
    specialty: Optional[str] = None
    hospital: Optional[str] = None
    contact_info: Optional[str] = None
    interaction_count: int = 0
    recent_interactions: list[dict] = []

    model_config = {"from_attributes": True}


# ── Interaction schemas ────────────────────────────────────────────────────────

class InteractionCreate(BaseModel):
    """
    Schema for creating a new interaction.
    date and time are accepted as strings (YYYY-MM-DD and HH:MM) for
    flexibility across API clients; parsing happens in the router.
    """
    hcp_id: int
    interaction_type: InteractionTypeEnum = InteractionTypeEnum.meeting
    date: Optional[str] = None          # YYYY-MM-DD
    time: Optional[str] = None          # HH:MM or HH:MM:SS
    attendees: Optional[str] = None
    topics_discussed: Optional[str] = None
    materials_shared: Optional[list[dict]] = Field(default_factory=list)
    samples_distributed: Optional[list[dict]] = Field(default_factory=list)
    sentiment: Optional[SentimentEnum] = SentimentEnum.neutral
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None

    @field_validator("materials_shared", "samples_distributed", mode="before")
    @classmethod
    def ensure_list(cls, v):
        if v is None:
            return []
        return v


class InteractionUpdate(BaseModel):
    """All fields optional — only provided fields are updated."""
    interaction_type: Optional[InteractionTypeEnum] = None
    date: Optional[str] = None          # YYYY-MM-DD
    time: Optional[str] = None          # HH:MM or HH:MM:SS
    attendees: Optional[str] = None
    topics_discussed: Optional[str] = None
    materials_shared: Optional[list[dict]] = None
    samples_distributed: Optional[list[dict]] = None
    sentiment: Optional[SentimentEnum] = None
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None


class InteractionResponse(BaseModel):
    id: int
    hcp_id: int
    hcp_name: Optional[str] = None
    interaction_type: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    attendees: Optional[str] = None
    topics_discussed: Optional[str] = None
    materials_shared: Optional[list[dict]] = None
    samples_distributed: Optional[list[dict]] = None
    sentiment: Optional[str] = None
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    follow_ups: Optional[list[dict]] = None

    model_config = {"from_attributes": True}


# ── Follow-up schemas ──────────────────────────────────────────────────────────

class FollowUpResponse(BaseModel):
    id: int
    interaction_id: int
    suggested_action: str
    status: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class FollowUpStatusUpdate(BaseModel):
    status: FollowUpStatusEnum


# ── Chat schemas ───────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    conversation_history: Optional[list[ChatMessage]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    tool_used: Optional[str] = None
    tool_result: Optional[dict] = None
    interaction_data: Optional[dict] = None
    suggestions: Optional[list[str]] = None
    success: bool = True


# ── Generic schemas ────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    database: str
    version: str = "1.0.0"
