"""
app/models/hcp.py
SQLAlchemy ORM model for Healthcare Professionals (HCPs).
"""
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class HCP(Base):
    __tablename__ = "hcps"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    specialty = Column(String(255), nullable=True)
    hospital = Column(String(255), nullable=True)
    contact_info = Column(Text, nullable=True)          # JSON-formatted string or plain text
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    interactions = relationship("Interaction", back_populates="hcp", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<HCP id={self.id} name={self.name!r} specialty={self.specialty!r}>"
