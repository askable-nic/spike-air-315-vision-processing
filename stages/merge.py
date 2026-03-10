from __future__ import annotations

import time

from src.models import (
    AnalyseResult,
    ObserveResult,
    PipelineConfig,
    ResolvedEvent,
    SessionManifest,
    SessionOutput,
    StageMetrics,
    TriageResult,
)
from src.similarity import events_are_duplicates


def run_merge(
    session: SessionManifest,
    config: PipelineConfig,
    analyse_result: AnalyseResult,
    triage_result: TriageResult,
    observe_result: ObserveResult | None = None,
) -> SessionOutput:
    """Merge analysis results: resolve timestamps, discard context events, deduplicate."""
    t0 = time.monotonic()
    mc = config.merge

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

            roi_dict = None
            if event.region_of_interest is not None:
                roi_dict = {
                    "x": event.region_of_interest.x,
                    "y": event.region_of_interest.y,
                    "width": event.region_of_interest.width,
                    "height": event.region_of_interest.height,
                }

            cursor_dict = None
            if event.cursor_position is not None:
                cursor_dict = {
                    "x": event.cursor_position.x,
                    "y": event.cursor_position.y,
                }

            resolved.append(ResolvedEvent(
                type=event.type,
                source=config.analyse.source,
                time_start=abs_start,
                time_end=abs_end,
                description=event.description,
                confidence=event.confidence,
                interaction_target=event.interaction_target,
                interaction_region_of_interest=roi_dict,
                cursor_position=cursor_dict,
                page_title=event.page_title,
                page_location=event.page_location,
                frame_description=event.frame_description,
                transcript_id=session.roomId,
                study_id=session.studyId,
            ))

    # Add local events that don't need enrichment (e.g. scroll, thrash)
    if observe_result is not None:
        offset = session.screenTrackStartOffset
        for local_event in observe_result.local_events:
            if not local_event.needs_enrichment:
                cursor_dict = None
                if local_event.cursor_positions:
                    p = local_event.cursor_positions[0]
                    cursor_dict = {"x": p.x, "y": p.y}

                resolved.append(ResolvedEvent(
                    type=local_event.type,
                    source=config.analyse.source,
                    time_start=local_event.time_start_ms + offset,
                    time_end=local_event.time_end_ms + offset,
                    description=local_event.description,
                    confidence=local_event.confidence,
                    cursor_position=cursor_dict,
                    transcript_id=session.roomId,
                    study_id=session.studyId,
                ))

    # Sort by start time
    resolved.sort(key=lambda e: e.time_start)

    # Deduplicate
    deduped = _deduplicate(resolved, mc.time_tolerance_ms, mc.similarity_threshold)

    elapsed = (time.monotonic() - t0) * 1000

    observe_metrics = StageMetrics()
    if observe_result is not None:
        observe_metrics = StageMetrics(
            duration_ms=observe_result.processing_time_ms,
            artifacts_created=len(observe_result.local_events),
        )

    return SessionOutput(
        recording_id=session.identifier,
        session=session,
        triage_metrics=StageMetrics(
            duration_ms=triage_result.processing_time_ms,
            artifacts_created=len(triage_result.segments),
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
        total_input_tokens=analyse_result.total_input_tokens,
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
