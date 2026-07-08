"""
app/routers/hcps.py
FastAPI router for HCP (Healthcare Professional) endpoints.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import HCP, Interaction
from app.schemas import HCPResponse, HCPCreate, HCPSearchResult

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/hcps", tags=["HCPs"])


@router.get("/search", response_model=list[HCPSearchResult], summary="Fuzzy-search HCPs by name")
def search_hcps(
    q: str = Query(..., min_length=1, description="Search term for HCP name"),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    Case-insensitive fuzzy search for HCPs by name.
    Powers the 'Search or select HCP' dropdown in the Log Interaction form.
    Returns each HCP with their recent interaction history summary.
    """
    hcps = (
        db.query(HCP)
        .filter(HCP.name.ilike(f"%{q}%"))
        .order_by(HCP.name)
        .limit(limit)
        .all()
    )

    results = []
    for hcp in hcps:
        recent = (
            db.query(Interaction)
            .filter(Interaction.hcp_id == hcp.id)
            .order_by(Interaction.created_at.desc())
            .limit(5)
            .all()
        )
        interaction_summaries = [
            {
                "id": i.id,
                "type": i.interaction_type.value if i.interaction_type else None,
                "date": i.date.isoformat() if i.date else None,
                "sentiment": i.sentiment.value if i.sentiment else None,
                "topics_snippet": (
                    (i.topics_discussed or "")[:100] + "..."
                    if i.topics_discussed and len(i.topics_discussed) > 100
                    else (i.topics_discussed or "")
                ),
            }
            for i in recent
        ]
        results.append(
            HCPSearchResult(
                id=hcp.id,
                name=hcp.name,
                specialty=hcp.specialty,
                hospital=hcp.hospital,
                contact_info=hcp.contact_info,
                interaction_count=len(recent),
                recent_interactions=interaction_summaries,
            )
        )

    return results


@router.get("", response_model=list[HCPResponse], summary="List all HCPs")
def list_hcps(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Return paginated list of all HCPs ordered by name."""
    return db.query(HCP).order_by(HCP.name).offset(skip).limit(limit).all()


@router.get("/{hcp_id}", response_model=HCPResponse, summary="Get HCP by ID")
def get_hcp(hcp_id: int, db: Session = Depends(get_db)):
    """Fetch a single HCP by their ID."""
    hcp = db.query(HCP).filter(HCP.id == hcp_id).first()
    if not hcp:
        raise HTTPException(status_code=404, detail=f"HCP with id={hcp_id} not found")
    return hcp


@router.post("", response_model=HCPResponse, status_code=201, summary="Create a new HCP")
def create_hcp(payload: HCPCreate, db: Session = Depends(get_db)):
    """Create a new HCP record."""
    hcp = HCP(**payload.model_dump())
    db.add(hcp)
    db.commit()
    db.refresh(hcp)
    logger.info(f"[hcps] Created HCP id={hcp.id} name={hcp.name!r}")
    return hcp
