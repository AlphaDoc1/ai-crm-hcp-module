"""
app/models/__init__.py
Import all models here so SQLAlchemy's Base.metadata knows about every table
before create_all() is called.
"""
from app.models.hcp import HCP
from app.models.interaction import Interaction, SentimentEnum, InteractionTypeEnum
from app.models.follow_up import FollowUp, FollowUpStatusEnum

__all__ = [
    "HCP",
    "Interaction",
    "SentimentEnum",
    "InteractionTypeEnum",
    "FollowUp",
    "FollowUpStatusEnum",
]
