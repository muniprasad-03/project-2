from __future__ import annotations

import json
import logging
import time
from typing import Any, Optional, Type, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import settings


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Generic Pydantic type
# ---------------------------------------------------------------------------

T = TypeVar("T", bound=BaseModel)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class LLMError(Exception):
    """Base exception for LLM-related failures."""


class LLMConfigurationError(LLMError):
    """Raised when no LLM provider is configured."""


class LLMProviderError(LLMError):
    """Raised when an LLM provider fails."""


class LLMResponseValidationError(LLMError):
    """Raised when the LLM response cannot be validated."""


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models"
)

GROQ_API_URL = (
    "https://api.groq.com/openai/v1/chat/completions"
)

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"

DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_TOKENS = 4096

MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1.0
REQUEST_TIMEOUT_SECONDS = 60.0


# ---------------------------------------------------------------------------
# LLM Client
# ---------------------------------------------------------------------------

class LLMClient:
    """
    Unified client for the configured LLM providers.

    Provider order:

        1. Groq
        2. Gemini

    If GROQ_API_KEY is empty, Groq is skipped.

    If Groq fails, Gemini is attempted.

    The client supports:

        - retries
        - exponential backoff
        - provider fallback
        - plain text responses
        - structured Pydantic responses
    """

    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        groq_api_key: Optional[str] = None,
    ) -> None:

        self.gemini_api_key = (
            gemini_api_key
            if gemini_api_key is not None
            else settings.GEMINI_API_KEY
        )

        self.groq_api_key = (
            groq_api_key
            if groq_api_key is not None
            else settings.GROQ_API_KEY
        )

        self.gemini_api_key = self.gemini_api_key.strip()
        self.groq_api_key = self.groq_api_key.strip()

        if not self.gemini_api_key and not self.groq_api_key:
            raise LLMConfigurationError(
                "No LLM provider is configured. "
                "Set GEMINI_API_KEY or GROQ_API_KEY."
            )

    # -----------------------------------------------------------------------
    # Provider availability
    # -----------------------------------------------------------------------

    @property
    def available_providers(self) -> list[str]:
        """
        Return the currently configured providers.
        """
        providers = []

        if self.groq_api_key:
            providers.append("groq")

        if self.gemini_api_key:
            providers.append("gemini")

        return providers

    # -----------------------------------------------------------------------
    # Public text generation
    # -----------------------------------------------------------------------

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> str:
        """
        Generate a plain text response.

        The client attempts configured providers in fallback order.
        """

        prompt = prompt.strip()

        if not prompt:
            raise ValueError(
                "Prompt cannot be empty."
            )

        errors = []

        for provider in self._provider_order():

            try:
                logger.info(
                    "Attempting LLM provider: %s",
                    provider,
                )

                if provider == "groq":
                    return self._generate_groq(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )

                if provider == "gemini":
                    return self._generate_gemini(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )

            except Exception as exc:

                logger.warning(
                    "LLM provider '%s' failed: %s",
                    provider,
                    exc,
                )

                errors.append(
                    f"{provider}: {exc}"
                )

        raise LLMProviderError(
            "All configured LLM providers failed. "
            + " | ".join(errors)
        )

    # -----------------------------------------------------------------------
    # Public structured generation
    # -----------------------------------------------------------------------

    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> T:
        """
        Generate JSON from an LLM and validate it against a Pydantic model.

        The LLM is explicitly instructed to return JSON only.
        """

        schema = response_model.model_json_schema()

        json_instruction = (
            "\n\nReturn ONLY valid JSON. "
            "Do not use Markdown code fences. "
            "Do not add explanations before or after the JSON.\n\n"
            "The JSON must conform to this schema:\n"
            f"{json.dumps(schema, indent=2)}"
        )

        full_prompt = prompt + json_instruction

        raw_response = self.generate(
            prompt=full_prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        parsed_json = self._parse_json_response(
            raw_response
        )

        try:
            return response_model.model_validate(
                parsed_json
            )

        except ValidationError as exc:

            logger.error(
                "LLM response failed Pydantic validation: %s",
                exc,
            )

            raise LLMResponseValidationError(
                "The LLM returned JSON that does not match "
                f"{response_model.__name__}."
            ) from exc

    # -----------------------------------------------------------------------
    # Provider ordering
    # -----------------------------------------------------------------------

    def _provider_order(self) -> list[str]:
        """
        Return providers in fallback order.

        Groq is preferred when configured.
        Gemini is used as fallback.
        """

        providers = []

        if self.groq_api_key:
            providers.append("groq")

        if self.gemini_api_key:
            providers.append("gemini")

        if not providers:
            raise LLMConfigurationError(
                "No LLM provider is configured."
            )

        return providers

    # -----------------------------------------------------------------------
    # Retry helper
    # -----------------------------------------------------------------------

    def _with_retry(
        self,
        operation,
        provider_name: str,
    ) -> Any:
        """
        Execute an LLM operation with exponential backoff.
        """

        last_exception: Optional[Exception] = None

        for attempt in range(1, MAX_RETRIES + 1):

            try:
                return operation()

            except Exception as exc:

                last_exception = exc

                if attempt >= MAX_RETRIES:
                    break

                delay = (
                    INITIAL_BACKOFF_SECONDS
                    * (2 ** (attempt - 1))
                )

                logger.warning(
                    "%s attempt %d/%d failed. "
                    "Retrying in %.1f seconds.",
                    provider_name,
                    attempt,
                    MAX_RETRIES,
                    delay,
                )

                time.sleep(delay)

        raise LLMProviderError(
            f"{provider_name} failed after "
            f"{MAX_RETRIES} attempts."
        ) from last_exception

    # -----------------------------------------------------------------------
    # Groq
    # -----------------------------------------------------------------------

    def _generate_groq(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """
        Generate a response using Groq's OpenAI-compatible API.
        """

        if not self.groq_api_key:
            raise LLMConfigurationError(
                "GROQ_API_KEY is not configured."
            )

        messages = []

        if system_prompt:
            messages.append(
                {
                    "role": "system",
                    "content": system_prompt,
                }
            )

        messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        payload = {
            "model": DEFAULT_GROQ_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        headers = {
            "Authorization": (
                f"Bearer {self.groq_api_key}"
            ),
            "Content-Type": "application/json",
        }

        def operation() -> str:

            with httpx.Client(
                timeout=REQUEST_TIMEOUT_SECONDS
            ) as client:

                response = client.post(
                    GROQ_API_URL,
                    headers=headers,
                    json=payload,
                )

                response.raise_for_status()

                data = response.json()

            try:
                content = data["choices"][0]["message"]["content"]

            except (
                KeyError,
                IndexError,
                TypeError,
            ) as exc:

                raise LLMProviderError(
                    "Unexpected response structure from Groq."
                ) from exc

            if not isinstance(content, str):
                raise LLMProviderError(
                    "Groq returned a non-text response."
                )

            content = content.strip()

            if not content:
                raise LLMProviderError(
                    "Groq returned an empty response."
                )

            return content

        return self._with_retry(
            operation,
            "Groq",
        )

    # -----------------------------------------------------------------------
    # Gemini
    # -----------------------------------------------------------------------

    def _generate_gemini(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """
        Generate a response using Google's Gemini REST API.
        """

        if not self.gemini_api_key:
            raise LLMConfigurationError(
                "GEMINI_API_KEY is not configured."
            )

        model_url = (
            f"{GEMINI_API_URL}/"
            f"{DEFAULT_GEMINI_MODEL}:generateContent"
        )

        contents = []

        if system_prompt:
            contents.append(
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": (
                                "System instructions:\n"
                                f"{system_prompt}"
                            )
                        }
                    ],
                }
            )

        contents.append(
            {
                "role": "user",
                "parts": [
                    {
                        "text": prompt,
                    }
                ],
            }
        )

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        params = {
            "key": self.gemini_api_key,
        }

        def operation() -> str:

            with httpx.Client(
                timeout=REQUEST_TIMEOUT_SECONDS
            ) as client:

                response = client.post(
                    model_url,
                    params=params,
                    json=payload,
                )

                response.raise_for_status()

                data = response.json()

            return self._extract_gemini_text(
                data
            )

        return self._with_retry(
            operation,
            "Gemini",
        )

    # -----------------------------------------------------------------------
    # Gemini response parsing
    # -----------------------------------------------------------------------

    @staticmethod
    def _extract_gemini_text(
        data: dict,
    ) -> str:
        """
        Extract generated text from a Gemini API response.
        """

        try:
            candidates = data["candidates"]

            if not candidates:
                raise LLMProviderError(
                    "Gemini returned no candidates."
                )

            parts = candidates[0]["content"]["parts"]

        except (
            KeyError,
            IndexError,
            TypeError,
        ) as exc:

            raise LLMProviderError(
                "Unexpected response structure from Gemini."
            ) from exc

        text_parts = []

        for part in parts:

            if not isinstance(part, dict):
                continue

            text = part.get("text")

            if isinstance(text, str):
                text_parts.append(text)

        result = "\n".join(
            text_parts
        ).strip()

        if not result:
            raise LLMProviderError(
                "Gemini returned an empty response."
            )

        return result

    # -----------------------------------------------------------------------
    # JSON parsing
    # -----------------------------------------------------------------------

    @staticmethod
    def _parse_json_response(
        response: str,
    ) -> Any:
        """
        Parse JSON returned by an LLM.

        Handles:
            1. Pure JSON
            2. JSON wrapped in ```json ... ```
            3. JSON surrounded by accidental text
        """

        response = response.strip()

        if not response:
            raise LLMResponseValidationError(
                "LLM returned an empty response."
            )

        # ---------------------------------------------------------------
        # Direct JSON
        # ---------------------------------------------------------------

        try:
            return json.loads(response)

        except json.JSONDecodeError:
            pass

        # ---------------------------------------------------------------
        # Markdown code fence
        # ---------------------------------------------------------------

        cleaned = response

        if cleaned.startswith("```"):
            lines = cleaned.splitlines()

            if lines:
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            cleaned = "\n".join(lines).strip()

            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()

            try:
                return json.loads(cleaned)

            except json.JSONDecodeError:
                pass

        # ---------------------------------------------------------------
        # Find JSON object
        # ---------------------------------------------------------------

        object_start = response.find("{")
        object_end = response.rfind("}")

        if (
            object_start != -1
            and object_end > object_start
        ):
            candidate = response[
                object_start : object_end + 1
            ]

            try:
                return json.loads(candidate)

            except json.JSONDecodeError:
                pass

        # ---------------------------------------------------------------
        # Find JSON array
        # ---------------------------------------------------------------

        array_start = response.find("[")
        array_end = response.rfind("]")

        if (
            array_start != -1
            and array_end > array_start
        ):
            candidate = response[
                array_start : array_end + 1
            ]

            try:
                return json.loads(candidate)

            except json.JSONDecodeError:
                pass

        raise LLMResponseValidationError(
            "Unable to parse the LLM response as JSON."
        )


# ---------------------------------------------------------------------------
# Shared client instance
# ---------------------------------------------------------------------------

llm_client = LLMClient()