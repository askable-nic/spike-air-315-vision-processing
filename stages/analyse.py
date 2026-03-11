from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

from google.genai import types

from src.gemini import create_client, estimate_tokens, make_request
from src.log import log
from src.models import (
    AnalyseConfig,
    AnalyseResult,
    FrameRef,
    ObserveResult,
    PipelineConfig,
    RawEvent,
    SegmentAnalysisResult,
    SelectedFrame,
    SessionManifest,
    TriageResult,
    TriageSegment,
)
from src.prompts import fill_template, resolve_prompt
from src.video import crop_frame, encode_jpeg, extract_frames, extract_frames_at_timestamps


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
    output_dir: Path | None = None,
    observe_result: ObserveResult | None = None,
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
                output_dir=output_dir,
                observe_result=observe_result,
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
    output_dir: Path | None = None,
    observe_result: ObserveResult | None = None,
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

        # ROI cropping when observe_result has ROI rects
        roi_by_ts: dict[float, Any] = {}
        if observe_result is not None and observe_result.roi_rects:
            from stages.observe import _lookup_cursor_at_timestamp
            for roi in observe_result.roi_rects:
                roi_by_ts[roi.timestamp_ms] = roi

        # Save frame JPEGs as debug artifacts
        segment_frames_dir = None
        if output_dir is not None:
            segment_frames_dir = output_dir / session.identifier / "frames" / f"segment_{segment.segment_index:03d}"
            segment_frames_dir.mkdir(parents=True, exist_ok=True)

        jpeg_cache: list[bytes] = []
        cursor_labels: dict[int, str] = {}
        for ref, (ts, frame) in zip(frame_refs, all_frames):
            frame_to_encode = frame

            # Apply ROI crop if available (find nearest ROI within 200ms)
            if roi_by_ts and not ref.is_context:
                nearest_roi = None
                best_dist = 200.0
                for roi_ts, roi in roi_by_ts.items():
                    dist = abs(roi_ts - ts)
                    if dist < best_dist:
                        nearest_roi = roi
                        best_dist = dist

                if nearest_roi is not None:
                    frame_to_encode = crop_frame(
                        frame, nearest_roi.x, nearest_roi.y, nearest_roi.width, nearest_roi.height,
                    )
                    cursor_labels[ref.frame_index_in_request] = (
                        f"cursor at ({nearest_roi.cursor_x:.0f}, {nearest_roi.cursor_y:.0f})"
                    )

            # Add cursor label from observe trajectory even without ROI
            if ref.frame_index_in_request not in cursor_labels and observe_result is not None:
                from stages.observe import _lookup_cursor_at_timestamp
                detection = _lookup_cursor_at_timestamp(observe_result.cursor_trajectory, ts)
                if detection is not None:
                    cursor_labels[ref.frame_index_in_request] = (
                        f"cursor at ({detection.x:.0f}, {detection.y:.0f})"
                    )

            jpeg_bytes = encode_jpeg(frame_to_encode, ac.jpeg_quality)
            jpeg_cache.append(jpeg_bytes)

            if segment_frames_dir is not None:
                suffix = "_ctx" if ref.is_context else ""
                filename = f"frame_{ref.frame_index_in_request:03d}_{int(ts)}ms{suffix}.jpg"
                (segment_frames_dir / filename).write_bytes(jpeg_bytes)

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

        # Format local events for prompt injection
        local_events_text = ""
        if observe_result is not None and observe_result.local_events:
            from stages.observe import format_local_events_for_prompt
            local_events_text = format_local_events_for_prompt(
                observe_result.local_events, segment.start_ms, segment.end_ms,
            )

        user_prompt = fill_template(user_template, {
            "segment_index": segment.segment_index,
            "start_time": f"{segment.start_ms / 1000:.1f}s",
            "end_time": f"{segment.end_ms / 1000:.1f}s",
            "fps": effective_fps,
            "tier": segment.tier,
            "frame_count": len(all_frames),
            "context_note": context_note,
            "local_events": local_events_text,
        })

        # Save prompt as debug artifact
        if segment_frames_dir is not None:
            (segment_frames_dir / "prompt.txt").write_text(user_prompt)

        # Build content parts: interleaved frame labels + images
        content_parts: list[Any] = []
        for ref, jpeg_bytes in zip(frame_refs, jpeg_cache):
            ts = ref.timestamp_ms
            label = f"[Frame {ref.frame_index_in_request} | {ts:.0f}ms"
            if ref.is_context:
                label += " | CONTEXT"
            cursor_info = cursor_labels.get(ref.frame_index_in_request)
            if cursor_info:
                label += f" | {cursor_info}"
            label += "]"
            content_parts.append(label)
            content_parts.append(types.Part.from_bytes(data=jpeg_bytes, mime_type="image/jpeg"))

        content_parts.append(user_prompt)

        # Call Gemini
        log(f"  Analysing segment {segment.segment_index} ({segment.tier}, {len(all_frames)} frames, {effective_fps:.1f} fps)...")

        response = await make_request(
            client=client,
            model=ac.model,
            system_prompt=system_prompt,
            content_parts=content_parts,
            response_schema=_RESPONSE_SCHEMA,
            temperature=ac.temperature,
        )

        # Save raw response as debug artifact
        if segment_frames_dir is not None:
            (segment_frames_dir / "response.json").write_text(response["text"])

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
        log(f"  Warning: Failed to parse Gemini response as JSON")
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
            log(f"  Warning: Skipping malformed event: {e}")

    return tuple(events)


