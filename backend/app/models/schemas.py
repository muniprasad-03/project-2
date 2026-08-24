from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ============================================================================
# Common
# ============================================================================

class APIModel(BaseModel):
    """
    Base Pydantic model used by API request/response schemas.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


# ============================================================================
# RIASEC
# ============================================================================

class RIASECProfile(APIModel):
    """
    User's six-dimensional RIASEC interest profile.

    Values are expected to represent the user's relative interest
    in each RIASEC dimension.
    """

    realistic: float = Field(
        default=0.0,
        ge=0.0,
        description="Realistic interest score.",
    )

    investigative: float = Field(
        default=0.0,
        ge=0.0,
        description="Investigative interest score.",
    )

    artistic: float = Field(
        default=0.0,
        ge=0.0,
        description="Artistic interest score.",
    )

    social: float = Field(
        default=0.0,
        ge=0.0,
        description="Social interest score.",
    )

    enterprising: float = Field(
        default=0.0,
        ge=0.0,
        description="Enterprising interest score.",
    )

    conventional: float = Field(
        default=0.0,
        ge=0.0,
        description="Conventional interest score.",
    )

    def to_riasec_dict(self) -> Dict[str, float]:
        """
        Convert API field names to the format expected by
        the ML inference engine.
        """
        return {
            "Realistic": self.realistic,
            "Investigative": self.investigative,
            "Artistic": self.artistic,
            "Social": self.social,
            "Enterprising": self.enterprising,
            "Conventional": self.conventional,
        }


# ============================================================================
# Career Recommendation
# ============================================================================

class SkillMatchRequest(APIModel):
    """
    Request body for:

        POST /api/v1/recommend/skills
    """

    user_skills: List[str] = Field(
        ...,
        min_length=1,
        description="Skills provided by the user.",
    )

    preferred_industry: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Optional preferred industry.",
    )

    top_k: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of career recommendations to return.",
    )

    riasec_profile: Optional[RIASECProfile] = Field(
        default=None,
        description="Optional RIASEC interest profile.",
    )

    @field_validator("user_skills")
    @classmethod
    def validate_user_skills(
        cls,
        skills: List[str],
    ) -> List[str]:
        """
        Remove empty skills and duplicate skills while preserving
        the original order.
        """
        cleaned: List[str] = []
        seen = set()

        for skill in skills:
            skill = skill.strip()

            if not skill:
                continue

            key = skill.lower()

            if key in seen:
                continue

            seen.add(key)
            cleaned.append(skill)

        if not cleaned:
            raise ValueError(
                "user_skills must contain at least one non-empty skill."
            )

        return cleaned


class CareerMatchResult(APIModel):
    """
    A single career recommendation.
    """

    onet_soc_code: str = Field(
        ...,
        description="O*NET-SOC occupation code.",
    )

    job_title: str = Field(
        ...,
        description="Occupation title.",
    )

    description: str = Field(
        default="",
        description="Occupation description.",
    )

    match_percentage: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Overall career match percentage.",
    )

    matched_skills: List[str] = Field(
        default_factory=list,
        description="Skills from the user profile matched by the occupation.",
    )

    missing_skills: List[str] = Field(
        default_factory=list,
        description="Skills that are not currently represented by the occupation profile.",
    )

    text_similarity: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="TF-IDF cosine similarity.",
    )

    skill_coverage: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Proportion of user skills matched by the occupation.",
    )

    riasec_similarity: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="RIASEC profile similarity.",
    )

    riasec: Dict[str, Optional[float]] = Field(
        default_factory=dict,
        description="O*NET occupational RIASEC profile.",
    )

    hot_technologies: List[str] = Field(
        default_factory=list,
        description="Hot technologies associated with the occupation.",
    )

    in_demand_software: List[str] = Field(
        default_factory=list,
        description="In-demand software associated with the occupation.",
    )


class SkillMatchResponse(APIModel):
    """
    Response body for:

        POST /api/v1/recommend/skills
    """

    user_skills: List[str]

    preferred_industry: Optional[str] = None

    recommendations: List[CareerMatchResult]

    total_results: int = Field(
        ...,
        ge=0,
    )


# ============================================================================
# Resume Parsing
# ============================================================================

class ResumeParseResponse(APIModel):
    """
    Response returned after parsing a PDF/DOCX resume.

    The actual file upload is handled by FastAPI's UploadFile;
    this model represents the extracted result.
    """

    filename: str

    content_type: str

    extracted_text_length: int = Field(
        ...,
        ge=0,
    )

    skills: List[str] = Field(
        default_factory=list,
    )

    message: str = (
        "Resume processed successfully."
    )


# ============================================================================
# Roadmap
# ============================================================================

class RoadmapRequest(APIModel):
    """
    Request body for:

        POST /api/v1/roadmap/generate
    """

    target_job_title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Career/occupation for which the roadmap is requested.",
    )

    recommendation_id: Optional[int] = Field(
        default=None,
        description="Optional ID of the recommendation history record to update.",
    )

    missing_skills: List[str] = Field(
        default_factory=list,
        description="Skills the user should develop.",
    )

    current_skills: List[str] = Field(
        default_factory=list,
        description="Skills the user already has.",
    )

    weeks: int = Field(
        default=12,
        ge=1,
        le=52,
        description="Desired roadmap duration in weeks.",
    )

    @field_validator(
        "missing_skills",
        "current_skills",
    )
    @classmethod
    def clean_skill_lists(
        cls,
        skills: List[str],
    ) -> List[str]:
        """
        Clean and deduplicate skill lists.
        """
        result: List[str] = []
        seen = set()

        for skill in skills:
            skill = skill.strip()

            if not skill:
                continue

            key = skill.lower()

            if key in seen:
                continue

            seen.add(key)
            result.append(skill)

        return result


class RoadmapResource(APIModel):
    """
    Learning resource included in a roadmap week.
    """

    title: str

    url: Optional[str] = None

    resource_type: Optional[str] = None


class RoadmapWeek(APIModel):
    """
    One week of the generated career roadmap.
    """

    week: int = Field(
        ...,
        ge=1,
    )

    title: str

    objectives: List[str] = Field(
        default_factory=list,
    )

    skills: List[str] = Field(
        default_factory=list,
    )

    resources: List[RoadmapResource] = Field(
        default_factory=list,
    )


class RoadmapResponse(APIModel):
    """
    Response body for:

        POST /api/v1/roadmap/generate
    """

    target_job_title: str

    duration_weeks: int = Field(
        ...,
        ge=1,
    )

    weeks: List[RoadmapWeek] = Field(
        default_factory=list,
    )

    summary: Optional[str] = None


# ============================================================================
# Chat
# ============================================================================

class ChatMessage(APIModel):
    """
    A single chat message.
    """

    role: Literal[
        "user",
        "assistant",
    ]

    content: str = Field(
        ...,
        min_length=1,
        max_length=10000,
    )


class ChatRequest(APIModel):
    """
    Request body for:

        POST /api/v1/chat/advise
    """

    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
    )

    conversation: List[ChatMessage] = Field(
        default_factory=list,
        description="Previous messages in the conversation.",
    )

    current_skills: List[str] = Field(
        default_factory=list,
    )

    target_job_title: Optional[str] = Field(
        default=None,
        max_length=200,
    )

    @field_validator("message")
    @classmethod
    def validate_message(
        cls,
        message: str,
    ) -> str:
        message = message.strip()

        if not message:
            raise ValueError(
                "message cannot be empty."
            )

        return message


class ChatResponse(APIModel):
    """
    Response body for:

        POST /api/v1/chat/advise
    """

    message: str

    conversation: List[ChatMessage] = Field(
        default_factory=list,
    )


# ============================================================================
# History
# ============================================================================

class RecommendationHistoryItem(APIModel):
    """
    One stored recommendation/history entry.
    """

    id: int

    user_id: str

    job_title: str

    match_percentage: float = Field(
        ...,
        ge=0.0,
        le=100.0,
    )

    matched_skills: List[str] = Field(
        default_factory=list,
    )

    missing_skills: List[str] = Field(
        default_factory=list,
    )

    roadmap: Optional[dict] = None

    is_bookmarked: bool = False

    timestamp: Optional[str] = None


class HistoryResponse(APIModel):
    """
    Response for:

        GET /api/v1/history/{user_id}
    """

    user_id: str

    items: List[RecommendationHistoryItem] = Field(
        default_factory=list,
    )

    total: int = Field(
        ...,
        ge=0,
    )


class BookmarkResponse(APIModel):
    """
    Response for:

        POST /api/v1/bookmark/{id}
    """

    id: int

    bookmarked: bool


class ClearHistoryResponse(APIModel):
    """
    Response for:

        DELETE /api/v1/history/{user_id}
    """

    user_id: str

    deleted_count: int = Field(
        ...,
        ge=0,
    )

    message: str