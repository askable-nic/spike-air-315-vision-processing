from __future__ import annotations

import asyncio
import json
import math
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from google.genai import types

from src.gemini import create_client, make_request
from src.log import log
from src.models import (
    GenerateBaselinesConfig,
    ResolvedEvent,
    SessionManifest,
    VideoAnalysisEvent,
    VideoSegment,
)
from src.prompts import fill_template
from src.similarity import string_similarity
from src.video import get_video_metadata
from stages.merge import deduplicate_events


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
            "cursor_position_x": {"type": "INTEGER"},
            "cursor_position_y": {"type": "INTEGER"},
            "page_title": {"type": "STRING"},
            "page_location": {"type": "STRING"},
            "frame_description": {"type": "STRING"},
        },
        "required": ["type", "time_start_ms", "time_end_ms", "description", "confidence"],
    },
}


def compute_segments(
    duration_ms: float,
    max_segment_duration_ms: int,
    segment_overlap_ms: int,
    output_dir: Path,
) -> tuple[VideoSegment, ...]:
    """Split a video duration into close-to-equal segments with overlaps."""
    n_segments = math.ceil(duration_ms / max_segment_duration_ms)
    if n_segments < 1:
        n_segments = 1
    base_duration = duration_ms / n_segments

    segments: list[VideoSegment] = []
    for i in range(n_segments):
        content_start = i * base_duration
        content_end = (i + 1) * base_duration

        actual_start = max(0.0, content_start - segment_overlap_ms) if i > 0 else 0.0
        actual_end = min(duration_ms, content_end + segment_overlap_ms) if i < n_segments - 1 else duration_ms

        overlap_start_ms = content_start - actual_start if i > 0 else 0.0
        overlap_end_ms = actual_end - content_end if i < n_segments - 1 else 0.0

        segment_dir = output_dir / f"segment_{i:03d}"
        segment_dir.mkdir(parents=True, exist_ok=True)

        segments.append(VideoSegment(
            index=i,
            start_ms=actual_start,
            end_ms=actual_end,
            overlap_start_ms=overlap_start_ms,
            overlap_end_ms=overlap_end_ms,
            path=segment_dir / "video.mp4",
        ))

    return tuple(segments)


def extract_segment(video_path: Path, segment: VideoSegment) -> Path:
    """Extract a video segment using ffmpeg -c copy."""
    start_sec = segment.start_ms / 1000.0
    end_sec = segment.end_ms / 1000.0

    segment.path.parent.mkdir(parents=True, exist_ok=True)

    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-ss", f"{start_sec:.3f}",
                "-to", f"{end_sec:.3f}",
                "-i", str(video_path),
                "-c", "copy",
                str(segment.path),
            ],
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        # Fallback to re-encode if copy fails (keyframe issues)
        log(f"  Segment {segment.index}: -c copy failed, falling back to re-encode")
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-ss", f"{start_sec:.3f}",
                "-to", f"{end_sec:.3f}",
                "-i", str(video_path),
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-an",
                str(segment.path),
            ],
            capture_output=True,
            check=True,
        )

    return segment.path


async def analyse_segment(
    client: Any,
    segment: VideoSegment,
    config: GenerateBaselinesConfig,
    system_prompt: str,
    semaphore: asyncio.Semaphore,
    force: bool = False,
) -> tuple[list[dict], dict]:
    """Analyse a video segment with Gemini, returning parsed events and token usage."""
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
        log(f"  Segment {segment.index}: sending to Gemini...")
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
            "response_mime_type": "application/json",
            "response_schema": _VIDEO_ANALYSIS_SCHEMA,
            "system_prompt_length": len(system_prompt),
        }
        (segment_dir / "request.json").write_text(json.dumps(request_record, indent=2))
        (segment_dir / "prompt.txt").write_text(system_prompt)
        (segment_dir / "response.json").write_text(json.dumps(result, indent=2))
        (segment_dir / "events.json").write_text(json.dumps(raw_events, indent=2))

        log(f"  Segment {segment.index}: {len(raw_events)} events, "
            f"{result['input_tokens']:,} in / {result['output_tokens']:,} out tokens")

        return raw_events, token_usage


