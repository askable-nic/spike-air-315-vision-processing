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
    CursorDetection,
    CursorPosition,
    FlowWindow,
    LocalEvent,
    ObserveConfig,
    ObserveResult,
    PipelineConfig,
    ROIRect,
    SessionManifest,
    TriageResult,
)
from src.video import compute_optical_flow, extract_frames, get_video_metadata


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


def track_cursor(
    video_path: Path,
    triage_result: TriageResult,
    oc: ObserveConfig,
    base_dir: Path = Path("."),
) -> tuple[CursorDetection, ...]:
    """Track cursor across the full recording at tracking_fps.

    Frames are extracted at oc.resolution_height but downscaled to _MATCH_HEIGHT
    for template matching.  Detected coordinates are mapped back to source resolution.
    """
    templates = load_templates(base_dir / "cursor_templates", base_dir)
    if not templates:
        return ()

    meta = get_video_metadata(video_path)

    total_start = 0.0
    total_end = triage_result.total_duration_ms / 1000.0

    raw_frames = extract_frames(
        video_path,
        total_start,
        total_end,
        oc.tracking_fps,
        scale_height=_MATCH_HEIGHT,
    )

    # Scale factor: from match resolution back to source
    scale_factor = meta.height / _MATCH_HEIGHT if _MATCH_HEIGHT > 0 else 1.0

    total_frames = len(raw_frames)
    log(f"  Observe: matching {total_frames} frames against {len(templates)} templates × {len(oc.template_scales)} scales at {_MATCH_HEIGHT}p...")

    # Pre-scale templates once
    all_prescaled = _prescale_templates(templates, oc.template_scales)

    detections: list[CursorDetection] = []
    log_interval = max(1, total_frames // 10)

    # Temporal coherence: try last-matched template+scale first
    last_match_id: str | None = None

    for idx, (ts_ms, frame) in enumerate(raw_frames):
        if idx > 0 and idx % log_interval == 0:
            detected_so_far = sum(1 for d in detections if d.detected)
            log(f"  Observe: {idx}/{total_frames} frames ({detected_so_far} detections)")

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame

        # Try last-matched template first for speed
        match: MatchResult | None = None
        if last_match_id is not None:
            priority = tuple(e for e in all_prescaled if e.template.template_id == last_match_id)
            if priority:
                match = match_cursor_in_frame(
                    gray, priority, oc.match_threshold, oc.early_exit_threshold,
                )

        # Fall back to full search
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

    interpolated = interpolate_trajectory(tuple(detections), oc.max_interpolation_gap_ms)
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
    triage_result: TriageResult,
    cursor_trajectory: tuple[CursorDetection, ...],
    oc: ObserveConfig,
) -> tuple[FlowWindow, ...]:
    """Compute optical flow summaries in sliding windows across the recording."""
    total_end = triage_result.total_duration_ms / 1000.0
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
    total_ms = triage_result.total_duration_ms

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
    hesitations = _detect_hesitations(detected, click_candidates, oc)

    events.extend(filtered_hovers)
    events.extend(dwells)
    events.extend(click_candidates)
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
    """Detect click candidates: brief cursor stop preceded/followed by movement."""
    events: list[LocalEvent] = []
    n = len(trajectory)

    for i in range(1, n - 1):
        # Find brief stops
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
# Top-level orchestrator
# ---------------------------------------------------------------------------

def run_observe(
    session: SessionManifest,
    config: PipelineConfig,
    triage_result: TriageResult,
    video_path: Path,
    base_dir: Path = Path("."),
) -> ObserveResult:
    """Run the observe stage: cursor tracking, optical flow, event synthesis, ROI computation."""
    t0 = time.monotonic()

    oc = config.observe
    meta = get_video_metadata(video_path)

    log(f"  Observe: tracking cursor...")
    t_step = time.monotonic()
    cursor_trajectory = track_cursor(video_path, triage_result, oc, base_dir)
    t_track = (time.monotonic() - t_step) * 1000

    detected_count = sum(1 for d in cursor_trajectory if d.detected)
    detection_rate = detected_count / len(cursor_trajectory) if cursor_trajectory else 0.0
    log(f"  Observe: cursor detected in {detected_count}/{len(cursor_trajectory)} frames ({detection_rate:.1%}) [{t_track:.0f}ms]")

    log(f"  Observe: computing optical flow...")
    t_step = time.monotonic()
    flow_summary = compute_flow_summaries(video_path, triage_result, cursor_trajectory, oc)
    t_flow = (time.monotonic() - t_step) * 1000
    log(f"  Observe: {len(flow_summary)} flow windows [{t_flow:.0f}ms]")

    t_step = time.monotonic()
    local_events = synthesize_local_events(cursor_trajectory, flow_summary, oc)
    t_synth = (time.monotonic() - t_step) * 1000
    log(f"  Observe: {len(local_events)} local events synthesized [{t_synth:.0f}ms]")

    t_step = time.monotonic()
    analyse_timestamps = _compute_analyse_timestamps(triage_result, config)
    roi_rects = compute_roi_rects(
        cursor_trajectory, analyse_timestamps, oc, meta.width, meta.height,
    )
    t_roi = (time.monotonic() - t_step) * 1000
    log(f"  Observe: {len(roi_rects)} ROI rects [{t_roi:.0f}ms]")

    elapsed = (time.monotonic() - t0) * 1000
    log(f"  Observe: total {elapsed:.0f}ms (track={t_track:.0f} flow={t_flow:.0f} synth={t_synth:.0f} roi={t_roi:.0f})")

    return ObserveResult(
        recording_id=session.identifier,
        cursor_trajectory=cursor_trajectory,
        flow_summary=flow_summary,
        local_events=local_events,
        roi_rects=roi_rects,
        processing_time_ms=elapsed,
        frames_analysed=len(cursor_trajectory),
        cursor_detection_rate=detection_rate,
    )
