from __future__ import annotations

import json
import math
import time
from bisect import bisect_left
from pathlib import Path
from typing import NamedTuple

import cv2
import numpy as np

from src.log import log
from src.models import (
    ChangeRegion,
    CursorDetection,
    CursorPosition,
    FlowEvent,
    FlowWindow,
    LocalEvent,
    Moment,
    ObserveConfig,
    ObserveResult,
    PipelineConfig,
    ROIRect,
    SelectedFrame,
    SessionManifest,
    TriageResult,
    VideoMetadata,
    VisualChangeEvent,
    VisualChangeFrame,
)
from src.video import (
    compute_frame_diff,
    compute_optical_flow,
    detect_visual_changes,
    extract_frames,
    extract_frames_at_timestamps,
    get_video_metadata,
)


# ---------------------------------------------------------------------------
# Template loading
# ---------------------------------------------------------------------------

class TemplateInfo(NamedTuple):
    template_id: str
    image: np.ndarray  # grayscale
    mask: np.ndarray | None  # alpha mask or None
    hotspot_x: int
    hotspot_y: int


class MatchResult(NamedTuple):
    x: float
    y: float
    confidence: float
    template_id: str


def load_templates(
    templates_dir: Path,
    base_dir: Path = Path("."),
) -> tuple[TemplateInfo, ...]:
    """Load cursor template PNGs and metadata from templates_dir."""
    meta_path = templates_dir / "templates.json"
    if not meta_path.exists():
        # Fallback to base_dir / cursor_templates
        templates_dir = base_dir / "cursor_templates"
        meta_path = templates_dir / "templates.json"

    if not meta_path.exists():
        return ()

    with open(meta_path) as f:
        meta = json.load(f)

    templates: list[TemplateInfo] = []
    for entry in meta.get("templates", []):
        img_path = templates_dir / entry["file"]
        if not img_path.exists():
            continue

        img = cv2.imread(str(img_path), cv2.IMREAD_UNCHANGED)
        if img is None:
            continue

        mask: np.ndarray | None = None
        if img.shape[2] == 4:
            mask = img[:, :, 3]
            gray = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2GRAY)
        else:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        templates.append(TemplateInfo(
            template_id=entry["template_id"],
            image=gray,
            mask=mask,
            hotspot_x=entry.get("hotspot_x", 0),
            hotspot_y=entry.get("hotspot_y", 0),
        ))

    return tuple(templates)


# ---------------------------------------------------------------------------
# Cursor matching
# ---------------------------------------------------------------------------

class _PrescaledEntry(NamedTuple):
    template: TemplateInfo
    scale: float
    image: np.ndarray


def _prescale_templates(
    templates: tuple[TemplateInfo, ...],
    scales: tuple[float, ...],
) -> tuple[_PrescaledEntry, ...]:
    """Pre-compute scaled template images (grayscale, no mask) for all template/scale combos."""
    entries: list[_PrescaledEntry] = []
    for tmpl in templates:
        for scale in scales:
            th, tw = tmpl.image.shape[:2]
            sh = max(1, int(th * scale))
            sw = max(1, int(tw * scale))
            scaled_img = cv2.resize(tmpl.image, (sw, sh))
            entries.append(_PrescaledEntry(template=tmpl, scale=scale, image=scaled_img))
    return tuple(entries)


def match_cursor_in_frame(
    gray_frame: np.ndarray,
    prescaled: tuple[_PrescaledEntry, ...],
    threshold: float,
    early_exit_threshold: float = 0.9,
) -> MatchResult | None:
    """Multi-scale template matching using pre-scaled templates (no mask for speed).

    Returns best match above threshold or None.
    """
    best: MatchResult | None = None
    best_conf = threshold

    fh, fw = gray_frame.shape[:2]

    for entry in prescaled:
        sh, sw = entry.image.shape[:2]

        if sh >= fh or sw >= fw:
            continue

        result = cv2.matchTemplate(gray_frame, entry.image, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val > best_conf:
            hotspot_x = entry.template.hotspot_x * entry.scale
            hotspot_y = entry.template.hotspot_y * entry.scale
            best = MatchResult(
                x=max_loc[0] + hotspot_x,
                y=max_loc[1] + hotspot_y,
                confidence=float(max_val),
                template_id=entry.template.template_id,
            )
            best_conf = max_val

            if max_val >= early_exit_threshold:
                return best

    return best


# ---------------------------------------------------------------------------
# Cursor tracking
# ---------------------------------------------------------------------------

_MATCH_HEIGHT = 360  # Internal resolution for template matching (speed vs accuracy)


def _match_frames(
    raw_frames: tuple[tuple[float, np.ndarray], ...],
    all_prescaled: tuple[_PrescaledEntry, ...],
    oc: ObserveConfig,
    scale_factor: float,
) -> list[CursorDetection]:
    """Run template matching on a batch of frames, returning detections."""
    detections: list[CursorDetection] = []
    total_frames = len(raw_frames)
    log_interval = max(1, total_frames // 10)
    last_match_id: str | None = None

    for idx, (ts_ms, frame) in enumerate(raw_frames):
        if idx > 0 and idx % log_interval == 0:
            detected_so_far = sum(1 for d in detections if d.detected)
            log(f"  Observe: {idx}/{total_frames} frames ({detected_so_far} detections)")

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame

        match: MatchResult | None = None
        if last_match_id is not None:
            priority = tuple(e for e in all_prescaled if e.template.template_id == last_match_id)
            if priority:
                match = match_cursor_in_frame(
                    gray, priority, oc.match_threshold, oc.early_exit_threshold,
                )

        if match is None:
            match = match_cursor_in_frame(
                gray, all_prescaled, oc.match_threshold, oc.early_exit_threshold,
            )

        if match is not None:
            last_match_id = match.template_id
            detections.append(CursorDetection(
                timestamp_ms=ts_ms,
                x=match.x * scale_factor,
                y=match.y * scale_factor,
                confidence=match.confidence,
                template_id=match.template_id,
                detected=True,
            ))
        else:
            last_match_id = None
            detections.append(CursorDetection(
                timestamp_ms=ts_ms,
                x=0.0,
                y=0.0,
                confidence=0.0,
                template_id="",
                detected=False,
            ))

    return detections


def _identify_active_regions(
    detections: tuple[CursorDetection, ...],
    displacement_threshold_px: float,
    padding_ms: float,
) -> tuple[tuple[float, float], ...]:
    """Scan consecutive detected frames; where displacement exceeds threshold, mark as active.

    Merges overlapping intervals and pads each side by padding_ms.
    Returns sorted, non-overlapping (start_ms, end_ms) tuples.
    """
    detected = [d for d in detections if d.detected]
    if len(detected) < 2:
        return ()

    raw_intervals: list[tuple[float, float]] = []
    for i in range(1, len(detected)):
        dx = detected[i].x - detected[i - 1].x
        dy = detected[i].y - detected[i - 1].y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > displacement_threshold_px:
            start = detected[i - 1].timestamp_ms - padding_ms
            end = detected[i].timestamp_ms + padding_ms
            raw_intervals.append((max(0.0, start), end))

    if not raw_intervals:
        return ()

    # Sort and merge overlapping
    raw_intervals.sort()
    merged: list[tuple[float, float]] = [raw_intervals[0]]
    for start, end in raw_intervals[1:]:
        prev_start, prev_end = merged[-1]
        if start <= prev_end:
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))

    return tuple(merged)