def adjust_timestamps(
    events: list[dict],
    segment: VideoSegment,
    screen_track_start_offset: float,
    source: str,
) -> list[ResolvedEvent]:
    """Convert segment-relative timestamps to transcript-relative ResolvedEvents."""
    resolved: list[ResolvedEvent] = []
    for raw in events:
        # Segment-relative ms → absolute video ms → transcript ms
        abs_start = raw["time_start_ms"] + segment.start_ms + screen_track_start_offset
        abs_end = raw["time_end_ms"] + segment.start_ms + screen_track_start_offset

        cursor_dict = None
        if raw.get("cursor_position_x") is not None and raw.get("cursor_position_y") is not None:
            cursor_dict = {"x": raw["cursor_position_x"], "y": raw["cursor_position_y"]}

        # Validate event type
        event_type = raw.get("type", "change_ui_state")
        valid_types = {
            "click", "hover", "navigate", "input_text", "select",
            "dwell", "cursor_thrash", "scroll", "drag", "hesitate", "change_ui_state",
        }
        if event_type not in valid_types:
            event_type = "change_ui_state"

        resolved.append(ResolvedEvent(
            type=event_type,
            time_start=abs_start,
            time_end=abs_end,
            description=raw.get("description", ""),
            confidence=raw.get("confidence", 0.5),
            interaction_target=raw.get("interaction_target"),
            cursor_position=cursor_dict,
            page_title=raw.get("page_title"),
            page_location=raw.get("page_location"),
            frame_description=raw.get("frame_description"),
        ))

    return resolved


def deduplicate_overlap_events(
    events: list[ResolvedEvent],
    segments: tuple[VideoSegment, ...],
    screen_track_start_offset: float,
    close_time_ms: float = 3000,
    min_similarity: float = 0.3,
) -> list[ResolvedEvent]:
    """Aggressive dedup for same-type events near segment boundaries.

    Events of the same type within close_time_ms of each other, where at least one
    falls inside an overlap window, are likely the same event seen by two segments.
    Keeps the higher-confidence version.
    """
    if len(segments) < 2 or not events:
        return events

    # Build overlap windows in absolute (transcript-relative) time
    overlap_windows: list[tuple[float, float]] = []
    for i in range(len(segments) - 1):
        # Overlap region = where segment i and segment i+1 both cover
        overlap_start = segments[i + 1].start_ms + screen_track_start_offset
        overlap_end = segments[i].end_ms + screen_track_start_offset
        if overlap_start < overlap_end:
            overlap_windows.append((overlap_start, overlap_end))

    def in_overlap(t: float) -> bool:
        return any(start <= t <= end for start, end in overlap_windows)

    keep: list[ResolvedEvent] = []
    for event in events:
        is_dup = False
        for i, existing in enumerate(keep):
            if event.type != existing.type:
                continue
            time_gap = abs(event.time_start - existing.time_start)
            if time_gap > close_time_ms:
                continue
            # Only apply aggressive dedup if at least one event is in an overlap window
            if not (in_overlap(event.time_start) or in_overlap(existing.time_start)):
                continue
            sim = string_similarity(event.description, existing.description)
            if sim >= min_similarity:
                if event.confidence > existing.confidence:
                    keep[i] = event
                is_dup = True
                break
        if not is_dup:
            keep.append(event)

    return keep


