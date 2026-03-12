from __future__ import annotations

import asyncio
import math
import os
import time
from typing import Any

from dotenv import load_dotenv

from src.log import log
from google import genai
from google.genai import types


load_dotenv()


def create_client() -> genai.Client:
    """Create a Gemini API client from environment variable."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set")
    return genai.Client(api_key=api_key)


async def make_request(
    client: genai.Client,
    model: str,
    system_prompt: str,
    content_parts: list[Any],
    response_schema: type | None = None,
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
                log(f"  Gemini request failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {wait}s...")
                await asyncio.sleep(wait)

    raise RuntimeError(f"Gemini request failed after {max_retries} attempts: {last_error}")


def estimate_image_tokens(width: int, height: int, tokens_per_tile: int = 258) -> int:
    """Estimate Gemini image tokens using the tiling formula.

    Gemini divides images into 768x768 tiles, each costing ``tokens_per_tile``
    tokens (258 by default).  For example a 1920x1080 frame requires
    ceil(1920/768) * ceil(1080/768) = 3*2 = 6 tiles = 1548 tokens, while a
    512x512 ROI crop needs just 1 tile = 258 tokens.
    """
    tiles = math.ceil(width / 768) * math.ceil(height / 768)
    return tiles * tokens_per_tile


def estimate_tokens(frame_count: int, tokens_per_frame: int = 1548) -> int:
    """Estimate token usage for a set of frames."""
    return frame_count * tokens_per_frame
