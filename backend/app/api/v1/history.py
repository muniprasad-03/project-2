from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.db_models import RecommendationLog


router = APIRouter(
    prefix="/api/v1",
    tags=["History"],
)


@router.get("/history/{user_id}")
def get_history(
    user_id: str,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    Retrieve all recommendation history entries for a user.

    Results are returned from newest to oldest.
    """

    statement = (
        select(RecommendationLog)
        .where(RecommendationLog.user_id == user_id)
        .order_by(RecommendationLog.timestamp.desc())
    )

    records = db.scalars(statement).all()

    return [
        {
            "id": record.id,
            "user_id": record.user_id,
            "job_title": record.job_title,
            "match_percentage": record.match_percentage,
            "missing_skills": record.missing_skills,
            "roadmap": record.roadmap,
            "timestamp": record.timestamp,
            "is_bookmarked": record.is_bookmarked,
        }
        for record in records
    ]


@router.post("/bookmark/{record_id}")
def toggle_bookmark(
    record_id: int,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Toggle the bookmark state of a recommendation history entry.
    """

    statement = select(RecommendationLog).where(
        RecommendationLog.id == record_id
    )

    record = db.scalar(statement)

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation history record not found.",
        )

    record.is_bookmarked = not record.is_bookmarked

    db.commit()
    db.refresh(record)

    return {
        "id": record.id,
        "is_bookmarked": record.is_bookmarked,
        "message": (
            "Recommendation bookmarked."
            if record.is_bookmarked
            else "Recommendation bookmark removed."
        ),
    }


@router.delete("/history/{user_id}")
def delete_history(
    user_id: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Delete all recommendation history entries belonging to a user.
    """

    statement = (
        delete(RecommendationLog)
        .where(RecommendationLog.user_id == user_id)
        .returning(RecommendationLog.id)
    )

    deleted_ids = db.execute(statement).scalars().all()

    db.commit()

    return {
        "user_id": user_id,
        "deleted_count": len(deleted_ids),
        "message": (
            "Recommendation history deleted."
            if deleted_ids
            else "No recommendation history found."
        ),
    }