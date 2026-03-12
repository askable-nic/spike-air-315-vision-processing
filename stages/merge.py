from __future__ import annotations

import time
from bisect import bisect_left
from pathlib import Path

from src.models import (
    AnalyseResult,
    CursorDetection,
    EventType,
    Moment,
    ObserveResult,
    PipelineConfig,
    ResolvedEvent,
    SceneDescription,
    SessionManifest,
    SessionOutput,
    StageMetrics,
    TriageResult,
)
from src.similarity import events_are_duplicates
from src.video import get_video_metadata
from stages.observe import _lookup_cursor_at_timestamp


def _find_moment_scene_context(
    timestamp_ms: float,
    scene_descriptions: tuple[SceneDescription, ...],
) -> SceneDescription | None:
    """Find the most recent scene description before the given timestamp."""
    best: SceneDescription | None = None
    for sd in scene_descriptions:
        if sd.timestamp_ms <= timestamp_ms:
            if best is None or sd.timestamp_ms > best.timestamp_ms:
                best = sd
    return best


def _resolve_cursor_position(
    event_type: EventType,
    start_ms: float,
    end_ms: float,
    observe_result: ObserveResult | None,
) -> dict | None:
    """Look up cursor position from the observe trajectory for LLM-analysed events."""
    if observe_result is None or not observe_result.cursor_trajectory:
        return None

    trajectory = observe_result.cursor_trajectory

    if event_type in ("click", "hover", "dwell"):
        detection = _lookup_cursor_at_timestamp(trajectory, start_ms)
        if detection is not None:
            return {"x": detection.x, "y": detection.y}
        return None

    if event_type == "cursor_thrash":
        timestamps = [d.timestamp_ms for d in trajectory]
        lo = bisect_left(timestamps, start_ms)
        hi = bisect_left(timestamps, end_ms)
        points: list[CursorDetection] = [
            d for d in trajectory[lo:hi]
            if d.detected or d.confidence > 0
        ]
        if not points:
            return None
        avg_x = sum(d.x for d in points) / len(points)
        avg_y = sum(d.y for d in points) / len(points)
        return {"x": avg_x, "y": avg_y}

    return None


