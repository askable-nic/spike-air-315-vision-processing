"""
Scale-calibration A/B comparison.

Runs cursor tracking twice with identical config:
  A) calibration disabled (monkeypatched _calibrate_scales returns None)
     — affinity still active, but fine pass uses all scales
  B) calibration enabled (normal code)
     — coarse pass narrows scales for fine pass

Compares timing and trajectory output to isolate the performance impact
of coarse-pass scale calibration.

Usage:
  python experiment_scale_affinity.py
"""
from __future__ import annotations

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

from vex_extract.config import load_config
from vex_extract import cursor as cursor_module
from vex_extract.cursor import track_cursor
from vex_extract.models import CursorDetection
from vex_extract.video import get_video_metadata

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASELINE_RUN = APP_ROOT / "output" / "2026-03-15_030547"


def compare_trajectories(
    baseline: tuple[CursorDetection, ...],
    experiment: tuple[CursorDetection, ...],
) -> dict:
    """Compare two trajectories sample-by-sample where timestamps align."""
    baseline_by_ts = {d.timestamp_ms: d for d in baseline}
    experiment_by_ts = {d.timestamp_ms: d for d in experiment}

    common_ts = sorted(set(baseline_by_ts) & set(experiment_by_ts))

    identical = 0
    both_detected = 0
    detection_disagreement = 0
    distances: list[float] = []

    for ts in common_ts:
        b = baseline_by_ts[ts]
        e = experiment_by_ts[ts]

        if b.detected == e.detected and b.x == e.x and b.y == e.y:
            identical += 1

        if b.detected and e.detected:
            both_detected += 1
            d = math.sqrt((b.x - e.x) ** 2 + (b.y - e.y) ** 2)
            distances.append(d)
        elif b.detected != e.detected:
            detection_disagreement += 1

    return {
        "baseline_samples": len(baseline),
        "experiment_samples": len(experiment),
        "common_timestamps": len(common_ts),
        "identical_samples": identical,
        "both_detected": both_detected,
        "detection_disagreement": detection_disagreement,
        "baseline_detected": sum(1 for d in baseline if d.detected),
        "experiment_detected": sum(1 for d in experiment if d.detected),
        "distances": distances,
    }


def run_tracking(config, norm_path, video_meta, templates_dir, label):
    """Run track_cursor and return (trajectory, time_ms)."""
    print(f"\nRunning: {label}...")
    t_start = time.monotonic()
    trajectory = track_cursor(
        video_path=norm_path,
        config=config.cursor,
        templates_dir=templates_dir,
        total_duration_ms=video_meta.duration_ms,
    )
    elapsed_ms = (time.monotonic() - t_start) * 1000
    det = sum(1 for d in trajectory if d.detected)
    print(f"  {len(trajectory)} samples, {det} detected, {elapsed_ms/1000:.1f}s")
    return trajectory, elapsed_ms


def main():
    config = load_config(APP_ROOT / "config.yaml")

    meta = json.loads((BASELINE_RUN / "run_metadata.json").read_text())
    video_path = Path(meta["video_path"])
    norm_path = APP_ROOT / "tmp" / f"{video_path.stem}_normalized.mp4"

    if not norm_path.exists():
        print(f"ERROR: Normalized video not found at {norm_path}")
        sys.exit(1)

    video_meta = get_video_metadata(norm_path)
    templates_dir = APP_ROOT / "cursor_templates"

    print("=" * 60)
    print("Scale-calibration A/B test")
    print(f"Session: {video_path.stem}")
    print(f"Config: base={config.cursor.tracking_base_fps}, peak={config.cursor.tracking_peak_fps}, "
          f"match_height={config.cursor.match_height}, scales={config.cursor.template_scales}")
    print("=" * 60)

    # --- A) Without calibration (monkeypatch _calibrate_scales to return None) ---
    original_calibrate = cursor_module._calibrate_scales

    def _calibrate_disabled(*_args, **_kwargs):
        return None

    cursor_module._calibrate_scales = _calibrate_disabled
    traj_no_calibration, time_no_calibration = run_tracking(
        config, norm_path, video_meta, templates_dir,
        "A) No scale calibration (affinity still active)",
    )

    # --- B) With calibration (restore original) ---
    cursor_module._calibrate_scales = original_calibrate
    traj_with_calibration, time_with_calibration = run_tracking(
        config, norm_path, video_meta, templates_dir,
        "B) Scale calibration enabled",
    )

    # --- Compare ---
    comp = compare_trajectories(traj_no_calibration, traj_with_calibration)

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    print(f"\n## Timing")
    print(f"  No calibration:   {time_no_calibration/1000:.1f}s")
    print(f"  With calibration: {time_with_calibration/1000:.1f}s")
    speedup = (1 - time_with_calibration / time_no_calibration) * 100
    print(f"  Speedup:          {speedup:.1f}%")

    print(f"\n## Trajectory")
    print(f"  No calibration:   {comp['baseline_samples']} samples ({comp['baseline_detected']} detected)")
    print(f"  With calibration: {comp['experiment_samples']} samples ({comp['experiment_detected']} detected)")
    print(f"  Common timestamps:       {comp['common_timestamps']}")
    print(f"  Identical samples:       {comp['identical_samples']}/{comp['common_timestamps']}")
    print(f"  Detection disagreements: {comp['detection_disagreement']}")

    if comp["distances"]:
        dists = sorted(comp["distances"])
        zero_drift = sum(1 for d in dists if d == 0.0)
        print(f"\n## Position Accuracy (both detected: {comp['both_detected']})")
        print(f"  Identical position: {zero_drift}/{len(dists)}")
        print(f"  Mean drift:   {sum(dists)/len(dists):.1f}px")
        print(f"  Median drift: {dists[len(dists)//2]:.1f}px")
        print(f"  Max drift:    {max(dists):.1f}px")
        print(f"  Within 1px:   {sum(1 for d in dists if d <= 1)}/{len(dists)}")
        print(f"  Within 5px:   {sum(1 for d in dists if d <= 5)}/{len(dists)}")
        print(f"  Within 20px:  {sum(1 for d in dists if d <= 20)}/{len(dists)}")
    else:
        print("\n## Position Accuracy: no common detected timestamps to compare")

    # --- Save ---
    output_dir = APP_ROOT / "output" / "experiment_scale_affinity"
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "trajectory_no_calibration.json").write_text(
        json.dumps([d.model_dump() for d in traj_no_calibration], indent=2)
    )
    (output_dir / "trajectory_with_calibration.json").write_text(
        json.dumps([d.model_dump() for d in traj_with_calibration], indent=2)
    )
    (output_dir / "comparison.json").write_text(json.dumps({
        "time_no_calibration_ms": time_no_calibration,
        "time_with_calibration_ms": time_with_calibration,
        "speedup_pct": round(speedup, 1),
        "samples_no_calibration": comp["baseline_samples"],
        "samples_with_calibration": comp["experiment_samples"],
        "detected_no_calibration": comp["baseline_detected"],
        "detected_with_calibration": comp["experiment_detected"],
        "common_timestamps": comp["common_timestamps"],
        "identical_samples": comp["identical_samples"],
        "detection_disagreement": comp["detection_disagreement"],
        "both_detected": comp["both_detected"],
        "mean_drift_px": round(sum(comp["distances"]) / len(comp["distances"]), 2) if comp["distances"] else None,
        "max_drift_px": round(max(comp["distances"]), 2) if comp["distances"] else None,
    }, indent=2))

    print(f"\nResults saved to {output_dir}")


if __name__ == "__main__":
    main()