def track_cursor(
    video_path: Path,
    triage_result: TriageResult | None,
    oc: ObserveConfig,
    base_dir: Path = Path("."),
    total_duration_ms: float | None = None,
) -> tuple[CursorDetection, ...]:
    """Track cursor via adaptive two-pass approach.

    Pass 1: coarse scan at tracking_base_fps across the full video.
    Identify active regions where cursor displacement exceeds threshold.
    Pass 2: fine scan at tracking_peak_fps within active regions only.
    Merge, interpolate, and smooth.
    """
    templates = load_templates(base_dir / "cursor_templates", base_dir)
    if not templates:
        return ()

    meta = get_video_metadata(video_path)

    duration_ms = (
        triage_result.total_duration_ms if triage_result is not None
        else (total_duration_ms if total_duration_ms is not None else meta.duration_ms)
    )
    total_end = duration_ms / 1000.0

    scale_factor = meta.height / _MATCH_HEIGHT if _MATCH_HEIGHT > 0 else 1.0
    all_prescaled = _prescale_templates(templates, oc.template_scales)

    # --- Pass 1: coarse ---
    coarse_frames = extract_frames(
        video_path, 0.0, total_end, oc.tracking_base_fps, scale_height=_MATCH_HEIGHT,
    )
    log(
        f"  Observe: pass 1 — matching {len(coarse_frames)} frames at {oc.tracking_base_fps} FPS "
        f"against {len(templates)} templates × {len(oc.template_scales)} scales at {_MATCH_HEIGHT}p..."
    )
    coarse_detections = _match_frames(coarse_frames, all_prescaled, oc, scale_factor)

    # --- Identify active regions ---
    active_regions = _identify_active_regions(
        tuple(coarse_detections),
        oc.tracking_displacement_threshold_px,
        oc.tracking_active_padding_ms,
    )
    log(f"  Observe: {len(active_regions)} active regions identified")

    # --- Pass 2: fine scan within active regions ---
    fine_detections: list[CursorDetection] = []
    for region_start, region_end in active_regions:
        region_frames = extract_frames(
            video_path,
            region_start / 1000.0,
            region_end / 1000.0,
            oc.tracking_peak_fps,
            scale_height=_MATCH_HEIGHT,
        )
        if region_frames:
            log(f"  Observe: pass 2 — {len(region_frames)} frames at {oc.tracking_peak_fps} FPS [{region_start:.0f}ms-{region_end:.0f}ms]")
            fine_detections.extend(_match_frames(region_frames, all_prescaled, oc, scale_factor))

    # --- Merge: in active regions, replace coarse with fine ---
    def _in_active_region(ts_ms: float) -> bool:
        return any(s <= ts_ms <= e for s, e in active_regions)

    merged: list[CursorDetection] = [d for d in coarse_detections if not _in_active_region(d.timestamp_ms)]
    merged.extend(fine_detections)
    merged.sort(key=lambda d: d.timestamp_ms)

    log(f"  Observe: merged {len(merged)} detections ({sum(1 for d in merged if d.detected)} detected)")

    interpolated = interpolate_trajectory(tuple(merged), oc.max_interpolation_gap_ms)
    smoothed = smooth_trajectory(interpolated, oc.smooth_window, oc.smooth_displacement_threshold)
    return smoothed


def interpolate_trajectory(
    detections: tuple[CursorDetection, ...],
    max_gap_ms: int,
) -> tuple[CursorDetection, ...]:
    """Fill gaps in cursor trajectory via linear interpolation for gaps < max_gap_ms."""
    if len(detections) <= 1:
        return detections

    result = list(detections)

    # Find runs of undetected frames and interpolate if bounded by detected frames within gap
    i = 0
    while i < len(result):
        if not result[i].detected:
            # Find start of gap (last detected before this)
            gap_start = i - 1
            gap_end = i
            while gap_end < len(result) and not result[gap_end].detected:
                gap_end += 1

            if gap_start >= 0 and gap_end < len(result):
                a = result[gap_start]
                b = result[gap_end]
                gap_duration = b.timestamp_ms - a.timestamp_ms
                if gap_duration <= max_gap_ms and gap_duration > 0:
                    for j in range(gap_start + 1, gap_end):
                        t = (result[j].timestamp_ms - a.timestamp_ms) / gap_duration
                        result[j] = CursorDetection(
                            timestamp_ms=result[j].timestamp_ms,
                            x=a.x + (b.x - a.x) * t,
                            y=a.y + (b.y - a.y) * t,
                            confidence=min(a.confidence, b.confidence) * 0.5,
                            template_id=a.template_id,
                            detected=False,
                        )
            i = gap_end
        else:
            i += 1

    return tuple(result)


def smooth_trajectory(
    detections: tuple[CursorDetection, ...],
    window: int = 3,
    threshold: float = 50.0,
) -> tuple[CursorDetection, ...]:
    """Moving average smoothing for small displacements only."""
    if len(detections) < window:
        return detections

    result = list(detections)
    half = window // 2

    for i in range(half, len(result) - half):
        if not result[i].detected and result[i].confidence == 0:
            continue

        # Check if displacement from neighbours is small enough to smooth
        prev_d = result[i - 1] if i > 0 else result[i]
        next_d = result[i + 1] if i < len(result) - 1 else result[i]

        dx = abs(result[i].x - prev_d.x) + abs(result[i].x - next_d.x)
        dy = abs(result[i].y - prev_d.y) + abs(result[i].y - next_d.y)
        displacement = math.sqrt(dx * dx + dy * dy)

        if displacement > threshold:
            continue

        # Average within window
        window_slice = result[max(0, i - half):i + half + 1]
        detected_in_window = [d for d in window_slice if d.detected or d.confidence > 0]
        if not detected_in_window:
            continue

        avg_x = sum(d.x for d in detected_in_window) / len(detected_in_window)
        avg_y = sum(d.y for d in detected_in_window) / len(detected_in_window)
        result[i] = CursorDetection(
            timestamp_ms=result[i].timestamp_ms,
            x=avg_x,
            y=avg_y,
            confidence=result[i].confidence,
            template_id=result[i].template_id,
            detected=result[i].detected,
        )

    return tuple(result)


# ---------------------------------------------------------------------------
# Optical flow summaries
# ---------------------------------------------------------------------------

_DIRECTION_BINS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")


def _angle_to_direction(angle_rad: float) -> str:
    """Map angle (in radians, 0=right, CCW positive) to 8-bin compass direction."""
    deg = math.degrees(angle_rad) % 360
    idx = int((deg + 22.5) / 45) % 8
    # Map: 0=E, 1=NE, 2=N, 3=NW, 4=W, 5=SW, 6=S, 7=SE
    mapping = ("E", "NE", "N", "NW", "W", "SW", "S", "SE")
    return mapping[idx]


def compute_flow_summaries(
    video_path: Path,
    triage_result: TriageResult | None,
    cursor_trajectory: tuple[CursorDetection, ...],
    oc: ObserveConfig,
    total_duration_ms: float | None = None,
) -> tuple[FlowWindow, ...]:
    """Compute optical flow summaries in sliding windows across the recording."""
    duration_ms = (
        triage_result.total_duration_ms if triage_result is not None
        else (total_duration_ms if total_duration_ms is not None else 0.0)
    )
    total_end = duration_ms / 1000.0
    frames = extract_frames(video_path, 0.0, total_end, oc.flow_fps, scale_height=oc.resolution_height)

    if len(frames) < 2:
        return ()

    log(f"  Observe: computing flow across {len(frames)} frame pairs...")

    # Compute flow between consecutive frames
    flow_pairs: list[tuple[float, float, np.ndarray, np.ndarray, np.ndarray]] = []
    for i in range(len(frames) - 1):
        ts_a, frame_a = frames[i]
        ts_b, frame_b = frames[i + 1]
        points, displacements, status = compute_optical_flow(frame_a, frame_b, oc.flow_grid_step)
        flow_pairs.append((ts_a, ts_b, points, displacements, status))

    # Sliding window aggregation
    windows: list[FlowWindow] = []
    window_ms = oc.flow_window_size_ms
    step_ms = oc.flow_window_step_ms
    total_ms = duration_ms

    t = 0.0
    while t + window_ms <= total_ms:
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


def _aggregate_flow_window(
    start_ms: float,
    end_ms: float,
    flow_pairs: list[tuple[float, float, np.ndarray, np.ndarray, np.ndarray]],
    cursor_trajectory: tuple[CursorDetection, ...],
) -> FlowWindow:
    """Aggregate flow data within a window into a FlowWindow summary."""
    all_magnitudes: list[float] = []
    all_angles: list[float] = []
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
            all_angles.append(angle)

    mean_mag = float(np.mean(all_magnitudes)) if all_magnitudes else 0.0

    # Dominant direction
    dominant = max(direction_counts, key=lambda d: direction_counts[d]) if direction_counts else ""
    total_dir_points = sum(direction_counts.values())
    dominant_count = direction_counts.get(dominant, 0)

    # Flow uniformity: fraction of points flowing in the dominant direction
    flow_uniformity = dominant_count / total_dir_points if total_dir_points > 0 else 0.0

    # Cursor flow divergence: compare cursor movement to mean flow
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


# ---------------------------------------------------------------------------
# Local event synthesis
# ---------------------------------------------------------------------------

def synthesize_local_events(
    trajectory: tuple[CursorDetection, ...],
    flow_summary: tuple[FlowWindow, ...],
    oc: ObserveConfig,
) -> tuple[LocalEvent, ...]:
    """Synthesize local events from cursor trajectory and optical flow — no API calls."""
    detected = tuple(d for d in trajectory if d.detected or d.confidence > 0)
    if not detected:
        return ()

    events: list[LocalEvent] = []

    hovers = _detect_hovers(detected, oc)
    dwells = _detect_dwells(detected, oc)

    # Dwells supersede overlapping hovers
    dwell_intervals = [(d.time_start_ms, d.time_end_ms) for d in dwells]
    filtered_hovers = tuple(
        h for h in hovers
        if not any(ds <= h.time_start_ms and de >= h.time_end_ms for ds, de in dwell_intervals)
    )

    click_candidates = _detect_click_candidates(detected, oc)
    thrash = _detect_thrash(detected, oc)
    scrolls = _detect_scrolls(flow_summary, oc)

    # Suppress click candidates whose time range falls within a hover or dwell —
    # a stationary cursor should not also be reported as a click.
    stationary_intervals = (
        [(h.time_start_ms, h.time_end_ms) for h in filtered_hovers]
        + dwell_intervals
    )
    filtered_clicks = tuple(
        c for c in click_candidates
        if not any(
            s <= c.time_start_ms and e >= c.time_end_ms
            for s, e in stationary_intervals
        )
    )

    hesitations = _detect_hesitations(detected, filtered_clicks, oc)

    events.extend(filtered_hovers)
    events.extend(dwells)
    events.extend(filtered_clicks)
    events.extend(thrash)
    events.extend(scrolls)
    events.extend(hesitations)

    # Sort by start time
    events.sort(key=lambda e: e.time_start_ms)
    return tuple(events)


