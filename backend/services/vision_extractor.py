from __future__ import annotations

import base64
import json
import logging
import os
from dataclasses import dataclass
from typing import Optional

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AzureOpenAI,
    InternalServerError,
    RateLimitError,
)
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

AZURE_OPENAI_SCOPE = "https://cognitiveservices.azure.com/.default"
AZURE_OPENAI_API_KEY_ENV = 'AZURE_OPENAI_API_KEY'


class RetryableVisionError(RuntimeError):
    pass


class VisionExtractorError(RuntimeError):
    pass


class TitleBlockExtractionSchema(BaseModel):
    drawing_number: Optional[str] = None
    drawing_revision: Optional[str] = None
    drawing_title: Optional[str] = None

    model_config = ConfigDict(extra='forbid')


@dataclass(frozen=True)
class VisionExtractionResult:
    extraction: TitleBlockExtractionSchema
    raw_response_json: str
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]
    total_tokens: Optional[int]


def normalize_optional_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def normalize_extraction(
    extraction: TitleBlockExtractionSchema,
) -> TitleBlockExtractionSchema:
    return TitleBlockExtractionSchema(
        drawing_number=normalize_optional_text(extraction.drawing_number),
        drawing_revision=normalize_optional_text(extraction.drawing_revision),
        drawing_title=normalize_optional_text(extraction.drawing_title),
    )


def extraction_has_values(extraction: TitleBlockExtractionSchema) -> bool:
    return any(
        [
            extraction.drawing_number,
            extraction.drawing_revision,
            extraction.drawing_title,
        ]
    )


def _png_data_uri(payload: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(payload).decode('ascii')


class VisionExtractor:
    """Azure OpenAI vision extraction using structured output parsing."""

    def __init__(
        self,
        endpoint: str,
        deployment_name: str,
        *,
        api_version: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.endpoint = (endpoint or '').strip()
        self.deployment_name = (deployment_name or '').strip()
        self.api_version = (
            api_version
            or os.getenv('AZURE_OPENAI_API_VERSION', '2025-01-01-preview')
        ).strip()
        self.api_key = (api_key or os.getenv(
            AZURE_OPENAI_API_KEY_ENV, '')).strip()
        self.client: Optional[AzureOpenAI] = None

        if self.endpoint and self.deployment_name:
            client_kwargs = {
                'api_version': self.api_version,
                'azure_endpoint': self.endpoint,
                'max_retries': 0,
            }
            if self.api_key:
                client_kwargs['api_key'] = self.api_key
            else:
                client_kwargs['azure_ad_token_provider'] = get_bearer_token_provider(
                    DefaultAzureCredential(),
                    AZURE_OPENAI_SCOPE,
                )
            self.client = AzureOpenAI(**client_kwargs)
        else:
            logger.warning(
                "Vision extractor is not configured "
                "(endpoint=%s deployment=%s)",
                bool(self.endpoint),
                bool(self.deployment_name),
            )

    @property
    def is_configured(self) -> bool:
        return self.client is not None

    def extract_title_block(
        self,
        *,
        crop_png: bytes,
        context_png: bytes,
        filename: str,
    ) -> VisionExtractionResult:
        if self.client is None:
            raise VisionExtractorError("Vision extractor is not configured")

        messages = [
            {
                "role": "system",
                "content": (
                    "You extract title block metadata from engineering drawings. "
                    "Use the cropped title block image as the primary source. "
                    "Use the full-page image only for orientation. "
                    "Return null for any field that is absent, illegible, or uncertain. "
                    "Do not invent values."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Extract drawing_number, drawing_revision, and drawing_title "
                            f"from the title block for file '{filename}'. "
                            "Image 1 is the cropped title block. "
                            "Image 2 is the full page context."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": _png_data_uri(crop_png),
                            "detail": "high",
                        },
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": _png_data_uri(context_png),
                            "detail": "low",
                        },
                    },
                ],
            },
        ]

        try:
            response = self.client.beta.chat.completions.parse(
                model=self.deployment_name,
                messages=messages,
                response_format=TitleBlockExtractionSchema,
                temperature=0,
            )
        except (APIConnectionError, APITimeoutError, RateLimitError, InternalServerError) as exc:
            raise RetryableVisionError(str(exc)) from exc
        except APIStatusError as exc:
            if exc.status_code and int(exc.status_code) >= 500:
                raise RetryableVisionError(str(exc)) from exc
            raise VisionExtractorError(str(exc)) from exc
        except Exception as exc:
            raise VisionExtractorError(str(exc)) from exc

        choice = response.choices[0]
        if getattr(choice.message, 'refusal', None):
            raise VisionExtractorError(
                f"Vision request refused: {choice.message.refusal}")
        if choice.message.parsed is None:
            raise VisionExtractorError(
                "Vision response did not contain a parsed payload")

        normalized = normalize_extraction(choice.message.parsed)
        usage = response.usage
        raw_response_json = json.dumps(response.model_dump(), default=str)

        return VisionExtractionResult(
            extraction=normalized,
            raw_response_json=raw_response_json,
            prompt_tokens=getattr(usage, 'prompt_tokens', None),
            completion_tokens=getattr(usage, 'completion_tokens', None),
            total_tokens=getattr(usage, 'total_tokens', None),
        )
