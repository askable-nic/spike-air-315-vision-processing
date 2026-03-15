from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from google.genai import types

from vex_extract.config import AppConfig
from vex_extract.cv_summary import generate_cursor_summary, generate_flow_summary
from vex_extract.gemini import make_request
from vex_extract.models import CursorDetection, FlowWindow, VideoSegment

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt section templates — injected conditionally by render_prompt
# ---------------------------------------------------------------------------

_CURSOR_SECTION = """\
## Cursor Tracking Data

The following cursor position data was extracted from this video segment via template matching. Each line describes a time span where the cursor was stationary at a position, moved in a straight line between two positions, or was not detected. Coordinates are in pixels from the top-left of the video frame.

Use this data to:
- Confirm cursor positions when reporting click, hover, and drag events
- Identify dwell patterns where the cursor holds position over interactive elements
- Detect cursor movement trajectories that may be subtle in the video
- Notice rapid back-and-forth movement suggesting cursor thrash

The video is always ground truth — if cursor data conflicts with what you see, trust the video. Short "not-detected" gaps between stationary spans at the same position are tracker noise, not the cursor disappearing.

```
{cursor_summary}
```"""

_FLOW_SECTION = """\
## Optical Flow Data

The following scroll/pan data was extracted from this video segment using optical flow analysis. Each line describes a time span where significant uniform motion was detected across the viewport, indicating the user was scrolling. Magnitude reflects scroll speed (higher = faster).

Use this data to:
- Detect scroll events that may be subtle or fast in the video
- Determine scroll direction and duration precisely
- Distinguish user-initiated scrolling from static periods

```
{flow_summary}
```"""

_CV_USAGE_BOTH = """\
Use the cursor tracking and optical flow data above to:
- Confirm cursor positions when reporting hover, click, and drag events
- Detect scroll events that may be subtle in the video — the flow data gives precise scroll direction and timing
- Identify hover/dwell patterns where the cursor stays stationary over interactive elements
- Notice cursor thrash patterns from rapid movement in the cursor data
"""

_CV_USAGE_CURSOR_ONLY = """\
Use the cursor tracking data above to:
- Confirm cursor positions when reporting hover, click, and drag events
- Identify hover/dwell patterns where the cursor stays stationary over interactive elements
- Notice cursor thrash patterns from rapid movement in the cursor data
"""

_CV_USAGE_FLOW_ONLY = """\
Use the optical flow data above to:
- Detect scroll events that may be subtle in the video — the flow data gives precise scroll direction and timing
- Distinguish user-initiated scrolling from static periods
"""

_FIRST_SEGMENT_SECTION = """\
### Initial screen state

This is the **first segment** of the recording. You must return a `change_ui_state` event at `time_start_ms: 0` and `time_end_ms: 0` describing the initial screen state visible in roughly the first second of video. Use the first second rather than the very first frame, as the opening frame is often more compressed while the screen-sharing connection stabilises. Describe what application or page is shown, the overall layout, and any notable UI elements visible.

"""


_VIDEO_ANALYSIS_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "type": {"type": "STRING"},
            "time_start_ms": {"type": "NUMBER"},
            "time_end_ms": {"type": "NUMBER"},
            "description": {"type": "STRING"},
            "confidence": {"type": "NUMBER"},
            "interaction_target": {"type": "STRING"},
            "page_title": {"type": "STRING"},
            "page_location": {"type": "STRING"},
            "frame_description": {"type": "STRING"},
        },
        "required": ["type", "time_start_ms", "time_end_ms", "description", "confidence"],
    },
}


def render_prompt(
    template: str,
    segment: VideoSegment,
    total_segments: int,
    cursor_summary: str | None,
    flow_summary: str | None,
    video_fps: int,
) -> str:
    """Fill placeholder variables in the prompt template.

    CV sections are included only when their summary is not None.
    """
    # Build conditional CV blocks
    cv_parts: list[str] = []
    if cursor_summary is not None:
        cv_parts.append(_CURSOR_SECTION.replace("{cursor_summary}", cursor_summary))
    if flow_summary is not None:
        cv_parts.append(_FLOW_SECTION.replace("{flow_summary}", flow_summary))
    cv_sections = "\n\n".join(cv_parts) + "\n" if cv_parts else ""

    has_cursor = cursor_summary is not None
    has_flow = flow_summary is not None
    if has_cursor and has_flow:
        cv_usage = _CV_USAGE_BOTH
    elif has_cursor:
        cv_usage = _CV_USAGE_CURSOR_ONLY
    elif has_flow:
        cv_usage = _CV_USAGE_FLOW_ONLY
    else:
        cv_usage = ""

    first_segment_section = _FIRST_SEGMENT_SECTION if segment.index == 0 else ""

    result = template
    variables = {
        "segment_index": segment.index + 1,
        "total_segments": total_segments,
        "segment_start_ms": int(segment.start_ms),
        "segment_end_ms": int(segment.end_ms),
        "video_fps": video_fps,
        "cv_sections": cv_sections,
        "cv_usage_instructions": cv_usage,
        "first_segment_section": first_segment_section,
    }
    for key, value in variables.items():
        result = result.replace(f"{{{key}}}", str(value))
    return result