# ---------------------------------------------------------------------------
# Observe-driven analyse path
# ---------------------------------------------------------------------------

def _batch_selected_frames(
    selected_frames: tuple[SelectedFrame, ...],
    ac: AnalyseConfig,
) -> tuple[tuple[SelectedFrame, ...], ...]:
    """Group selected frames into LLM request batches by time proximity.

    New batch when gap from previous frame > batch_gap_ms, or when estimated
    tokens for the batch would exceed token_budget_per_segment.
    """
    if not selected_frames:
        return ()

    sorted_frames = tuple(sorted(selected_frames, key=lambda f: f.timestamp_ms))
    max_frames_per_batch = ac.token_budget_per_segment // ac.tokens_per_frame

    batches: list[list[SelectedFrame]] = [[sorted_frames[0]]]

    for frame in sorted_frames[1:]:
        current_batch = batches[-1]
        gap = frame.timestamp_ms - current_batch[-1].timestamp_ms
        if gap > ac.batch_gap_ms or len(current_batch) >= max_frames_per_batch:
            batches.append([frame])
        else:
            current_batch.append(frame)

    return tuple(tuple(b) for b in batches)


async def run_analyse_from_observe(
    session: SessionManifest,
    config: PipelineConfig,
    video_path: Path,
    observe_result: ObserveResult,
    branch: str = "",
    iteration: int = 1,
    base_dir: Path = Path("."),
    output_dir: Path | None = None,
) -> AnalyseResult:
    """Run analysis driven by observe-selected frames instead of triage segments."""
    t0 = time.monotonic()
    client = create_client()
    ac = config.analyse
    semaphore = asyncio.Semaphore(ac.max_concurrent)

    system_prompt = resolve_prompt("system", branch, iteration, base_dir)

    batches = _batch_selected_frames(observe_result.selected_frames, ac)
    log(f"  Analyse (observe-driven): {len(batches)} batches from {len(observe_result.selected_frames)} selected frames")

    tasks = [
        _analyse_observe_batch(
            client=client,
            session=session,
            config=config,
            batch=batch,
            batch_index=batch_idx,
            video_path=video_path,
            system_prompt=system_prompt,
            observe_result=observe_result,
            branch=branch,
            iteration=iteration,
            base_dir=base_dir,
            semaphore=semaphore,
            output_dir=output_dir,
        )
        for batch_idx, batch in enumerate(batches)
    ]

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


