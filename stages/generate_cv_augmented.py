from __future__ import annotations

import asyncio
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from google.genai import types

from src.gemini import create_client, make_request
from src.log import log
from src.models import (
    CursorDetection,
    CvAugmentedConfig,
    FlowWindow,
    ObserveConfig,
    ResolvedEvent,
    SessionManifest,
    VideoSegment,
)
from src.prompts import fill_template
from src.video import get_video_metadata
from stages.generate_baselines import (
    _VIDEO_ANALYSIS_SCHEMA,
    _estimate_tokens,
    adjust_timestamps,
    compute_segments,
    deduplicate_overlap_events,
    extract_segment,
)
from stages.merge import deduplicate_events
from stages.observe import compute_flow_summaries, track_cursor


# ---------------------------------------------------------------------------
# CV analysis: thin wrapper over observe.py functions
# ---------------------------------------------------------------------------

def _build_observe_config(config: CvAugmentedConfig) -> ObserveConfig:
    """Build an ObserveConfig from CvAugmentedConfig fields for cursor/flow calls."""
    return ObserveConfig(
        enabled=True,
        tracking_base_fps=config.tracking_base_fps,
        tracking_peak_fps=config.tracking_peak_fps,
        tracking_displacement_threshold_px=config.tracking_displacement_threshold_px,
        tracking_active_padding_ms=config.tracking_active_padding_ms,
        resolution_height=config.resolution_height,
        template_scales=config.template_scales,
        match_threshold=config.match_threshold,
        early_exit_threshold=config.early_exit_threshold,
        max_interpolation_gap_ms=config.max_interpolation_gap_ms,
        smooth_window=config.smooth_window,
        smooth_displacement_threshold=config.smooth_displacement_threshold,
        flow_fps=config.flow_fps,
        flow_grid_step=config.flow_grid_step,
        flow_window_size_ms=config.flow_window_size_ms,
        flow_window_step_ms=config.flow_window_step_ms,
    )


def run_cv_analysis(
    video_path: Path,
    config: CvAugmentedConfig,
    base_dir: Path,
    duration_ms: float,
) -> tuple[tuple[CursorDetection, ...], tuple[FlowWindow, ...]]:
    """Run cursor tracking and optical flow analysis on the full video."""
    oc = _build_observe_config(config)

    log("  CV: running cursor tracking...")
    cursor_trajectory = track_cursor(
        video_path=video_path,
        triage_result=None,
        oc=oc,
        base_dir=base_dir,
        total_duration_ms=duration_ms,
    )
    log(f"  CV: {len(cursor_trajectory)} cursor detections "
        f"({sum(1 for d in cursor_trajectory if d.detected)} detected)")

    log("  CV: computing optical flow summaries...")
    flow_windows = compute_flow_summaries(
        video_path=video_path,
        triage_result=None,
        cursor_trajectory=cursor_trajectory,
        oc=oc,
        total_duration_ms=duration_ms,
    )
    log(f"  CV: {len(flow_windows)} flow windows")

    return cursor_trajectory, flow_windows


# ---------------------------------------------------------------------------
# CV summary generation
# ---------------------------------------------------------------------------

def _classify_cursor_activity(
    detections: tuple[CursorDetection, ...],
    radius_px: float = 15.0,
) -> str:
    """Classify cursor activity within a time window."""
    if not detections:
        return "not-detected"

    detected = tuple(d for d in detections if d.detected or d.confidence > 0)
    if not detected:
        return "not-detected"

    if len(detected) == 1:
        return "stationary"

    # Check displacement
    xs = tuple(d.x for d in detected)
    ys = tuple(d.y for d in detected)
    dx = max(xs) - min(xs)
    dy = max(ys) - min(ys)
    displacement = math.sqrt(dx * dx + dy * dy)

    if displacement <= radius_px:
        return "stationary"

    return "moving"


def _find_scroll_annotation(
    flow_windows: tuple[FlowWindow, ...],
    window_start_ms: float,
    window_end_ms: float,
    min_magnitude: float = 3.0,
    min_uniformity: float = 0.6,
) -> str | None:
    """Check if there's a scroll-like flow pattern in a time window."""
    relevant = tuple(
        fw for fw in flow_windows
        if fw.start_ms < window_end_ms and fw.end_ms > window_start_ms
    )
    if not relevant:
        return None

    for fw in relevant:
        if fw.mean_flow_magnitude >= min_magnitude and fw.flow_uniformity >= min_uniformity:
            direction = fw.dominant_direction
            if direction in ("N", "NE", "NW"):
                return "scroll-up"
            elif direction in ("S", "SE", "SW"):
                return "scroll-down"
            elif direction == "E":
                return "scroll-right"
            elif direction == "W":
                return "scroll-left"
    return None


