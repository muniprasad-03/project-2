from __future__ import annotations

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.models.schemas import ResumeParseResponse
from app.services.llm_client import (
    LLMError,
    LLMResponseValidationError,
    llm_client,
)
from app.services.resume_parser import (
    EmptyResumeError,
    ResumeParserError,
    UnsupportedResumeTypeError,
    extract_text,
)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(
    prefix="/resume",
    tags=["Resume"],
)


# ---------------------------------------------------------------------------
# Resume skill extraction schema
# ---------------------------------------------------------------------------

from pydantic import BaseModel, Field


class ExtractedResumeSkills(BaseModel):
    """
    Structured response expected from the LLM after analysing
    extracted resume text.
    """

    skills: list[str] = Field(
        default_factory=list,
        description="Technical and professional skills extracted from the resume.",
    )


# ---------------------------------------------------------------------------
# LLM prompts
# ---------------------------------------------------------------------------

RESUME_SYSTEM_PROMPT = """
You are a resume analysis assistant for an AI career recommendation system.

Extract skills explicitly supported by the resume.

Focus on:
- Programming languages
- Frameworks
- Libraries
- Databases
- Cloud technologies
- Machine learning and AI technologies
- Software tools
- Technical concepts
- Engineering skills
- Professional/domain skills

Do not invent skills that are not supported by the resume.

Return only structured JSON matching the requested schema.
""".strip()


def build_resume_prompt(resume_text: str) -> str:
    """
    Build the LLM prompt used to extract skills from the resume.
    """

    return f"""
Analyze the following resume and extract the user's skills.

RESUME TEXT
-----------
{resume_text}
-----------

Return the skills as a JSON array through the requested response schema.

Only include skills that are reasonably supported by the resume.
Do not infer technologies solely from job titles.
""".strip()


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post(
    "/parse",
    response_model=ResumeParseResponse,
    status_code=status.HTTP_200_OK,
    summary="Parse a resume and extract skills",
    description=(
        "Accepts a PDF or DOCX resume, extracts its text in memory, "
        "and uses the configured LLM provider to identify skills."
    ),
)
async def parse_resume(
    file: UploadFile = File(...),
) -> ResumeParseResponse:
    """
    Parse an uploaded resume and extract skills.

    Endpoint:

        POST /api/v1/resume/parse

    Supported formats:

        PDF
        DOCX

    The uploaded file is processed in memory and is not saved
    to local disk.
    """

    # -----------------------------------------------------------------------
    # Validate filename
    # -----------------------------------------------------------------------

    filename = file.filename or "resume"

    logger.info(
        "Resume upload received: %s",
        filename,
    )

    # -----------------------------------------------------------------------
    # Read uploaded file
    # -----------------------------------------------------------------------

    try:
        file_bytes = await file.read()

    except Exception as exc:

        logger.exception(
            "Unable to read uploaded resume."
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to read the uploaded resume.",
        ) from exc

    finally:

        await file.close()

    # -----------------------------------------------------------------------
    # Extract resume text
    # -----------------------------------------------------------------------

    try:

        resume_text = extract_text(
            file_bytes=file_bytes,
            content_type=file.content_type,
            filename=filename,
        )

    except UnsupportedResumeTypeError as exc:

        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc),
        ) from exc

    except EmptyResumeError as exc:

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except ResumeParserError as exc:

        logger.warning(
            "Resume parsing failed: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception as exc:

        logger.exception(
            "Unexpected resume parsing error."
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to process the resume.",
        ) from exc

    # -----------------------------------------------------------------------
    # Extract skills using LLM
    # -----------------------------------------------------------------------

    prompt = build_resume_prompt(
        resume_text
    )

    try:

        extracted = llm_client.generate_structured(
            prompt=prompt,
            response_model=ExtractedResumeSkills,
            system_prompt=RESUME_SYSTEM_PROMPT,
            temperature=0.1,
            max_tokens=2048,
        )

    except LLMResponseValidationError as exc:

        logger.error(
            "Resume skill extraction returned invalid structured data."
        )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "The AI provider returned an invalid "
                "resume analysis response."
            ),
        ) from exc

    except LLMError as exc:

        logger.error(
            "Resume skill extraction failed: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The AI resume analysis service is currently unavailable."
            ),
        ) from exc

    except Exception as exc:

        logger.exception(
            "Unexpected LLM resume analysis error."
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to analyse the resume.",
        ) from exc

    # -----------------------------------------------------------------------
    # Clean extracted skills
    # -----------------------------------------------------------------------

    skills: list[str] = []

    seen = set()

    for skill in extracted.skills:

        skill = skill.strip()

        if not skill:
            continue

        key = skill.lower()

        if key in seen:
            continue

        seen.add(key)
        skills.append(skill)

    # -----------------------------------------------------------------------
    # Return response
    # -----------------------------------------------------------------------

    logger.info(
        "Resume processed successfully: %s | %d skills extracted",
        filename,
        len(skills),
    )

    return ResumeParseResponse(
        filename=filename,
        content_type=file.content_type or "application/octet-stream",
        extracted_text_length=len(resume_text),
        skills=skills,
        message="Resume processed successfully.",
    )