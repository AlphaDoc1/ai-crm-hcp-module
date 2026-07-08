"""
app/models/follow_up.py
SQLAlchemy ORM model for AI-Suggested Follow-up Actions.

Each row is one suggested follow-up linked to a specific interaction,
with a status to track whether the rep has acted on it.
"""
import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class FollowUpStatusEnum(str, enum.Enum):
    pending = "pending"
    done = "done"


class FollowUp(Base):
    __tablename__ = "follow_ups"

    id = Column(Integer, primary_key=True, index=True)

    # FK → interactions
    interaction_id = Column(
        Integer,
        ForeignKey("interactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    suggested_action = Column(Text, nullable=False)   # LLM-generated suggestion text

    status = Column(
        SAEnum(FollowUpStatusEnum, name="followupstatus_enum"),
        nullable=False,
        default=FollowUpStatusEnum.pending,
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    interaction = relationship("Interaction", back_populates="follow_ups")

    def __repr__(self):
        return f"<FollowUp id={self.id} interaction_id={self.interaction_id} status={self.status}>"
