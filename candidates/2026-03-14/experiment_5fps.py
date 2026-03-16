"""
Experiment: tracking_peak_fps=5 vs tracking_peak_fps=15

Compares cursor tracking at 5fps peak vs the existing 15fps baseline
on the travel_expert_william session, measuring impact on:
  a) CV summary sent to Gemini (prompt text)
  b) Cursor lookups on final merged events
  c) Processing time

Uses the complete 15fps run at output/2026-03-15_030547 as baseline.
"""
from __future__ import annotations

import difflib
import json
import math
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap: add vex_extract to path
# ---------------------------------------------------------------------------
APP_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_ROOT))

from vex_extract.config import AppConfig, CursorConfig, load_config
from vex_extract.cursor import track_cursor
from vex_extract.cv_summary import generate_cursor_summary
from vex_extract.merge import _lookup_cursor_at_timestamp, enrich_cursor_positions
from vex_extract.models import CursorDetection, FlowWindow, ResolvedEvent, VideoSegment
from vex_extract.video import compute_segments, get_video_metadata

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASELINE_RUN = APP_ROOT / "output" / "2026-03-15_030547"
REPORT_DIR = APP_ROOT / "output" / "experiment_5fps"

CURSOR_EVENT_TYPES = ("click", "hover", "dwell", "cursor_thrash", "select", "drag")


def load_baseline():
    """Load metadata, events, cursor trajectory, and flow windows from the 15fps baseline run."""
    meta = json.loads((BASELINE_RUN / "run_metadata.json").read_text())
    events = json.loads((BASELINE_RUN / "events.json").read_text())
    trajectory_raw = json.loads((BASELINE_RUN / "cv" / "cursor_trajectory.json").read_text())
    trajectory = tuple(CursorDetection(**d) for d in trajectory_raw)
    flow_raw = json.loads((BASELINE_RUN / "cv" / "flow_windows.json").read_text())
    flow_windows = tuple(FlowWindow(**fw) for fw in flow_raw)

    # Load per-segment Gemini responses to re-merge with alternative cursor data
    segment_responses = []
    seg_idx = 0
    while True:
        seg_dir = BASELINE_RUN / "segments" / f"segment_{seg_idx:03d}"
        if not seg_dir.exists():
            break
        resp_path = seg_dir / "response.json"
        if resp_path.exists():
            raw = json.loads(resp_path.read_text())
            # response.json wraps events in {"text": "<json>", "input_tokens": ..., ...}
            if isinstance(raw, dict) and "text" in raw:
                segment_responses.append(json.loads(raw["text"]))
            else:
                segment_responses.append(raw if isinstance(raw, list) else [])
        else:
            segment_responses.append([])
        seg_idx += 1

    return meta, events, trajectory, flow_windows, segment_responses


def build_segments(meta: dict, config: AppConfig) -> tuple[VideoSegment, ...]:
    """Reconstruct VideoSegment objects from run metadata."""
    duration_ms = meta["video_duration_ms"]
    # We need the segments_dir but won't extract video — just compute boundaries
    seg_key = (
        f"travel_expert_william_normalized"
        f"_dur{config.segmentation.max_segment_duration_ms}"
        f"_ovl{config.segmentation.segment_overlap_ms}"
    )
    segments_dir = APP_ROOT / "tmp" / "segments" / seg_key
    return compute_segments(
        duration_ms=duration_ms,
        max_segment_duration_ms=config.segmentation.max_segment_duration_ms,
        segment_overlap_ms=config.segmentation.segment_overlap_ms,
        segments_dir=segments_dir,
    )


# ---------------------------------------------------------------------------
# Quality check: detect dropout artifacts in trajectory
# ---------------------------------------------------------------------------