def generate_cv_summary(
    cursor_trajectory: tuple[CursorDetection, ...],
    flow_windows: tuple[FlowWindow, ...],
    segment: VideoSegment,
    summary_window_ms: int = 250,
) -> str:
    """Convert raw CV data for a segment time range into a text summary.

    Divides the segment into windows, classifies cursor activity, adds scroll
    annotations from flow data, and merges consecutive identical windows.
    """
    seg_start = segment.start_ms
    seg_end = segment.end_ms
    duration = seg_end - seg_start

    n_windows = max(1, int(math.ceil(duration / summary_window_ms)))
    raw_lines: list[tuple[float, float, str, str | None, float | None, float | None]] = []

    for i in range(n_windows):
        w_start = seg_start + i * summary_window_ms
        w_end = min(seg_start + (i + 1) * summary_window_ms, seg_end)

        # Get cursor detections in this window
        window_detections = tuple(
            d for d in cursor_trajectory
            if w_start <= d.timestamp_ms < w_end
        )

        activity = _classify_cursor_activity(window_detections)
        scroll = _find_scroll_annotation(flow_windows, w_start, w_end)

        # Get representative cursor position
        detected_in_window = tuple(
            d for d in window_detections if d.detected or d.confidence > 0
        )
        cursor_x: float | None = None
        cursor_y: float | None = None
        if detected_in_window:
            mid = detected_in_window[len(detected_in_window) // 2]
            cursor_x = round(mid.x, 1)
            cursor_y = round(mid.y, 1)

        raw_lines.append((w_start - seg_start, w_end - seg_start, activity, scroll, cursor_x, cursor_y))

    # Merge consecutive identical windows
    merged_lines: list[str] = []
    i = 0
    while i < len(raw_lines):
        start_ms, _, activity, scroll, cx, cy = raw_lines[i]
        end_ms = raw_lines[i][1]

        # Merge while next window has same activity and scroll
        while (i + 1 < len(raw_lines)
               and raw_lines[i + 1][2] == activity
               and raw_lines[i + 1][3] == scroll):
            i += 1
            end_ms = raw_lines[i][1]
            # Update cursor position to latest
            if raw_lines[i][4] is not None:
                cx = raw_lines[i][4]
                cy = raw_lines[i][5]

        parts = [f"{int(start_ms)}-{int(end_ms)}ms: cursor={activity}"]
        if cx is not None and cy is not None:
            parts.append(f"pos=({cx},{cy})")
        if scroll is not None:
            parts.append(scroll)

        merged_lines.append(" ".join(parts))
        i += 1

    return "\n".join(merged_lines)


# ---------------------------------------------------------------------------
# Segment analysis with CV context
# ---------------------------------------------------------------------------

async def analyse_segment_with_cv(
    client: Any,
    segment: VideoSegment,
    cv_summary: str,
    config: CvAugmentedConfig,
    system_prompt: str,
    semaphore: asyncio.Semaphore,
    force: bool = False,
) -> tuple[list[dict], dict]:
    """Analyse a video segment with Gemini, prepending CV summary as text context."""
    segment_dir = segment.path.parent
    cached_response = segment_dir / "response.json"
    cached_events = segment_dir / "events.json"

    if not force and cached_response.exists() and cached_events.exists():
        result = json.loads(cached_response.read_text())
        raw_events = json.loads(cached_events.read_text())
        token_usage = {
            "input_tokens": result.get("input_tokens", 0),
            "output_tokens": result.get("output_tokens", 0),
        }
        log(f"  Segment {segment.index}: {len(raw_events)} events (cached)")
        return raw_events, token_usage

    async with semaphore:
        log(f"  Segment {segment.index}: sending to Gemini (with CV context)...")
        video_bytes = segment.path.read_bytes()
        video_part = types.Part(
            inline_data=types.Blob(data=video_bytes, mime_type="video/mp4"),
            video_metadata=types.VideoMetadata(fps=float(config.video_fps)),
        )

        result = await make_request(
            client=client,
            model=config.model,
            system_prompt=system_prompt,
            content_parts=[video_part],
            response_schema=_VIDEO_ANALYSIS_SCHEMA,
            temperature=config.temperature,
        )

        raw_events = json.loads(result["text"]) if result["text"] else []
        token_usage = {
            "input_tokens": result["input_tokens"],
            "output_tokens": result["output_tokens"],
        }

        # Save artifacts
        request_record = {
            "model": config.model,
            "temperature": config.temperature,
            "video_fps": config.video_fps,
            "video_metadata": {"fps": float(config.video_fps)},
            "video_mime_type": "video/mp4",
            "video_bytes_size": len(video_bytes),
            "segment_index": segment.index,
            "segment_start_ms": segment.start_ms,
            "segment_end_ms": segment.end_ms,
            "cv_summary_lines": len(cv_summary.splitlines()),
            "response_mime_type": "application/json",
            "response_schema": _VIDEO_ANALYSIS_SCHEMA,
            "system_prompt_length": len(system_prompt),
        }
        (segment_dir / "request.json").write_text(json.dumps(request_record, indent=2))
        (segment_dir / "prompt.txt").write_text(system_prompt)
        (segment_dir / "cv_summary.txt").write_text(cv_summary)
        (segment_dir / "response.json").write_text(json.dumps(result, indent=2))
        (segment_dir / "events.json").write_text(json.dumps(raw_events, indent=2))

        log(f"  Segment {segment.index}: {len(raw_events)} events, "
            f"{result['input_tokens']:,} in / {result['output_tokens']:,} out tokens")

        return raw_events, token_usage


# ---------------------------------------------------------------------------
# Session orchestrator
# ---------------------------------------------------------------------------

async def generate_session_cv_augmented(
    session_manifest: SessionManifest,
    video_path: Path,
    config: CvAugmentedConfig,
    prompt_template: str,
    base_dir: Path,
    output_dir: Path,
    dry_run: bool = False,
    force: bool = False,
) -> dict | None:
    """Generate CV-augmented event extraction for a single session.

    Returns run metadata dict, or None if skipped.
    """
    session_id = session_manifest.identifier
    session_output_dir = output_dir / session_id
    events_path = session_output_dir / "events.json"
    artifacts_dir = session_output_dir / "artifacts"

    if events_path.exists() and not force:
        log(f"  {session_id}: output already exists (use --force to overwrite)")
        return None

    # Get video metadata
    meta = get_video_metadata(video_path)
    duration_ms = meta.duration_ms

    # Compute segments
    segments = compute_segments(
        duration_ms=duration_ms,
        max_segment_duration_ms=config.max_segment_duration_ms,
        segment_overlap_ms=config.segment_overlap_ms,
        output_dir=artifacts_dir,
    )

    if dry_run:
        _print_dry_run(session_manifest, meta, segments, config)
        return {
            "session": session_id,
            "duration_ms": duration_ms,
            "segments": len(segments),
            "estimated_tokens": _estimate_tokens(segments, config.video_fps),
            "dry_run": True,
        }

    log(f"  {session_id}: {len(segments)} segments from {duration_ms/1000:.0f}s video")

    # Run CV analysis on full video
    cursor_trajectory, flow_windows = run_cv_analysis(
        video_path=video_path,
        config=config,
        base_dir=base_dir,
        duration_ms=duration_ms,
    )

    # Save CV artifacts
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir / "cursor_trajectory.json").write_text(
        json.dumps([d.model_dump() for d in cursor_trajectory], indent=2)
    )
    (artifacts_dir / "flow_windows.json").write_text(
        json.dumps([fw.model_dump() for fw in flow_windows], indent=2)
    )

    # Extract all segments
    for segment in segments:
        extract_segment(video_path, segment)
        log(f"  Segment {segment.index}: extracted {(segment.end_ms - segment.start_ms)/1000:.1f}s")

    # Generate CV summaries and analyse segments concurrently
    client = create_client()
    semaphore = asyncio.Semaphore(config.max_concurrent)

    analysis_tasks = []
    for segment in segments:
        cv_summary = generate_cv_summary(
            cursor_trajectory=cursor_trajectory,
            flow_windows=flow_windows,
            segment=segment,
            summary_window_ms=config.summary_window_ms,
        )

        prompt = fill_template(prompt_template, {
            "segment_index": segment.index + 1,
            "total_segments": len(segments),
            "segment_start_ms": int(segment.start_ms),
            "segment_end_ms": int(segment.end_ms),
            "video_fps": config.video_fps,
            "study_name": session_manifest.study,
            "participant": session_manifest.participant,
            "cv_summary": cv_summary,
        })
        analysis_tasks.append(
            analyse_segment_with_cv(client, segment, cv_summary, config, prompt, semaphore, force=force)
        )

    t0 = time.monotonic()
    results = await asyncio.gather(*analysis_tasks)
    analysis_time_ms = (time.monotonic() - t0) * 1000

    # Adjust timestamps and collect all events
    all_resolved: list[ResolvedEvent] = []
    segment_metadata: list[dict] = []
    total_input_tokens = 0
    total_output_tokens = 0

    for segment, (raw_events, token_usage) in zip(segments, results):
        resolved = adjust_timestamps(
            raw_events,
            segment,
            session_manifest.screenTrackStartOffset,
            config.source,
        )
        all_resolved.extend(resolved)
        total_input_tokens += token_usage["input_tokens"]
        total_output_tokens += token_usage["output_tokens"]
        segment_metadata.append({
            "index": segment.index,
            "start_ms": segment.start_ms,
            "end_ms": segment.end_ms,
            "event_count": len(raw_events),
            "input_tokens": token_usage["input_tokens"],
            "output_tokens": token_usage["output_tokens"],
        })

    # Sort by time
    all_resolved.sort(key=lambda e: e.time_start)

    # Save merged events (before dedup)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    merged_dicts = [e.model_dump() for e in all_resolved]
    (artifacts_dir / "merged_events.json").write_text(json.dumps(merged_dicts, indent=2))

    # Deduplicate: overlap-aware pass first, then general pass
    overlap_deduped = deduplicate_overlap_events(
        all_resolved,
        segments,
        session_manifest.screenTrackStartOffset,
    )
    deduped = deduplicate_events(
        overlap_deduped,
        config.merge.time_tolerance_ms,
        config.merge.similarity_threshold,
    )

    # Save deduplicated events
    deduped_dicts = [e.model_dump() for e in deduped]
    (artifacts_dir / "deduplicated_events.json").write_text(json.dumps(deduped_dicts, indent=2))

    log(f"  {session_id}: {len(all_resolved)} merged -> {len(overlap_deduped)} overlap-dedup -> {len(deduped)} final")

    # Build final output
    final_events = [
        {
            "type": e.type,
            "source": config.source,
            "time_start": e.time_start,
            "time_end": e.time_end,
            "description": e.description,
            "confidence": e.confidence,
            "transcript_id": session_manifest.identifier,
            "study_id": session_manifest.studyId,
            **({"interaction_target": e.interaction_target} if e.interaction_target else {}),
            **({"cursor_position": e.cursor_position} if e.cursor_position else {}),
            **({"page_title": e.page_title} if e.page_title else {}),
            **({"page_location": e.page_location} if e.page_location else {}),
            **({"frame_description": e.frame_description} if e.frame_description else {}),
        }
        for e in deduped
    ]

    # Write final events
    session_output_dir.mkdir(parents=True, exist_ok=True)
    events_path.write_text(json.dumps(final_events, indent=2))
    log(f"  {session_id}: wrote {len(final_events)} events to {events_path}")

    # Write run metadata
    run_meta = {
        "session": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": config.model_dump(),
        "video_duration_ms": duration_ms,
        "video_path": str(video_path),
        "segments": segment_metadata,
        "cv_analysis": {
            "cursor_detections": len(cursor_trajectory),
            "cursor_detected": sum(1 for d in cursor_trajectory if d.detected),
            "flow_windows": len(flow_windows),
        },
        "total_events_merged": len(all_resolved),
        "total_events_deduped": len(deduped),
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "analysis_time_ms": round(analysis_time_ms, 1),
    }
    (artifacts_dir / "run_metadata.json").write_text(json.dumps(run_meta, indent=2))

    return run_meta


def _print_dry_run(
    session: SessionManifest,
    meta: Any,
    segments: tuple[VideoSegment, ...],
    config: CvAugmentedConfig,
) -> None:
    duration_s = meta.duration_ms / 1000.0
    mins = int(duration_s // 60)
    secs = int(duration_s % 60)
    estimated_tokens = _estimate_tokens(segments, config.video_fps)

    avg_duration = sum((s.end_ms - s.start_ms) for s in segments) / len(segments) / 1000.0
    avg_mins = int(avg_duration // 60)
    avg_secs = int(avg_duration % 60)

    print(f"\nSession: {session.identifier}")
    print(f"  Duration: {mins}:{secs:02d}")
    print(f"  Segments: {len(segments)} (~{avg_mins}:{avg_secs:02d} each, "
          f"{config.segment_overlap_ms/1000:.0f}s overlaps)")
    print(f"  Video FPS: {config.video_fps} (vs baseline 20)")
    print(f"  Estimated video tokens: ~{estimated_tokens:,}")
    print(f"  CV context: cursor tracking + optical flow summaries")
    print(f"  Summary window: {config.summary_window_ms}ms")
