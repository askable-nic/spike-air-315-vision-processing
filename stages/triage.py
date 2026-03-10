from __future__ import annotations

import time
from pathlib import Path

from src.models import (
    ActivityTier,
    ActivityWindow,
    FrameDiff,
    PipelineConfig,
    SessionManifest,
    TriageResult,
    TriageSegment,
    VideoMetadata,
)
from src.video import compute_frame_diff, extract_frames, get_video_metadata


def run_triage(
    session: SessionManifest,
    config: PipelineConfig,
    video_path: Path,
) -> TriageResult:
    """Run triage on a session's screen track video.

    If triage is disabled, returns a single segment spanning the whole video at uniform FPS.
    """
    t0 = time.monotonic()
    meta = get_video_metadata(video_path)
    tc = config.triage

    if not tc.enabled:
        segments = _bypass_segments(meta, config)
    else:
        diffs = compute_activity_signal(video_path, tc.sample_fps, tc.resolution_height)
        windows = apply_sliding_window(
            diffs,
            tc.window_size_ms,
            tc.window_step_ms,
            tc.thresholds,
        )
        segments = merge_windows_to_segments(
            windows,
            tc.fps_mapping,
            tc.min_segment_duration_ms,
            meta.duration_ms,
        )

    elapsed = (time.monotonic() - t0) * 1000
    return TriageResult(
        recording_id=session.identifier,
        segments=segments,
        total_duration_ms=meta.duration_ms,
        processing_time_ms=elapsed,
    )


def _bypass_segments(meta: VideoMetadata, config: PipelineConfig) -> tuple[TriageSegment, ...]:
    """Create a single segment spanning the entire video at the medium-tier FPS."""
    fps = config.triage.fps_mapping.get("medium", 4.0)
    return (
        TriageSegment(
            segment_index=0,
            start_ms=0,
            end_ms=meta.duration_ms,
            tier="medium",
            assigned_fps=fps,
            mean_activity=0.0,
        ),
    )


def compute_activity_signal(
    video_path: Path,
    sample_fps: float,
    resolution_height: int,
) -> tuple[FrameDiff, ...]:
    """Sample frames and compute pairwise diffs to produce an activity signal."""
    meta = get_video_metadata(video_path)
    duration_sec = meta.duration_ms / 1000

    frames = extract_frames(
        video_path,
        start_sec=0,
        end_sec=duration_sec,
        fps=sample_fps,
        scale_height=resolution_height,
    )

    if len(frames) < 2:
        return ()

    diffs: list[FrameDiff] = []
    for i in range(1, len(frames)):
        ts_prev, frame_prev = frames[i - 1]
        ts_curr, frame_curr = frames[i]

        magnitude, bbox = compute_frame_diff(frame_prev, frame_curr)

        bbox_area_ratio = 0.0
        if bbox is not None:
            _, _, bw, bh = bbox
            total_area = frame_curr.shape[0] * frame_curr.shape[1]
            bbox_area_ratio = (bw * bh) / total_area if total_area > 0 else 0.0

        diffs.append(FrameDiff(
            frame_index=i,
            timestamp_ms=ts_curr,
            magnitude=magnitude,
            bbox=bbox,
            bbox_area_ratio=bbox_area_ratio,
        ))

    return tuple(diffs)


def _classify_magnitude(magnitude: float, thresholds: dict[str, float]) -> ActivityTier:
    """Classify a magnitude value into an activity tier based on thresholds."""
    idle_t = thresholds.get("idle", 0.005)
    low_t = thresholds.get("low", 0.02)
    medium_t = thresholds.get("medium", 0.08)

    if magnitude < idle_t:
        return "idle"
    elif magnitude < low_t:
        return "low"
    elif magnitude < medium_t:
        return "medium"
    else:
        return "high"


def apply_sliding_window(
    diffs: tuple[FrameDiff, ...],
    window_size_ms: int,
    step_ms: int,
    thresholds: dict[str, float],
) -> tuple[ActivityWindow, ...]:
    """Apply sliding window over diff magnitudes and classify each window."""
    if not diffs:
        return ()

    start_ms = diffs[0].timestamp_ms
    end_ms = diffs[-1].timestamp_ms

    windows: list[ActivityWindow] = []
    window_start = start_ms

    while window_start < end_ms:
        window_end = window_start + window_size_ms

        window_diffs = [d for d in diffs if window_start <= d.timestamp_ms < window_end]

        if window_diffs:
            mean_mag = sum(d.magnitude for d in window_diffs) / len(window_diffs)
        else:
            mean_mag = 0.0

        tier = _classify_magnitude(mean_mag, thresholds)

        windows.append(ActivityWindow(
            start_ms=window_start,
            end_ms=min(window_end, end_ms),
            mean_magnitude=mean_mag,
            tier=tier,
        ))

        window_start += step_ms

    return tuple(windows)


def merge_windows_to_segments(
    windows: tuple[ActivityWindow, ...],
    fps_mapping: dict[str, float],
    min_duration_ms: int,
    total_duration_ms: float,
) -> tuple[TriageSegment, ...]:
    """Merge adjacent same-tier windows into contiguous segments, then absorb short segments."""
    if not windows:
        return ()

    # Merge adjacent same-tier windows
    merged: list[dict] = []
    for w in windows:
        if merged and merged[-1]["tier"] == w.tier:
            merged[-1]["end_ms"] = w.end_ms
            merged[-1]["magnitudes"].append(w.mean_magnitude)
        else:
            merged.append({
                "start_ms": w.start_ms,
                "end_ms": w.end_ms,
                "tier": w.tier,
                "magnitudes": [w.mean_magnitude],
            })

    # Absorb short segments into neighbours
    absorbed: list[dict] = []
    for seg in merged:
        duration = seg["end_ms"] - seg["start_ms"]
        if duration < min_duration_ms and absorbed:
            # Merge into previous segment
            absorbed[-1]["end_ms"] = seg["end_ms"]
            absorbed[-1]["magnitudes"].extend(seg["magnitudes"])
        else:
            absorbed.append(seg)

    # If last segment is too short, merge into previous
    if len(absorbed) > 1:
        last = absorbed[-1]
        if (last["end_ms"] - last["start_ms"]) < min_duration_ms:
            absorbed[-2]["end_ms"] = last["end_ms"]
            absorbed[-2]["magnitudes"].extend(last["magnitudes"])
            absorbed.pop()

    # Build final segments
    segments: list[TriageSegment] = []
    for i, seg in enumerate(absorbed):
        tier: ActivityTier = seg["tier"]
        fps = fps_mapping.get(tier, 4.0)
        mean_activity = sum(seg["magnitudes"]) / len(seg["magnitudes"]) if seg["magnitudes"] else 0.0

        segments.append(TriageSegment(
            segment_index=i,
            start_ms=seg["start_ms"],
            end_ms=min(seg["end_ms"], total_duration_ms),
            tier=tier,
            assigned_fps=fps,
            mean_activity=mean_activity,
        ))

    return tuple(segments)
