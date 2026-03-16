from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import NamedTuple

import cv2
import numpy as np

from vex_extract.config import CursorConfig
from vex_extract.models import CursorDetection
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
    scale: float


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
                scale=entry.scale,
            )
            best_conf = max_val

            if max_val >= early_exit_threshold:
                return best

    return best


def _narrow_prescaled(
    all_prescaled: tuple[_PrescaledEntry, ...],
    template_id: str,
    target_scale: float,
    sorted_scales: tuple[float, ...],
) -> tuple[_PrescaledEntry, ...]:
    """Filter prescaled entries to same template at target scale ± 1 neighbor."""
    try:
        idx = sorted_scales.index(target_scale)
    except ValueError:
        return ()
    neighbor_scales = frozenset(
        sorted_scales[i] for i in range(max(0, idx - 1), min(len(sorted_scales), idx + 2))
    )
    return tuple(
        e for e in all_prescaled
        if e.template.template_id == template_id and e.scale in neighbor_scales
    )


def _calibrate_scales(
    observations: tuple[tuple[float, float], ...],
    sorted_scales: tuple[float, ...],
    min_confident: int = 5,
    confidence_floor: float = 0.75,
    dominance_ratio: float = 0.5,
) -> tuple[float, ...] | None:
    """Analyze coarse-pass scale observations to narrow the prescaled set for fine pass.

    Returns the dominant scale ± 1 neighbor from sorted_scales, or None if
    no clear dominant scale can be determined.
    """
    confident = [(s, c) for s, c in observations if c >= confidence_floor]
    if len(confident) < min_confident:
        return None

    counts: dict[float, int] = {}
    for s, _ in confident:
        counts[s] = counts.get(s, 0) + 1

    total = len(confident)
    ranked = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    mode_scale, mode_count = ranked[0]

    dominant_scale: float | None = None

    if mode_count / total >= dominance_ratio:
        dominant_scale = mode_scale
    elif len(ranked) >= 2:
        second_scale, second_count = ranked[1]
        # Check if top-2 are adjacent and together dominant
        try:
            idx_a = sorted_scales.index(mode_scale)
            idx_b = sorted_scales.index(second_scale)
        except ValueError:
            return None
        if abs(idx_a - idx_b) == 1 and (mode_count + second_count) / total >= dominance_ratio:
            dominant_scale = mode_scale

    if dominant_scale is None:
        return None

    try:
        idx = sorted_scales.index(dominant_scale)
    except ValueError:
        return None

    neighbors = tuple(
        sorted_scales[i]
        for i in range(max(0, idx - 1), min(len(sorted_scales), idx + 2))
    )
    return neighbors


def _match_frames(
    raw_frames: tuple[tuple[float, np.ndarray], ...],
    all_prescaled: tuple[_PrescaledEntry, ...],
    config: CursorConfig,
    scale_factor: float,
) -> tuple[list[CursorDetection], tuple[tuple[float, float], ...]]:
    """Run template matching on a batch of frames, returning detections and scale observations.

    Returns (detections, observations) where observations is a tuple of
    (scale, confidence) pairs for every detected frame.
    """
    detections: list[CursorDetection] = []
    observations: list[tuple[float, float]] = []
    total_frames = len(raw_frames)
    log_interval = max(1, total_frames // 10)
    sorted_scales = tuple(sorted({e.scale for e in all_prescaled}))
    last_match_id: str | None = None
    last_match_scale: float | None = None

    for idx, (ts_ms, frame) in enumerate(raw_frames):
        if idx > 0 and idx % log_interval == 0:
            detected_so_far = sum(1 for d in detections if d.detected)
            logger.info("  Cursor: %d/%d frames (%d detections)", idx, total_frames, detected_so_far)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame

        match: MatchResult | None = None
        if last_match_id is not None and last_match_scale is not None:
            narrow = _narrow_prescaled(all_prescaled, last_match_id, last_match_scale, sorted_scales)
            if narrow:
                match = match_cursor_in_frame(
                    gray, narrow, config.match_threshold, config.early_exit_threshold,
                )

        if match is None:
            match = match_cursor_in_frame(
                gray, all_prescaled, config.match_threshold, config.early_exit_threshold,
            )

        if match is not None:
            last_match_id = match.template_id
            last_match_scale = match.scale
            observations.append((match.scale, match.confidence))
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
            last_match_scale = None
            detections.append(CursorDetection(
                timestamp_ms=ts_ms,
                x=0.0,
                y=0.0,
                confidence=0.0,
                template_id="",
                detected=False,
            ))

    return detections, tuple(observations)


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


def track_cursor(
    video_path: Path,
    config: CursorConfig,
    templates_dir: Path,
    total_duration_ms: float | None = None,
) -> tuple[CursorDetection, ...]:
    """Track cursor via adaptive two-pass approach.

    Pass 1: coarse scan at tracking_base_fps across the full video.
    Identify active regions where cursor displacement exceeds threshold.
    Pass 2: fine scan at tracking_peak_fps within active regions only.
    Merge, interpolate, and smooth.
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
    coarse_detections, coarse_observations = _match_frames(coarse_frames, all_prescaled, config, scale_factor)

    # --- Scale calibration ---
    calibrated_scales = _calibrate_scales(coarse_observations, tuple(sorted(config.template_scales)))
    if calibrated_scales is not None:
        fine_prescaled = _prescale_templates(
            templates, calibrated_scales,
            resample_down=config.resample_down, resample_up=config.resample_up,
        )
        logger.info("  Cursor: calibrated to scales %s from coarse pass", calibrated_scales)
    else:
        fine_prescaled = all_prescaled
        logger.info("  Cursor: scale calibration inconclusive, using all scales")

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
            fine_dets, _ = _match_frames(region_frames, fine_prescaled, config, scale_factor)
            fine_detections.extend(fine_dets)

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
