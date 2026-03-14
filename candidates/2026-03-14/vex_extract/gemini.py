from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


def create_client(api_key_env: str = "GEMINI_API_KEY") -> genai.Client:
    """Create a Gemini API client from environment variable."""
    api_key = os.environ.get(api_key_env, "")
    if not api_key:
        raise ValueError(f"{api_key_env} environment variable is not set")
    return genai.Client(api_key=api_key)


async def make_request(
    client: genai.Client,
    model: str,
    system_prompt: str,
    content_parts: list[Any],
    response_schema: type | dict | None = None,
    temperature: float = 0.1,
    max_retries: int = 3,
) -> dict:
    """Make a single Gemini API call with retry and exponential backoff.

    Returns the parsed response dict and token usage.
    """
    config_kwargs: dict[str, Any] = {
        "temperature": temperature,
        "system_instruction": system_prompt,
    }
    if response_schema is not None:
        config_kwargs["response_mime_type"] = "application/json"
        config_kwargs["response_schema"] = response_schema

    generation_config = types.GenerateContentConfig(**config_kwargs)

    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model,
                contents=content_parts,
                config=generation_config,
            )

            result: dict[str, Any] = {
                "text": response.text or "",
                "input_tokens": getattr(response.usage_metadata, "prompt_token_count", 0) if response.usage_metadata else 0,
                "output_tokens": getattr(response.usage_metadata, "candidates_token_count", 0) if response.usage_metadata else 0,
            }
            return result

        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                logger.warning(
                    "Gemini request failed (attempt %d/%d): %s. Retrying in %ds...",
                    attempt + 1, max_retries, e, wait,
                )
                await asyncio.sleep(wait)

    raise RuntimeError(f"Gemini request failed after {max_retries} attempts: {last_error}")