async def _analyse_observe_batch(
    client: Any,
    session: SessionManifest,
    config: PipelineConfig,
    batch: tuple[SelectedFrame, ...],
    batch_index: int,
    video_path: Path,
    system_prompt: str,
    observe_result: ObserveResult,
    branch: str,
    iteration: int,
    base_dir: Path,
    semaphore: asyncio.Semaphore,
    output_dir: Path | None = None,
) -> SegmentAnalysisResult:
    """Analyse a single batch of observe-selected frames."""
    async with semaphore:
        ac = config.analyse
        timestamps_ms = tuple(f.timestamp_ms for f in batch)

        # Extract full frames at the selected timestamps
        extracted = extract_frames_at_timestamps(video_path, timestamps_ms)
        frame_by_ts: dict[float, Any] = {}
        for ts, frame in extracted:
            frame_by_ts[ts] = frame

        # Build frame refs and encode
        frame_refs: list[FrameRef] = []
        jpeg_cache: list[bytes] = []
        frame_annotations: list[str] = []

        segment_frames_dir = None
        if output_dir is not None:
            segment_frames_dir = output_dir / session.identifier / "frames" / f"batch_{batch_index:03d}"
            segment_frames_dir.mkdir(parents=True, exist_ok=True)

        for idx, sel_frame in enumerate(batch):
            raw_frame = frame_by_ts.get(sel_frame.timestamp_ms)
            if raw_frame is None:
                continue

            frame_to_encode = raw_frame

            # Apply ROI crop if specified
            if sel_frame.roi is not None:
                frame_to_encode = crop_frame(
                    raw_frame,
                    sel_frame.roi.x, sel_frame.roi.y,
                    sel_frame.roi.width, sel_frame.roi.height,
                )

            frame_refs.append(FrameRef(
                frame_index_in_request=idx,
                timestamp_ms=sel_frame.timestamp_ms,
                is_context=False,
            ))

            jpeg_bytes = encode_jpeg(frame_to_encode, ac.jpeg_quality)
            jpeg_cache.append(jpeg_bytes)

            # Build annotation label
            label_parts = [
                f"[Frame {idx}",
                f"{sel_frame.timestamp_ms:.0f}ms",
                sel_frame.reason.replace("_", " "),
            ]
            if sel_frame.roi is not None:
                label_parts.append(f"cursor at ({sel_frame.roi.cursor_x:.0f}, {sel_frame.roi.cursor_y:.0f})")
            label = " | ".join(label_parts) + "]"
            frame_annotations.append(label)

            if segment_frames_dir is not None:
                filename = f"frame_{idx:03d}_{int(sel_frame.timestamp_ms)}ms_{sel_frame.reason}.jpg"
                (segment_frames_dir / filename).write_bytes(jpeg_bytes)

        if not frame_refs:
            return SegmentAnalysisResult(
                segment_index=batch_index,
                events=(),
                frame_refs=(),
            )

        start_time = batch[0].timestamp_ms
        end_time = batch[-1].timestamp_ms

        # Format local events for the batch time range
        from stages.observe import format_local_events_for_prompt
        local_events_text = format_local_events_for_prompt(
            observe_result.local_events, start_time, end_time,
        )

        # Build prompt
        try:
            user_template = resolve_prompt("observe_driven", branch, iteration, base_dir)
        except FileNotFoundError:
            user_template = resolve_prompt("user", branch, iteration, base_dir)

        user_prompt = fill_template(user_template, {
            "batch_index": batch_index,
            "start_time": f"{start_time / 1000:.1f}s",
            "end_time": f"{end_time / 1000:.1f}s",
            "frame_count": len(frame_refs),
            "frame_annotations": "\n".join(frame_annotations),
            "local_events": local_events_text,
        })

        if segment_frames_dir is not None:
            (segment_frames_dir / "prompt.txt").write_text(user_prompt)

        # Build content parts
        content_parts: list[Any] = []
        for label, jpeg_bytes in zip(frame_annotations, jpeg_cache):
            content_parts.append(label)
            content_parts.append(types.Part.from_bytes(data=jpeg_bytes, mime_type="image/jpeg"))
        content_parts.append(user_prompt)

        log(f"  Analysing batch {batch_index} ({len(frame_refs)} frames, {start_time:.0f}-{end_time:.0f}ms)...")

        response = await make_request(
            client=client,
            model=ac.model,
            system_prompt=system_prompt,
            content_parts=content_parts,
            response_schema=_RESPONSE_SCHEMA,
            temperature=ac.temperature,
        )

        if segment_frames_dir is not None:
            (segment_frames_dir / "response.json").write_text(response["text"])

        events = _parse_events(response["text"])

        return SegmentAnalysisResult(
            segment_index=batch_index,
            events=events,
            frame_refs=tuple(frame_refs),
            input_tokens=response.get("input_tokens", 0),
            output_tokens=response.get("output_tokens", 0),
        )