def _detect_stationary_windows(
    trajectory: tuple[CursorDetection, ...],
    radius_px: float,
) -> list[tuple[int, int]]:
    """Find maximal windows where cursor stays within radius_px of window start position.

    Returns list of (start_index, end_index) pairs.
    """
    windows: list[tuple[int, int]] = []
    n = len(trajectory)
    i = 0

    while i < n:
        anchor_x = trajectory[i].x
        anchor_y = trajectory[i].y
        j = i + 1
        while j < n:
            dx = trajectory[j].x - anchor_x
            dy = trajectory[j].y - anchor_y
            if math.sqrt(dx * dx + dy * dy) > radius_px:
                break
            j += 1

        if j > i + 1:
            windows.append((i, j - 1))
        i = max(i + 1, j)

    return windows


def _detect_hovers(
    trajectory: tuple[CursorDetection, ...],
    oc: ObserveConfig,
) -> tuple[LocalEvent, ...]:
    """Detect hover events: stationary for hover_min_ms..hover_max_ms."""
    windows = _detect_stationary_windows(trajectory, oc.hover_radius_px)
    events: list[LocalEvent] = []

    for start_idx, end_idx in windows:
        duration = trajectory[end_idx].timestamp_ms - trajectory[start_idx].timestamp_ms
        if oc.hover_min_ms <= duration <= oc.hover_max_ms:
            positions = tuple(
                CursorPosition(x=d.x, y=d.y) for d in trajectory[start_idx:end_idx + 1]
            )
            events.append(LocalEvent(
                type="hover",
                time_start_ms=trajectory[start_idx].timestamp_ms,
                time_end_ms=trajectory[end_idx].timestamp_ms,
                cursor_positions=positions,
                confidence=0.6,
                synthesis_method="cursor_stationary",
                description=f"Cursor stationary for {duration:.0f}ms near ({trajectory[start_idx].x:.0f}, {trajectory[start_idx].y:.0f})",
                needs_enrichment=True,
            ))

    return tuple(events)


def _detect_dwells(
    trajectory: tuple[CursorDetection, ...],
    oc: ObserveConfig,
) -> tuple[LocalEvent, ...]:
    """Detect dwell events: stationary for >= dwell_min_ms."""
    windows = _detect_stationary_windows(trajectory, oc.dwell_radius_px)
    events: list[LocalEvent] = []

    for start_idx, end_idx in windows:
        duration = trajectory[end_idx].timestamp_ms - trajectory[start_idx].timestamp_ms
        if duration >= oc.dwell_min_ms:
            positions = tuple(
                CursorPosition(x=d.x, y=d.y) for d in trajectory[start_idx:end_idx + 1]
            )
            events.append(LocalEvent(
                type="dwell",
                time_start_ms=trajectory[start_idx].timestamp_ms,
                time_end_ms=trajectory[end_idx].timestamp_ms,
                cursor_positions=positions,
                confidence=0.7,
                synthesis_method="cursor_stationary_extended",
                description=f"Extended pause ({duration:.0f}ms) near ({trajectory[start_idx].x:.0f}, {trajectory[start_idx].y:.0f})",
                needs_enrichment=True,
            ))

    return tuple(events)


def _detect_thrash(
    trajectory: tuple[CursorDetection, ...],
    oc: ObserveConfig,
) -> tuple[LocalEvent, ...]:
    """Detect cursor thrash: rapid direction changes within a sliding window."""
    if len(trajectory) < 3:
        return ()

    events: list[LocalEvent] = []
    window_ms = oc.thrash_window_ms
    angle_thresh = math.radians(oc.thrash_angle_threshold_deg)

    i = 0
    while i < len(trajectory) - 2:
        window_end_ms = trajectory[i].timestamp_ms + window_ms
        # Collect points in window
        j = i
        while j < len(trajectory) and trajectory[j].timestamp_ms <= window_end_ms:
            j += 1
        window_pts = trajectory[i:j]

        if len(window_pts) < 3:
            i += 1
            continue

        # Count direction changes
        direction_changes = 0
        total_distance = 0.0
        for k in range(1, len(window_pts) - 1):
            dx1 = window_pts[k].x - window_pts[k - 1].x
            dy1 = window_pts[k].y - window_pts[k - 1].y
            dx2 = window_pts[k + 1].x - window_pts[k].x
            dy2 = window_pts[k + 1].y - window_pts[k].y

            total_distance += math.sqrt(dx1 * dx1 + dy1 * dy1)

            mag1 = math.sqrt(dx1 * dx1 + dy1 * dy1)
            mag2 = math.sqrt(dx2 * dx2 + dy2 * dy2)
            if mag1 > 0.5 and mag2 > 0.5:
                cos_angle = (dx1 * dx2 + dy1 * dy2) / (mag1 * mag2)
                cos_angle = max(-1.0, min(1.0, cos_angle))
                angle = math.acos(cos_angle)
                if angle >= angle_thresh:
                    direction_changes += 1

        # Add last segment distance
        if len(window_pts) >= 2:
            dx = window_pts[-1].x - window_pts[-2].x
            dy = window_pts[-1].y - window_pts[-2].y
            total_distance += math.sqrt(dx * dx + dy * dy)

        duration_sec = (window_pts[-1].timestamp_ms - window_pts[0].timestamp_ms) / 1000
        speed = total_distance / duration_sec if duration_sec > 0 else 0

        if direction_changes >= oc.thrash_min_direction_changes and speed >= oc.thrash_min_speed_px_per_sec:
            positions = tuple(CursorPosition(x=d.x, y=d.y) for d in window_pts)
            events.append(LocalEvent(
                type="cursor_thrash",
                time_start_ms=window_pts[0].timestamp_ms,
                time_end_ms=window_pts[-1].timestamp_ms,
                cursor_positions=positions,
                confidence=0.65,
                synthesis_method="direction_change_density",
                description=f"Rapid cursor movement with {direction_changes} direction changes at {speed:.0f}px/s",
                needs_enrichment=False,
            ))
            i = j  # Skip past this window
        else:
            i += 1

    return tuple(events)


def _detect_click_candidates(
    trajectory: tuple[CursorDetection, ...],
    oc: ObserveConfig,
) -> tuple[LocalEvent, ...]:
    """Detect click candidates: brief cursor stop preceded/followed by movement.

    Advances past each detected stop window to avoid emitting duplicate
    click events from overlapping sub-windows of the same stationary period.
    """
    events: list[LocalEvent] = []
    n = len(trajectory)
    i = 1

    while i < n - 1:
        # Find the maximal brief stop starting at i
        stop_start = i
        stop_end = i
        while stop_end + 1 < n:
            dx = trajectory[stop_end + 1].x - trajectory[stop_start].x
            dy = trajectory[stop_end + 1].y - trajectory[stop_start].y
            if math.sqrt(dx * dx + dy * dy) > oc.click_stop_radius_px:
                break
            stop_end += 1

        stop_duration = trajectory[stop_end].timestamp_ms - trajectory[stop_start].timestamp_ms
        if stop_duration > oc.click_stop_max_ms or stop_duration < 0:
            i += 1
            continue

        # Check for movement before and after
        has_movement_before = False
        if stop_start > 0:
            dx = trajectory[stop_start].x - trajectory[stop_start - 1].x
            dy = trajectory[stop_start].y - trajectory[stop_start - 1].y
            has_movement_before = math.sqrt(dx * dx + dy * dy) > oc.click_stop_radius_px

        has_movement_after = False
        if stop_end + 1 < n:
            dx = trajectory[stop_end + 1].x - trajectory[stop_end].x
            dy = trajectory[stop_end + 1].y - trajectory[stop_end].y
            has_movement_after = math.sqrt(dx * dx + dy * dy) > oc.click_stop_radius_px

        if has_movement_before or has_movement_after:
            pos = CursorPosition(x=trajectory[stop_start].x, y=trajectory[stop_start].y)
            events.append(LocalEvent(
                type="click",
                time_start_ms=trajectory[stop_start].timestamp_ms,
                time_end_ms=trajectory[stop_end].timestamp_ms,
                cursor_positions=(pos,),
                confidence=oc.click_min_confidence,
                synthesis_method="brief_stop_pattern",
                description=f"Possible click at ({trajectory[stop_start].x:.0f}, {trajectory[stop_start].y:.0f})",
                needs_enrichment=True,
            ))
            # Skip past this stop window to avoid duplicates
            i = stop_end + 1
        else:
            i += 1

    return tuple(events)


