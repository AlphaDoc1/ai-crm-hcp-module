"""
app/models/interaction.py
SQLAlchemy ORM model for HCP Interactions.

Stores every field captured on the "Log HCP Interaction" form:
 - hcp_id (FK → hcps.id)
 - interaction_type (Meeting / Call / Email / Conference)
 - date / time of the interaction
 - attendees (comma-separated or JSON list)
 - topics_discussed (free text)
 - materials_shared  (JSON array — e.g. [{name, type}])
 - samples_distributed (JSON array — e.g. [{drug, quantity, lot_number}])
 - sentiment enum (positive / neutral / negative)
 - outcomes / follow_up_actions (free text)
"""
import enum
from sqlalchemy import (
    Column, Integer, String, Text, Date, Time,
    DateTime, ForeignKey, Enum as SAEnum
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class SentimentEnum(str, enum.Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"


class InteractionTypeEnum(str, enum.Enum):
    meeting = "Meeting"
    call = "Call"
    email = "Email"
    conference = "Conference"


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign key — which HCP this interaction was with
    hcp_id = Column(Integer, ForeignKey("hcps.id", ondelete="CASCADE"), nullable=False, index=True)

    interaction_type = Column(
        SAEnum(InteractionTypeEnum, name="interactiontype_enum"),
        nullable=False,
        default=InteractionTypeEnum.meeting,
    )

    date = Column(Date, nullable=True)
    time = Column(Time, nullable=True)

    attendees = Column(Text, nullable=True)          # comma-separated attendee names
    topics_discussed = Column(Text, nullable=True)

    # JSONB fields — store structured lists
    materials_shared = Column(JSONB, nullable=True, default=list)
    samples_distributed = Column(JSONB, nullable=True, default=list)

    sentiment = Column(
        SAEnum(SentimentEnum, name="sentiment_enum"),
        nullable=True,
        default=SentimentEnum.neutral,
    )

    outcomes = Column(Text, nullable=True)
    follow_up_actions = Column(Text, nullable=True)

    # Audit timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    hcp = relationship("HCP", back_populates="interactions")
    follow_ups = relationship("FollowUp", back_populates="interaction", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Interaction id={self.id} hcp_id={self.hcp_id} type={self.interaction_type}>"
