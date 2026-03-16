"""
Parameterized FPS experiment runner.

Compares cursor tracking with custom base/peak FPS against the existing
base=2/peak=15 baseline on travel_expert_william, measuring impact on:
  a) CV summary sent to Gemini (prompt text)
  b) Cursor lookups on final merged events
  c) Processing time

Usage:
  python experiment_fps.py --base-fps 1 --peak-fps 5
"""
from __future__ import annotations

import argparse
import difflib
import json
import math
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
APP_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_ROOT))

from vex_extract.config import AppConfig, CursorConfig, load_config
from vex_extract.cursor import track_cursor
from vex_extract.cv_summary import generate_cursor_summary
from vex_extract.merge import enrich_cursor_positions, adjust_timestamps
from vex_extract.models import CursorDetection, FlowWindow, ResolvedEvent, VideoSegment
from vex_extract.video import compute_segments, get_video_metadata

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASELINE_RUN = APP_ROOT / "output" / "2026-03-15_030547"
CURSOR_EVENT_TYPES = ("click", "hover", "dwell", "cursor_thrash", "select", "drag")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_baseline():
    meta = json.loads((BASELINE_RUN / "run_metadata.json").read_text())
    events = json.loads((BASELINE_RUN / "events.json").read_text())
    trajectory_raw = json.loads((BASELINE_RUN / "cv" / "cursor_trajectory.json").read_text())
    trajectory = tuple(CursorDetection(**d) for d in trajectory_raw)
    flow_raw = json.loads((BASELINE_RUN / "cv" / "flow_windows.json").read_text())
    flow_windows = tuple(FlowWindow(**fw) for fw in flow_raw)

    segment_responses = []
    seg_idx = 0
    while True:
        seg_dir = BASELINE_RUN / "segments" / f"segment_{seg_idx:03d}"
        if not seg_dir.exists():
            break
        resp_path = seg_dir / "response.json"
        if resp_path.exists():
            raw = json.loads(resp_path.read_text())
            if isinstance(raw, dict) and "text" in raw:
                segment_responses.append(json.loads(raw["text"]))
            else:
                segment_responses.append(raw if isinstance(raw, list) else [])
        else:
            segment_responses.append([])
        seg_idx += 1

    return meta, events, trajectory, flow_windows, segment_responses


def build_segments(meta: dict, config: AppConfig) -> tuple[VideoSegment, ...]:
    duration_ms = meta["video_duration_ms"]
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
# Quality check
# ---------------------------------------------------------------------------

def analyze_trajectory_quality(
    trajectory: tuple[CursorDetection, ...],
    label: str,
    expected_peak_interval_ms: float,
) -> dict:
    if not trajectory:
        return {"label": label, "total": 0, "detected": 0, "issues": ["empty trajectory"]}

    detected = [d for d in trajectory if d.detected]
    total_duration_ms = trajectory[-1].timestamp_ms - trajectory[0].timestamp_ms

    gaps = []
    for i in range(1, len(detected)):
        gaps.append(detected[i].timestamp_ms - detected[i - 1].timestamp_ms)

    large_gap_threshold_ms = expected_peak_interval_ms * 10
    large_gaps = [(i, g) for i, g in enumerate(gaps) if g > large_gap_threshold_ms]

    non_detect_runs = []
    run_start = None
    for i, d in enumerate(trajectory):
        if not d.detected:
            if run_start is None:
                run_start = i
        else:
            if run_start is not None:
                run_dur = trajectory[i - 1].timestamp_ms - trajectory[run_start].timestamp_ms
                if run_dur > 5000:
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
            for i, g in large_gaps[:10]
        ],
        "long_non_detection_runs": non_detect_runs[:10],
    }


# ---------------------------------------------------------------------------
# Summary comparison
# ---------------------------------------------------------------------------

def compare_summaries(
    trajectory_baseline: tuple[CursorDetection, ...],
    trajectory_exp: tuple[CursorDetection, ...],
    segments: tuple[VideoSegment, ...],
    baseline_label: str,
    exp_label: str,
) -> list[dict]:
    results = []
    for seg in segments:
        summary_base = generate_cursor_summary(trajectory_baseline, seg)
        summary_exp = generate_cursor_summary(trajectory_exp, seg)

        diff_lines = list(difflib.unified_diff(
            summary_base.splitlines(keepends=True),
            summary_exp.splitlines(keepends=True),
            fromfile=f"segment_{seg.index:03d} ({baseline_label})",
            tofile=f"segment_{seg.index:03d} ({exp_label})",
            lineterm="",
        ))

        results.append({
            "segment": seg.index,
            "lines_baseline": len(summary_base.splitlines()) if summary_base else 0,
            "lines_exp": len(summary_exp.splitlines()) if summary_exp else 0,
            "summary_baseline": summary_base,
            "summary_exp": summary_exp,
            "diff": "\n".join(diff_lines) if diff_lines else "(identical)",
            "identical": not diff_lines,
        })

    return results