def _detect_scrolls(
    flow_summary: tuple[FlowWindow, ...],
    oc: ObserveConfig,
) -> tuple[LocalEvent, ...]:
    """Detect scroll events from flow windows with high uniformity and vertical direction."""
    events: list[LocalEvent] = []
    vertical_directions = {"N", "S"}

    for fw in flow_summary:
        if (
            fw.flow_uniformity >= oc.scroll_min_flow_uniformity
            and fw.mean_flow_magnitude >= oc.scroll_min_magnitude
            and fw.dominant_direction in vertical_directions
        ):
            direction = "down" if fw.dominant_direction == "S" else "up"
            events.append(LocalEvent(
                type="scroll",
                time_start_ms=fw.start_ms,
                time_end_ms=fw.end_ms,
                cursor_positions=(),
                confidence=0.7,
                synthesis_method="optical_flow_uniformity",
                description=f"Scroll {direction} (flow magnitude: {fw.mean_flow_magnitude:.1f}, uniformity: {fw.flow_uniformity:.2f})",
                needs_enrichment=False,
            ))

    return tuple(events)


def _detect_hesitations(
    trajectory: tuple[CursorDetection, ...],
    click_candidates: tuple[LocalEvent, ...],
    oc: ObserveConfig,
) -> tuple[LocalEvent, ...]:
    """Detect hesitation: pause before an action onset."""
    events: list[LocalEvent] = []
    windows = _detect_stationary_windows(trajectory, oc.hesitation_radius_px)

    # Collect action onset times from click candidates
    action_onsets = {c.time_start_ms for c in click_candidates}

    for start_idx, end_idx in windows:
        duration = trajectory[end_idx].timestamp_ms - trajectory[start_idx].timestamp_ms
        if not (oc.hesitation_min_ms <= duration <= oc.hesitation_max_ms):
            continue

        # Check if followed by an action within a short time
        end_time = trajectory[end_idx].timestamp_ms
        followed_by_action = any(
            0 < (onset - end_time) < 1000 for onset in action_onsets
        )

        if followed_by_action:
            positions = tuple(
                CursorPosition(x=d.x, y=d.y) for d in trajectory[start_idx:end_idx + 1]
            )
            events.append(LocalEvent(
                type="hesitate",
                time_start_ms=trajectory[start_idx].timestamp_ms,
                time_end_ms=trajectory[end_idx].timestamp_ms,
                cursor_positions=positions,
                confidence=0.5,
                synthesis_method="pause_before_action",
                description=f"Hesitation ({duration:.0f}ms) near ({trajectory[start_idx].x:.0f}, {trajectory[start_idx].y:.0f}) before action",
                needs_enrichment=True,
            ))

    return tuple(events)


# ---------------------------------------------------------------------------
# ROI computation
# ---------------------------------------------------------------------------

def _lookup_cursor_at_timestamp(
    trajectory: tuple[CursorDetection, ...],
    timestamp_ms: float,
    tolerance_ms: float = 200.0,
) -> CursorDetection | None:
    """Bisect-based lookup of the nearest cursor detection to timestamp_ms."""
    if not trajectory:
        return None

    timestamps = [d.timestamp_ms for d in trajectory]
    idx = bisect_left(timestamps, timestamp_ms)

    best: CursorDetection | None = None
    best_dist = tolerance_ms

    for candidate_idx in (idx - 1, idx, idx + 1):
        if 0 <= candidate_idx < len(trajectory):
            dist = abs(trajectory[candidate_idx].timestamp_ms - timestamp_ms)
            if dist < best_dist and (trajectory[candidate_idx].detected or trajectory[candidate_idx].confidence > 0):
                best = trajectory[candidate_idx]
                best_dist = dist

    return best


def _compute_analyse_timestamps(
    triage_result: TriageResult,
    config: PipelineConfig,
) -> tuple[float, ...]:
    """Predict the frame timestamps that analyse will extract."""
    timestamps: list[float] = []
    for seg in triage_result.segments:
        duration_sec = (seg.end_ms - seg.start_ms) / 1000
        fps = seg.assigned_fps
        # Approximate: frames at 1/fps intervals
        t = seg.start_ms
        interval_ms = 1000.0 / fps if fps > 0 else 1000.0
        while t <= seg.end_ms:
            timestamps.append(t)
            t += interval_ms
    return tuple(sorted(timestamps))


