from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import NamedTuple

import cv2
import numpy as np

from vex_extract.config import CursorConfig
from vex_extract.models import CursorDetection, FlowWindow
from vex_extract.video import extract_frames, get_video_metadata

logger = logging.getLogger(__name__)


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


class MatchCandidate(NamedTuple):
    """A cursor candidate at match resolution, before scaling."""
    x: float
    y: float
    confidence: float
    template_id: str


class _PrescaledEntry(NamedTuple):
    template: TemplateInfo
    scale: float
    image: np.ndarray


def load_templates(templates_dir: Path) -> tuple[TemplateInfo, ...]:
    """Load cursor template PNGs and metadata from templates_dir."""
    meta_path = templates_dir / "metadata.json"
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


def _prescale_templates(
    templates: tuple[TemplateInfo, ...],
    scales: tuple[float, ...],
    resample_down: str = "area",
    resample_up: str = "nearest",
) -> tuple[_PrescaledEntry, ...]:
    """Pre-compute scaled template images for all template/scale combos."""
    from vex_extract.video import _INTERPOLATION_FLAGS
    interp_down = _INTERPOLATION_FLAGS.get(resample_down, cv2.INTER_AREA)
    interp_up = _INTERPOLATION_FLAGS.get(resample_up, cv2.INTER_NEAREST)

    entries: list[_PrescaledEntry] = []
    for tmpl in templates:
        for scale in scales:
            th, tw = tmpl.image.shape[:2]
            sh = max(1, int(th * scale))
            sw = max(1, int(tw * scale))
            interp = interp_down if scale < 1.0 else interp_up
            scaled_img = cv2.resize(tmpl.image, (sw, sh), interpolation=interp)
            entries.append(_PrescaledEntry(template=tmpl, scale=scale, image=scaled_img))
    return tuple(entries)


def match_cursor_in_frame(
    gray_frame: np.ndarray,
    prescaled: tuple[_PrescaledEntry, ...],
    threshold: float,
    early_exit_threshold: float = 0.9,
) -> MatchResult | None:
    """Multi-scale template matching. Returns best match above threshold or None."""
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


