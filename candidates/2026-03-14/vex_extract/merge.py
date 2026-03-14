from __future__ import annotations

import logging
from bisect import bisect_left

from vex_extract.config import AppConfig
from vex_extract.models import CursorDetection, ResolvedEvent, VideoMetadata, VideoSegment
from vex_extract.similarity import events_are_duplicates, string_similarity

logger = logging.getLogger(__name__)


VALID_EVENT_TYPES = frozenset({
    "click", "hover", "navigate", "input_text", "select",
    "dwell", "cursor_thrash", "scroll", "drag", "hesitate", "change_ui_state",
})


def adjust_timestamps(
    events: list[dict],
    segment: VideoSegment,
    screen_track_start_offset: float,
) -> list[ResolvedEvent]:
    """Convert segment-relative timestamps to absolute ResolvedEvents."""
    resolved: list[ResolvedEvent] = []
    for raw in events:
        abs_start = raw["time_start_ms"] + segment.start_ms + screen_track_start_offset
        abs_end = raw["time_end_ms"] + segment.start_ms + screen_track_start_offset

        event_type = raw.get("type", "change_ui_state")
        if event_type not in VALID_EVENT_TYPES:
            event_type = "change_ui_state"

        resolved.append(ResolvedEvent(
            type=event_type,
            time_start=abs_start,
            time_end=abs_end,
            description=raw.get("description", ""),
            confidence=raw.get("confidence", 0.5),
            interaction_target=raw.get("interaction_target"),
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
    """
    if len(segments) < 2 or not events:
        return events

    overlap_windows: list[tuple[float, float]] = []
    for i in range(len(segments) - 1):
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


def deduplicate_events(
    events: list[ResolvedEvent],
    time_tolerance_ms: float,
    similarity_threshold: float,
) -> list[ResolvedEvent]:
    """Remove duplicate events, keeping the higher confidence one."""
    if not events:
        return []

    keep: list[ResolvedEvent] = []
    for event in events:
        is_dup = False
        for i, existing in enumerate(keep):
            if events_are_duplicates(event, existing, time_tolerance_ms, similarity_threshold):
                if event.confidence > existing.confidence:
                    keep[i] = event
                is_dup = True
                break
        if not is_dup:
            keep.append(event)

    return keep


def _lookup_cursor_at_timestamp(
    trajectory: tuple[CursorDetection, ...],
    timestamp_ms: float,
    tolerance_ms: float = 500.0,
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


def enrich_cursor_positions(
    events: list[ResolvedEvent],
    cursor_trajectory: tuple[CursorDetection, ...],
    screen_track_start_offset: float,
    cursor_event_types: tuple[str, ...],
) -> list[ResolvedEvent]:
    """Enrich events with cursor positions from the CV trajectory.

    For click/hover/dwell/select: closest detection within +/-500ms of event start.
    For cursor_thrash/drag: average positions across the event's time range.
    """
    if not cursor_trajectory:
        return [
            e.model_copy(update={"cursor_position": None}) if e.type in cursor_event_types else e
            for e in events
        ]

    enriched: list[ResolvedEvent] = []
    for event in events:
        if event.type not in cursor_event_types:
            enriched.append(event)
            continue

        video_relative_start = event.time_start - screen_track_start_offset
        video_relative_end = event.time_end - screen_track_start_offset

        cursor_dict: dict | None = None

        if event.type in ("cursor_thrash", "drag"):
            # Average positions across the event's time range
            timestamps = [d.timestamp_ms for d in cursor_trajectory]
            lo = bisect_left(timestamps, video_relative_start)
            hi = bisect_left(timestamps, video_relative_end)
            points = [
                d for d in cursor_trajectory[lo:hi]
                if d.detected or d.confidence > 0
            ]
            if points:
                avg_x = sum(d.x for d in points) / len(points)
                avg_y = sum(d.y for d in points) / len(points)
                cursor_dict = {"x": round(avg_x, 1), "y": round(avg_y, 1)}
        else:
            # Single point: closest detection within +/-500ms
            detection = _lookup_cursor_at_timestamp(cursor_trajectory, video_relative_start)
            if detection is not None:
                cursor_dict = {"x": round(detection.x, 1), "y": round(detection.y, 1)}

        enriched.append(event.model_copy(update={"cursor_position": cursor_dict}))

    return enriched


def merge_events(
    segment_results: list[tuple[VideoSegment, list[dict], dict]],
    segments: tuple[VideoSegment, ...],
    cursor_trajectory: tuple[CursorDetection, ...],
    video_metadata: VideoMetadata,
    screen_track_start_offset: float,
    config: AppConfig,
) -> tuple[list[ResolvedEvent], list[ResolvedEvent]]:
    """Full merge pipeline: adjust timestamps, dedup, enrich cursor positions.

    Returns (merged_before_dedup, final_events).
    """
    all_resolved: list[ResolvedEvent] = []
    for segment, raw_events, _token_usage in segment_results:
        resolved = adjust_timestamps(raw_events, segment, screen_track_start_offset)
        all_resolved.extend(resolved)

    all_resolved.sort(key=lambda e: e.time_start)

    # Add viewport dimensions
    all_resolved = [
        e.model_copy(update={
            "viewport_width": video_metadata.width,
            "viewport_height": video_metadata.height,
        })
        for e in all_resolved
    ]

    merged_snapshot = list(all_resolved)

    # Overlap-aware dedup first, then general dedup
    overlap_deduped = deduplicate_overlap_events(
        all_resolved, segments, screen_track_start_offset,
    )
    deduped = deduplicate_events(
        overlap_deduped,
        config.merge.time_tolerance_ms,
        config.merge.similarity_threshold,
    )

    logger.info(
        "Merge: %d merged -> %d overlap-dedup -> %d final",
        len(all_resolved), len(overlap_deduped), len(deduped),
    )

    # Enrich cursor positions
    enriched = enrich_cursor_positions(
        deduped,
        cursor_trajectory,
        screen_track_start_offset,
        config.merge.cursor_event_types,
    )

    return merged_snapshot, enriched