def compute_roi_rects(
    cursor_trajectory: tuple[CursorDetection, ...],
    frame_timestamps: tuple[float, ...],
    oc: ObserveConfig,
    frame_width: int,
    frame_height: int,
) -> tuple[ROIRect, ...]:
    """Compute ROI crop rectangles centered on cursor position for each frame timestamp."""
    rois: list[ROIRect] = []
    roi_size = oc.roi_size
    padding = oc.roi_padding
    crop_size = roi_size + 2 * padding

    for ts in frame_timestamps:
        detection = _lookup_cursor_at_timestamp(cursor_trajectory, ts)
        if detection is None:
            # No cursor data — use full frame center
            cx, cy = frame_width // 2, frame_height // 2
            rois.append(ROIRect(
                timestamp_ms=ts,
                x=max(0, cx - crop_size // 2),
                y=max(0, cy - crop_size // 2),
                width=min(crop_size, frame_width),
                height=min(crop_size, frame_height),
                cursor_x=float(cx),
                cursor_y=float(cy),
            ))
            continue

        cx = int(detection.x)
        cy = int(detection.y)
        x0 = cx - crop_size // 2
        y0 = cy - crop_size // 2

        # Clamp to frame bounds
        x0 = max(0, min(x0, frame_width - crop_size))
        y0 = max(0, min(y0, frame_height - crop_size))
        w = min(crop_size, frame_width - x0)
        h = min(crop_size, frame_height - y0)

        rois.append(ROIRect(
            timestamp_ms=ts,
            x=x0,
            y=y0,
            width=w,
            height=h,
            cursor_x=detection.x,
            cursor_y=detection.y,
        ))

    return tuple(rois)


# ---------------------------------------------------------------------------
# Event-driven frame selection
# ---------------------------------------------------------------------------

_EVENT_FRAME_RULES: dict[str, tuple[str, ...]] = {
    "click": ("event_start", "event_end"),
    "hover": ("event_start", "event_end"),
    "hesitate": ("event_start", "event_end"),
    "dwell": ("event_mid",),
    "cursor_thrash": ("event_start", "event_end"),
    "scroll": ("event_start", "event_end"),
}

_FULL_FRAME_EVENT_TYPES = frozenset({"scroll"})


def select_frames_for_analysis(
    local_events: tuple[LocalEvent, ...],
    flow_summary: tuple[FlowWindow, ...],
    cursor_trajectory: tuple[CursorDetection, ...],
    video_path: Path,
    oc: ObserveConfig,
    frame_width: int,
    frame_height: int,
    total_duration_ms: float,
) -> tuple[SelectedFrame, ...]:
    """Select frames for LLM analysis based on events, visual changes, and baselines."""
    candidates: list[SelectedFrame] = []

    # --- A. Event frames ---
    for event_idx, event in enumerate(local_events):
        rules = _EVENT_FRAME_RULES.get(event.type, ("event_start", "event_end"))
        use_roi = event.type not in _FULL_FRAME_EVENT_TYPES

        for reason in rules:
            if reason == "event_start":
                ts = event.time_start_ms
            elif reason == "event_end":
                ts = event.time_end_ms
            elif reason == "event_mid":
                ts = (event.time_start_ms + event.time_end_ms) / 2.0
            else:
                continue

            roi = None
            if use_roi:
                roi_rects = compute_roi_rects(
                    cursor_trajectory, (ts,), oc, frame_width, frame_height,
                )
                if roi_rects:
                    roi = roi_rects[0]

            candidates.append(SelectedFrame(
                timestamp_ms=ts,
                reason=reason,
                event_index=event_idx,
                roi=roi,
            ))

    # --- B. Visual change frames ---
    event_timestamps = sorted(c.timestamp_ms for c in candidates)
    gaps = _find_gaps(event_timestamps, total_duration_ms, oc.visual_scan_gap_ms)

    for gap_start, gap_end in gaps:
        gap_frames = extract_frames(
            video_path,
            gap_start / 1000.0,
            gap_end / 1000.0,
            oc.visual_scan_fps,
        )
        if len(gap_frames) < 2:
            continue
        for i in range(len(gap_frames) - 1):
            ts_a, frame_a = gap_frames[i]
            ts_b, frame_b = gap_frames[i + 1]
            magnitude, _ = compute_frame_diff(frame_a, frame_b)
            if magnitude > oc.visual_change_threshold:
                candidates.append(SelectedFrame(timestamp_ms=ts_a, reason="visual_change"))
                candidates.append(SelectedFrame(timestamp_ms=ts_b, reason="visual_change"))

    # --- C. Baseline frames ---
    all_timestamps = sorted(c.timestamp_ms for c in candidates)
    baseline_gaps = _find_gaps(all_timestamps, total_duration_ms, oc.baseline_max_gap_ms)
    for gap_start, gap_end in baseline_gaps:
        mid = (gap_start + gap_end) / 2.0
        candidates.append(SelectedFrame(timestamp_ms=mid, reason="baseline"))

    # --- D. Deduplication ---
    candidates.sort(key=lambda f: f.timestamp_ms)
    deduped = _deduplicate_frames(candidates, oc.frame_dedup_ms)

    return tuple(deduped)


_FRAME_PRIORITY = {"event_start": 0, "event_end": 0, "event_mid": 0, "visual_change": 1, "baseline": 2}


def _deduplicate_frames(
    frames: list[SelectedFrame],
    dedup_ms: float,
) -> list[SelectedFrame]:
    """Remove frames within dedup_ms of each other, keeping highest priority."""
    if not frames:
        return []

    result: list[SelectedFrame] = []
    for frame in frames:
        merged = False
        for i, existing in enumerate(result):
            if abs(frame.timestamp_ms - existing.timestamp_ms) <= dedup_ms:
                # Keep higher priority (lower number)
                frame_pri = _FRAME_PRIORITY.get(frame.reason, 2)
                existing_pri = _FRAME_PRIORITY.get(existing.reason, 2)
                if frame_pri < existing_pri:
                    result[i] = frame
                merged = True
                break
        if not merged:
            result.append(frame)
    return result


def _find_gaps(
    timestamps: list[float],
    total_duration_ms: float,
    min_gap_ms: float,
) -> list[tuple[float, float]]:
    """Find gaps in a sorted list of timestamps that exceed min_gap_ms."""
    gaps: list[tuple[float, float]] = []
    boundaries = [0.0] + sorted(timestamps) + [total_duration_ms]
    for i in range(len(boundaries) - 1):
        gap = boundaries[i + 1] - boundaries[i]
        if gap > min_gap_ms:
            gaps.append((boundaries[i], boundaries[i + 1]))
    return gaps


# ---------------------------------------------------------------------------
# Prompt formatting
# ---------------------------------------------------------------------------

def format_local_events_for_prompt(
    local_events: tuple[LocalEvent, ...],
    segment_start_ms: float,
    segment_end_ms: float,
) -> str:
    """Format local event candidates for injection into the analyse prompt."""
    relevant = [
        e for e in local_events
        if e.time_end_ms >= segment_start_ms and e.time_start_ms <= segment_end_ms and e.needs_enrichment
    ]

    if not relevant:
        return ""

    lines = [
        "## Local Event Candidates",
        "",
        "The following events were detected locally from cursor tracking and optical flow.",
        "Please confirm, reject, or modify each candidate based on what you see in the frames.",
        "",
    ]

    for i, event in enumerate(relevant):
        cursor_info = ""
        if event.cursor_positions:
            p = event.cursor_positions[0]
            cursor_info = f" at cursor ({p.x:.0f}, {p.y:.0f})"
        lines.append(
            f"- **Candidate {i + 1}**: {event.type} | "
            f"{event.time_start_ms:.0f}ms-{event.time_end_ms:.0f}ms | "
            f"confidence={event.confidence:.2f}{cursor_info} | "
            f"{event.description}"
        )

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Visual-change-driven pipeline
# ---------------------------------------------------------------------------


def _bbox_iou(
    a: tuple[int, int, int, int],
    b: tuple[int, int, int, int],
) -> float:
    """Compute IoU between two (x, y, w, h) bounding boxes."""
    ax0, ay0, aw, ah = a
    bx0, by0, bw, bh = b
    ax1, ay1 = ax0 + aw, ay0 + ah
    bx1, by1 = bx0 + bw, by0 + bh

    ix0 = max(ax0, bx0)
    iy0 = max(ay0, by0)
    ix1 = min(ax1, bx1)
    iy1 = min(ay1, by1)

    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0

    inter = (ix1 - ix0) * (iy1 - iy0)
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


def _union_bbox(
    boxes: list[tuple[int, int, int, int]],
) -> tuple[int, int, int, int]:
    """Compute the union bounding box of a list of (x, y, w, h) boxes."""
    if not boxes:
        return (0, 0, 0, 0)
    x0 = min(b[0] for b in boxes)
    y0 = min(b[1] for b in boxes)
    x1 = max(b[0] + b[2] for b in boxes)
    y1 = max(b[1] + b[3] for b in boxes)
    return (x0, y0, x1 - x0, y1 - y0)


def detect_visual_change_events(
    change_frames: tuple[VisualChangeFrame, ...],
    frame_width: int,
    frame_height: int,
    oc: ObserveConfig,
) -> tuple[VisualChangeEvent, ...]:
    """Cluster contiguous VisualChangeFrames into VisualChangeEvents.

    Two consecutive change frames are contiguous if:
    - Adjacent in time (no gap at extraction FPS), AND
    - Spatial overlap (IoU > 0) between any region pair, OR
    - Both exceed scene_change_area_threshold
    """
    if not change_frames:
        return ()

    interval_ms = 1000.0 / oc.change_detect_fps
    max_gap_ms = interval_ms * 1.5  # allow small timing jitter

    clusters: list[list[VisualChangeFrame]] = [[change_frames[0]]]

    for i in range(1, len(change_frames)):
        prev = change_frames[i - 1]
        curr = change_frames[i]

        # Check temporal adjacency
        time_gap = curr.timestamp_a_ms - prev.timestamp_b_ms
        if time_gap > max_gap_ms:
            clusters.append([curr])
            continue

        # Check spatial overlap or both scene-level
        both_large = (
            prev.frame_area_fraction >= oc.scene_change_area_threshold
            and curr.frame_area_fraction >= oc.scene_change_area_threshold
        )

        has_overlap = False
        if not both_large:
            for r_prev in prev.regions:
                for r_curr in curr.regions:
                    iou = _bbox_iou(
                        (r_prev.x, r_prev.y, r_prev.width, r_prev.height),
                        (r_curr.x, r_curr.y, r_curr.width, r_curr.height),
                    )
                    if iou > 0:
                        has_overlap = True
                        break
                if has_overlap:
                    break

        if both_large or has_overlap:
            clusters[-1].append(curr)
        else:
            clusters.append([curr])

    events: list[VisualChangeEvent] = []
    for cluster in clusters:
        time_start = cluster[0].timestamp_a_ms
        time_end = cluster[-1].timestamp_b_ms
        duration = time_end - time_start
        peak_fraction = max(f.frame_area_fraction for f in cluster)

        all_boxes = [
            (r.x, r.y, r.width, r.height)
            for f in cluster for r in f.regions
        ]
        bbox = _union_bbox(all_boxes)

        # Classify
        if duration > oc.continuous_change_max_duration_ms:
            # Check area stability for continuous vs load
            fractions = [f.frame_area_fraction for f in cluster]
            mean_frac = sum(fractions) / len(fractions)
            variance = sum((x - mean_frac) ** 2 for x in fractions) / len(fractions)
            std_frac = math.sqrt(variance)
            # Stable area → continuous; growing area → treat as scene_change
            if std_frac < mean_frac * 0.5:
                category = "continuous_change"
            else:
                category = "scene_change"
        elif peak_fraction >= oc.scene_change_area_threshold:
            category = "scene_change"
        else:
            category = "local_change"

        events.append(VisualChangeEvent(
            time_start_ms=time_start,
            time_end_ms=time_end,
            frames=tuple(cluster),
            peak_changed_area_fraction=peak_fraction,
            bounding_box=bbox,
            category=category,
        ))

    return tuple(events)


def detect_flow_events(
    flow_summary: tuple[FlowWindow, ...],
    oc: ObserveConfig,
) -> tuple[FlowEvent, ...]:
    """Convert flow windows into discrete FlowEvents.

    Scan consecutive windows where uniformity >= threshold and magnitude >= threshold
    persist across 2+ windows. Merge contiguous events with same direction.
    """
    if len(flow_summary) < 2:
        return ()

    events: list[FlowEvent] = []
    vertical = {"N", "S"}
    horizontal = {"E", "W"}

    i = 0
    while i < len(flow_summary):
        fw = flow_summary[i]
        if (
            fw.flow_uniformity >= oc.scroll_min_flow_uniformity
            and fw.mean_flow_magnitude >= oc.scroll_min_magnitude
        ):
            # Start of a potential flow event — extend while condition holds
            run = [fw]
            j = i + 1
            while j < len(flow_summary):
                nxt = flow_summary[j]
                if (
                    nxt.flow_uniformity >= oc.scroll_min_flow_uniformity
                    and nxt.mean_flow_magnitude >= oc.scroll_min_magnitude
                ):
                    run.append(nxt)
                    j += 1
                else:
                    break

            if len(run) >= 2:
                mean_mag = sum(w.mean_flow_magnitude for w in run) / len(run)
                mean_uni = sum(w.flow_uniformity for w in run) / len(run)

                # Dominant direction: most common across run
                dir_counts: dict[str, int] = {}
                for w in run:
                    dir_counts[w.dominant_direction] = dir_counts.get(w.dominant_direction, 0) + 1
                dominant = max(dir_counts, key=lambda d: dir_counts[d])

                if dominant in vertical and mean_uni >= oc.scroll_min_flow_uniformity:
                    cat = "scroll"
                elif dominant in horizontal and mean_uni >= oc.scroll_min_flow_uniformity:
                    cat = "pan"
                else:
                    cat = "mixed"

                events.append(FlowEvent(
                    time_start_ms=run[0].start_ms,
                    time_end_ms=run[-1].end_ms,
                    dominant_direction=dominant,
                    mean_magnitude=mean_mag,
                    flow_uniformity=mean_uni,
                    category=cat,
                ))
                i = j
                continue
        i += 1

    # Merge contiguous events with same direction
    if len(events) < 2:
        return tuple(events)

    merged: list[FlowEvent] = [events[0]]
    for ev in events[1:]:
        prev = merged[-1]
        if ev.dominant_direction == prev.dominant_direction and ev.category == prev.category:
            gap = ev.time_start_ms - prev.time_end_ms
            if gap <= oc.flow_window_step_ms * 1.5:
                total_dur = ev.time_end_ms - prev.time_start_ms
                prev_dur = prev.time_end_ms - prev.time_start_ms
                ev_dur = ev.time_end_ms - ev.time_start_ms
                merged[-1] = FlowEvent(
                    time_start_ms=prev.time_start_ms,
                    time_end_ms=ev.time_end_ms,
                    dominant_direction=prev.dominant_direction,
                    mean_magnitude=(prev.mean_magnitude * prev_dur + ev.mean_magnitude * ev_dur) / total_dur if total_dur > 0 else prev.mean_magnitude,
                    flow_uniformity=(prev.flow_uniformity + ev.flow_uniformity) / 2,
                    category=prev.category,
                )
                continue
        merged.append(ev)

    return tuple(merged)


def detect_cursor_stops(
    trajectory: tuple[CursorDetection, ...],
    oc: ObserveConfig,
) -> tuple[tuple[float, float, float, float], ...]:
    """Detect significant cursor stops: stationary for >= cursor_stop_min_ms.

    Returns (start_ms, end_ms, x, y) tuples.
    """
    detected = tuple(d for d in trajectory if d.detected or d.confidence > 0)
    if not detected:
        return ()

    windows = _detect_stationary_windows(detected, oc.cursor_stop_radius_px)
    stops: list[tuple[float, float, float, float]] = []

    for start_idx, end_idx in windows:
        duration = detected[end_idx].timestamp_ms - detected[start_idx].timestamp_ms
        if duration >= oc.cursor_stop_min_ms:
            stops.append((
                detected[start_idx].timestamp_ms,
                detected[end_idx].timestamp_ms,
                detected[start_idx].x,
                detected[start_idx].y,
            ))

    return tuple(stops)


def _time_ranges_overlap(
    a_start: float, a_end: float,
    b_start: float, b_end: float,
) -> bool:
    """Check if two time ranges overlap."""
    return a_start < b_end and b_start < a_end


def _per_frame_tokens(
    category: str,
    visual_change: VisualChangeEvent | None,
    frame_width: int,
    frame_height: int,
    roi_min_size: int,
    roi_padding: int,
) -> int:
    """Token cost of a single image for this moment type."""
    from src.gemini import estimate_image_tokens

    # Full-frame categories (Pass 1), and pre_scene_change without a known
    # change region (the trigger element could be anywhere on the page)
    if category in ("scene_change", "scroll", "continuous", "baseline"):
        return estimate_image_tokens(frame_width, frame_height)
    if category == "pre_scene_change" and visual_change is None:
        return estimate_image_tokens(frame_width, frame_height)

    # ROI-cropped categories (Pass 2)
    if visual_change is not None:
        _bx, _by, bw, bh = visual_change.bounding_box
        roi_w = min(max(roi_min_size, bw + 2 * roi_padding), frame_width)
        roi_h = min(max(roi_min_size, bh + 2 * roi_padding), frame_height)
    else:
        size = roi_min_size + 2 * roi_padding
        roi_w = min(size, frame_width)
        roi_h = min(size, frame_height)

    return estimate_image_tokens(roi_w, roi_h)


def _base_frame_count(category: str, visual_change: VisualChangeEvent | None) -> int:
    """Minimum frame count for a moment category."""
    if category == "pre_scene_change":
        return 2
    if category == "interaction" and visual_change is not None:
        return 2
    return 1


def _ideal_frame_count(
    category: str,
    visual_change: VisualChangeEvent | None,
    duration_ms: float,
    sample_interval_ms: int,
    max_frames: int,
) -> int:
    """Activity-based frame count: more frames for longer moments."""
    base = _base_frame_count(category, visual_change)
    if sample_interval_ms <= 0 or duration_ms <= 0:
        return base

    if category == "pre_scene_change" or (category == "interaction" and visual_change is not None):
        # before + evenly spaced intermediates + after
        intermediates = max(0, int(duration_ms / sample_interval_ms) - 1)
        count = 2 + intermediates
    else:
        count = max(1, math.ceil(duration_ms / sample_interval_ms))

    if max_frames > 0:
        count = min(count, max_frames)
    return max(base, count)


def _estimate_moment_tokens(
    category: str,
    visual_change: VisualChangeEvent | None,
    frame_width: int,
    frame_height: int,
    roi_min_size: int,
    roi_padding: int,
    frame_count: int = 0,
) -> int:
    """Estimate total token cost for a moment.

    When *frame_count* is 0 the default for the category is used (2 for
    interactions, 1 for everything else).
    """
    if frame_count <= 0:
        frame_count = _base_frame_count(category, visual_change)
    return _per_frame_tokens(
        category, visual_change, frame_width, frame_height,
        roi_min_size, roi_padding,
    ) * frame_count


def detect_moments(
    visual_changes: tuple[VisualChangeEvent, ...],
    flow_events: tuple[FlowEvent, ...],
    cursor_stops: tuple[tuple[float, float, float, float], ...],
    dwells: tuple[LocalEvent, ...],
    thrashes: tuple[LocalEvent, ...],
    trajectory: tuple[CursorDetection, ...],
    oc: ObserveConfig,
    frame_width: int,
    frame_height: int,
    duration_ms: float,
) -> tuple[Moment, ...]:
    """Combine timelines into moments and apply budget-based selection.

    Implements spec steps 1-9.
    """
    candidates: list[Moment] = []
    used_time_ranges: list[tuple[float, float]] = []

    enabled_cats = set(oc.moment_categories)
    min_vc_dur = oc.min_visual_change_duration_ms

    # Step 1-3: Visual change events → moment candidates, subtract scrolls
    for vc in visual_changes:
        # Duration filter — skip transient changes
        if min_vc_dur > 0 and (vc.time_end_ms - vc.time_start_ms) < min_vc_dur:
            continue

        # Step 2: Check if overlapping with a flow event (scroll)
        overlapping_flow = None
        for fe in flow_events:
            if _time_ranges_overlap(vc.time_start_ms, vc.time_end_ms, fe.time_start_ms, fe.time_end_ms):
                overlapping_flow = fe
                break

        if overlapping_flow is not None:
            # Scroll moment — self-describing
            candidates.append(Moment(
                time_start_ms=vc.time_start_ms,
                time_end_ms=vc.time_end_ms,
                visual_change=vc,
                flow_event=overlapping_flow,
                category="scroll",
                priority=2,
                estimated_tokens=_estimate_moment_tokens(
                    "scroll", vc, frame_width, frame_height,
                    oc.roi_min_size, oc.roi_padding,
                ),
                frame_count=_base_frame_count("scroll", vc),
            ))
            used_time_ranges.append((vc.time_start_ms, vc.time_end_ms))
            continue

        # Step 3: Classify by VisualChangeEvent.category
        cursor_before = None
        cursor_after = None
        cursor_associated = False

        # Step 4: Attach cursor context
        if trajectory:
            det_before = _lookup_cursor_at_timestamp(trajectory, vc.time_start_ms - 500, tolerance_ms=600)
            det_after = _lookup_cursor_at_timestamp(trajectory, vc.time_end_ms, tolerance_ms=600)
            if det_before is not None:
                cursor_before = CursorPosition(x=det_before.x, y=det_before.y)
            if det_after is not None:
                cursor_after = CursorPosition(x=det_after.x, y=det_after.y)

            # Check if cursor is near the change region
            bbox_x, bbox_y, bbox_w, bbox_h = vc.bounding_box
            padding = oc.roi_padding
            for det in (det_before, det_after):
                if det is not None:
                    if (bbox_x - padding <= det.x <= bbox_x + bbox_w + padding and
                            bbox_y - padding <= det.y <= bbox_y + bbox_h + padding):
                        cursor_associated = True
                        break

        if vc.category == "scene_change":
            cat, pri = "scene_change", 0
        elif vc.category == "continuous_change":
            cat, pri = "continuous", 2
        else:  # local_change
            cat, pri = "interaction", 1

        candidates.append(Moment(
            time_start_ms=vc.time_start_ms,
            time_end_ms=vc.time_end_ms,
            visual_change=vc,
            cursor_before=cursor_before,
            cursor_after=cursor_after,
            cursor_associated=cursor_associated,
            category=cat,
            priority=pri,
            estimated_tokens=_estimate_moment_tokens(
                cat, vc, frame_width, frame_height,
                oc.roi_min_size, oc.roi_padding,
            ),
            frame_count=_base_frame_count(cat, vc),
        ))
        used_time_ranges.append((vc.time_start_ms, vc.time_end_ms))

        # Companion: capture the window just before a scene change so
        # Pass 2 can identify what triggered the navigation.
        if vc.category == "scene_change" and "pre_scene_change" in enabled_cats:
            anchor_ms = vc.frames[0].timestamp_a_ms if vc.frames else vc.time_start_ms
            pre_start = max(0, anchor_ms - 500)
            pre_end = anchor_ms

            # Cursor at the moment of the trigger — may be None
            pre_cursor: CursorPosition | None = None
            pre_cursor_assoc = False
            if trajectory:
                det = _lookup_cursor_at_timestamp(trajectory, anchor_ms, tolerance_ms=600)
                if det is not None:
                    pre_cursor = CursorPosition(x=det.x, y=det.y)
                    pre_cursor_assoc = True

            candidates.append(Moment(
                time_start_ms=pre_start,
                time_end_ms=pre_end,
                cursor_before=pre_cursor,
                cursor_associated=pre_cursor_assoc,
                category="pre_scene_change",
                priority=1,
                estimated_tokens=_estimate_moment_tokens(
                    "pre_scene_change", None, frame_width, frame_height,
                    oc.roi_min_size, oc.roi_padding,
                ),
                frame_count=2,
            ))

    # Step 5: Add cursor_stop moments not overlapping existing
    for start_ms, end_ms, cx, cy in cursor_stops:
        overlaps = any(
            _time_ranges_overlap(start_ms, end_ms, ur[0], ur[1])
            for ur in used_time_ranges
        )
        if not overlaps:
            candidates.append(Moment(
                time_start_ms=start_ms,
                time_end_ms=end_ms,
                cursor_before=CursorPosition(x=cx, y=cy),
                cursor_associated=True,
                category="cursor_stop",
                priority=3,
                estimated_tokens=_estimate_moment_tokens(
                    "cursor_stop", None, frame_width, frame_height,
                    oc.roi_min_size, oc.roi_padding,
                ),
                frame_count=1,
            ))
            used_time_ranges.append((start_ms, end_ms))

    # Step 6: Add cursor-only moments from dwells/thrashes
    for event in (*dwells, *thrashes):
        overlaps = any(
            _time_ranges_overlap(event.time_start_ms, event.time_end_ms, ur[0], ur[1])
            for ur in used_time_ranges
        )
        if not overlaps:
            cursor_pos = None
            if event.cursor_positions:
                p = event.cursor_positions[0]
                cursor_pos = CursorPosition(x=p.x, y=p.y)
            candidates.append(Moment(
                time_start_ms=event.time_start_ms,
                time_end_ms=event.time_end_ms,
                cursor_before=cursor_pos,
                cursor_associated=cursor_pos is not None,
                category="cursor_only",
                priority=4,
                estimated_tokens=_estimate_moment_tokens(
                    "cursor_only", None, frame_width, frame_height,
                    oc.roi_min_size, oc.roi_padding,
                ),
                frame_count=1,
            ))
            used_time_ranges.append((event.time_start_ms, event.time_end_ms))

    # Step 7: Merge adjacent candidates
    candidates.sort(key=lambda m: m.time_start_ms)
    merged: list[Moment] = []
    for m in candidates:
        if merged and (m.time_start_ms - merged[-1].time_end_ms) <= oc.moment_merge_gap_ms:
            prev = merged[-1]
            # Keep higher priority (lower number)
            best_pri = min(prev.priority, m.priority)
            best_cat = prev.category if prev.priority <= m.priority else m.category
            merged_vc = prev.visual_change or m.visual_change
            merged_base = _base_frame_count(best_cat, merged_vc)
            merged[-1] = Moment(
                time_start_ms=prev.time_start_ms,
                time_end_ms=max(prev.time_end_ms, m.time_end_ms),
                visual_change=merged_vc,
                flow_event=prev.flow_event or m.flow_event,
                cursor_before=prev.cursor_before or m.cursor_before,
                cursor_after=m.cursor_after or prev.cursor_after,
                cursor_associated=prev.cursor_associated or m.cursor_associated,
                category=best_cat,
                priority=best_pri,
                estimated_tokens=_estimate_moment_tokens(
                    best_cat, merged_vc, frame_width, frame_height,
                    oc.roi_min_size, oc.roi_padding, merged_base,
                ),
                frame_count=merged_base,
            )
        else:
            merged.append(m)

    # Category filter — drop disabled categories after merging
    merged = [m for m in merged if m.category in enabled_cats]

    # Step 8: Budget-based selection
    budget = (duration_ms / 60000.0) * oc.token_budget_per_minute

    # Scene changes always included (if enabled)
    selected: list[Moment] = [m for m in merged if m.category == "scene_change"]
    remaining = [m for m in merged if m.category != "scene_change"]
    used_budget = sum(m.estimated_tokens for m in selected)

    # Fill by priority order
    remaining.sort(key=lambda m: (m.priority, m.time_start_ms))
    for m in remaining:
        if used_budget + m.estimated_tokens <= budget:
            selected.append(m)
            used_budget += m.estimated_tokens

    # Step 9: Add baseline moments in gaps > baseline_max_gap_ms
    if "baseline" in enabled_cats:
        selected.sort(key=lambda m: m.time_start_ms)
        all_times = [0.0] + [m.time_start_ms for m in selected] + [m.time_end_ms for m in selected] + [duration_ms]
        all_times.sort()

        baseline_tokens = _estimate_moment_tokens(
            "baseline", None, frame_width, frame_height,
            oc.roi_min_size, oc.roi_padding,
        )
        baselines: list[Moment] = []
        for i in range(len(all_times) - 1):
            gap = all_times[i + 1] - all_times[i]
            if gap > oc.baseline_max_gap_ms:
                mid = (all_times[i] + all_times[i + 1]) / 2.0
                baseline = Moment(
                    time_start_ms=mid,
                    time_end_ms=mid,
                    category="baseline",
                    priority=5,
                    estimated_tokens=baseline_tokens,
                    frame_count=1,
                )
                if used_budget + baseline_tokens <= budget:
                    baselines.append(baseline)
                    used_budget += baseline_tokens

        selected.extend(baselines)

    selected.sort(key=lambda m: m.time_start_ms)

    # Step 10: Density cap — keep highest priority if over limit
    max_per_min = oc.max_moments_per_minute
    if max_per_min > 0:
        max_moments = max(1, int((duration_ms / 60000.0) * max_per_min))
        if len(selected) > max_moments:
            selected.sort(key=lambda m: (m.priority, m.time_start_ms))
            selected = selected[:max_moments]
            selected.sort(key=lambda m: m.time_start_ms)

    # Step 11: Distribute extra frames from remaining budget
    #
    # Moments were selected at base frame counts (1 or 2).  When
    # moment_sample_interval_ms is set, compute the ideal (activity-based)
    # frame count for each moment and upgrade as many as the remaining budget
    # allows, longest moments first.
    if oc.moment_sample_interval_ms > 0:
        remaining_budget = budget - sum(m.estimated_tokens for m in selected)

        # Build upgrade candidates: (index, extra_frames_wanted, per_frame_cost)
        upgrades: list[tuple[int, int, int]] = []
        for i, m in enumerate(selected):
            ideal = _ideal_frame_count(
                m.category, m.visual_change,
                m.time_end_ms - m.time_start_ms,
                oc.moment_sample_interval_ms, oc.moment_max_frames,
            )
            extra = ideal - m.frame_count
            if extra > 0:
                pf = _per_frame_tokens(
                    m.category, m.visual_change, frame_width, frame_height,
                    oc.roi_min_size, oc.roi_padding,
                )
                upgrades.append((i, extra, pf))

        # Longest moments benefit most from extra frames
        upgrades.sort(key=lambda u: -(selected[u[0]].time_end_ms - selected[u[0]].time_start_ms))

        for idx, extra_wanted, pf_cost in upgrades:
            granted = 0
            for _ in range(extra_wanted):
                if remaining_budget >= pf_cost:
                    granted += 1
                    remaining_budget -= pf_cost
                else:
                    break
            if granted > 0:
                m = selected[idx]
                new_count = m.frame_count + granted
                selected[idx] = m.model_copy(update={
                    "frame_count": new_count,
                    "estimated_tokens": _estimate_moment_tokens(
                        m.category, m.visual_change, frame_width, frame_height,
                        oc.roi_min_size, oc.roi_padding, new_count,
                    ),
                })

    return tuple(selected)


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------

def run_observe(
    session: SessionManifest,
    config: PipelineConfig,
    triage_result: TriageResult | None,
    video_path: Path,
    base_dir: Path = Path("."),
) -> ObserveResult:
    """Run the observe stage: cursor tracking, optical flow, event synthesis, frame selection."""
    t0 = time.monotonic()

    oc = config.observe
    meta = get_video_metadata(video_path)
    total_duration_ms = (
        triage_result.total_duration_ms if triage_result is not None else meta.duration_ms
    )

    if oc.visual_change_driven:
        return _run_observe_visual_change(
            session, config, triage_result, video_path, base_dir,
            oc, meta, total_duration_ms, t0,
        )

    log(f"  Observe: tracking cursor (adaptive 2-pass)...")
    t_step = time.monotonic()
    cursor_trajectory = track_cursor(video_path, triage_result, oc, base_dir, total_duration_ms)
    t_track = (time.monotonic() - t_step) * 1000

    detected_count = sum(1 for d in cursor_trajectory if d.detected)
    detection_rate = detected_count / len(cursor_trajectory) if cursor_trajectory else 0.0
    log(f"  Observe: cursor detected in {detected_count}/{len(cursor_trajectory)} frames ({detection_rate:.1%}) [{t_track:.0f}ms]")

    log(f"  Observe: computing optical flow...")
    t_step = time.monotonic()
    flow_summary = compute_flow_summaries(video_path, triage_result, cursor_trajectory, oc, total_duration_ms)
    t_flow = (time.monotonic() - t_step) * 1000
    log(f"  Observe: {len(flow_summary)} flow windows [{t_flow:.0f}ms]")

    t_step = time.monotonic()
    local_events = synthesize_local_events(cursor_trajectory, flow_summary, oc)
    t_synth = (time.monotonic() - t_step) * 1000
    log(f"  Observe: {len(local_events)} local events synthesized [{t_synth:.0f}ms]")

    # Frame selection (replaces _compute_analyse_timestamps + compute_roi_rects)
    t_step = time.monotonic()
    selected_frames = select_frames_for_analysis(
        local_events, flow_summary, cursor_trajectory,
        video_path, oc, meta.width, meta.height, total_duration_ms,
    )
    t_select = (time.monotonic() - t_step) * 1000
    log(f"  Observe: {len(selected_frames)} frames selected [{t_select:.0f}ms]")

    # Legacy ROI rects for backward compatibility with triage-based analyse
    roi_rects: tuple[ROIRect, ...] = ()
    if triage_result is not None:
        analyse_timestamps = _compute_analyse_timestamps(triage_result, config)
        roi_rects = compute_roi_rects(
            cursor_trajectory, analyse_timestamps, oc, meta.width, meta.height,
        )

    elapsed = (time.monotonic() - t0) * 1000
    log(f"  Observe: total {elapsed:.0f}ms (track={t_track:.0f} flow={t_flow:.0f} synth={t_synth:.0f} select={t_select:.0f})")

    return ObserveResult(
        recording_id=session.identifier,
        cursor_trajectory=cursor_trajectory,
        flow_summary=flow_summary,
        local_events=local_events,
        roi_rects=roi_rects,
        selected_frames=selected_frames,
        processing_time_ms=elapsed,
        frames_analysed=len(cursor_trajectory),
        cursor_detection_rate=detection_rate,
    )


def _run_observe_visual_change(
    session: SessionManifest,
    config: PipelineConfig,
    triage_result: TriageResult | None,
    video_path: Path,
    base_dir: Path,
    oc: ObserveConfig,
    meta: VideoMetadata,
    total_duration_ms: float,
    t0: float,
) -> ObserveResult:
    """Visual-change-driven observe path."""
    # Cursor tracking (optional)
    cursor_trajectory: tuple[CursorDetection, ...] = ()
    detection_rate = 0.0

    if oc.cursor_tracking_enabled:
        log(f"  Observe (visual-change): tracking cursor...")
        t_step = time.monotonic()
        cursor_trajectory = track_cursor(video_path, triage_result, oc, base_dir, total_duration_ms)
        t_track = (time.monotonic() - t_step) * 1000
        detected_count = sum(1 for d in cursor_trajectory if d.detected)
        detection_rate = detected_count / len(cursor_trajectory) if cursor_trajectory else 0.0
        log(f"  Observe (visual-change): cursor {detected_count}/{len(cursor_trajectory)} ({detection_rate:.1%}) [{t_track:.0f}ms]")
    else:
        log(f"  Observe (visual-change): cursor tracking disabled")

    # Visual change detection
    log(f"  Observe (visual-change): detecting visual changes at {oc.change_detect_fps} FPS...")
    t_step = time.monotonic()
    change_frames = detect_visual_changes(
        video_path,
        fps=oc.change_detect_fps,
        pixel_threshold=oc.change_pixel_threshold,
        min_area_px=oc.change_min_area_px,
        blur_kernel=oc.change_blur_kernel,
        morph_kernel=oc.change_morph_kernel,
        scale_height=oc.resolution_height,
    )
    t_vc = (time.monotonic() - t_step) * 1000
    log(f"  Observe (visual-change): {len(change_frames)} change frames [{t_vc:.0f}ms]")

    visual_changes = detect_visual_change_events(
        change_frames, meta.width, meta.height, oc,
    )
    log(f"  Observe (visual-change): {len(visual_changes)} visual change events")

    # Optical flow
    log(f"  Observe (visual-change): computing optical flow...")
    t_step = time.monotonic()
    flow_summary = compute_flow_summaries(video_path, triage_result, cursor_trajectory, oc, total_duration_ms)
    t_flow = (time.monotonic() - t_step) * 1000
    log(f"  Observe (visual-change): {len(flow_summary)} flow windows [{t_flow:.0f}ms]")

    flow_evts = detect_flow_events(flow_summary, oc)
    log(f"  Observe (visual-change): {len(flow_evts)} flow events")

    # Cursor stops
    cursor_stops = detect_cursor_stops(cursor_trajectory, oc)
    log(f"  Observe (visual-change): {len(cursor_stops)} cursor stops")

    # Dwells and thrashes (reuse existing detectors)
    detected_traj = tuple(d for d in cursor_trajectory if d.detected or d.confidence > 0)
    dwells = _detect_dwells(detected_traj, oc) if detected_traj else ()
    thrashes = _detect_thrash(detected_traj, oc) if detected_traj else ()

    # Moment detection
    t_step = time.monotonic()
    moments = detect_moments(
        visual_changes, flow_evts, cursor_stops, dwells, thrashes,
        cursor_trajectory, oc, meta.width, meta.height, total_duration_ms,
    )
    t_moments = (time.monotonic() - t_step) * 1000
    log(f"  Observe (visual-change): {len(moments)} moments [{t_moments:.0f}ms]")

    # Budget tracking
    token_budget = int((total_duration_ms / 60000.0) * oc.token_budget_per_minute)
    token_budget_used = sum(m.estimated_tokens for m in moments)

    # Log moment breakdown
    cat_counts: dict[str, int] = {}
    for m in moments:
        cat_counts[m.category] = cat_counts.get(m.category, 0) + 1
    usage_pct = (token_budget_used / token_budget * 100) if token_budget > 0 else 0.0
    log(f"  Observe (visual-change): moment breakdown: {cat_counts}")
    log(f"  Observe (visual-change): token budget {token_budget_used:,}/{token_budget:,} ({usage_pct:.1f}%)")

    elapsed = (time.monotonic() - t0) * 1000

    return ObserveResult(
        recording_id=session.identifier,
        cursor_trajectory=cursor_trajectory,
        flow_summary=flow_summary,
        visual_changes=visual_changes,
        flow_events=flow_evts,
        moments=moments,
        token_budget=token_budget,
        token_budget_used=token_budget_used,
        processing_time_ms=elapsed,
        frames_analysed=len(cursor_trajectory) if cursor_trajectory else len(change_frames),
        cursor_detection_rate=detection_rate,
    )