def snapshot_existing_baseline(baselines_dir: Path) -> dict | None:
    """Capture a summary of the existing baseline before overwriting.

    Saves a timestamped snapshot JSON to the artifacts directory and returns the summary.
    """
    events_path = baselines_dir / "events.json"
    if not events_path.exists():
        return None

    events = json.loads(events_path.read_text())
    if not events:
        return None

    type_counts: dict[str, int] = {}
    sources: set[str] = set()
    fields_present: dict[str, int] = {
        "interaction_target": 0, "cursor_position": 0,
        "page_title": 0, "page_location": 0, "frame_description": 0,
    }
    for e in events:
        t = e.get("type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1
        sources.add(e.get("source", "unknown"))
        for f in fields_present:
            if e.get(f):
                fields_present[f] += 1

    time_starts = [e["time_start"] for e in events if e.get("time_start") is not None]
    time_ends = [e["time_end"] for e in events if e.get("time_end") is not None]

    summary: dict[str, Any] = {
        "snapshot_timestamp": datetime.now(timezone.utc).isoformat(),
        "total_events": len(events),
        "sources": sorted(sources),
        "event_types": dict(sorted(type_counts.items())),
        "time_range_ms": {
            "start": min(time_starts) if time_starts else None,
            "end": max(time_ends) if time_ends else None,
        },
        "field_coverage": {k: f"{v}/{len(events)}" for k, v in fields_present.items()},
    }

    # Include previous run metadata if available
    run_meta_path = baselines_dir / "artifacts" / "run_metadata.json"
    if run_meta_path.exists():
        prev_meta = json.loads(run_meta_path.read_text())
        summary["previous_run"] = {
            "timestamp": prev_meta.get("timestamp"),
            "model": prev_meta.get("config", {}).get("model"),
            "video_fps": prev_meta.get("config", {}).get("video_fps"),
            "max_segment_duration_ms": prev_meta.get("config", {}).get("max_segment_duration_ms"),
            "segments": len(prev_meta.get("segments", [])),
            "total_input_tokens": prev_meta.get("total_input_tokens"),
            "total_output_tokens": prev_meta.get("total_output_tokens"),
            "analysis_time_ms": prev_meta.get("analysis_time_ms"),
        }

    # Save snapshot
    artifacts_dir = baselines_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snapshot_path = artifacts_dir / f"snapshot_{ts}.json"
    snapshot_path.write_text(json.dumps(summary, indent=2))

    log(f"  Snapshot saved: {snapshot_path.name} ({summary['total_events']} events, "
        f"sources={summary['sources']})")

    return summary


async def generate_session_baseline(
    session_manifest: SessionManifest,
    video_path: Path,
    config: GenerateBaselinesConfig,
    prompt_template: str,
    base_dir: Path,
    dry_run: bool = False,
    force: bool = False,
) -> dict | None:
    """Generate a baseline for a single session.

    Returns run metadata dict, or None if skipped.
    """
    session_id = session_manifest.identifier
    baselines_dir = base_dir / "baselines" / session_id
    events_path = baselines_dir / "events.json"
    artifacts_dir = baselines_dir / "artifacts"

    if events_path.exists() and not force:
        log(f"  {session_id}: baseline already exists (use --force to overwrite)")
        return None

    if events_path.exists() and force:
        snapshot_existing_baseline(baselines_dir)

    # Get video duration
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

    # Extract all segments
    for segment in segments:
        extract_segment(video_path, segment)
        log(f"  Segment {segment.index}: extracted {(segment.end_ms - segment.start_ms)/1000:.1f}s")

    # Analyse segments concurrently
    client = create_client()
    semaphore = asyncio.Semaphore(config.max_concurrent)

    analysis_tasks = []
    for segment in segments:
        prompt = fill_template(prompt_template, {
            "segment_index": segment.index + 1,
            "total_segments": len(segments),
            "segment_start_ms": int(segment.start_ms),
            "segment_end_ms": int(segment.end_ms),
            "video_fps": config.video_fps,
            "study_name": session_manifest.study,
            "participant": session_manifest.participant,
        })
        analysis_tasks.append(
            analyse_segment(client, segment, config, prompt, semaphore, force=force)
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

    log(f"  {session_id}: {len(all_resolved)} merged → {len(overlap_deduped)} overlap-dedup → {len(deduped)} final")

    # Build final output with session metadata
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
    baselines_dir.mkdir(parents=True, exist_ok=True)
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
        "total_events_merged": len(all_resolved),
        "total_events_deduped": len(deduped),
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "analysis_time_ms": round(analysis_time_ms, 1),
    }
    (artifacts_dir / "run_metadata.json").write_text(json.dumps(run_meta, indent=2))

    return run_meta


def _estimate_tokens(segments: tuple[VideoSegment, ...], video_fps: int) -> int:
    """Estimate total input tokens for all segments."""
    total = 0
    for seg in segments:
        duration_s = (seg.end_ms - seg.start_ms) / 1000.0
        frames = duration_s * video_fps
        total += int(frames * 263)
    return total


def _print_dry_run(
    session: SessionManifest,
    meta: Any,
    segments: tuple[VideoSegment, ...],
    config: GenerateBaselinesConfig,
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
    print(f"  Video FPS: {config.video_fps}")
    print(f"  Estimated tokens: ~{estimated_tokens:,}")