def analyze_trajectory_quality(
    trajectory: tuple[CursorDetection, ...],
    label: str,
    expected_peak_interval_ms: float,
) -> dict:
    """Analyze a cursor trajectory for dropout artifacts.

    Looks for:
    - Unexpectedly large gaps between consecutive detected frames
    - Runs of non-detection that might indicate system sleeping
    - Overall detection density
    """
    if not trajectory:
        return {"label": label, "total": 0, "detected": 0, "issues": ["empty trajectory"]}

    detected = [d for d in trajectory if d.detected]
    total_duration_ms = trajectory[-1].timestamp_ms - trajectory[0].timestamp_ms

    # Analyze gaps between consecutive detected frames
    gaps = []
    for i in range(1, len(detected)):
        gap_ms = detected[i].timestamp_ms - detected[i - 1].timestamp_ms
        gaps.append(gap_ms)

    large_gap_threshold_ms = expected_peak_interval_ms * 10  # 10x expected = suspicious
    large_gaps = [(i, g) for i, g in enumerate(gaps) if g > large_gap_threshold_ms]

    # Analyze runs of non-detection
    non_detect_runs = []
    run_start = None
    for i, d in enumerate(trajectory):
        if not d.detected:
            if run_start is None:
                run_start = i
        else:
            if run_start is not None:
                run_dur = trajectory[i - 1].timestamp_ms - trajectory[run_start].timestamp_ms
                if run_dur > 5000:  # >5s of no detection
                    non_detect_runs.append({
                        "start_ms": trajectory[run_start].timestamp_ms,
                        "end_ms": trajectory[i - 1].timestamp_ms,
                        "duration_ms": round(run_dur, 1),
                    })
                run_start = None

    return {
        "label": label,
        "total_samples": len(trajectory),
        "detected_samples": len(detected),
        "detection_rate": round(len(detected) / len(trajectory) * 100, 1) if trajectory else 0,
        "total_duration_ms": round(total_duration_ms, 1),
        "coverage_density_per_sec": round(len(detected) / (total_duration_ms / 1000), 2) if total_duration_ms > 0 else 0,
        "gap_stats": {
            "median_ms": round(sorted(gaps)[len(gaps) // 2], 1) if gaps else 0,
            "p95_ms": round(sorted(gaps)[int(len(gaps) * 0.95)], 1) if gaps else 0,
            "max_ms": round(max(gaps), 1) if gaps else 0,
        },
        "large_gaps_count": len(large_gaps),
        "large_gaps": [
            {"after_detection_idx": i, "gap_ms": round(g, 1)}
            for i, g in large_gaps[:10]  # cap at 10
        ],
        "long_non_detection_runs": non_detect_runs[:10],
    }


# ---------------------------------------------------------------------------
# Summary comparison
# ---------------------------------------------------------------------------

def compare_summaries(
    trajectory_15: tuple[CursorDetection, ...],
    trajectory_5: tuple[CursorDetection, ...],
    segments: tuple[VideoSegment, ...],
) -> list[dict]:
    """Generate and diff cursor summaries for each segment."""
    results = []
    for seg in segments:
        summary_15 = generate_cursor_summary(trajectory_15, seg)
        summary_5 = generate_cursor_summary(trajectory_5, seg)

        diff_lines = list(difflib.unified_diff(
            summary_15.splitlines(keepends=True),
            summary_5.splitlines(keepends=True),
            fromfile=f"segment_{seg.index:03d} (15fps)",
            tofile=f"segment_{seg.index:03d} (5fps)",
            lineterm="",
        ))

        results.append({
            "segment": seg.index,
            "lines_15fps": len(summary_15.splitlines()) if summary_15 else 0,
            "lines_5fps": len(summary_5.splitlines()) if summary_5 else 0,
            "summary_15fps": summary_15,
            "summary_5fps": summary_5,
            "diff": "\n".join(diff_lines) if diff_lines else "(identical)",
            "identical": not diff_lines,
        })

    return results


# ---------------------------------------------------------------------------
# Event cursor position comparison
# ---------------------------------------------------------------------------

def compare_cursor_enrichment(
    events_raw: list[dict],
    segment_responses: list[list],
    segments: tuple[VideoSegment, ...],
    trajectory_15: tuple[CursorDetection, ...],
    trajectory_5: tuple[CursorDetection, ...],
    offset: int,
) -> list[dict]:
    """Re-enrich events using both trajectories and compare cursor positions."""
    from vex_extract.merge import adjust_timestamps

    # Reconstruct resolved events from segment responses
    all_resolved: list[ResolvedEvent] = []
    for seg, raw_events in zip(segments, segment_responses):
        resolved = adjust_timestamps(raw_events, seg, offset)
        all_resolved.extend(resolved)
    all_resolved.sort(key=lambda e: e.time_start)

    # Enrich with both trajectories
    enriched_15 = enrich_cursor_positions(all_resolved, trajectory_15, offset, CURSOR_EVENT_TYPES)
    enriched_5 = enrich_cursor_positions(all_resolved, trajectory_5, offset, CURSOR_EVENT_TYPES)

    comparisons = []
    for e15, e5 in zip(enriched_15, enriched_5):
        if e15.type not in CURSOR_EVENT_TYPES:
            continue

        pos_15 = e15.cursor_position
        pos_5 = e5.cursor_position

        distance = None
        if pos_15 and pos_5:
            dx = pos_15["x"] - pos_5["x"]
            dy = pos_15["y"] - pos_5["y"]
            distance = round(math.sqrt(dx * dx + dy * dy), 1)

        comparisons.append({
            "type": e15.type,
            "time_start": e15.time_start,
            "description": e15.description[:80],
            "pos_15fps": pos_15,
            "pos_5fps": pos_5,
            "pixel_distance": distance,
            "15fps_has_position": pos_15 is not None,
            "5fps_has_position": pos_5 is not None,
            "coverage_lost": pos_15 is not None and pos_5 is None,
            "coverage_gained": pos_15 is None and pos_5 is not None,
        })

    return comparisons


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(
    quality_15: dict,
    quality_5: dict,
    summary_diffs: list[dict],
    cursor_comparisons: list[dict],
    tracking_time_15_ms: float,
    tracking_time_5_ms: float,
    trajectory_15: tuple[CursorDetection, ...],
    trajectory_5: tuple[CursorDetection, ...],
) -> str:
    """Build the final markdown report."""
    lines = ["# Experiment: tracking_peak_fps = 5 vs 15", ""]

    # --- Timing ---
    lines.append("## 1. Processing Time")
    lines.append("")
    lines.append(f"| Metric | 15fps | 5fps | Ratio |")
    lines.append(f"|--------|------:|-----:|------:|")
    lines.append(f"| Cursor tracking (ms) | {tracking_time_15_ms:,.0f} | {tracking_time_5_ms:,.0f} | {tracking_time_5_ms / tracking_time_15_ms:.2f}x |")
    lines.append(f"| Cursor tracking (s) | {tracking_time_15_ms / 1000:.1f} | {tracking_time_5_ms / 1000:.1f} | |")
    speedup = (1 - tracking_time_5_ms / tracking_time_15_ms) * 100
    lines.append(f"| Time saved | | | **{speedup:.0f}%** |")
    lines.append("")

    # --- Trajectory stats ---
    lines.append("## 2. Trajectory Statistics")
    lines.append("")
    det_15 = sum(1 for d in trajectory_15 if d.detected)
    det_5 = sum(1 for d in trajectory_5 if d.detected)
    lines.append(f"| Metric | 15fps | 5fps |")
    lines.append(f"|--------|------:|-----:|")
    lines.append(f"| Total samples | {len(trajectory_15)} | {len(trajectory_5)} |")
    lines.append(f"| Detected samples | {det_15} | {det_5} |")
    lines.append(f"| Detection rate | {det_15/len(trajectory_15)*100:.1f}% | {det_5/len(trajectory_5)*100:.1f}% |")
    lines.append(f"| Detections/sec | {quality_15['coverage_density_per_sec']} | {quality_5['coverage_density_per_sec']} |")
    lines.append("")

    # --- Quality check ---
    lines.append("## 3. Trajectory Quality (dropout check)")
    lines.append("")
    for q in (quality_15, quality_5):
        lines.append(f"### {q['label']}")
        lines.append(f"- Gap stats (between detected frames): median={q['gap_stats']['median_ms']}ms, p95={q['gap_stats']['p95_ms']}ms, max={q['gap_stats']['max_ms']}ms")
        lines.append(f"- Large gaps (>10x expected interval): {q['large_gaps_count']}")
        if q["long_non_detection_runs"]:
            lines.append(f"- Long non-detection runs (>5s):")
            for run in q["long_non_detection_runs"]:
                lines.append(f"  - {run['start_ms']/1000:.1f}s - {run['end_ms']/1000:.1f}s ({run['duration_ms']/1000:.1f}s)")
        else:
            lines.append(f"- No long non-detection runs (>5s)")
        lines.append("")

    # --- Summary comparison ---
    lines.append("## 4. Impact on CV Summary (Gemini prompt)")
    lines.append("")
    identical_count = sum(1 for s in summary_diffs if s["identical"])
    lines.append(f"Segments with identical summaries: {identical_count}/{len(summary_diffs)}")
    lines.append("")

    for sd in summary_diffs:
        lines.append(f"### Segment {sd['segment']}")
        lines.append(f"- 15fps: {sd['lines_15fps']} lines, 5fps: {sd['lines_5fps']} lines")
        if sd["identical"]:
            lines.append(f"- **Identical**")
        else:
            lines.append(f"- Diff:")
            lines.append("```diff")
            lines.append(sd["diff"])
            lines.append("```")
        lines.append("")

    # --- Cursor position comparison ---
    lines.append("## 5. Impact on Final Event Cursor Positions")
    lines.append("")

    cursor_events = [c for c in cursor_comparisons]
    both_have = [c for c in cursor_events if c["15fps_has_position"] and c["5fps_has_position"]]
    coverage_lost = [c for c in cursor_events if c["coverage_lost"]]
    coverage_gained = [c for c in cursor_events if c["coverage_gained"]]
    neither = [c for c in cursor_events if not c["15fps_has_position"] and not c["5fps_has_position"]]

    lines.append(f"| Category | Count |")
    lines.append(f"|----------|------:|")
    lines.append(f"| Cursor events total | {len(cursor_events)} |")
    lines.append(f"| Both have position | {len(both_have)} |")
    lines.append(f"| Coverage lost (15fps had, 5fps doesn't) | {len(coverage_lost)} |")
    lines.append(f"| Coverage gained (5fps has, 15fps didn't) | {len(coverage_gained)} |")
    lines.append(f"| Neither has position | {len(neither)} |")
    lines.append("")

    if both_have:
        distances = [c["pixel_distance"] for c in both_have if c["pixel_distance"] is not None]
        if distances:
            distances_sorted = sorted(distances)
            lines.append(f"### Position accuracy (where both have data)")
            lines.append(f"- Mean distance: {sum(distances)/len(distances):.1f}px")
            lines.append(f"- Median distance: {distances_sorted[len(distances_sorted)//2]:.1f}px")
            lines.append(f"- Max distance: {max(distances):.1f}px")
            lines.append(f"- Within 5px: {sum(1 for d in distances if d <= 5)}/{len(distances)}")
            lines.append(f"- Within 20px: {sum(1 for d in distances if d <= 20)}/{len(distances)}")
            lines.append(f"- Within 50px: {sum(1 for d in distances if d <= 50)}/{len(distances)}")
            lines.append("")

    if coverage_lost:
        lines.append("### Events that lost cursor coverage at 5fps")
        lines.append("")
        lines.append("| Time (ms) | Type | Description | 15fps pos |")
        lines.append("|----------:|------|-------------|-----------|")
        for c in coverage_lost:
            lines.append(f"| {c['time_start']:.0f} | {c['type']} | {c['description']} | ({c['pos_15fps']['x']},{c['pos_15fps']['y']}) |")
        lines.append("")

    if both_have:
        lines.append("### All cursor position comparisons")
        lines.append("")
        lines.append("| Time (ms) | Type | 15fps pos | 5fps pos | Distance (px) |")
        lines.append("|----------:|------|-----------|----------|-------------:|")
        for c in both_have:
            p15 = f"({c['pos_15fps']['x']},{c['pos_15fps']['y']})"
            p5 = f"({c['pos_5fps']['x']},{c['pos_5fps']['y']})"
            lines.append(f"| {c['time_start']:.0f} | {c['type']} | {p15} | {p5} | {c['pixel_distance']} |")
        lines.append("")

    # --- Conclusion ---
    lines.append("## 6. Conclusion")
    lines.append("")
    lines.append(f"- **Processing speedup**: {speedup:.0f}% faster cursor tracking at 5fps peak")
    lines.append(f"- **Summary fidelity**: {identical_count}/{len(summary_diffs)} segments produced identical Gemini prompts")
    if coverage_lost:
        lines.append(f"- **Coverage impact**: {len(coverage_lost)} events lost cursor position data")
    else:
        lines.append(f"- **Coverage impact**: No events lost cursor position data")
    if both_have:
        mean_dist = sum(d for d in distances if d is not None) / len(distances) if distances else 0
        lines.append(f"- **Position accuracy**: Mean {mean_dist:.1f}px drift where both have data")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Experiment: tracking_peak_fps = 5 vs 15")
    print("Session: travel_expert_william")
    print("=" * 60)

    # Load config and baseline
    config = load_config(APP_ROOT / "config.yaml")
    meta, baseline_events, trajectory_15, flow_windows, segment_responses = load_baseline()
    offset = meta["screen_track_start_offset"]
    video_path = Path(meta["video_path"])
    norm_path = APP_ROOT / "tmp" / f"{video_path.stem}_normalized.mp4"

    if not norm_path.exists():
        print(f"ERROR: Normalized video not found at {norm_path}")
        print("Run the pipeline at least through 'normalize' first.")
        sys.exit(1)

    tracking_time_15_ms = meta["timing"]["cursor_tracking_ms"]

    print(f"\nBaseline (15fps): {len(trajectory_15)} samples, "
          f"{sum(1 for d in trajectory_15 if d.detected)} detected, "
          f"tracked in {tracking_time_15_ms/1000:.1f}s")

    # --- Run 5fps cursor tracking (or load cached) ---
    config_5fps = CursorConfig(
        tracking_base_fps=config.cursor.tracking_base_fps,
        tracking_peak_fps=5.0,
        tracking_displacement_threshold_px=config.cursor.tracking_displacement_threshold_px,
        tracking_active_padding_ms=config.cursor.tracking_active_padding_ms,
        template_scales=config.cursor.template_scales,
        match_threshold=config.cursor.match_threshold,
        early_exit_threshold=config.cursor.early_exit_threshold,
        static_filter_duration_ms=config.cursor.static_filter_duration_ms,
        static_filter_tolerance_px=config.cursor.static_filter_tolerance_px,
        max_interpolation_gap_ms=config.cursor.max_interpolation_gap_ms,
        smooth_window=config.cursor.smooth_window,
        smooth_displacement_threshold=config.cursor.smooth_displacement_threshold,
    )

    templates_dir = APP_ROOT / "cursor_templates"
    video_meta = get_video_metadata(norm_path)

    cached_5fps = REPORT_DIR / "cursor_trajectory_5fps.json"
    cached_timing = REPORT_DIR / "tracking_time_5fps_ms.txt"

    if cached_5fps.exists() and cached_timing.exists():
        print("\nLoading cached 5fps cursor trajectory...")
        raw_5 = json.loads(cached_5fps.read_text())
        trajectory_5 = tuple(CursorDetection(**d) for d in raw_5)
        tracking_time_5_ms = float(cached_timing.read_text().strip())
    else:
        print("\nRunning cursor tracking at 5fps peak...")
        REPORT_DIR.mkdir(parents=True, exist_ok=True)

        t_start = time.monotonic()
        trajectory_5 = track_cursor(
            video_path=norm_path,
            config=config_5fps,
            templates_dir=templates_dir,
            total_duration_ms=video_meta.duration_ms,
        )
        tracking_time_5_ms = (time.monotonic() - t_start) * 1000

        # Cache for re-runs
        cached_5fps.write_text(json.dumps([d.model_dump() for d in trajectory_5], indent=2))
        cached_timing.write_text(str(tracking_time_5_ms))

    print(f"5fps result: {len(trajectory_5)} samples, "
          f"{sum(1 for d in trajectory_5 if d.detected)} detected, "
          f"tracked in {tracking_time_5_ms/1000:.1f}s")

    # --- Quality check ---
    print("\nAnalyzing trajectory quality...")
    quality_15 = analyze_trajectory_quality(trajectory_15, "15fps baseline", 1000.0 / 15.0)
    quality_5 = analyze_trajectory_quality(trajectory_5, "5fps experiment", 1000.0 / 5.0)

    # --- Build segments ---
    segments = build_segments(meta, config)

    # --- Compare summaries ---
    print("Comparing CV summaries per segment...")
    summary_diffs = compare_summaries(trajectory_15, trajectory_5, segments)

    # --- Compare cursor enrichment ---
    print("Comparing cursor position enrichment on events...")
    cursor_comparisons = compare_cursor_enrichment(
        baseline_events, segment_responses, segments,
        trajectory_15, trajectory_5, offset,
    )

    # --- Generate report ---
    print("Generating report...")
    report = generate_report(
        quality_15, quality_5,
        summary_diffs, cursor_comparisons,
        tracking_time_15_ms, tracking_time_5_ms,
        trajectory_15, trajectory_5,
    )

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / "report.md"
    report_path.write_text(report)
    print(f"\nReport written to: {report_path}")

    # Also save raw data for further analysis
    raw_data = {
        "tracking_time_15_ms": tracking_time_15_ms,
        "tracking_time_5_ms": tracking_time_5_ms,
        "trajectory_15_count": len(trajectory_15),
        "trajectory_5_count": len(trajectory_5),
        "trajectory_15_detected": sum(1 for d in trajectory_15 if d.detected),
        "trajectory_5_detected": sum(1 for d in trajectory_5 if d.detected),
        "quality_15": quality_15,
        "quality_5": quality_5,
        "summary_diffs": [
            {k: v for k, v in sd.items() if k != "diff"}
            for sd in summary_diffs
        ],
        "cursor_comparisons": cursor_comparisons,
    }
    (REPORT_DIR / "raw_data.json").write_text(json.dumps(raw_data, indent=2))

    # Save the 5fps trajectory for reference
    (REPORT_DIR / "cursor_trajectory_5fps.json").write_text(
        json.dumps([d.model_dump() for d in trajectory_5], indent=2)
    )

    print(f"Raw data written to: {REPORT_DIR / 'raw_data.json'}")
    print(f"5fps trajectory written to: {REPORT_DIR / 'cursor_trajectory_5fps.json'}")
    print("\nDone!")


if __name__ == "__main__":
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )
    main()
