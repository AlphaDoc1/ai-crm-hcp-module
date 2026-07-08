"""
app/routers/interactions.py
FastAPI router for Interaction CRUD endpoints.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Interaction
from app.schemas import InteractionCreate, InteractionUpdate, InteractionResponse
from datetime import time as time_type

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/interactions", tags=["Interactions"])


def _parse_time(raw: str):
    """Parse HH:MM or HH:MM:SS string to a time object, or return None."""
    if not raw:
        return None
    try:
        parts = raw.split(":")
        return time_type(int(parts[0]), int(parts[1]))
    except (ValueError, IndexError, TypeError):
        return None


def _serialize(interaction: Interaction, db: Session) -> dict:
    """Serialize an Interaction ORM object to a response dict."""
    hcp = db.query(HCP).filter(HCP.id == interaction.hcp_id).first()
    follow_ups = (
        db.query(FollowUp)
        .filter(FollowUp.interaction_id == interaction.id)
        .order_by(FollowUp.created_at.desc())
        .all()
    )
    return {
        "id": interaction.id,
        "hcp_id": interaction.hcp_id,
        "hcp_name": hcp.name if hcp else None,
        "interaction_type": interaction.interaction_type.value if interaction.interaction_type else None,
        "date": interaction.date.isoformat() if interaction.date else None,
        "time": interaction.time.strftime("%H:%M") if interaction.time else None,
        "attendees": interaction.attendees,
        "topics_discussed": interaction.topics_discussed,
        "materials_shared": interaction.materials_shared or [],
        "samples_distributed": interaction.samples_distributed or [],
        "sentiment": interaction.sentiment.value if interaction.sentiment else None,
        "outcomes": interaction.outcomes,
        "follow_up_actions": interaction.follow_up_actions,
        "created_at": interaction.created_at.isoformat() if interaction.created_at else None,
        "updated_at": interaction.updated_at.isoformat() if interaction.updated_at else None,
        "follow_ups": [
            {
                "id": f.id,
                "suggested_action": f.suggested_action,
                "status": f.status.value,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in follow_ups
        ],
    }


@router.post("", status_code=201, summary="Create a new interaction (form submission)")
def create_interaction(payload: InteractionCreate, db: Session = Depends(get_db)):
    """
    Create a new HCP interaction from the structured form (left panel).
    Validates that the referenced HCP exists before saving.
    """
    hcp = db.query(HCP).filter(HCP.id == payload.hcp_id).first()
    if not hcp:
        raise HTTPException(status_code=404, detail=f"HCP with id={payload.hcp_id} not found")

    # Map Pydantic enum → ORM enum
    try:
        orm_type = OrmInteractionTypeEnum(payload.interaction_type.value)
    except ValueError:
        orm_type = OrmInteractionTypeEnum.meeting

    try:
        orm_sentiment = OrmSentimentEnum(payload.sentiment.value) if payload.sentiment else OrmSentimentEnum.neutral
    except ValueError:
        orm_sentiment = OrmSentimentEnum.neutral

    interaction = Interaction(
        hcp_id=payload.hcp_id,
        interaction_type=orm_type,
        date=payload.date,
        time=_parse_time(payload.time),
        attendees=payload.attendees,
        topics_discussed=payload.topics_discussed,
        materials_shared=payload.materials_shared or [],
        samples_distributed=payload.samples_distributed or [],
        sentiment=orm_sentiment,
        outcomes=payload.outcomes,
        follow_up_actions=payload.follow_up_actions,
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    logger.info(f"[interactions] Created interaction id={interaction.id} for HCP id={payload.hcp_id}")
    return _serialize(interaction, db)


@router.get("", summary="List all interactions")
def list_interactions(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    hcp_id: int = Query(default=None, description="Filter by HCP ID"),
    db: Session = Depends(get_db),
):
    """Return paginated list of interactions, optionally filtered by HCP."""
    query = db.query(Interaction)
    if hcp_id:
        query = query.filter(Interaction.hcp_id == hcp_id)
    interactions = query.order_by(Interaction.created_at.desc()).offset(skip).limit(limit).all()
    total = query.count()
    return {
        "items": [_serialize(i, db) for i in interactions],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/{interaction_id}", summary="Get a single interaction by ID")
def get_interaction(interaction_id: int, db: Session = Depends(get_db)):
    """Fetch a single interaction with full details and follow-ups."""
    interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not interaction:
        raise HTTPException(status_code=404, detail=f"Interaction {interaction_id} not found")
    return _serialize(interaction, db)


@router.put("/{interaction_id}", summary="Update an existing interaction")
def update_interaction(
    interaction_id: int,
    payload: InteractionUpdate,
    db: Session = Depends(get_db),
):
    """
    Partially update an interaction — only provided fields are changed.
    Used by both the form (left panel) edits and the LangGraph edit_interaction tool.
    """
    interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not interaction:
        raise HTTPException(status_code=404, detail=f"Interaction {interaction_id} not found")

    update_data = payload.model_dump(exclude_unset=True)
    updated_fields = []

    for field, value in update_data.items():
        if value is None:
            continue
        if field == "interaction_type":
            try:
                setattr(interaction, field, OrmInteractionTypeEnum(value.value if hasattr(value, 'value') else value))
                updated_fields.append(field)
            except ValueError:
                pass
        elif field == "sentiment":
            try:
                setattr(interaction, field, OrmSentimentEnum(value.value if hasattr(value, 'value') else value))
                updated_fields.append(field)
            except ValueError:
                pass
        elif field == "time":
            setattr(interaction, field, _parse_time(value))
            updated_fields.append(field)
        else:
            setattr(interaction, field, value)
            updated_fields.append(field)

    db.commit()
    db.refresh(interaction)
    logger.info(f"[interactions] Updated id={interaction_id} fields={updated_fields}")
    return _serialize(interaction, db)


@router.delete("/{interaction_id}", status_code=204, summary="Delete an interaction")
def delete_interaction(interaction_id: int, db: Session = Depends(get_db)):
    """Delete an interaction and all its associated follow-ups (cascade)."""
    interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not interaction:
        raise HTTPException(status_code=404, detail=f"Interaction {interaction_id} not found")
    db.delete(interaction)
    db.commit()
    logger.info(f"[interactions] Deleted interaction id={interaction_id}")
    return None
