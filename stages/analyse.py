from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

from google.genai import types

from src.gemini import create_client, estimate_tokens, make_request
from src.models import (
    AnalyseResult,
    FrameRef,
    PipelineConfig,
    RawEvent,
    SegmentAnalysisResult,
    SessionManifest,
    TriageResult,
    TriageSegment,
)
from src.prompts import fill_template, resolve_prompt
from src.video import encode_jpeg, extract_frames


# Flat response schema for Gemini structured output (avoids $defs issues)
class _GeminiEvent:
    """Schema hint — actual parsing is from JSON dict."""
    pass


_RESPONSE_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "frame_index_start": {"type": "INTEGER"},
            "frame_index_end": {"type": "INTEGER"},
            "type": {
                "type": "STRING",
                "enum": [
                    "click", "hover", "navigate", "input_text", "select",
                    "dwell", "cursor_thrash", "scroll", "drag", "hesitate",
                    "change_ui_state",
                ],
            },
            "description": {"type": "STRING"},
            "confidence": {"type": "NUMBER"},
            "interaction_target": {"type": "STRING"},
            "page_title": {"type": "STRING"},
            "page_location": {"type": "STRING"},
            "frame_description": {"type": "STRING"},
        },
        "required": ["frame_index_start", "frame_index_end", "type", "description", "confidence"],
    },
}


async def run_analyse(
    session: SessionManifest,
    config: PipelineConfig,
    triage_result: TriageResult,
    video_path: Path,
    branch: str = "",
    iteration: int = 1,
    base_dir: Path = Path("."),
) -> AnalyseResult:
    """Run analysis on all triage segments using Gemini API."""
    t0 = time.monotonic()
    client = create_client()
    ac = config.analyse
    semaphore = asyncio.Semaphore(ac.max_concurrent)

    system_prompt = resolve_prompt("system", branch, iteration, base_dir)

    tasks = []
    for segment in triage_result.segments:
        adjacent = _get_adjacent_segments(segment, triage_result.segments)
        tasks.append(
            _analyse_segment(
                client=client,
                session=session,
                config=config,
                segment=segment,
                adjacent_segments=adjacent,
                video_path=video_path,
                system_prompt=system_prompt,
                branch=branch,
                iteration=iteration,
                base_dir=base_dir,
                semaphore=semaphore,
            )
        )

    results = await asyncio.gather(*tasks)

    total_in = sum(r.input_tokens for r in results)
    total_out = sum(r.output_tokens for r in results)
    elapsed = (time.monotonic() - t0) * 1000

    return AnalyseResult(
        recording_id=session.identifier,
        segments=tuple(results),
        total_input_tokens=total_in,
        total_output_tokens=total_out,
        processing_time_ms=elapsed,
    )


def _get_adjacent_segments(
    segment: TriageSegment,
    all_segments: tuple[TriageSegment, ...],
) -> tuple[TriageSegment | None, TriageSegment | None]:
    """Get the previous and next segments adjacent to the given segment."""
    idx = segment.segment_index
    prev = next((s for s in all_segments if s.segment_index == idx - 1), None)
    nxt = next((s for s in all_segments if s.segment_index == idx + 1), None)
    return prev, nxt


def apply_token_budget(
    segment: TriageSegment,
    config: PipelineConfig,
) -> float:
    """Return the effective FPS for a segment, reduced if it exceeds token budget."""
    ac = config.analyse
    duration_sec = (segment.end_ms - segment.start_ms) / 1000
    frame_count = duration_sec * segment.assigned_fps
    estimated_tokens = estimate_tokens(int(frame_count), ac.tokens_per_frame)

    if estimated_tokens <= ac.token_budget_per_segment:
        return segment.assigned_fps

    max_frames = ac.token_budget_per_segment / ac.tokens_per_frame
    reduced_fps = max_frames / duration_sec if duration_sec > 0 else segment.assigned_fps
    return max(0.5, reduced_fps)


