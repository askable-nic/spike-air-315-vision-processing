"""Backfill cv/ and segments/ data from candidate output to standalone-c/1 experiment."""

import json
import shutil
from pathlib import Path

CANDIDATE_OUTPUT = Path("/Users/nic/Developer/spike-air-315-vision-processing/candidates/2026-03-14/output")
EXPERIMENT_OUTPUT = Path("/Users/nic/Developer/spike-air-315-vision-processing/experiments/standalone-c/1/output")

SESSION_IDS = [
    "travel_expert_veronika",
    "travel_expert_lisa",
    "travel_expert_william",
    "travel_learner_sophia_jayde",
    "opportunity_list_georgie",
    "opportunity_list_ben",
    "flight_centre_booking_kay",
    "flight_centre_booking_james",
    "cfs_home_loan_serene",
    "cfs_home_loan_sasha",
    "ask_results_usability_brandon",
    "ask_create_study_brandon",
]

CV_FILES = ["cursor_trajectory.json", "flow_windows.json"]
SEGMENT_FILES = ["cursor_summary.txt", "flow_summary.txt", "prompt.txt"]


def backfill():
    for session_id in SESSION_IDS:
        experiment_dir = EXPERIMENT_OUTPUT / session_id
        metadata_path = experiment_dir / "run_metadata.json"

        if not metadata_path.exists():
            print(f"  SKIP {session_id}: no run_metadata.json")
            continue

        with open(metadata_path) as f:
            metadata = json.load(f)

        run_id = metadata["run_id"]
        candidate_dir = CANDIDATE_OUTPUT / run_id

        if not candidate_dir.exists():
            print(f"  SKIP {session_id}: candidate run {run_id} not found")
            continue

        print(f"\n{session_id} (run_id={run_id})")

        # Copy cv/ files
        src_cv = candidate_dir / "cv"
        dst_cv = experiment_dir / "cv"
        if src_cv.exists():
            dst_cv.mkdir(exist_ok=True)
            for filename in CV_FILES:
                src = src_cv / filename
                dst = dst_cv / filename
                if src.exists():
                    shutil.copy2(src, dst)
                    size_kb = src.stat().st_size / 1024
                    print(f"  cv/{filename} ({size_kb:.1f} KB)")
                else:
                    print(f"  cv/{filename} — NOT FOUND in source")
        else:
            print(f"  cv/ — NOT FOUND in source")

        # Copy segment files
        src_segments = candidate_dir / "segments"
        dst_segments = experiment_dir / "segments"
        if src_segments.exists():
            segment_dirs = sorted(d for d in src_segments.iterdir() if d.is_dir())
            for seg_dir in segment_dirs:
                dst_seg = dst_segments / seg_dir.name
                dst_seg.mkdir(parents=True, exist_ok=True)
                for filename in SEGMENT_FILES:
                    src = seg_dir / filename
                    dst = dst_seg / filename
                    if src.exists():
                        shutil.copy2(src, dst)
                        size_kb = src.stat().st_size / 1024
                        print(f"  segments/{seg_dir.name}/{filename} ({size_kb:.1f} KB)")
                    else:
                        print(f"  segments/{seg_dir.name}/{filename} — NOT FOUND")
        else:
            print(f"  segments/ — NOT FOUND in source")


if __name__ == "__main__":
    backfill()