def run_merge(
    session: SessionManifest,
    config: PipelineConfig,
    analyse_result: AnalyseResult,
    triage_result: TriageResult | None = None,
    observe_result: ObserveResult | None = None,
    video_path: Path | None = None,
) -> SessionOutput:
    """Merge analysis results: resolve timestamps, discard context events, deduplicate."""
    t0 = time.monotonic()
    mc = config.merge

    viewport_w: int | None = None
    viewport_h: int | None = None
    if video_path is not None:
        meta = get_video_metadata(video_path)
        viewport_w = meta.width
        viewport_h = meta.height

    resolved: list[ResolvedEvent] = []

    for seg_result in analyse_result.segments:
        # Build lookup from frame index to FrameRef
        ref_by_idx = {r.frame_index_in_request: r for r in seg_result.frame_refs}

        for event in seg_result.events:
            start_ref = ref_by_idx.get(event.frame_index_start)
            end_ref = ref_by_idx.get(event.frame_index_end)

            if start_ref is None or end_ref is None:
                continue

            # Discard events originating entirely from context frames
            if mc.discard_context_events:
                event_refs = [
                    ref_by_idx[i]
                    for i in range(event.frame_index_start, event.frame_index_end + 1)
                    if i in ref_by_idx
                ]
                if event_refs and all(r.is_context for r in event_refs):
                    continue

            # Resolve absolute timestamps
            abs_start = start_ref.timestamp_ms + session.screenTrackStartOffset
            abs_end = end_ref.timestamp_ms + session.screenTrackStartOffset

            cursor_dict = _resolve_cursor_position(
                event.type,
                start_ref.timestamp_ms,
                end_ref.timestamp_ms,
                observe_result,
            )

            resolved.append(ResolvedEvent(
                type=event.type,
                time_start=abs_start,
                time_end=abs_end,
                description=event.description,
                confidence=event.confidence,
                interaction_target=event.interaction_target,
                cursor_position=cursor_dict,
                page_title=event.page_title,
                page_location=event.page_location,
                viewport_width=viewport_w,
                viewport_height=viewport_h,
                frame_description=event.frame_description,
            ))

    # Add local events that don't need enrichment (e.g. scroll, thrash)
    if observe_result is not None:
        offset = session.screenTrackStartOffset
        for local_event in observe_result.local_events:
            if not local_event.needs_enrichment:
                cursor_dict = None
                if local_event.cursor_positions:
                    if local_event.type == "cursor_thrash":
                        positions = local_event.cursor_positions
                        avg_x = sum(p.x for p in positions) / len(positions)
                        avg_y = sum(p.y for p in positions) / len(positions)
                        cursor_dict = {"x": avg_x, "y": avg_y}
                    else:
                        p = local_event.cursor_positions[0]
                        cursor_dict = {"x": p.x, "y": p.y}

                resolved.append(ResolvedEvent(
                    type=local_event.type,
                    time_start=local_event.time_start_ms + offset,
                    time_end=local_event.time_end_ms + offset,
                    description=local_event.description,
                    confidence=local_event.confidence,
                    cursor_position=cursor_dict,
                    viewport_width=viewport_w,
                    viewport_height=viewport_h,
                ))

    # Add scroll moments from visual-change-driven pipeline
    if observe_result is not None and observe_result.moments:
        offset = session.screenTrackStartOffset
        for moment in observe_result.moments:
            if moment.category == "scroll" and moment.flow_event is not None:
                fe = moment.flow_event
                direction = "down" if fe.dominant_direction == "S" else "up" if fe.dominant_direction == "N" else fe.dominant_direction
                # Find scene context for page_title
                page_title = None
                scene_ctx = _find_moment_scene_context(moment.time_start_ms, observe_result.scene_descriptions)
                if scene_ctx is not None:
                    page_title = scene_ctx.page_title

                resolved.append(ResolvedEvent(
                    type="scroll",
                    time_start=moment.time_start_ms + offset,
                    time_end=moment.time_end_ms + offset,
                    description=f"Scroll {direction} (magnitude: {fe.mean_magnitude:.1f}, uniformity: {fe.flow_uniformity:.2f})",
                    confidence=0.8,
                    page_title=page_title,
                    viewport_width=viewport_w,
                    viewport_height=viewport_h,
                ))

    # Sort by start time
    resolved.sort(key=lambda e: e.time_start)

    # Deduplicate
    deduped = _deduplicate(resolved, mc.time_tolerance_ms, mc.similarity_threshold)

    elapsed = (time.monotonic() - t0) * 1000

    observe_metrics = StageMetrics()
    if observe_result is not None:
        artifacts = len(observe_result.moments) if observe_result.moments else len(observe_result.local_events)
        observe_metrics = StageMetrics(
            duration_ms=observe_result.processing_time_ms,
            artifacts_created=artifacts,
        )

    budget = observe_result.token_budget if observe_result is not None else 0
    input_tokens = analyse_result.total_input_tokens
    utilisation = round(input_tokens / budget * 100, 1) if budget > 0 else 0.0

    return SessionOutput(
        recording_id=session.identifier,
        session=session,
        triage_metrics=(
            StageMetrics(
                duration_ms=triage_result.processing_time_ms,
                artifacts_created=len(triage_result.segments),
            )
            if triage_result is not None
            else StageMetrics()
        ),
        observe_metrics=observe_metrics,
        analyse_metrics=StageMetrics(
            duration_ms=analyse_result.processing_time_ms,
            artifacts_created=sum(len(s.events) for s in analyse_result.segments),
        ),
        merge_metrics=StageMetrics(
            duration_ms=elapsed,
            artifacts_created=len(deduped),
        ),
        events=tuple(deduped),
        event_count=len(deduped),
        total_input_token_budget=budget,
        total_input_token_budget_utilisation=utilisation,
        total_input_tokens=input_tokens,
        total_output_tokens=analyse_result.total_output_tokens,
    )


def _deduplicate(
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
                # Keep higher confidence
                if event.confidence > existing.confidence:
                    keep[i] = event
                is_dup = True
                break
        if not is_dup:
            keep.append(event)

    return keep
