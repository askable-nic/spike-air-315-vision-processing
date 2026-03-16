"""
Multi-config FPS experiment: runs multiple cursor tracking configs on a single
session and compares all against the highest-fidelity config as baseline.

Usage:
  python experiment_multi.py --gemini-run 2026-03-15_103341
"""
from __future__ import annotations

import argparse
import difflib
import json
import math
import sys
import time
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_ROOT))

from vex_extract.config import AppConfig, CursorConfig, load_config
from vex_extract.cursor import track_cursor
from vex_extract.cv_summary import generate_cursor_summary
from vex_extract.merge import adjust_timestamps, enrich_cursor_positions
from vex_extract.models import CursorDetection, FlowWindow, ResolvedEvent, VideoSegment
from vex_extract.video import compute_segments, get_video_metadata

CURSOR_EVENT_TYPES = ("click", "hover", "dwell", "cursor_thrash", "select", "drag")

CONFIGS = [
    {"label": "base2_peak15", "base_fps": 2.0, "peak_fps": 15.0},
    {"label": "base3_peak6",  "base_fps": 3.0, "peak_fps": 6.0},
    {"label": "base2_peak5",  "base_fps": 2.0, "peak_fps": 5.0},
]


def load_gemini_run(run_dir: Path):
    """Load metadata and Gemini segment responses from a no-cursor run."""
    meta = json.loads((run_dir / "run_metadata.json").read_text())
    events = json.loads((run_dir / "events.json").read_text())

    segment_responses = []
    seg_idx = 0
    while True:
        seg_dir = run_dir / "segments" / f"segment_{seg_idx:03d}"
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

    return meta, events, segment_responses


