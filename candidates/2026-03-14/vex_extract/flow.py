from __future__ import annotations

import logging
import math
from pathlib import Path

import numpy as np

from vex_extract.config import FlowConfig
from vex_extract.models import CursorDetection, FlowWindow
from vex_extract.video import compute_optical_flow, extract_frames

logger = logging.getLogger(__name__)

_DIRECTION_BINS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")


def _angle_to_direction(angle_rad: float) -> str:
    """Map angle (in radians, 0=right, CCW positive) to 8-bin compass direction."""
    deg = math.degrees(angle_rad) % 360
    idx = int((deg + 22.5) / 45) % 8
    mapping = ("E", "NE", "N", "NW", "W", "SW", "S", "SE")
    return mapping[idx]


def _aggregate_flow_window(
    start_ms: float,
    end_ms: float,
    flow_pairs: list[tuple[float, float, np.ndarray, np.ndarray, np.ndarray]],
    cursor_trajectory: tuple[CursorDetection, ...],
) -> FlowWindow:
    """Aggregate flow data within a window into a FlowWindow summary."""
    all_magnitudes: list[float] = []
    direction_counts: dict[str, int] = {d: 0 for d in _DIRECTION_BINS}

    for _ts_a, _ts_b, points, displacements, status in flow_pairs:
        valid = status.flatten() == 1
        if not valid.any():
            continue

        valid_disp = displacements[valid]
        mags = np.sqrt(valid_disp[:, 0] ** 2 + valid_disp[:, 1] ** 2)
        all_magnitudes.extend(mags.tolist())

        for dx, dy in valid_disp:
            angle = math.atan2(-dy, dx)  # -dy because y-axis is inverted in image coords
            direction = _angle_to_direction(angle)
            direction_counts[direction] = direction_counts.get(direction, 0) + 1

    mean_mag = float(np.mean(all_magnitudes)) if all_magnitudes else 0.0

    dominant = max(direction_counts, key=lambda d: direction_counts[d]) if direction_counts else ""
    total_dir_points = sum(direction_counts.values())
    dominant_count = direction_counts.get(dominant, 0)

    flow_uniformity = dominant_count / total_dir_points if total_dir_points > 0 else 0.0

    cursor_flow_div = 0.0
    if cursor_trajectory and all_magnitudes:
        cursor_in_window = [
            d for d in cursor_trajectory
            if start_ms <= d.timestamp_ms <= end_ms and (d.detected or d.confidence > 0)
        ]
        if len(cursor_in_window) >= 2:
            first = cursor_in_window[0]
            last = cursor_in_window[-1]
            cursor_dx = last.x - first.x
            cursor_dy = last.y - first.y
            cursor_mag = math.sqrt(cursor_dx ** 2 + cursor_dy ** 2)
            cursor_flow_div = abs(cursor_mag - mean_mag) / (mean_mag + 1e-6)

    return FlowWindow(
        start_ms=start_ms,
        end_ms=end_ms,
        mean_flow_magnitude=mean_mag,
        dominant_direction=dominant,
        flow_uniformity=flow_uniformity,
        cursor_flow_divergence=cursor_flow_div,
    )


def compute_flow_summaries(
    video_path: Path,
    cursor_trajectory: tuple[CursorDetection, ...],
    config: FlowConfig,
    total_duration_ms: float,
) -> tuple[FlowWindow, ...]:
    """Compute optical flow summaries in sliding windows across the recording."""
    total_end = total_duration_ms / 1000.0
    frames = extract_frames(video_path, 0.0, total_end, config.flow_fps, scale_height=config.resolution_height)

    if len(frames) < 2:
        return ()

    logger.info("  Flow: computing across %d frame pairs...", len(frames) - 1)

    flow_pairs: list[tuple[float, float, np.ndarray, np.ndarray, np.ndarray]] = []
    for i in range(len(frames) - 1):
        ts_a, frame_a = frames[i]
        ts_b, frame_b = frames[i + 1]
        points, displacements, status = compute_optical_flow(frame_a, frame_b, config.flow_grid_step)
        flow_pairs.append((ts_a, ts_b, points, displacements, status))

    windows: list[FlowWindow] = []
    window_ms = config.flow_window_size_ms
    step_ms = config.flow_window_step_ms

    t = 0.0
    while t + window_ms <= total_duration_ms:
        window_end = t + window_ms
        relevant = [
            fp for fp in flow_pairs
            if fp[0] >= t and fp[1] <= window_end
        ]
        if relevant:
            fw = _aggregate_flow_window(t, window_end, relevant, cursor_trajectory)
            windows.append(fw)
        t += step_ms

    return tuple(windows)
