from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
)
from app.services.llm_client import (
    LLMError,
    llm_client,
)


logger = logging.getLogger(__name__)


# ============================================================================
# Router
# ============================================================================

router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)


# ============================================================================
# System prompt
# ============================================================================

CHAT_SYSTEM_PROMPT = """
You are an AI career guidance assistant.

Your purpose is to help students and career seekers make informed
career and learning decisions.

You may help with:

- Career exploration
- Understanding job roles
- Skill development
- Skill gaps
- Learning strategies
- Career roadmaps
- Interview preparation
- Portfolio projects
- Technology choices
- Professional development

Important rules:

1. Give practical and actionable advice.
2. Use the user's provided skills and target career when relevant.
3. Do not invent information about the user's background.
4. Do not claim certainty about future employment outcomes.
5. Do not guarantee salaries, jobs, admissions, or career success.
6. When discussing rapidly changing technologies, clearly distinguish
   general guidance from current facts.
7. Encourage the user to verify important career decisions using
   authoritative sources.
8. Keep answers understandable for students.
9. Do not unnecessarily repeat the conversation history.
10. If the user's question is unclear, ask a concise clarifying question.
""".strip()


# ============================================================================
# Conversation formatting
# ============================================================================

def build_chat_prompt(
    request: ChatRequest,
) -> str:
    """
    Build the prompt sent to the LLM.

    The current user message is combined with the previous conversation
    and optional career context.
    """

    sections: list[str] = []

    # ------------------------------------------------------------------------
    # Career context
    # ------------------------------------------------------------------------

    if request.target_job_title:

        sections.append(
            "TARGET CAREER:\n"
            f"{request.target_job_title}"
        )

    # ------------------------------------------------------------------------
    # Current skills
    # ------------------------------------------------------------------------

    if request.current_skills:

        skills_text = ", ".join(
            request.current_skills
        )

        sections.append(
            "CURRENT SKILLS:\n"
            f"{skills_text}"
        )

    # ------------------------------------------------------------------------
    # Conversation history
    # ------------------------------------------------------------------------

    if request.conversation:

        history_lines = []

        for message in request.conversation:

            role = message.role.upper()

            history_lines.append(
                f"{role}: {message.content}"
            )

        sections.append(
            "CONVERSATION HISTORY:\n"
            + "\n".join(history_lines)
        )

    # ------------------------------------------------------------------------
    # Current question
    # ------------------------------------------------------------------------

    sections.append(
        "CURRENT USER MESSAGE:\n"
        f"{request.message}"
    )

    return "\n\n".join(
        sections
    )


# ============================================================================
# Endpoint
# ============================================================================

@router.post(
    "/advise",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Get AI career advice",
    description=(
        "Provides career guidance using the configured LLM provider "
        "and optional conversation context."
    ),
)
def career_advice(
    request: ChatRequest,
) -> ChatResponse:
    """
    Generate an AI career-advice response.

    Endpoint:

        POST /api/v1/chat/advise
    """

    logger.info(
        "Career chat request received."
    )

    prompt = build_chat_prompt(
        request
    )

    try:

        answer = llm_client.generate(
            prompt=prompt,
            system_prompt=CHAT_SYSTEM_PROMPT,
            temperature=0.4,
            max_tokens=4096,
        )

    except LLMError as exc:

        logger.error(
            "Career chat LLM request failed: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The AI career advice service is currently "
                "unavailable."
            ),
        ) from exc

    except Exception as exc:

        logger.exception(
            "Unexpected career chat error."
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Unable to generate career advice."
            ),
        ) from exc

    # ------------------------------------------------------------------------
    # Build conversation response
    # ------------------------------------------------------------------------

    updated_conversation = list(
        request.conversation
    )

    updated_conversation.append(
        ChatMessage(
            role="user",
            content=request.message,
        )
    )

    updated_conversation.append(
        ChatMessage(
            role="assistant",
            content=answer,
        )
    )

    logger.info(
        "Career advice response generated successfully."
    )

    return ChatResponse(
        message=answer,
        conversation=updated_conversation,
    )