# ---------------------------------------------------------------------------
# Event cursor position comparison
# ---------------------------------------------------------------------------

def compare_cursor_enrichment(
    segment_responses: list[list],
    segments: tuple[VideoSegment, ...],
    trajectory_baseline: tuple[CursorDetection, ...],
    trajectory_exp: tuple[CursorDetection, ...],
    offset: int,
) -> list[dict]:
    all_resolved: list[ResolvedEvent] = []
    for seg, raw_events in zip(segments, segment_responses):
        resolved = adjust_timestamps(raw_events, seg, offset)
        all_resolved.extend(resolved)
    all_resolved.sort(key=lambda e: e.time_start)

    enriched_base = enrich_cursor_positions(all_resolved, trajectory_baseline, offset, CURSOR_EVENT_TYPES)
    enriched_exp = enrich_cursor_positions(all_resolved, trajectory_exp, offset, CURSOR_EVENT_TYPES)

    comparisons = []
    for eb, ee in zip(enriched_base, enriched_exp):
        if eb.type not in CURSOR_EVENT_TYPES:
            continue

        pos_base = eb.cursor_position
        pos_exp = ee.cursor_position

        distance = None
        if pos_base and pos_exp:
            dx = pos_base["x"] - pos_exp["x"]
            dy = pos_base["y"] - pos_exp["y"]
            distance = round(math.sqrt(dx * dx + dy * dy), 1)

        comparisons.append({
            "type": eb.type,
            "time_start": eb.time_start,
            "description": eb.description[:80],
            "pos_baseline": pos_base,
            "pos_exp": pos_exp,
            "pixel_distance": distance,
            "baseline_has_position": pos_base is not None,
            "exp_has_position": pos_exp is not None,
            "coverage_lost": pos_base is not None and pos_exp is None,
            "coverage_gained": pos_base is None and pos_exp is not None,
        })

    return comparisons


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def generate_report(
    baseline_label: str,
    exp_label: str,
    quality_baseline: dict,
    quality_exp: dict,
    summary_diffs: list[dict],
    cursor_comparisons: list[dict],
    tracking_time_baseline_ms: float,
    tracking_time_exp_ms: float,
    trajectory_baseline: tuple[CursorDetection, ...],
    trajectory_exp: tuple[CursorDetection, ...],
) -> str:
    lines = [f"# Experiment: {exp_label} vs {baseline_label}", ""]

    # --- Timing ---
    lines.append("## 1. Processing Time")
    lines.append("")
    lines.append(f"| Metric | {baseline_label} | {exp_label} | Ratio |")
    lines.append(f"|--------|------:|-----:|------:|")
    lines.append(f"| Cursor tracking (ms) | {tracking_time_baseline_ms:,.0f} | {tracking_time_exp_ms:,.0f} | {tracking_time_exp_ms / tracking_time_baseline_ms:.2f}x |")
    lines.append(f"| Cursor tracking (s) | {tracking_time_baseline_ms / 1000:.1f} | {tracking_time_exp_ms / 1000:.1f} | |")
    speedup = (1 - tracking_time_exp_ms / tracking_time_baseline_ms) * 100
    lines.append(f"| Time saved | | | **{speedup:.0f}%** |")
    lines.append("")

    # --- Trajectory stats ---
    lines.append("## 2. Trajectory Statistics")
    lines.append("")
    det_base = sum(1 for d in trajectory_baseline if d.detected)
    det_exp = sum(1 for d in trajectory_exp if d.detected)
    lines.append(f"| Metric | {baseline_label} | {exp_label} |")
    lines.append(f"|--------|------:|-----:|")
    lines.append(f"| Total samples | {len(trajectory_baseline)} | {len(trajectory_exp)} |")
    lines.append(f"| Detected samples | {det_base} | {det_exp} |")
    lines.append(f"| Detection rate | {det_base/len(trajectory_baseline)*100:.1f}% | {det_exp/len(trajectory_exp)*100:.1f}% |")
    lines.append(f"| Detections/sec | {quality_baseline['coverage_density_per_sec']} | {quality_exp['coverage_density_per_sec']} |")
    lines.append("")

    # --- Active region impact ---
    lines.append("## 3. Coarse Pass & Active Region Impact")
    lines.append("")
    lines.append("The coarse pass (base FPS) determines which time ranges are scanned at peak FPS.")
    lines.append("A lower base FPS means fewer coarse samples, which can cause the system to")
    lines.append("miss brief cursor movements that fall between coarse samples.")
    lines.append("")

    # --- Quality check ---
    lines.append("## 4. Trajectory Quality (dropout check)")
    lines.append("")
    for q in (quality_baseline, quality_exp):
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
    lines.append("## 5. Impact on CV Summary (Gemini prompt)")
    lines.append("")
    identical_count = sum(1 for s in summary_diffs if s["identical"])
    lines.append(f"Segments with identical summaries: {identical_count}/{len(summary_diffs)}")
    lines.append("")

    for sd in summary_diffs:
        lines.append(f"### Segment {sd['segment']}")
        lines.append(f"- {baseline_label}: {sd['lines_baseline']} lines, {exp_label}: {sd['lines_exp']} lines")
        if sd["identical"]:
            lines.append(f"- **Identical**")
        else:
            lines.append(f"- Diff:")
            lines.append("```diff")
            lines.append(sd["diff"])
            lines.append("```")
        lines.append("")

    # --- Cursor position comparison ---
    lines.append("## 6. Impact on Final Event Cursor Positions")
    lines.append("")

    cursor_events = list(cursor_comparisons)
    both_have = [c for c in cursor_events if c["baseline_has_position"] and c["exp_has_position"]]
    coverage_lost = [c for c in cursor_events if c["coverage_lost"]]
    coverage_gained = [c for c in cursor_events if c["coverage_gained"]]
    neither = [c for c in cursor_events if not c["baseline_has_position"] and not c["exp_has_position"]]

    lines.append(f"| Category | Count |")
    lines.append(f"|----------|------:|")
    lines.append(f"| Cursor events total | {len(cursor_events)} |")
    lines.append(f"| Both have position | {len(both_have)} |")
    lines.append(f"| Coverage lost ({baseline_label} had, {exp_label} doesn't) | {len(coverage_lost)} |")
    lines.append(f"| Coverage gained ({exp_label} has, {baseline_label} didn't) | {len(coverage_gained)} |")
    lines.append(f"| Neither has position | {len(neither)} |")
    lines.append("")

    distances = []
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
        lines.append(f"### Events that lost cursor coverage")
        lines.append("")
        lines.append(f"| Time (ms) | Type | Description | {baseline_label} pos |")
        lines.append(f"|----------:|------|-------------|-----------|")
        for c in coverage_lost:
            lines.append(f"| {c['time_start']:.0f} | {c['type']} | {c['description']} | ({c['pos_baseline']['x']},{c['pos_baseline']['y']}) |")
        lines.append("")

    if both_have:
        lines.append("### All cursor position comparisons")
        lines.append("")
        lines.append(f"| Time (ms) | Type | {baseline_label} pos | {exp_label} pos | Distance (px) |")
        lines.append(f"|----------:|------|-----------|----------|-------------:|")
        for c in both_have:
            pb = f"({c['pos_baseline']['x']},{c['pos_baseline']['y']})"
            pe = f"({c['pos_exp']['x']},{c['pos_exp']['y']})"
            lines.append(f"| {c['time_start']:.0f} | {c['type']} | {pb} | {pe} | {c['pixel_distance']} |")
        lines.append("")

    # --- Conclusion ---
    lines.append("## 7. Conclusion")
    lines.append("")
    lines.append(f"- **Processing speedup**: {speedup:.0f}% faster cursor tracking")
    lines.append(f"- **Summary fidelity**: {identical_count}/{len(summary_diffs)} segments produced identical Gemini prompts")
    if coverage_lost:
        lines.append(f"- **Coverage impact**: {len(coverage_lost)} events lost cursor position data")
    else:
        lines.append(f"- **Coverage impact**: No events lost cursor position data")
    if distances:
        mean_dist = sum(distances) / len(distances)
        lines.append(f"- **Position accuracy**: Mean {mean_dist:.1f}px drift where both have data")
    elif both_have:
        lines.append(f"- **Position accuracy**: No overlapping positions to compare")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="FPS experiment runner")
    parser.add_argument("--base-fps", type=float, required=True, help="Coarse pass FPS")
    parser.add_argument("--peak-fps", type=float, required=True, help="Fine pass FPS")
    args = parser.parse_args()

    exp_label = f"base{args.base_fps:.0f}_peak{args.peak_fps:.0f}"
    baseline_label = "base2_peak15"
    report_dir = APP_ROOT / "output" / f"experiment_{exp_label}"

    print("=" * 60)
    print(f"Experiment: {exp_label} vs {baseline_label}")
    print("Session: travel_expert_william")
    print("=" * 60)

    config = load_config(APP_ROOT / "config.yaml")
    meta, baseline_events, trajectory_baseline, flow_windows, segment_responses = load_baseline()
    offset = meta["screen_track_start_offset"]
    video_path = Path(meta["video_path"])
    norm_path = APP_ROOT / "tmp" / f"{video_path.stem}_normalized.mp4"

    if not norm_path.exists():
        print(f"ERROR: Normalized video not found at {norm_path}")
        sys.exit(1)

    tracking_time_baseline_ms = meta["timing"]["cursor_tracking_ms"]

    print(f"\nBaseline ({baseline_label}): {len(trajectory_baseline)} samples, "
          f"{sum(1 for d in trajectory_baseline if d.detected)} detected, "
          f"tracked in {tracking_time_baseline_ms/1000:.1f}s")

    # --- Build experiment config ---
    config_exp = CursorConfig(
        tracking_base_fps=args.base_fps,
        tracking_peak_fps=args.peak_fps,
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

    # --- Run or load cached ---
    report_dir.mkdir(parents=True, exist_ok=True)
    cached_trajectory = report_dir / "cursor_trajectory.json"
    cached_timing = report_dir / "tracking_time_ms.txt"

    if cached_trajectory.exists() and cached_timing.exists():
        print(f"\nLoading cached {exp_label} cursor trajectory...")
        raw_exp = json.loads(cached_trajectory.read_text())
        trajectory_exp = tuple(CursorDetection(**d) for d in raw_exp)
        tracking_time_exp_ms = float(cached_timing.read_text().strip())
    else:
        print(f"\nRunning cursor tracking at base={args.base_fps}, peak={args.peak_fps}...")

        t_start = time.monotonic()
        trajectory_exp = track_cursor(
            video_path=norm_path,
            config=config_exp,
            templates_dir=templates_dir,
            total_duration_ms=video_meta.duration_ms,
        )
        tracking_time_exp_ms = (time.monotonic() - t_start) * 1000

        cached_trajectory.write_text(json.dumps([d.model_dump() for d in trajectory_exp], indent=2))
        cached_timing.write_text(str(tracking_time_exp_ms))

    det_exp = sum(1 for d in trajectory_exp if d.detected)
    print(f"{exp_label} result: {len(trajectory_exp)} samples, "
          f"{det_exp} detected, tracked in {tracking_time_exp_ms/1000:.1f}s")

    # --- Quality check ---
    print("\nAnalyzing trajectory quality...")
    quality_baseline = analyze_trajectory_quality(
        trajectory_baseline, f"{baseline_label} baseline", 1000.0 / 15.0,
    )
    quality_exp = analyze_trajectory_quality(
        trajectory_exp, f"{exp_label} experiment", 1000.0 / args.peak_fps,
    )

    # --- Build segments ---
    segments = build_segments(meta, config)

    # --- Compare summaries ---
    print("Comparing CV summaries per segment...")
    summary_diffs = compare_summaries(
        trajectory_baseline, trajectory_exp, segments,
        baseline_label, exp_label,
    )

    # --- Compare cursor enrichment ---
    print("Comparing cursor position enrichment on events...")
    cursor_comparisons = compare_cursor_enrichment(
        segment_responses, segments,
        trajectory_baseline, trajectory_exp, offset,
    )

    # --- Generate report ---
    print("Generating report...")
    report = generate_report(
        baseline_label, exp_label,
        quality_baseline, quality_exp,
        summary_diffs, cursor_comparisons,
        tracking_time_baseline_ms, tracking_time_exp_ms,
        trajectory_baseline, trajectory_exp,
    )

    report_path = report_dir / "report.md"
    report_path.write_text(report)
    print(f"\nReport written to: {report_path}")

    # Save raw data
    raw_data = {
        "baseline_label": baseline_label,
        "exp_label": exp_label,
        "tracking_time_baseline_ms": tracking_time_baseline_ms,
        "tracking_time_exp_ms": tracking_time_exp_ms,
        "trajectory_baseline_count": len(trajectory_baseline),
        "trajectory_exp_count": len(trajectory_exp),
        "trajectory_baseline_detected": sum(1 for d in trajectory_baseline if d.detected),
        "trajectory_exp_detected": det_exp,
        "quality_baseline": quality_baseline,
        "quality_exp": quality_exp,
        "summary_diffs": [
            {k: v for k, v in sd.items() if k != "diff"}
            for sd in summary_diffs
        ],
        "cursor_comparisons": cursor_comparisons,
    }
    (report_dir / "raw_data.json").write_text(json.dumps(raw_data, indent=2))

    print(f"Raw data written to: {report_dir / 'raw_data.json'}")
    print("\nDone!")


if __name__ == "__main__":
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )
    main()