class PreparedSegment:
    """Prompt and CV summaries rendered for a single segment, ready for Gemini."""

    __slots__ = ("segment", "rendered_prompt", "cursor_summary", "flow_summary", "output_dir")

    def __init__(
        self,
        segment: VideoSegment,
        rendered_prompt: str,
        cursor_summary: str | None,
        flow_summary: str | None,
        output_dir: Path,
    ) -> None:
        self.segment = segment
        self.rendered_prompt = rendered_prompt
        self.cursor_summary = cursor_summary
        self.flow_summary = flow_summary
        self.output_dir = output_dir


def prepare_all_prompts(
    segments: tuple[VideoSegment, ...],
    cursor_trajectory: tuple[CursorDetection, ...],
    flow_windows: tuple[FlowWindow, ...],
    prompt_template: str,
    config: AppConfig,
    run_dir: Path,
) -> tuple[PreparedSegment, ...]:
    """Render prompts and save artifacts for every segment. No API calls."""
    prepared: list[PreparedSegment] = []

    for segment in segments:
        cursor_text = generate_cursor_summary(cursor_trajectory, segment) if cursor_trajectory else None
        flow_text = generate_flow_summary(flow_windows, segment) if flow_windows else None
        # Empty summary (e.g. no significant flow in this segment) → omit the section
        cursor_text = cursor_text or None
        flow_text = flow_text or None
        rendered = render_prompt(
            template=prompt_template,
            segment=segment,
            total_segments=len(segments),
            cursor_summary=cursor_text,
            flow_summary=flow_text,
            video_fps=config.video.video_fps,
        )

        output_dir = run_dir / "segments" / f"segment_{segment.index:03d}"
        output_dir.mkdir(parents=True, exist_ok=True)

        cv_summary_lines = (
            (len(cursor_text.splitlines()) if cursor_text else 0)
            + (len(flow_text.splitlines()) if flow_text else 0)
        )
        request_record = {
            "model": config.gemini.model,
            "temperature": config.gemini.temperature,
            "video_fps": config.video.video_fps,
            "video_metadata": {"fps": float(config.video.video_fps)},
            "video_mime_type": "video/mp4",
            "video_bytes_size": segment.path.stat().st_size if segment.path.exists() else 0,
            "segment_index": segment.index,
            "segment_start_ms": segment.start_ms,
            "segment_end_ms": segment.end_ms,
            "cv_summary_lines": cv_summary_lines,
            "response_mime_type": "application/json",
            "response_schema": _VIDEO_ANALYSIS_SCHEMA,
            "system_prompt_length": len(rendered),
        }
        (output_dir / "request.json").write_text(json.dumps(request_record, indent=2))
        (output_dir / "prompt.txt").write_text(rendered)
        if cursor_text is not None:
            (output_dir / "cursor_summary.txt").write_text(cursor_text)
        if flow_text is not None:
            (output_dir / "flow_summary.txt").write_text(flow_text)

        logger.info("Segment %d: prompt prepared (%d chars)", segment.index, len(rendered))
        prepared.append(PreparedSegment(segment, rendered, cursor_text, flow_text, output_dir))

    return tuple(prepared)


async def _analyse_one(
    client: Any,
    prep: PreparedSegment,
    config: AppConfig,
    semaphore: asyncio.Semaphore,
) -> tuple[VideoSegment, list[dict], dict]:
    """Send a single prepared segment to Gemini and save the response."""
    async with semaphore:
        logger.info("Segment %d: sending to Gemini...", prep.segment.index)
        video_bytes = prep.segment.path.read_bytes()
        video_part = types.Part(
            inline_data=types.Blob(data=video_bytes, mime_type="video/mp4"),
            video_metadata=types.VideoMetadata(fps=float(config.video.video_fps)),
        )

        result = await make_request(
            client=client,
            model=config.gemini.model,
            system_prompt=prep.rendered_prompt,
            content_parts=[video_part],
            response_schema=_VIDEO_ANALYSIS_SCHEMA,
            temperature=config.gemini.temperature,
        )

        raw_events = json.loads(result["text"]) if result["text"] else []
        token_usage = {
            "input_tokens": result["input_tokens"],
            "output_tokens": result["output_tokens"],
        }

        (prep.output_dir / "response.json").write_text(json.dumps(result, indent=2))

        logger.info(
            "Segment %d: %d events, %s in / %s out tokens",
            prep.segment.index, len(raw_events),
            f"{result['input_tokens']:,}", f"{result['output_tokens']:,}",
        )

        return prep.segment, raw_events, token_usage


async def analyse_all_segments(
    client: Any,
    prepared: tuple[PreparedSegment, ...],
    config: AppConfig,
) -> list[tuple[VideoSegment, list[dict], dict]]:
    """Send all prepared segments to Gemini concurrently."""
    semaphore = asyncio.Semaphore(config.gemini.max_concurrent)

    async def _safe(prep: PreparedSegment) -> tuple[VideoSegment, list[dict], dict]:
        try:
            return await _analyse_one(client, prep, config, semaphore)
        except Exception as e:
            logger.error("Segment %d failed: %s", prep.segment.index, e)
            prep.output_dir.mkdir(parents=True, exist_ok=True)
            (prep.output_dir / "error.txt").write_text(str(e))
            return prep.segment, [], {"input_tokens": 0, "output_tokens": 0, "error": str(e)}

    tasks = [_safe(p) for p in prepared]
    results = await asyncio.gather(*tasks)
    return list(results)