def match_cursor_in_frame_multi(
    gray_frame: np.ndarray,
    prescaled: tuple[_PrescaledEntry, ...],
    threshold: float,
    confidence_range: float = 0.05,
    early_exit_threshold: float = 0.9,
    min_candidate_distance: float = 20.0,
) -> tuple[MatchCandidate, ...]:
    """Multi-scale template matching returning all spatially-distinct candidates
    within confidence_range of the best match.

    Each template/scale combo contributes at most one peak (the global maximum
    from matchTemplate). Candidates at nearby positions are deduplicated,
    keeping the highest confidence.
    """
    all_matches: list[MatchCandidate] = []
    fh, fw = gray_frame.shape[:2]
    overall_best_conf = threshold

    for entry in prescaled:
        sh, sw = entry.image.shape[:2]
        if sh >= fh or sw >= fw:
            continue

        result = cv2.matchTemplate(gray_frame, entry.image, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val > threshold:
            hotspot_x = entry.template.hotspot_x * entry.scale
            hotspot_y = entry.template.hotspot_y * entry.scale
            all_matches.append(MatchCandidate(
                x=max_loc[0] + hotspot_x,
                y=max_loc[1] + hotspot_y,
                confidence=float(max_val),
                template_id=entry.template.template_id,
            ))
            if max_val > overall_best_conf:
                overall_best_conf = max_val

    if not all_matches:
        return ()

    if overall_best_conf >= early_exit_threshold:
        return (max(all_matches, key=lambda c: c.confidence),)

    # Keep all within confidence_range, deduplicated by spatial proximity
    min_conf = overall_best_conf - confidence_range
    viable = [c for c in all_matches if c.confidence >= min_conf]

    deduped: list[MatchCandidate] = []
    for c in sorted(viable, key=lambda x: x.confidence, reverse=True):
        too_close = any(
            math.sqrt((c.x - d.x) ** 2 + (c.y - d.y) ** 2) < min_candidate_distance
            for d in deduped
        )
        if not too_close:
            deduped.append(c)

    return tuple(deduped)


_MATCH_HEIGHT = 360


def _match_frames(
    raw_frames: tuple[tuple[float, np.ndarray], ...],
    all_prescaled: tuple[_PrescaledEntry, ...],
    config: CursorConfig,
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
            logger.info("  Cursor: %d/%d frames (%d detections)", idx, total_frames, detected_so_far)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame

        match: MatchResult | None = None
        if last_match_id is not None:
            priority = tuple(e for e in all_prescaled if e.template.template_id == last_match_id)
            if priority:
                match = match_cursor_in_frame(
                    gray, priority, config.match_threshold, config.early_exit_threshold,
                )

        if match is None:
            match = match_cursor_in_frame(
                gray, all_prescaled, config.match_threshold, config.early_exit_threshold,
            )

        if match is not None:
            last_match_id = match.template_id
            detections.append(CursorDetection(
                timestamp_ms=ts_ms,
                x=round(match.x * scale_factor),
                y=round(match.y * scale_factor),
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


def _match_frames_multi(
    raw_frames: tuple[tuple[float, np.ndarray], ...],
    all_prescaled: tuple[_PrescaledEntry, ...],
    config: CursorConfig,
    confidence_range: float,
) -> list[tuple[float, tuple[MatchCandidate, ...]]]:
    """Run multi-candidate template matching on a batch of frames."""
    results: list[tuple[float, tuple[MatchCandidate, ...]]] = []
    total_frames = len(raw_frames)
    log_interval = max(1, total_frames // 10)

    for idx, (ts_ms, frame) in enumerate(raw_frames):
        if idx > 0 and idx % log_interval == 0:
            multi_count = sum(1 for _, cs in results if len(cs) > 1)
            logger.info(
                "  Cursor: %d/%d frames (%d multi-candidate)",
                idx, total_frames, multi_count,
            )

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        candidates = match_cursor_in_frame_multi(
            gray, all_prescaled, config.match_threshold,
            confidence_range, config.early_exit_threshold,
        )
        results.append((ts_ms, candidates))

    return results


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

    raw_intervals.sort()
    merged: list[tuple[float, float]] = [raw_intervals[0]]
    for start, end in raw_intervals[1:]:
        prev_start, prev_end = merged[-1]
        if start <= prev_end:
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))

    return tuple(merged)


# ---------------------------------------------------------------------------
# Multi-candidate resolution
# ---------------------------------------------------------------------------

_FLOW_VECTORS: dict[str, tuple[float, float]] = {
    "N":  ( 0.0, -1.0), "NE": ( 0.707, -0.707),
    "E":  ( 1.0,  0.0), "SE": ( 0.707,  0.707),
    "S":  ( 0.0,  1.0), "SW": (-0.707,  0.707),
    "W":  (-1.0,  0.0), "NW": (-0.707, -0.707),
}


def _count_position_clusters(
    frame_candidates: list[tuple[float, tuple[MatchCandidate, ...]]],
    tolerance_px: float,
    cluster_gap_ms: float,
) -> dict[tuple[int, int], int]:
    """Count distinct time clusters per spatial position bucket.

    A position that appears in many separated time clusters (not just consecutive
    frames) is likely a static UI element rather than a real cursor.
    """
    buckets: dict[tuple[int, int], list[float]] = {}
    for ts, candidates in frame_candidates:
        for c in candidates:
            key = (round(c.x / tolerance_px), round(c.y / tolerance_px))
            buckets.setdefault(key, []).append(ts)

    result: dict[tuple[int, int], int] = {}
    for key, timestamps in buckets.items():
        sorted_ts = sorted(timestamps)
        clusters = 1
        for i in range(1, len(sorted_ts)):
            if sorted_ts[i] - sorted_ts[i - 1] > cluster_gap_ms:
                clusters += 1
        result[key] = clusters
    return result


def _score_candidate(
    candidate: MatchCandidate,
    expected_x: float | None,
    expected_y: float | None,
    prev_detection: CursorDetection | None,
    flow_window: FlowWindow | None,
    position_cluster_count: int,
    scale_factor: float,
    max_suspicious_clusters: int = 3,
    flow_magnitude_threshold: float = 3.0,
    flow_uniformity_threshold: float = 0.6,
) -> float:
    """Score a candidate combining confidence, trajectory, flow, and frequency.

    Adjustments are scaled so that trajectory + flow + frequency can
    collectively swing a decision within the typical confidence_range (0.05).
    """
    score = candidate.confidence

    # --- Trajectory smoothness: prefer candidates near expected position ---
    if expected_x is not None and expected_y is not None:
        dist = math.sqrt(
            (candidate.x - expected_x) ** 2 + (candidate.y - expected_y) ** 2
        )
        if dist < 20:
            score += 0.03
        elif dist < 100:
            score += 0.03 * (1.0 - (dist - 20.0) / 80.0)
        else:
            score -= 0.02

    # --- Flow independence: penalise movement that tracks UI scroll ---
    if (flow_window is not None
            and prev_detection is not None and prev_detection.detected
            and flow_window.mean_flow_magnitude >= flow_magnitude_threshold
            and flow_window.flow_uniformity >= flow_uniformity_threshold):
        cx = candidate.x * scale_factor
        cy = candidate.y * scale_factor
        dx = cx - prev_detection.x
        dy = cy - prev_detection.y
        cursor_mag = math.sqrt(dx * dx + dy * dy)
        if cursor_mag > 1.0:
            cursor_dir = (dx / cursor_mag, dy / cursor_mag)
            flow_dir = _FLOW_VECTORS.get(flow_window.dominant_direction, (0.0, 0.0))
            alignment = cursor_dir[0] * flow_dir[0] + cursor_dir[1] * flow_dir[1]
            flow_sig = min(
                flow_window.mean_flow_magnitude / flow_magnitude_threshold, 1.0,
            ) * flow_window.flow_uniformity
            score -= 0.03 * max(0.0, alignment) * flow_sig

    # --- Position frequency: penalise recurring static positions ---
    if position_cluster_count > max_suspicious_clusters:
        penalty_scale = min(
            (position_cluster_count - max_suspicious_clusters) / 5.0, 1.0,
        )
        score -= 0.02 * penalty_scale

    return score


def resolve_candidates(
    frame_candidates: list[tuple[float, tuple[MatchCandidate, ...]]],
    scale_factor: float,
    flow_windows: tuple[FlowWindow, ...] = (),
    position_tolerance_px: float = 5.0,
    cluster_gap_ms: float = 5000.0,
    max_suspicious_clusters: int = 3,
) -> tuple[CursorDetection, ...]:
    """Resolve multi-candidate frames into single detections.

    Algorithm:
    1. Compute position frequency map across all candidates.
    2. Resolve single-candidate and no-candidate frames immediately.
    3. For each multi-candidate frame, find nearest resolved anchors
       before and after, interpolate an expected position, and score
       candidates using trajectory proximity + flow independence +
       position frequency.
    """
    if not frame_candidates:
        return ()

    cluster_counts = _count_position_clusters(
        frame_candidates, position_tolerance_px, cluster_gap_ms,
    )

    def _cluster_count_for(c: MatchCandidate) -> int:
        key = (round(c.x / position_tolerance_px), round(c.y / position_tolerance_px))
        return cluster_counts.get(key, 0)

    n = len(frame_candidates)
    resolved: list[CursorDetection | None] = [None] * n

    # Pass 1: resolve unambiguous frames (0 or 1 candidate)
    for i, (ts, candidates) in enumerate(frame_candidates):
        if len(candidates) == 0:
            resolved[i] = CursorDetection(
                timestamp_ms=ts, x=0.0, y=0.0,
                confidence=0.0, template_id="", detected=False,
            )
        elif len(candidates) == 1:
            c = candidates[0]
            resolved[i] = CursorDetection(
                timestamp_ms=ts,
                x=round(c.x * scale_factor),
                y=round(c.y * scale_factor),
                confidence=c.confidence,
                template_id=c.template_id,
                detected=True,
            )

    # Pass 2: resolve multi-candidate frames using bidirectional context
    for i, (ts, candidates) in enumerate(frame_candidates):
        if resolved[i] is not None:
            continue

        # Nearest resolved anchor before
        prev: CursorDetection | None = None
        for j in range(i - 1, -1, -1):
            if resolved[j] is not None and resolved[j].detected:
                prev = resolved[j]
                break

        # Nearest resolved anchor after
        after: CursorDetection | None = None
        for j in range(i + 1, n):
            if resolved[j] is not None and resolved[j].detected:
                after = resolved[j]
                break

        # Expected position via linear interpolation (in match resolution)
        expected_x: float | None = None
        expected_y: float | None = None
        if prev and after:
            t_range = after.timestamp_ms - prev.timestamp_ms
            if t_range > 0:
                t_frac = (ts - prev.timestamp_ms) / t_range
                expected_x = (prev.x + (after.x - prev.x) * t_frac) / scale_factor
                expected_y = (prev.y + (after.y - prev.y) * t_frac) / scale_factor
        elif prev:
            expected_x = prev.x / scale_factor
            expected_y = prev.y / scale_factor
        elif after:
            expected_x = after.x / scale_factor
            expected_y = after.y / scale_factor

        # Flow window covering this timestamp
        fw: FlowWindow | None = None
        for f in flow_windows:
            if f.start_ms <= ts <= f.end_ms:
                fw = f
                break

        # Score and pick
        best_score = -math.inf
        best_candidate = candidates[0]
        for c in candidates:
            s = _score_candidate(
                c, expected_x, expected_y, prev, fw,
                _cluster_count_for(c), scale_factor,
                max_suspicious_clusters=max_suspicious_clusters,
            )
            if s > best_score:
                best_score = s
                best_candidate = c

        resolved[i] = CursorDetection(
            timestamp_ms=ts,
            x=round(best_candidate.x * scale_factor),
            y=round(best_candidate.y * scale_factor),
            confidence=best_candidate.confidence,
            template_id=best_candidate.template_id,
            detected=True,
        )

    multi_count = sum(1 for _, cs in frame_candidates if len(cs) > 1)
    if multi_count > 0:
        logger.info(
            "  Cursor: resolved %d multi-candidate frames out of %d total",
            multi_count, n,
        )

    return tuple(d for d in resolved if d is not None)


def track_cursor(
    video_path: Path,
    config: CursorConfig,
    templates_dir: Path,
    total_duration_ms: float | None = None,
    *,
    flow_windows: tuple[FlowWindow, ...] = (),
    confidence_range: float = 0.0,
) -> tuple[CursorDetection, ...]:
    """Track cursor via adaptive two-pass approach.

    Pass 1: coarse scan at tracking_base_fps across the full video.
    Identify active regions where cursor displacement exceeds threshold.
    Pass 2: fine scan at tracking_peak_fps within active regions only.
    Merge, interpolate, and smooth.

    When confidence_range > 0, the fine pass returns multiple candidates
    per frame (all within confidence_range of the best match) and resolves
    ambiguity using trajectory context, flow data, and position frequency.
    """
    templates = load_templates(templates_dir)
    if not templates:
        logger.warning("No cursor templates found in %s", templates_dir)
        return ()

    meta = get_video_metadata(video_path)
    duration_ms = total_duration_ms if total_duration_ms is not None else meta.duration_ms
    total_end = duration_ms / 1000.0

    match_height = config.match_height
    scale_factor = meta.height / match_height if match_height > 0 else 1.0
    all_prescaled = _prescale_templates(
        templates, config.template_scales,
        resample_down=config.resample_down,
        resample_up=config.resample_up,
    )

    # --- Pass 1: coarse ---
    coarse_frames = extract_frames(
        video_path, 0.0, total_end, config.tracking_base_fps,
        scale_height=match_height, resample=config.resample_down,
    )
    logger.info(
        "  Cursor: pass 1 — matching %d frames at %.1f FPS against %d templates x %d scales at %dp...",
        len(coarse_frames), config.tracking_base_fps, len(templates), len(config.template_scales), match_height,
    )
    coarse_detections = _match_frames(coarse_frames, all_prescaled, config, scale_factor)

    # --- Identify active regions ---
    active_regions = _identify_active_regions(
        tuple(coarse_detections),
        config.tracking_displacement_threshold_px,
        config.tracking_active_padding_ms,
    )
    logger.info("  Cursor: %d active regions identified", len(active_regions))

    # --- Pass 2: fine scan within active regions ---
    def _in_active_region(ts_ms: float) -> bool:
        return any(s <= ts_ms <= e for s, e in active_regions)

    if confidence_range > 0:
        # Multi-candidate fine pass with disambiguation
        fine_candidates: list[tuple[float, tuple[MatchCandidate, ...]]] = []
        for region_start, region_end in active_regions:
            region_frames = extract_frames(
                video_path,
                region_start / 1000.0,
                region_end / 1000.0,
                config.tracking_peak_fps,
                scale_height=match_height, resample=config.resample_down,
            )
            if region_frames:
                logger.info(
                    "  Cursor: pass 2 — %d frames at %.1f FPS [%.0fms-%.0fms] (multi-candidate)",
                    len(region_frames), config.tracking_peak_fps, region_start, region_end,
                )
                fine_candidates.extend(
                    _match_frames_multi(region_frames, all_prescaled, config, confidence_range)
                )

        # Merge: wrap coarse detections as single-candidate entries
        all_candidates: list[tuple[float, tuple[MatchCandidate, ...]]] = []
        for d in coarse_detections:
            if not _in_active_region(d.timestamp_ms):
                if d.detected:
                    all_candidates.append((d.timestamp_ms, (MatchCandidate(
                        x=d.x / scale_factor, y=d.y / scale_factor,
                        confidence=d.confidence, template_id=d.template_id,
                    ),)))
                else:
                    all_candidates.append((d.timestamp_ms, ()))
        all_candidates.extend(fine_candidates)
        all_candidates.sort(key=lambda x: x[0])

        multi_count = sum(1 for _, cs in fine_candidates if len(cs) > 1)
        logger.info(
            "  Cursor: %d fine frames, %d with multiple candidates",
            len(fine_candidates), multi_count,
        )

        merged = list(resolve_candidates(all_candidates, scale_factor, flow_windows))
    else:
        # Original single-candidate fine pass
        fine_detections: list[CursorDetection] = []
        for region_start, region_end in active_regions:
            region_frames = extract_frames(
                video_path,
                region_start / 1000.0,
                region_end / 1000.0,
                config.tracking_peak_fps,
                scale_height=match_height, resample=config.resample_down,
            )
            if region_frames:
                logger.info(
                    "  Cursor: pass 2 — %d frames at %.1f FPS [%.0fms-%.0fms]",
                    len(region_frames), config.tracking_peak_fps, region_start, region_end,
                )
                fine_detections.extend(_match_frames(region_frames, all_prescaled, config, scale_factor))

        merged: list[CursorDetection] = [d for d in coarse_detections if not _in_active_region(d.timestamp_ms)]
        merged.extend(fine_detections)
        merged.sort(key=lambda d: d.timestamp_ms)

    logger.info(
        "  Cursor: merged %d detections (%d detected)",
        len(merged), sum(1 for d in merged if d.detected),
    )

    filtered = filter_static_detections(
        tuple(merged), config.static_filter_duration_ms, config.static_filter_tolerance_px,
    )
    interpolated = interpolate_trajectory(filtered, config.max_interpolation_gap_ms)
    smoothed = smooth_trajectory(interpolated, config.smooth_window, config.smooth_displacement_threshold)
    return smoothed


def filter_static_detections(
    detections: tuple[CursorDetection, ...],
    max_static_duration_ms: float,
    tolerance_px: float = 1.0,
) -> tuple[CursorDetection, ...]:
    """Remove runs of detections at an identical position lasting longer than max_static_duration_ms.

    Static UI elements (icon buttons, etc.) produce template matches at the exact same
    pixel position across many frames.  A real cursor shows at least sub-pixel jitter
    from video encoding artifacts, so perfectly-static runs are almost certainly false
    positives.
    """
    if not detections:
        return detections

    result = list(detections)

    run_start = 0
    while run_start < len(result):
        if not result[run_start].detected:
            run_start += 1
            continue

        # Walk forward while position stays within tolerance
        ref_x = result[run_start].x
        ref_y = result[run_start].y
        run_end = run_start + 1
        while run_end < len(result) and result[run_end].detected:
            dx = abs(result[run_end].x - ref_x)
            dy = abs(result[run_end].y - ref_y)
            if dx > tolerance_px or dy > tolerance_px:
                break
            run_end += 1

        run_duration = result[run_end - 1].timestamp_ms - result[run_start].timestamp_ms
        if run_duration >= max_static_duration_ms:
            logger.info(
                "  Cursor: filtering %d static detections at (%.1f, %.1f) spanning %.0fms",
                run_end - run_start, ref_x, ref_y, run_duration,
            )
            for i in range(run_start, run_end):
                result[i] = CursorDetection(
                    timestamp_ms=result[i].timestamp_ms,
                    x=0.0,
                    y=0.0,
                    confidence=0.0,
                    template_id="",
                    detected=False,
                )

        run_start = run_end

    return tuple(result)


def interpolate_trajectory(
    detections: tuple[CursorDetection, ...],
    max_gap_ms: int,
) -> tuple[CursorDetection, ...]:
    """Fill gaps in cursor trajectory via linear interpolation for gaps < max_gap_ms."""
    if len(detections) <= 1:
        return detections

    result = list(detections)

    i = 0
    while i < len(result):
        if not result[i].detected:
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
                            x=round(a.x + (b.x - a.x) * t),
                            y=round(a.y + (b.y - a.y) * t),
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

        prev_d = result[i - 1] if i > 0 else result[i]
        next_d = result[i + 1] if i < len(result) - 1 else result[i]

        dx = abs(result[i].x - prev_d.x) + abs(result[i].x - next_d.x)
        dy = abs(result[i].y - prev_d.y) + abs(result[i].y - next_d.y)
        displacement = math.sqrt(dx * dx + dy * dy)

        if displacement > threshold:
            continue

        window_slice = result[max(0, i - half):i + half + 1]
        detected_in_window = [d for d in window_slice if d.detected or d.confidence > 0]
        if not detected_in_window:
            continue

        avg_x = sum(d.x for d in detected_in_window) / len(detected_in_window)
        avg_y = sum(d.y for d in detected_in_window) / len(detected_in_window)
        result[i] = CursorDetection(
            timestamp_ms=result[i].timestamp_ms,
            x=round(avg_x),
            y=round(avg_y),
            confidence=result[i].confidence,
            template_id=result[i].template_id,
            detected=result[i].detected,
        )

    return tuple(result)
