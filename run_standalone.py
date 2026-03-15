"""Orchestrate standalone vex_extract runs across manifest sessions.

Runs the candidate pipeline for each session and copies event output
into an experiment branch directory.

Usage:
    python run_standalone.py \\
        --candidate 2026-03-14 \\
        --branch standalone \\
        --iteration 1 \\
        [--sessions id1,id2] \\
        [--force] \\
        [--no-cursor] [--no-flow] \\
        [-- --stop-after flow --skip cursor]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Sequence


def parse_args(argv: Sequence[str]) -> tuple[argparse.Namespace, list[str]]:
    """Parse orchestrator args and collect pass-through args for vex_extract."""
    parser = argparse.ArgumentParser(
        description="Orchestrate standalone vex_extract runs across sessions.",
    )
    parser.add_argument("--candidate", required=True, help="Candidate version directory (e.g. 2026-03-14)")
    parser.add_argument("--branch", required=True, help="Experiment branch name")
    parser.add_argument("--iteration", required=True, help="Iteration number/name")
    parser.add_argument("--sessions", default=None, help="Comma-separated session identifiers to target")
    parser.add_argument("--force", action="store_true", help="Rerun sessions that already have results")
    parser.add_argument("--no-cursor", action="store_true", help="Skip cursor tracking entirely")
    parser.add_argument("--no-flow", action="store_true", help="Skip optical flow analysis")
    args, extra = parser.parse_known_args(argv)
    # Strip leading '--' separator if the user used it to delimit pass-through args
    if extra and extra[0] == "--":
        extra = extra[1:]
    # Translate convenience flags into pass-through args
    if args.no_cursor:
        extra.append("--no-cursor")
    if args.no_flow:
        extra.append("--no-flow")
    return args, extra


def load_sessions(manifest_path: Path) -> tuple[dict[str, Any], ...]:
    """Read manifest.json and return session dicts."""
    with open(manifest_path) as f:
        return tuple(json.load(f))


def resolve_video_path(session: dict[str, Any], input_data_dir: Path) -> Path:
    """Resolve the screen track video path for a session."""
    return (input_data_dir / session["data"]["screenTrack"]).resolve()


def filter_sessions(
    sessions: tuple[dict[str, Any], ...],
    requested_ids: frozenset[str] | None,
    experiment_output_dir: Path,
    force: bool,
) -> tuple[dict[str, Any], ...]:
    """Select sessions to run based on CLI flags and existing results."""
    result: list[dict[str, Any]] = []

    if requested_ids is not None:
        manifest_ids = {s["identifier"] for s in sessions}
        unknown = requested_ids - manifest_ids
        for uid in sorted(unknown):
            print(f"  Warning: session '{uid}' not found in manifest, skipping")

    for session in sessions:
        sid = session["identifier"]
        if requested_ids is not None and sid not in requested_ids:
            continue
        events_path = experiment_output_dir / sid / "events.json"
        if events_path.exists() and not force:
            continue
        result.append(session)
    return tuple(result)


def build_command(
    python_path: Path,
    video_path: Path,
    offset: int,
    extra_args: list[str],
) -> list[str]:
    """Assemble the vex_extract subprocess command."""
    return [
        str(python_path), "-m", "vex_extract",
        "--video", str(video_path),
        "--offset", str(offset),
        *extra_args,
    ]


def find_run_output(candidate_output_dir: Path, stdout_text: str) -> Path | None:
    """Locate the run output directory from subprocess stdout or by newest dir."""
    # Primary: parse "Output: <path>" from the last matching line
    for line in reversed(stdout_text.splitlines()):
        match = re.match(r"Output:\s+(.+)", line.strip())
        if match:
            path = Path(match.group(1).strip())
            if path.is_dir():
                return path

    # Fallback: newest directory in the candidate output folder
    if candidate_output_dir.is_dir():
        dirs = sorted(
            (d for d in candidate_output_dir.iterdir() if d.is_dir()),
            key=lambda d: d.name,
        )
        if dirs:
            return dirs[-1]

    return None


def copy_results(run_dir: Path, dest_dir: Path) -> tuple[str, ...]:
    """Copy events.json and run_metadata.json to experiment output directory."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for filename in ("events.json", "run_metadata.json"):
        src = run_dir / filename
        if src.exists():
            shutil.copy2(src, dest_dir / filename)
            copied.append(filename)
    return tuple(copied)


def count_events(dest_dir: Path) -> int | None:
    """Read event count from the copied events.json."""
    events_path = dest_dir / "events.json"
    if not events_path.exists():
        return None
    try:
        with open(events_path) as f:
            return len(json.load(f))
    except (json.JSONDecodeError, TypeError):
        return None