async def _analyse_segment(
    client: Any,
    session: SessionManifest,
    config: PipelineConfig,
    segment: TriageSegment,
    adjacent_segments: tuple[TriageSegment | None, TriageSegment | None],
    video_path: Path,
    system_prompt: str,
    branch: str,
    iteration: int,
    base_dir: Path,
    semaphore: asyncio.Semaphore,
) -> SegmentAnalysisResult:
    """Analyse a single segment: extract frames, call Gemini, parse response."""
    async with semaphore:
        ac = config.analyse
        effective_fps = apply_token_budget(segment, config)

        # Extract primary frames
        start_sec = segment.start_ms / 1000
        end_sec = segment.end_ms / 1000
        primary_frames = extract_frames(video_path, start_sec, end_sec, effective_fps)

        # Build frame refs and collect context frames
        frame_refs: list[FrameRef] = []
        all_frames: list[tuple[float, Any]] = []

        prev_seg, next_seg = adjacent_segments

        # Context frames from previous segment
        context_before: list[tuple[float, Any]] = []
        if prev_seg is not None and ac.context_frames > 0:
            prev_end_sec = prev_seg.end_ms / 1000
            prev_start_sec = max(prev_seg.start_ms / 1000, prev_end_sec - (ac.context_frames / effective_fps))
            context_before = list(extract_frames(video_path, prev_start_sec, prev_end_sec, effective_fps))
            context_before = context_before[-ac.context_frames:]

        # Context frames from next segment
        context_after: list[tuple[float, Any]] = []
        if next_seg is not None and ac.context_frames > 0:
            next_start_sec = next_seg.start_ms / 1000
            next_end_sec = min(next_seg.end_ms / 1000, next_start_sec + (ac.context_frames / effective_fps))
            context_after = list(extract_frames(video_path, next_start_sec, next_end_sec, effective_fps))
            context_after = context_after[:ac.context_frames]

        # Assemble all frames with refs
        idx = 0
        for ts, frame in context_before:
            frame_refs.append(FrameRef(frame_index_in_request=idx, timestamp_ms=ts, is_context=True))
            all_frames.append((ts, frame))
            idx += 1

        for ts, frame in primary_frames:
            frame_refs.append(FrameRef(frame_index_in_request=idx, timestamp_ms=ts, is_context=False))
            all_frames.append((ts, frame))
            idx += 1

        for ts, frame in context_after:
            frame_refs.append(FrameRef(frame_index_in_request=idx, timestamp_ms=ts, is_context=True))
            all_frames.append((ts, frame))
            idx += 1

        if not all_frames:
            return SegmentAnalysisResult(
                segment_index=segment.segment_index,
                events=(),
                frame_refs=tuple(frame_refs),
            )

        # Choose prompt variant
        prompt_name = "idle" if segment.tier == "idle" else "user"
        try:
            user_template = resolve_prompt(prompt_name, branch, iteration, base_dir)
        except FileNotFoundError:
            user_template = resolve_prompt("user", branch, iteration, base_dir)

        context_note = ""
        if context_before:
            context_note += f"Frames 0-{len(context_before) - 1} are CONTEXT frames from the previous segment. "
        if context_after:
            after_start = len(context_before) + len(primary_frames)
            context_note += f"Frames {after_start}-{after_start + len(context_after) - 1} are CONTEXT frames from the next segment. "
        if context_note:
            context_note += "Do NOT report events from context frames."

        user_prompt = fill_template(user_template, {
            "segment_index": segment.segment_index,
            "start_time": f"{segment.start_ms / 1000:.1f}s",
            "end_time": f"{segment.end_ms / 1000:.1f}s",
            "fps": effective_fps,
            "tier": segment.tier,
            "frame_count": len(all_frames),
            "context_note": context_note,
        })

        # Build content parts: interleaved frame labels + images
        content_parts: list[Any] = []
        for ref, (ts, frame) in zip(frame_refs, all_frames):
            label = f"[Frame {ref.frame_index_in_request} | {ts:.0f}ms"
            if ref.is_context:
                label += " | CONTEXT"
            label += "]"
            content_parts.append(label)
            jpeg_bytes = encode_jpeg(frame, ac.jpeg_quality)
            content_parts.append(types.Part.from_bytes(data=jpeg_bytes, mime_type="image/jpeg"))

        content_parts.append(user_prompt)

        # Call Gemini
        print(f"  Analysing segment {segment.segment_index} ({segment.tier}, {len(all_frames)} frames, {effective_fps:.1f} fps)...")

        response = await make_request(
            client=client,
            model=ac.model,
            system_prompt=system_prompt,
            content_parts=content_parts,
            response_schema=_RESPONSE_SCHEMA,
            temperature=ac.temperature,
        )

        # Parse events
        events = _parse_events(response["text"])

        return SegmentAnalysisResult(
            segment_index=segment.segment_index,
            events=events,
            frame_refs=tuple(frame_refs),
            input_tokens=response.get("input_tokens", 0),
            output_tokens=response.get("output_tokens", 0),
        )


def _parse_events(response_text: str) -> tuple[RawEvent, ...]:
    """Parse Gemini JSON response into RawEvent models."""
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        print(f"  Warning: Failed to parse Gemini response as JSON")
        return ()

    if not isinstance(data, list):
        data = [data]

    events: list[RawEvent] = []
    for item in data:
        try:
            events.append(RawEvent(
                frame_index_start=item.get("frame_index_start", 0),
                frame_index_end=item.get("frame_index_end", 0),
                type=item["type"],
                description=item["description"],
                confidence=item.get("confidence", 0.5),
                interaction_target=item.get("interaction_target"),
                page_title=item.get("page_title"),
                page_location=item.get("page_location"),
                frame_description=item.get("frame_description"),
            ))
        except (KeyError, ValueError) as e:
            print(f"  Warning: Skipping malformed event: {e}")

    return tuple(events)
