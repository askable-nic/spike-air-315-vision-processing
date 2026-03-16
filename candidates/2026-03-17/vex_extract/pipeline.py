from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from vex_extract.analysis import analyse_all_segments, prepare_all_prompts
from vex_extract.config import AppConfig
from vex_extract.cursor import track_cursor
from vex_extract.flow import compute_flow_summaries
from vex_extract.gemini import create_client
from vex_extract.merge import merge_events
from vex_extract.models import CursorDetection, FlowWindow, VideoSegment
from vex_extract.video import (
    compute_segments,
    extract_segment,
    get_video_metadata,
    normalize_video,
)

logger = logging.getLogger(__name__)


def _cv_cache_key(video_stem: str, *configs: object) -> str:
    """Build a cache directory name from the video stem and config sections.

    Each config is JSON-serialised and fed into a sha256; the first 8 hex
    chars are appended.
    """
    parts: list[str] = []
    for cfg in configs:
        blob = json.dumps(cfg, sort_keys=True) if isinstance(cfg, (dict, str)) else json.dumps(cfg.model_dump(), sort_keys=True)
        parts.append(hashlib.sha256(blob.encode()).hexdigest()[:8])
    return f"{video_stem}_{'_'.join(parts)}"


def _save_output(
    run_dir: Path,
    *,
    config: AppConfig,
    video_path: Path,
    meta: object,
    offset: int,
    cursor_trajectory: tuple[CursorDetection, ...],
    flow_windows: tuple[FlowWindow, ...],
    segment_results: list[tuple[VideoSegment, list[dict], dict]],
    merged_snapshot: list,
    final_events: list,
    cursor_time_ms: float | None,
    flow_time_ms: float | None,
    analysis_time_ms: float,
    t0: float,
    run_id: str,
) -> None:
    """Write events.json and run_metadata.json."""
    detected_count = sum(1 for d in cursor_trajectory if d.detected)

    # Build final event dicts for output
    output_events: list[dict] = []
    for e in final_events:
        event_dict: dict = {
            "type": e.type,
            "time_start": e.time_start,
            "time_end": e.time_end,
            "description": e.description,
            "confidence": e.confidence,
        }
        if e.interaction_target is not None:
            event_dict["interaction_target"] = e.interaction_target
        if e.cursor_position is not None:
            event_dict["cursor_position"] = e.cursor_position
        elif e.type in config.merge.cursor_event_types:
            event_dict["cursor_position"] = None
        if e.page_title is not None:
            event_dict["page_title"] = e.page_title
        if e.page_location is not None:
            event_dict["page_location"] = e.page_location
        if e.viewport_width is not None:
            event_dict["viewport_width"] = e.viewport_width
        if e.viewport_height is not None:
            event_dict["viewport_height"] = e.viewport_height
        if e.frame_description is not None:
            event_dict["frame_description"] = e.frame_description
        output_events.append(event_dict)

    (run_dir / "events.json").write_text(json.dumps(output_events, indent=2))

    # Build segment metadata
    total_input_tokens = 0
    total_output_tokens = 0
    segment_metadata: list[dict] = []
    for segment, raw_events, token_usage in segment_results:
        total_input_tokens += token_usage.get("input_tokens", 0)
        total_output_tokens += token_usage.get("output_tokens", 0)
        seg_entry: dict = {
            "index": segment.index,
            "start_ms": segment.start_ms,
            "end_ms": segment.end_ms,
            "duration_ms": round(segment.end_ms - segment.start_ms, 1),
            "event_count": len(raw_events),
            "input_tokens": token_usage.get("input_tokens", 0),
            "output_tokens": token_usage.get("output_tokens", 0),
        }
        if "analysis_ms" in token_usage:
            seg_entry["analysis_ms"] = token_usage["analysis_ms"]
        if "error" in token_usage:
            seg_entry["error"] = token_usage["error"]
        segment_metadata.append(seg_entry)

    total_time_ms = (time.monotonic() - t0) * 1000
    run_metadata: dict = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": config.model_dump(),
        "video_path": str(video_path),
        "video_duration_ms": getattr(meta, "duration_ms", None),
        "video_dimensions": {"width": getattr(meta, "width", None), "height": getattr(meta, "height", None)},
        "screen_track_start_offset": offset,
        "segments": segment_metadata,
        "cv_analysis": {
            "cursor_detections": len(cursor_trajectory),
            "cursor_detected": detected_count,
            "flow_windows": len(flow_windows),
        },
        "events_merged": len(merged_snapshot),
        "events_final": len(output_events),
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "timing": {
            **({"cursor_tracking_ms": round(cursor_time_ms, 1)} if cursor_time_ms is not None else {}),
            **({"optical_flow_ms": round(flow_time_ms, 1)} if flow_time_ms is not None else {}),
            "gemini_analysis_ms": round(analysis_time_ms, 1),
            "total_ms": round(total_time_ms, 1),
            "video_duration_ms": getattr(meta, "duration_ms", None),
        },
    }
    (run_dir / "run_metadata.json").write_text(json.dumps(run_metadata, indent=2))