def run_session(
    session: dict[str, Any],
    candidate_dir: Path,
    python_path: Path,
    input_data_dir: Path,
    experiment_output_dir: Path,
    extra_args: list[str],
) -> dict[str, Any]:
    """Run vex_extract for a single session and copy results."""
    sid = session["identifier"]
    offset = session["screenTrackStartOffset"]

    try:
        video_path = resolve_video_path(session, input_data_dir)
    except Exception as exc:
        return {"identifier": sid, "success": False, "message": str(exc), "event_count": None}

    if not video_path.exists():
        return {"identifier": sid, "success": False, "message": f"Video not found: {video_path}", "event_count": None}

    cmd = build_command(python_path, video_path, offset, extra_args)
    print(f"      Video:   {video_path}")
    print(f"      Offset:  {offset} ms")
    print(f"      Command: {' '.join(cmd)}")
    print(f"      ...running...", flush=True)

    t0 = time.monotonic()
    proc = subprocess.Popen(
        cmd, cwd=candidate_dir,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )
    stdout_lines: list[str] = []
    for line in proc.stdout:
        stdout_lines.append(line)
        print(f"      | {line}", end="", flush=True)
    proc.wait()
    elapsed = time.monotonic() - t0
    stdout_text = "".join(stdout_lines)

    if proc.returncode != 0:
        return {
            "identifier": sid,
            "success": False,
            "message": f"Exit code {proc.returncode}",
            "event_count": None,
        }

    candidate_output_dir = candidate_dir / "output"
    run_dir = find_run_output(candidate_output_dir, stdout_text)
    if run_dir is None:
        return {"identifier": sid, "success": False, "message": "Could not find run output directory", "event_count": None}

    dest_dir = experiment_output_dir / sid
    copied = copy_results(run_dir, dest_dir)
    if "events.json" not in copied:
        return {"identifier": sid, "success": False, "message": "events.json missing from run output", "event_count": None}

    event_count = count_events(dest_dir)
    print(f"      OK — {event_count} events ({elapsed:.1f}s) -> {dest_dir.relative_to(dest_dir.parents[4])}/")
    return {"identifier": sid, "success": True, "message": "ok", "event_count": event_count}


def main() -> None:
    args, extra_args = parse_args(sys.argv[1:])

    project_root = Path(__file__).resolve().parent
    input_data_dir = project_root / "input_data"
    manifest_path = input_data_dir / "manifest.json"
    candidate_dir = project_root / "candidates" / args.candidate
    python_path = candidate_dir / ".venv" / "bin" / "python"
    experiment_output_dir = project_root / "experiments" / args.branch / args.iteration / "output"

    # Validate paths
    if not candidate_dir.is_dir():
        print(f"Error: candidate directory not found: {candidate_dir}", file=sys.stderr)
        sys.exit(1)
    if not python_path.exists():
        print(f"Error: candidate venv python not found: {python_path}", file=sys.stderr)
        sys.exit(1)
    if not manifest_path.exists():
        print(f"Error: manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    sessions = load_sessions(manifest_path)
    requested_ids = frozenset(args.sessions.split(",")) if args.sessions else None

    to_run = filter_sessions(sessions, requested_ids, experiment_output_dir, args.force)
    skipped_count = (len(sessions) if requested_ids is None else len(requested_ids & {s["identifier"] for s in sessions})) - len(to_run)

    print("=== Standalone Extraction ===")
    print(f"Candidate:  {args.candidate}")
    print(f"Branch:     {args.branch}")
    print(f"Iteration:  {args.iteration}")
    print(f"Sessions:   {len(to_run)} to run" + (f" ({skipped_count} already complete)" if skipped_count > 0 else ""))
    if extra_args:
        print(f"Pass-through: {' '.join(extra_args)}")
    print()

    if not to_run:
        print("Nothing to run.")
        sys.exit(0)

    results: list[dict[str, Any]] = []
    for i, session in enumerate(to_run):
        print(f"[{i + 1}/{len(to_run)}] {session['identifier']}")
        result = run_session(session, candidate_dir, python_path, input_data_dir, experiment_output_dir, extra_args)
        results.append(result)
        if not result["success"]:
            print(f"      FAILED: {result['message']}")
        print()

    succeeded = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    print("=== Summary ===")
    print(f"Succeeded: {len(succeeded)}/{len(results)}")
    if failed:
        print(f"Failed:    {len(failed)}/{len(results)}")
        for r in failed:
            print(f"  - {r['identifier']}: {r['message'].splitlines()[0]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