def build_segments(video_stem: str, duration_ms: float, config: AppConfig) -> tuple[VideoSegment, ...]:
    seg_key = (
        f"{video_stem}_normalized"
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


def run_or_load_tracking(
    label: str,
    base_fps: float,
    peak_fps: float,
    norm_path: Path,
    duration_ms: float,
    base_config: CursorConfig,
    report_dir: Path,
) -> tuple[tuple[CursorDetection, ...], float]:
    """Run cursor tracking or load from cache. Returns (trajectory, time_ms)."""
    cached_traj = report_dir / f"trajectory_{label}.json"
    cached_time = report_dir / f"time_{label}_ms.txt"

    if cached_traj.exists() and cached_time.exists():
        print(f"  {label}: loading cached...")
        raw = json.loads(cached_traj.read_text())
        trajectory = tuple(CursorDetection(**d) for d in raw)
        time_ms = float(cached_time.read_text().strip())
        return trajectory, time_ms

    cursor_config = CursorConfig(
        tracking_base_fps=base_fps,
        tracking_peak_fps=peak_fps,
        tracking_displacement_threshold_px=base_config.tracking_displacement_threshold_px,
        tracking_active_padding_ms=base_config.tracking_active_padding_ms,
        template_scales=base_config.template_scales,
        match_threshold=base_config.match_threshold,
        early_exit_threshold=base_config.early_exit_threshold,
        static_filter_duration_ms=base_config.static_filter_duration_ms,
        static_filter_tolerance_px=base_config.static_filter_tolerance_px,
        max_interpolation_gap_ms=base_config.max_interpolation_gap_ms,
        smooth_window=base_config.smooth_window,
        smooth_displacement_threshold=base_config.smooth_displacement_threshold,
    )

    templates_dir = APP_ROOT / "cursor_templates"

    print(f"  {label}: tracking...")
    t0 = time.monotonic()
    trajectory = track_cursor(
        video_path=norm_path,
        config=cursor_config,
        templates_dir=templates_dir,
        total_duration_ms=duration_ms,
    )
    time_ms = (time.monotonic() - t0) * 1000

    cached_traj.write_text(json.dumps([d.model_dump() for d in trajectory], indent=2))
    cached_time.write_text(str(time_ms))

    return trajectory, time_ms


def compare_enrichment(
    segment_responses: list[list],
    segments: tuple[VideoSegment, ...],
    traj_a: tuple[CursorDetection, ...],
    traj_b: tuple[CursorDetection, ...],
    offset: int,
) -> list[dict]:
    """Compare cursor enrichment between two trajectories."""
    all_resolved: list[ResolvedEvent] = []
    for seg, raw_events in zip(segments, segment_responses):
        resolved = adjust_timestamps(raw_events, seg, offset)
        all_resolved.extend(resolved)
    all_resolved.sort(key=lambda e: e.time_start)

    enriched_a = enrich_cursor_positions(all_resolved, traj_a, offset, CURSOR_EVENT_TYPES)
    enriched_b = enrich_cursor_positions(all_resolved, traj_b, offset, CURSOR_EVENT_TYPES)

    comparisons = []
    for ea, eb in zip(enriched_a, enriched_b):
        if ea.type not in CURSOR_EVENT_TYPES:
            continue

        pa, pb = ea.cursor_position, eb.cursor_position
        distance = None
        if pa and pb:
            distance = round(math.sqrt((pa["x"] - pb["x"]) ** 2 + (pa["y"] - pb["y"]) ** 2), 1)

        comparisons.append({
            "type": ea.type,
            "time_start": ea.time_start,
            "description": ea.description[:80],
            "pos_a": pa,
            "pos_b": pb,
            "pixel_distance": distance,
            "a_has": pa is not None,
            "b_has": pb is not None,
            "coverage_lost": pa is not None and pb is None,
        })

    return comparisons


def generate_report(
    session_name: str,
    video_duration_s: float,
    results: list[dict],
    baseline_label: str,
    comparisons_vs_baseline: dict[str, list[dict]],
    summary_line_counts: dict[str, list[int]],
) -> str:
    """Build the combined markdown report."""
    lines = [f"# Multi-config FPS Experiment: {session_name}", ""]
    lines.append(f"Video duration: {video_duration_s:.0f}s")
    lines.append("")

    # --- Timing table ---
    lines.append("## 1. Processing Time")
    lines.append("")
    bl = next(r for r in results if r["label"] == baseline_label)
    lines.append(f"| Config | Time (s) | Samples | Detected | Det/sec | Speedup vs {baseline_label} |")
    lines.append(f"|--------|--------:|--------:|---------:|--------:|------:|")
    for r in results:
        speedup = f"{(1 - r['time_ms'] / bl['time_ms']) * 100:.0f}%" if r["label"] != baseline_label else "—"
        lines.append(
            f"| {r['label']} | {r['time_ms']/1000:.1f} | {r['total']} | {r['detected']} "
            f"| {r['detected'] / (video_duration_s):.2f} | {speedup} |"
        )
    lines.append("")

    # --- Quality: non-detection runs ---
    lines.append("## 2. Trajectory Quality")
    lines.append("")
    for r in results:
        traj = r["trajectory"]
        detected = [d for d in traj if d.detected]
        gaps = [detected[i].timestamp_ms - detected[i-1].timestamp_ms for i in range(1, len(detected))]

        non_detect_runs = []
        run_start = None
        for i, d in enumerate(traj):
            if not d.detected:
                if run_start is None:
                    run_start = i
            else:
                if run_start is not None:
                    dur = traj[i-1].timestamp_ms - traj[run_start].timestamp_ms
                    if dur > 5000:
                        non_detect_runs.append(dur)
                    run_start = None

        lines.append(f"### {r['label']}")
        if gaps:
            sorted_gaps = sorted(gaps)
            lines.append(f"- Detection gaps: median={sorted_gaps[len(sorted_gaps)//2]:.0f}ms, "
                        f"p95={sorted_gaps[int(len(sorted_gaps)*0.95)]:.0f}ms, max={max(gaps):.0f}ms")
        lines.append(f"- Non-detection runs >5s: {len(non_detect_runs)}")
        lines.append("")

    # --- Summary line counts ---
    lines.append("## 3. CV Summary Size (lines per segment)")
    lines.append("")
    seg_count = len(next(iter(summary_line_counts.values())))
    header = "| Segment | " + " | ".join(r["label"] for r in results) + " |"
    sep = "|------:|" + "|------:" * len(results) + "|"
    lines.append(header)
    lines.append(sep)
    for i in range(seg_count):
        row = f"| {i} |"
        for r in results:
            row += f" {summary_line_counts[r['label']][i]} |"
        lines.append(row)
    lines.append("")

    # --- Cursor position comparison ---
    lines.append("## 4. Impact on Final Event Cursor Positions")
    lines.append("")
    lines.append(f"All comparisons are against **{baseline_label}** as reference.")
    lines.append("")

    for exp_label, comps in comparisons_vs_baseline.items():
        cursor_events = [c for c in comps]
        both = [c for c in cursor_events if c["a_has"] and c["b_has"]]
        lost = [c for c in cursor_events if c["coverage_lost"]]
        neither = [c for c in cursor_events if not c["a_has"] and not c["b_has"]]
        distances = [c["pixel_distance"] for c in both if c["pixel_distance"] is not None]

        lines.append(f"### {exp_label} vs {baseline_label}")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|------:|")
        lines.append(f"| Cursor events | {len(cursor_events)} |")
        lines.append(f"| Both have position | {len(both)} |")
        lines.append(f"| Coverage lost | {len(lost)} |")
        lines.append(f"| Neither has position | {len(neither)} |")

        if distances:
            sorted_d = sorted(distances)
            lines.append(f"| Mean distance | {sum(distances)/len(distances):.1f}px |")
            lines.append(f"| Median distance | {sorted_d[len(sorted_d)//2]:.1f}px |")
            lines.append(f"| Max distance | {max(distances):.1f}px |")
            lines.append(f"| Within 5px | {sum(1 for d in distances if d <= 5)}/{len(distances)} |")
            lines.append(f"| Within 50px | {sum(1 for d in distances if d <= 50)}/{len(distances)} |")
        lines.append("")

        if lost:
            lines.append(f"**Events that lost coverage:**")
            lines.append("")
            for c in lost:
                lines.append(f"- {c['time_start']:.0f}ms {c['type']}: {c['description']}")
            lines.append("")

        if distances and max(distances) > 5:
            lines.append(f"**Events with >5px drift:**")
            lines.append("")
            lines.append(f"| Time (ms) | Type | {baseline_label} | {exp_label} | Drift |")
            lines.append(f"|----------:|------|-----------|----------|------:|")
            for c in both:
                if c["pixel_distance"] and c["pixel_distance"] > 5:
                    pa = f"({c['pos_a']['x']},{c['pos_a']['y']})"
                    pb = f"({c['pos_b']['x']},{c['pos_b']['y']})"
                    lines.append(f"| {c['time_start']:.0f} | {c['type']} | {pa} | {pb} | {c['pixel_distance']}px |")
            lines.append("")

    # --- Summary ---
    lines.append("## 5. Summary")
    lines.append("")
    lines.append(f"| Config | Time | Speedup | Coverage lost | Mean drift | Max drift |")
    lines.append(f"|--------|-----:|--------:|--------------:|-----------:|----------:|")
    bl_time = bl["time_ms"]
    lines.append(f"| {baseline_label} | {bl_time/1000:.1f}s | — | — | — | — |")
    for exp_label, comps in comparisons_vs_baseline.items():
        r = next(x for x in results if x["label"] == exp_label)
        both = [c for c in comps if c["a_has"] and c["b_has"]]
        lost = sum(1 for c in comps if c["coverage_lost"])
        distances = [c["pixel_distance"] for c in both if c["pixel_distance"] is not None]
        mean_d = f"{sum(distances)/len(distances):.1f}px" if distances else "n/a"
        max_d = f"{max(distances):.1f}px" if distances else "n/a"
        speedup = f"{(1 - r['time_ms'] / bl_time) * 100:.0f}%"
        lines.append(f"| {exp_label} | {r['time_ms']/1000:.1f}s | {speedup} | {lost} | {mean_d} | {max_d} |")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Multi-config FPS experiment")
    parser.add_argument("--gemini-run", required=True, help="Run ID with Gemini results (e.g. 2026-03-15_103341)")
    args = parser.parse_args()

    gemini_run_dir = APP_ROOT / "output" / args.gemini_run
    meta, events, segment_responses = load_gemini_run(gemini_run_dir)

    video_path = Path(meta["video_path"])
    video_stem = video_path.stem
    offset = meta["screen_track_start_offset"]
    duration_ms = meta["video_duration_ms"]
    norm_path = APP_ROOT / "tmp" / f"{video_stem}_normalized.mp4"

    if not norm_path.exists():
        print(f"ERROR: Normalized video not found at {norm_path}")
        sys.exit(1)

    config = load_config(APP_ROOT / "config.yaml")
    video_meta = get_video_metadata(norm_path)
    segments = build_segments(video_stem, duration_ms, config)

    report_dir = APP_ROOT / "output" / f"experiment_multi_{video_stem}"
    report_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(f"Multi-config experiment: {video_stem}")
    print(f"Duration: {duration_ms/1000:.0f}s, Segments: {len(segments)}, Events: {len(events)}")
    print("=" * 60)

    # --- Run all configs ---
    results = []
    for cfg in CONFIGS:
        traj, t_ms = run_or_load_tracking(
            cfg["label"], cfg["base_fps"], cfg["peak_fps"],
            norm_path, video_meta.duration_ms, config.cursor, report_dir,
        )
        det = sum(1 for d in traj if d.detected)
        print(f"  {cfg['label']}: {len(traj)} samples, {det} detected, {t_ms/1000:.1f}s")
        results.append({
            "label": cfg["label"],
            "time_ms": t_ms,
            "total": len(traj),
            "detected": det,
            "trajectory": traj,
        })

    # --- Summaries ---
    print("\nComparing CV summaries...")
    summary_line_counts: dict[str, list[int]] = {}
    for r in results:
        counts = []
        for seg in segments:
            summary = generate_cursor_summary(r["trajectory"], seg)
            counts.append(len(summary.splitlines()) if summary else 0)
        summary_line_counts[r["label"]] = counts

    # --- Enrichment comparison vs baseline ---
    baseline_label = CONFIGS[0]["label"]
    baseline_traj = results[0]["trajectory"]

    print("Comparing cursor enrichment vs baseline...")
    comparisons_vs_baseline: dict[str, list[dict]] = {}
    for r in results[1:]:
        comps = compare_enrichment(
            segment_responses, segments,
            baseline_traj, r["trajectory"], offset,
        )
        comparisons_vs_baseline[r["label"]] = comps

    # --- Report ---
    print("Generating report...")
    report = generate_report(
        video_stem,
        duration_ms / 1000,
        results,
        baseline_label,
        comparisons_vs_baseline,
        summary_line_counts,
    )

    report_path = report_dir / "report.md"
    report_path.write_text(report)
    print(f"\nReport: {report_path}")
    print("Done!")


if __name__ == "__main__":
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )
    main()
