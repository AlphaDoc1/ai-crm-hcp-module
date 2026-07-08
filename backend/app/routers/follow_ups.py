"""
app/routers/follow_ups.py
FastAPI router for FollowUp suggestion endpoints.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import FollowUp
from app.schemas import FollowUpResponse, FollowUpStatusUpdate

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Follow-ups"])


@router.get(
    "/api/interactions/{interaction_id}/follow-ups",
    response_model=list[FollowUpResponse],
    summary="Get AI-suggested follow-ups for an interaction",
)
def get_follow_ups(
    interaction_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    """
    Retrieve all follow-up suggestions linked to a specific interaction.
    Powers the 'AI Suggested Follow-ups' chips in the UI.
    Returns both pending and done suggestions, ordered by creation date.
    """
    interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not interaction:
        raise HTTPException(status_code=404, detail=f"Interaction {interaction_id} not found")

    follow_ups = (
        db.query(FollowUp)
        .filter(FollowUp.interaction_id == interaction_id)
        .order_by(FollowUp.created_at.desc())
        .all()
    )
    return follow_ups


@router.patch(
    "/api/follow-ups/{follow_up_id}/status",
    response_model=FollowUpResponse,
    summary="Update follow-up status (pending → done)",
)
def update_follow_up_status(
    follow_up_id: int = Path(..., ge=1),
    payload: FollowUpStatusUpdate = ...,
    db: Session = Depends(get_db),
):
    """Mark a follow-up suggestion as done or reset to pending."""
    followup = db.query(FollowUp).filter(FollowUp.id == follow_up_id).first()
    if not followup:
        raise HTTPException(status_code=404, detail=f"FollowUp {follow_up_id} not found")

    followup.status = OrmFollowUpStatusEnum(payload.status.value)
    db.commit()
    db.refresh(followup)
    logger.info(f"[follow_ups] Updated follow_up id={follow_up_id} status={followup.status}")
    return followup
