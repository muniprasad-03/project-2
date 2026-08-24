from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.ml.inference import match_careers
from app.models.db_models import RecommendationLog
from app.models.schemas import (
    CareerMatchResult,
    SkillMatchRequest,
    SkillMatchResponse,
)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(
    prefix="/recommend",
    tags=["Recommendations"],
)


# ---------------------------------------------------------------------------
# Skill-based career recommendation
# ---------------------------------------------------------------------------

@router.post(
    "/skills",
    response_model=SkillMatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Recommend careers from user skills",
    description=(
        "Returns ranked career recommendations based on the "
        "user's skills using the Phase 1 ML recommendation engine."
    ),
)
def recommend_by_skills(
    request: SkillMatchRequest,
    user_id: str = Header(..., alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> SkillMatchResponse:
    """
    Generate career recommendations from user skills and persist
    the generated recommendations to the database.

    Endpoint:
        POST /api/v1/recommend/skills

    The user is identified through the X-User-Id request header.

    The actual recommendation calculation is delegated to
    app.ml.inference.match_careers().
    """

    logger.info(
        "Career recommendation request received: "
        "user_id=%s, %d skills, top_k=%d, industry=%s",
        user_id,
        len(request.user_skills),
        request.top_k,
        request.preferred_industry,
    )

    # ------------------------------------------------------------------
    # Convert optional RIASEC profile
    # ------------------------------------------------------------------

    user_riasec = None

    if request.riasec_profile is not None:
        user_riasec = request.riasec_profile.to_riasec_dict()

    # ------------------------------------------------------------------
    # Call Phase 1 ML engine
    # ------------------------------------------------------------------

    try:
        recommendations = match_careers(
            user_skills=request.user_skills,
            top_k=request.top_k,
            preferred_industry=request.preferred_industry,
            user_riasec=user_riasec,
        )

    except ValueError as exc:
        logger.warning(
            "Invalid recommendation request: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except FileNotFoundError as exc:
        logger.error(
            "ML artifacts are missing: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Career recommendation service is not "
                "properly initialized."
            ),
        ) from exc

    except Exception as exc:
        logger.exception(
            "Unexpected error while generating recommendations."
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Unable to generate career recommendations."
            ),
        ) from exc

    # ------------------------------------------------------------------
    # Convert ML results to Pydantic response models
    # ------------------------------------------------------------------

    try:
        career_results = [
            CareerMatchResult.model_validate(
                recommendation
            )
            for recommendation in recommendations
        ]

    except Exception as exc:
        logger.exception(
            "ML recommendation result failed response validation."
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Recommendation service returned "
                "an invalid response."
            ),
        ) from exc

    # ------------------------------------------------------------------
    # Persist recommendation history
    # ------------------------------------------------------------------

    try:
        for career in career_results:
            record = RecommendationLog(
                user_id=user_id,
                job_title=career.job_title,
                match_percentage=career.match_percentage,
                matched_skills=career.matched_skills,
                missing_skills=career.missing_skills,
                roadmap=None,
            )

            db.add(record)

        db.commit()

        logger.info(
            "Persisted %d recommendation records for user %s.",
            len(career_results),
            user_id,
        )

    except Exception as exc:
        db.rollback()

        logger.exception(
            "Failed to persist recommendation history "
            "for user %s.",
            user_id,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Recommendations were generated, but "
                "their history could not be saved."
            ),
        ) from exc

    # ------------------------------------------------------------------
    # Return API response
    # ------------------------------------------------------------------

    response = SkillMatchResponse(
        user_skills=request.user_skills,
        preferred_industry=request.preferred_industry,
        recommendations=career_results,
        total_results=len(career_results),
    )

    logger.info(
        "Generated %d career recommendations.",
        len(career_results),
    )

    return response