def run_pipeline(
    video_path: Path,
    offset: int,
    config: AppConfig,
    app_root: Path,
) -> Path:
    """Run the full event extraction pipeline. Returns the output directory path."""
    t0 = time.monotonic()
    tmp_dir = app_root / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    run_dir = app_root / "output" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Set up file logging
    file_handler = logging.FileHandler(run_dir / "run.log")
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.getLogger().addHandler(file_handler)

    logger.info("=== Video Event Extractor ===")
    logger.info("Video: %s", video_path)
    logger.info("Offset: %d ms", offset)
    logger.info("Run ID: %s", run_id)

    # --- Step 1: Normalize video ---
    logger.info("Step 1: Normalizing video...")
    norm_path = tmp_dir / f"{video_path.stem}_normalized.mp4"
    if norm_path.exists():
        logger.info("  Using cached normalized video: %s", norm_path)
    else:
        normalize_video(video_path, norm_path, config.video.target_pixels)
        logger.info("  Normalized video saved: %s", norm_path)

    meta = get_video_metadata(norm_path)
    logger.info("  Duration: %.1fs, %dx%d, %.1f fps", meta.duration_ms / 1000, meta.width, meta.height, meta.fps)

    # --- Step 2: Cursor tracking ---
    cv_dir = run_dir / "cv"
    cv_dir.mkdir(parents=True, exist_ok=True)
    cv_cache_dir = tmp_dir / "cv"
    cv_cache_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Step 2: Tracking cursor...")
    cursor_cache_name = _cv_cache_key(video_path.stem, config.cursor)
    cursor_cache_path = cv_cache_dir / f"{cursor_cache_name}_cursor" / "cursor_trajectory.json"

    cursor_time_ms: float | None = None
    if cursor_cache_path.exists():
        logger.info("  Using cached cursor trajectory: %s", cursor_cache_path)
        raw = json.loads(cursor_cache_path.read_text())
        cursor_trajectory: tuple[CursorDetection, ...] = tuple(CursorDetection(**d) for d in raw)
    else:
        t_cursor = time.monotonic()
        templates_dir = app_root / "cursor_templates"
        cursor_trajectory = track_cursor(
            video_path=norm_path,
            config=config.cursor,
            templates_dir=templates_dir,
            total_duration_ms=meta.duration_ms,
        )
        cursor_time_ms = (time.monotonic() - t_cursor) * 1000
        cursor_cache_path.parent.mkdir(parents=True, exist_ok=True)
        cursor_cache_path.write_text(
            json.dumps([d.model_dump() for d in cursor_trajectory], indent=2)
        )
        logger.info("  Cached cursor trajectory: %s", cursor_cache_path)

    detected_count = sum(1 for d in cursor_trajectory if d.detected)
    if cursor_time_ms is not None:
        logger.info("  %d cursor detections (%d detected) in %.1fs", len(cursor_trajectory), detected_count, cursor_time_ms / 1000)
    else:
        logger.info("  %d cursor detections (%d detected) [cached]", len(cursor_trajectory), detected_count)

    shutil.copy2(cursor_cache_path, cv_dir / "cursor_trajectory.json")

    # --- Step 3: Optical flow ---
    logger.info("Step 3: Computing optical flow...")
    flow_cache_name = _cv_cache_key(video_path.stem, config.flow, config.cursor)
    flow_cache_path = cv_cache_dir / f"{flow_cache_name}_flow" / "flow_windows.json"

    flow_time_ms: float | None = None
    if flow_cache_path.exists():
        logger.info("  Using cached flow windows: %s", flow_cache_path)
        raw = json.loads(flow_cache_path.read_text())
        flow_windows: tuple[FlowWindow, ...] = tuple(FlowWindow(**fw) for fw in raw)
    else:
        t_flow = time.monotonic()
        flow_windows = compute_flow_summaries(
            video_path=norm_path,
            cursor_trajectory=cursor_trajectory,
            config=config.flow,
            total_duration_ms=meta.duration_ms,
        )
        flow_time_ms = (time.monotonic() - t_flow) * 1000
        flow_cache_path.parent.mkdir(parents=True, exist_ok=True)
        flow_cache_path.write_text(
            json.dumps([fw.model_dump() for fw in flow_windows], indent=2)
        )
        logger.info("  Cached flow windows: %s", flow_cache_path)

    if flow_time_ms is not None:
        logger.info("  %d flow windows in %.1fs", len(flow_windows), flow_time_ms / 1000)
    else:
        logger.info("  %d flow windows [cached]", len(flow_windows))

    shutil.copy2(flow_cache_path, cv_dir / "flow_windows.json")

    # --- Step 4: Create video segments ---
    logger.info("Step 4: Creating video segments...")
    seg_key = (
        f"{video_path.stem}"
        f"_dur{config.segmentation.max_segment_duration_ms}"
        f"_ovl{config.segmentation.segment_overlap_ms}"
    )
    segments_dir = tmp_dir / "segments" / seg_key
    segments = compute_segments(
        duration_ms=meta.duration_ms,
        max_segment_duration_ms=config.segmentation.max_segment_duration_ms,
        segment_overlap_ms=config.segmentation.segment_overlap_ms,
        segments_dir=segments_dir,
    )
    logger.info("  %d segments", len(segments))

    for segment in segments:
        if segment.path.exists():
            logger.info("  Segment %d: cached", segment.index)
        else:
            extract_segment(norm_path, segment)
            logger.info(
                "  Segment %d: extracted %.1fs [%.0f-%.0f ms]",
                segment.index, (segment.end_ms - segment.start_ms) / 1000,
                segment.start_ms, segment.end_ms,
            )

    # --- Step 5: Prepare prompts ---
    logger.info("Step 5: Preparing prompts...")
    prompt_path = app_root / "prompts" / "system.txt"
    prompt_template = prompt_path.read_text()

    prepared_prompts = prepare_all_prompts(
        segments=segments,
        cursor_trajectory=cursor_trajectory,
        flow_windows=flow_windows,
        prompt_template=prompt_template,
        config=config,
        run_dir=run_dir,
    )
    logger.info("  %d prompts prepared", len(prepared_prompts))

    # --- Step 6: Gemini analysis ---
    logger.info("Step 6: Running Gemini analysis...")
    client = create_client(config.gemini.api_key_env)

    t_analysis = time.monotonic()
    segment_results = asyncio.run(
        analyse_all_segments(
            client=client,
            prepared=prepared_prompts,
            config=config,
        )
    )
    analysis_time_ms = (time.monotonic() - t_analysis) * 1000

    total_raw_events = sum(len(evts) for _, evts, _ in segment_results)
    logger.info("  Analysis complete: %d raw events in %.1fs", total_raw_events, analysis_time_ms / 1000)

    # --- Steps 7-8: Merge, dedup, enrich ---
    logger.info("Steps 7-8: Merging events and enriching cursor positions...")
    merged_snapshot, final_events = merge_events(
        segment_results=segment_results,
        segments=segments,
        cursor_trajectory=cursor_trajectory,
        video_metadata=meta,
        screen_track_start_offset=offset,
        config=config,
    )

    (run_dir / "merged_events.json").write_text(
        json.dumps([e.model_dump() for e in merged_snapshot], indent=2)
    )

    # --- Step 9: Save output ---
    logger.info("Step 9: Saving output...")
    _save_output(run_dir, config=config, video_path=video_path, meta=meta,
                 offset=offset, cursor_trajectory=cursor_trajectory,
                 flow_windows=flow_windows, segment_results=segment_results,
                 merged_snapshot=merged_snapshot, final_events=final_events,
                 cursor_time_ms=cursor_time_ms, flow_time_ms=flow_time_ms,
                 analysis_time_ms=analysis_time_ms, t0=t0, run_id=run_id)

    total_time_ms = (time.monotonic() - t0) * 1000
    event_count = len(final_events)
    logger.info(
        "Done! %d events in %.1fs. Output: %s",
        event_count, total_time_ms / 1000, run_dir,
    )

    logging.getLogger().removeHandler(file_handler)
    file_handler.close()

    return run_dir
