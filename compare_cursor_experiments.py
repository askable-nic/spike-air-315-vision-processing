"""Compare cursor tracking results between two experiment iterations.

Compares cursor trajectories, per-segment cursor summaries, and event
cursor enrichment between a baseline and an experimental run.

Usage:
    python compare_cursor_experiments.py \\
        --base standalone-c/1 \\
        --experiment standalone-c/2 \\
        [--sessions id1,id2]

Both iterations must have cv/cursor_trajectory.json (from copy_results).
The base iteration should have events.json for enrichment comparison.
"""
from __future__ import annotations

import argparse
import difflib
import json
import math
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
EXPERIMENTS_DIR = PROJECT_ROOT / "experiments"

CURSOR_EVENT_TYPES = frozenset(
    ("click", "hover", "dwell", "cursor_thrash", "select", "drag")
)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_trajectory(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text())


def load_events(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text())


def load_cursor_summary(path: Path) -> str | None:
    if not path.exists():
        return None
    text = path.read_text()
    return text if text.strip() else None


def load_metadata(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def discover_sessions(base_dir: Path, exp_dir: Path) -> list[str]:
    """Return session IDs present in both experiment output directories."""
    base_sessions = {d.name for d in (base_dir / "output").iterdir() if d.is_dir()} if (base_dir / "output").is_dir() else set()
    exp_sessions = {d.name for d in (exp_dir / "output").iterdir() if d.is_dir()} if (exp_dir / "output").is_dir() else set()
    return sorted(base_sessions & exp_sessions)


def discover_segments(session_dir: Path) -> list[str]:
    """Return sorted segment directory names (e.g. segment_000, segment_001)."""
    seg_root = session_dir / "segments"
    if not seg_root.is_dir():
        return []
    return sorted(d.name for d in seg_root.iterdir() if d.is_dir())


# ---------------------------------------------------------------------------
# Cursor position lookup (standalone, no vex_extract import)
# ---------------------------------------------------------------------------

def lookup_cursor_at_ms(
    trajectory: list[dict],
    timestamp_ms: float,
    max_gap_ms: float = 500.0,
) -> dict | None:
    """Find the nearest detected trajectory point to timestamp_ms.

    Returns {"x": int, "y": int} or None if no detection is close enough.
    """
    best: dict | None = None
    best_dist = max_gap_ms

    for det in trajectory:
        if not det.get("detected", False):
            continue
        dist = abs(det["timestamp_ms"] - timestamp_ms)
        if dist < best_dist:
            best_dist = dist
            best = det

    if best is None:
        return None
    return {"x": best["x"], "y": best["y"]}


# ---------------------------------------------------------------------------
# Trajectory comparison
# ---------------------------------------------------------------------------

def compare_trajectories(
    base_traj: list[dict],
    exp_traj: list[dict],
) -> dict:
    base_by_ts = {d["timestamp_ms"]: d for d in base_traj}
    exp_by_ts = {d["timestamp_ms"]: d for d in exp_traj}

    common_ts = sorted(set(base_by_ts) & set(exp_by_ts))

    base_detected = sum(1 for d in base_traj if d.get("detected"))
    exp_detected = sum(1 for d in exp_traj if d.get("detected"))

    identical = 0
    both_detected = 0
    detection_disagreement = 0
    distances: list[float] = []

    for ts in common_ts:
        b, e = base_by_ts[ts], exp_by_ts[ts]
        b_det, e_det = b.get("detected", False), e.get("detected", False)

        if b_det == e_det and b.get("x") == e.get("x") and b.get("y") == e.get("y"):
            identical += 1

        if b_det and e_det:
            both_detected += 1
            d = math.sqrt((b["x"] - e["x"]) ** 2 + (b["y"] - e["y"]) ** 2)
            distances.append(d)
        elif b_det != e_det:
            detection_disagreement += 1

    return {
        "base_samples": len(base_traj),
        "exp_samples": len(exp_traj),
        "base_detected": base_detected,
        "exp_detected": exp_detected,
        "common_timestamps": len(common_ts),
        "identical": identical,
        "both_detected": both_detected,
        "detection_disagreement": detection_disagreement,
        "distances": distances,
    }


# ---------------------------------------------------------------------------
# Event enrichment comparison
# ---------------------------------------------------------------------------

def compare_event_enrichment(
    events: list[dict],
    base_traj: list[dict],
    exp_traj: list[dict],
) -> list[dict]:
    """Re-enrich events using both trajectories and compare cursor positions."""
    comparisons: list[dict] = []

    for event in events:
        etype = event.get("type", "")
        if etype not in CURSOR_EVENT_TYPES:
            continue

        ts = event.get("time_start", 0)
        base_pos = lookup_cursor_at_ms(base_traj, ts)
        exp_pos = lookup_cursor_at_ms(exp_traj, ts)

        distance: float | None = None
        if base_pos and exp_pos:
            distance = round(math.sqrt(
                (base_pos["x"] - exp_pos["x"]) ** 2
                + (base_pos["y"] - exp_pos["y"]) ** 2
            ), 1)

        comparisons.append({
            "type": etype,
            "time_start": ts,
            "description": event.get("description", "")[:80],
            "base_pos": base_pos,
            "exp_pos": exp_pos,
            "distance_px": distance,
            "coverage_lost": base_pos is not None and exp_pos is None,
            "coverage_gained": base_pos is None and exp_pos is not None,
        })

    return comparisons


# ---------------------------------------------------------------------------
# Summary diff
# ---------------------------------------------------------------------------

def diff_cursor_summaries(
    base_dir: Path,
    exp_dir: Path,
    segments: list[str],
    base_label: str,
    exp_label: str,
) -> list[dict]:
    results: list[dict] = []
    for seg_name in segments:
        base_text = load_cursor_summary(base_dir / "segments" / seg_name / "cursor_summary.txt")
        exp_text = load_cursor_summary(exp_dir / "segments" / seg_name / "cursor_summary.txt")

        base_lines = (base_text or "").splitlines(keepends=True)
        exp_lines = (exp_text or "").splitlines(keepends=True)

        diff = list(difflib.unified_diff(
            base_lines, exp_lines,
            fromfile=f"{seg_name} ({base_label})",
            tofile=f"{seg_name} ({exp_label})",
            lineterm="",
        ))

        results.append({
            "segment": seg_name,
            "base_lines": len(base_lines),
            "exp_lines": len(exp_lines),
            "base_present": base_text is not None,
            "exp_present": exp_text is not None,
            "identical": not diff,
            "diff": "\n".join(diff) if diff else None,
        })

    return results


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def generate_report(
    base_label: str,
    exp_label: str,
    session_results: list[dict],
) -> str:
    lines = [
        f"# Cursor Experiment Comparison: {base_label} vs {exp_label}",
        "",
    ]

    # --- Aggregate trajectory stats ---
    lines.append("## 1. Trajectory Comparison (aggregate)")
    lines.append("")
    lines.append(f"| Session | {base_label} det | {exp_label} det | Common | Identical | Both det | Disagree | Mean drift | Max drift |")
    lines.append(f"|---------|---:|---:|---:|---:|---:|---:|---:|---:|")

    total_base_det = 0
    total_exp_det = 0
    total_both = 0
    total_identical = 0
    all_distances: list[float] = []

    for r in session_results:
        t = r["trajectory"]
        total_base_det += t["base_detected"]
        total_exp_det += t["exp_detected"]
        total_both += t["both_detected"]
        total_identical += t["identical"]
        all_distances.extend(t["distances"])

        dists = t["distances"]
        mean_d = f"{sum(dists)/len(dists):.1f}" if dists else "—"
        max_d = f"{max(dists):.1f}" if dists else "—"
        lines.append(
            f"| {r['session']} | {t['base_detected']} | {t['exp_detected']} "
            f"| {t['common_timestamps']} | {t['identical']} | {t['both_detected']} "
            f"| {t['detection_disagreement']} | {mean_d} | {max_d} |"
        )

    mean_all = f"{sum(all_distances)/len(all_distances):.1f}" if all_distances else "—"
    max_all = f"{max(all_distances):.1f}" if all_distances else "—"
    lines.append(
        f"| **TOTAL** | **{total_base_det}** | **{total_exp_det}** "
        f"| — | **{total_identical}** | **{total_both}** "
        f"| — | **{mean_all}** | **{max_all}** |"
    )
    lines.append("")

    if all_distances:
        sorted_d = sorted(all_distances)
        lines.append("### Position accuracy (where both detected)")
        lines.append(f"- Samples: {len(sorted_d)}")
        lines.append(f"- Identical (0px): {sum(1 for d in sorted_d if d == 0)}")
        lines.append(f"- Within 1px: {sum(1 for d in sorted_d if d <= 1)}")
        lines.append(f"- Within 5px: {sum(1 for d in sorted_d if d <= 5)}")
        lines.append(f"- Median: {sorted_d[len(sorted_d)//2]:.1f}px")
        lines.append(f"- Mean: {mean_all}px")
        lines.append(f"- Max: {max_all}px")
        lines.append("")

    # --- Cursor summary diffs ---
    lines.append("## 2. Cursor Summary Diffs (per segment)")
    lines.append("")

    total_segs = 0
    identical_segs = 0
    changed_segs: list[dict] = []

    for r in session_results:
        for sd in r["summary_diffs"]:
            total_segs += 1
            if sd["identical"]:
                identical_segs += 1
            else:
                changed_segs.append({"session": r["session"], **sd})

    lines.append(f"Identical: {identical_segs}/{total_segs} segments")
    lines.append(f"Changed: {total_segs - identical_segs}/{total_segs} segments")
    lines.append("")

    if changed_segs:
        for cs in changed_segs:
            lines.append(f"### {cs['session']} / {cs['segment']}")
            lines.append(f"- {base_label}: {cs['base_lines']} lines, {exp_label}: {cs['exp_lines']} lines")
            if cs["diff"]:
                lines.append("```diff")
                # Truncate very long diffs
                diff_lines = cs["diff"].splitlines()
                if len(diff_lines) > 40:
                    lines.extend(diff_lines[:30])
                    lines.append(f"... ({len(diff_lines) - 30} more lines)")
                else:
                    lines.append(cs["diff"])
                lines.append("```")
            lines.append("")

    # --- Event enrichment ---
    lines.append("## 3. Event Cursor Enrichment")
    lines.append("")

    all_enrichments: list[dict] = []
    for r in session_results:
        all_enrichments.extend(r["enrichment"])

    if not all_enrichments:
        lines.append(f"No cursor events found in {base_label} events.json.")
        lines.append("")
    else:
        both = [e for e in all_enrichments if e["base_pos"] and e["exp_pos"]]
        lost = [e for e in all_enrichments if e["coverage_lost"]]
        gained = [e for e in all_enrichments if e["coverage_gained"]]
        neither = [e for e in all_enrichments if not e["base_pos"] and not e["exp_pos"]]

        lines.append(f"| Category | Count |")
        lines.append(f"|----------|------:|")
        lines.append(f"| Cursor events total | {len(all_enrichments)} |")
        lines.append(f"| Both have position | {len(both)} |")
        lines.append(f"| Coverage lost ({exp_label} missing) | {len(lost)} |")
        lines.append(f"| Coverage gained ({exp_label} new) | {len(gained)} |")
        lines.append(f"| Neither has position | {len(neither)} |")
        lines.append("")

        enrich_dists = [e["distance_px"] for e in both if e["distance_px"] is not None]
        if enrich_dists:
            sorted_ed = sorted(enrich_dists)
            lines.append("### Position accuracy on events")
            lines.append(f"- Mean: {sum(enrich_dists)/len(enrich_dists):.1f}px")
            lines.append(f"- Median: {sorted_ed[len(sorted_ed)//2]:.1f}px")
            lines.append(f"- Max: {max(enrich_dists):.1f}px")
            lines.append(f"- Within 5px: {sum(1 for d in enrich_dists if d <= 5)}/{len(enrich_dists)}")
            lines.append(f"- Within 20px: {sum(1 for d in enrich_dists if d <= 20)}/{len(enrich_dists)}")
            lines.append("")

        if lost:
            lines.append(f"### Events that lost cursor coverage ({len(lost)})")
            lines.append("")
            lines.append(f"| Time (ms) | Type | Description | {base_label} pos |")
            lines.append(f"|----------:|------|-------------|-----------|")
            for e in lost[:30]:
                lines.append(f"| {e['time_start']:.0f} | {e['type']} | {e['description']} | ({e['base_pos']['x']},{e['base_pos']['y']}) |")
            if len(lost) > 30:
                lines.append(f"| ... | | {len(lost) - 30} more | |")
            lines.append("")

        if gained:
            lines.append(f"### Events that gained cursor coverage ({len(gained)})")
            lines.append("")
            lines.append(f"| Time (ms) | Type | Description | {exp_label} pos |")
            lines.append(f"|----------:|------|-------------|-----------|")
            for e in gained[:30]:
                lines.append(f"| {e['time_start']:.0f} | {e['type']} | {e['description']} | ({e['exp_pos']['x']},{e['exp_pos']['y']}) |")
            if len(gained) > 30:
                lines.append(f"| ... | | {len(gained) - 30} more | |")
            lines.append("")

    # --- Config comparison ---
    lines.append("## 4. Config Comparison")
    lines.append("")

    configs_found = False
    for r in session_results:
        if r.get("base_config") and r.get("exp_config"):
            bc = r["base_config"].get("cursor", {})
            ec = r["exp_config"].get("cursor", {})
            all_keys = sorted(set(bc) | set(ec))
            diffs = [(k, bc.get(k), ec.get(k)) for k in all_keys if bc.get(k) != ec.get(k)]
            if diffs:
                lines.append(f"| Setting | {base_label} | {exp_label} |")
                lines.append(f"|---------|-------------|------------|")
                for k, bv, ev in diffs:
                    lines.append(f"| cursor.{k} | {bv} | {ev} |")
                lines.append("")
            else:
                lines.append("Cursor config is identical between both runs.")
                lines.append("")
            configs_found = True
            break

    if not configs_found:
        lines.append("Config metadata not available for comparison.")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare cursor tracking between two experiment iterations.",
    )
    parser.add_argument("--base", required=True, help="Base experiment path (e.g. standalone-c/1)")
    parser.add_argument("--experiment", required=True, help="Experiment path (e.g. standalone-c/2)")
    parser.add_argument("--sessions", default=None, help="Comma-separated session IDs (default: all common)")
    parser.add_argument("--output", default=None, help="Output report path (default: auto)")
    args = parser.parse_args()

    base_dir = EXPERIMENTS_DIR / args.base
    exp_dir = EXPERIMENTS_DIR / args.experiment

    if not base_dir.is_dir():
        print(f"Error: base directory not found: {base_dir}", file=sys.stderr)
        sys.exit(1)
    if not exp_dir.is_dir():
        print(f"Error: experiment directory not found: {exp_dir}", file=sys.stderr)
        sys.exit(1)

    base_label = args.base.replace("/", "_")
    exp_label = args.experiment.replace("/", "_")

    if args.sessions:
        sessions = args.sessions.split(",")
    else:
        sessions = discover_sessions(base_dir, exp_dir)

    if not sessions:
        print("No common sessions found between base and experiment.", file=sys.stderr)
        sys.exit(1)

    print(f"Comparing {args.base} (base) vs {args.experiment} (experiment)")
    print(f"Sessions: {len(sessions)}")
    print()

    session_results: list[dict] = []

    for sid in sessions:
        print(f"  {sid}...", end="", flush=True)
        base_session = base_dir / "output" / sid
        exp_session = exp_dir / "output" / sid

        base_traj = load_trajectory(base_session / "cv" / "cursor_trajectory.json")
        exp_traj = load_trajectory(exp_session / "cv" / "cursor_trajectory.json")
        base_events = load_events(base_session / "events.json")
        base_meta = load_metadata(base_session / "run_metadata.json")
        exp_meta = load_metadata(exp_session / "run_metadata.json")

        # Trajectory comparison
        traj_comp = compare_trajectories(base_traj, exp_traj)

        # Segment summary diffs
        all_segments = sorted(set(
            discover_segments(base_session) + discover_segments(exp_session)
        ))
        summary_diffs = diff_cursor_summaries(
            base_session, exp_session, all_segments, base_label, exp_label,
        )

        # Event enrichment comparison
        enrichment = compare_event_enrichment(base_events, base_traj, exp_traj)

        session_results.append({
            "session": sid,
            "trajectory": traj_comp,
            "summary_diffs": summary_diffs,
            "enrichment": enrichment,
            "base_config": base_meta.get("config") if base_meta else None,
            "exp_config": exp_meta.get("config") if exp_meta else None,
        })

        det_info = f"base:{traj_comp['base_detected']} exp:{traj_comp['exp_detected']}"
        lost = sum(1 for e in enrichment if e["coverage_lost"])
        gained = sum(1 for e in enrichment if e["coverage_gained"])
        print(f" detected=[{det_info}] cursor_events_lost={lost} gained={gained}")

    # Generate report
    report = generate_report(base_label, exp_label, session_results)

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = exp_dir / f"comparison_vs_{base_label}.md"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report)
    print(f"\nReport: {output_path}")


if __name__ == "__main__":
    main()
