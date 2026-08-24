from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.db_models import RecommendationLog
from app.models.schemas import (
    RoadmapRequest,
    RoadmapResponse,
)
from app.services.llm_client import (
    LLMError,
    LLMResponseValidationError,
    llm_client,
)


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(
    prefix="/roadmap",
    tags=["Roadmap"],
)


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

ROADMAP_SYSTEM_PROMPT = """
You are an AI career-learning roadmap generator.

Create a practical, realistic learning roadmap for a student
who wants to become the specified target job.

The roadmap must:

- Start from the user's current skills.
- Prioritize missing skills.
- Progress from fundamentals to intermediate and advanced topics.
- Include practical projects or exercises.
- Avoid recommending skills unrelated to the target job.
- Use the requested number of weeks.
- Keep the workload realistic for a student.
- Recommend learning resources only when you can provide useful,
  reliable resource titles or URLs.
- Do not claim that a resource exists if you are uncertain.

Return ONLY JSON matching the requested response schema.
""".strip()


# ---------------------------------------------------------------------------
# Prompt Builder
# ---------------------------------------------------------------------------

def build_roadmap_prompt(
    request: RoadmapRequest,
) -> str:
    """
    Build the roadmap-generation prompt.
    """

    current_skills = (
        "\n".join(
            f"- {skill}"
            for skill in request.current_skills
        )
        if request.current_skills
        else "- No current skills provided"
    )

    missing_skills = (
        "\n".join(
            f"- {skill}"
            for skill in request.missing_skills
        )
        if request.missing_skills
        else "- No specific missing skills provided"
    )

    return f"""
Generate a {request.weeks}-week career learning roadmap.

TARGET JOB
----------
{request.target_job_title}

CURRENT SKILLS
--------------
{current_skills}

MISSING SKILLS
-------------
{missing_skills}

ROADMAP REQUIREMENTS
--------------------
1. Create exactly {request.weeks} weeks.

2. Each week must have:
   - a clear title
   - learning objectives
   - skills/topics to develop
   - optional learning resources

3. Prioritize the explicitly identified missing skills.

4. Build progressively from foundational knowledge to practical
   application.

5. Include project-based learning where appropriate.

6. The final weeks should focus on practical application,
   portfolio development, interview preparation, or job readiness
   when relevant to the target job.

7. Do not repeat the same objective unnecessarily.

8. Keep the roadmap suitable for a student.

Return the result using the requested JSON structure.
""".strip()


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post(
    "/generate",
    response_model=RoadmapResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate a career learning roadmap",
    description=(
        "Generates a structured learning roadmap using the "
        "configured LLM provider."
    ),
)
def generate_roadmap(
    request: RoadmapRequest,
    db: Session = Depends(get_db),
) -> RoadmapResponse:
    """
    Generate a personalized career roadmap.

    Endpoint:

        POST /api/v1/roadmap/generate
    """

    logger.info(
        "Roadmap generation requested for: %s",
        request.target_job_title,
    )

    prompt = build_roadmap_prompt(request)

    try:
        roadmap = llm_client.generate_structured(
            prompt=prompt,
            response_model=RoadmapResponse,
            system_prompt=ROADMAP_SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=6000,
        )

    except LLMResponseValidationError as exc:
        logger.error(
            "LLM returned invalid roadmap structure: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "The AI provider returned an invalid "
                "roadmap response."
            ),
        ) from exc

    except LLMError as exc:
        logger.error(
            "Roadmap generation failed: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The AI roadmap service is currently unavailable."
            ),
        ) from exc

    except ValidationError as exc:
        logger.error(
            "Roadmap response validation failed: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "The AI provider returned an invalid "
                "roadmap structure."
            ),
        ) from exc

    except Exception as exc:
        logger.exception(
            "Unexpected roadmap generation error."
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to generate the roadmap.",
        ) from exc

    # -----------------------------------------------------------------------
    # Ensure the requested duration is respected
    # -----------------------------------------------------------------------

    if len(roadmap.weeks) != request.weeks:
        logger.warning(
            "LLM returned %d weeks instead of %d.",
            len(roadmap.weeks),
            request.weeks,
        )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "The AI provider did not return the requested "
                "number of roadmap weeks."
            ),
        )

    # -----------------------------------------------------------------------
    # Save to database if recommendation_id is provided
    # -----------------------------------------------------------------------
    
    if request.recommendation_id is not None:
        try:
            statement = select(RecommendationLog).where(
                RecommendationLog.id == request.recommendation_id
            )
            record = db.scalar(statement)
            
            if record:
                record.roadmap = roadmap.model_dump()
                db.commit()
                logger.info("Saved roadmap to recommendation %d", request.recommendation_id)
            else:
                logger.warning("Recommendation ID %d not found, roadmap not saved", request.recommendation_id)
        except Exception as exc:
            db.rollback()
            logger.exception("Failed to save roadmap to database.")

    logger.info(
        "Roadmap generated successfully: %s (%d weeks)",
        request.target_job_title,
        len(roadmap.weeks),
    )

    return roadmap