from __future__ import annotations

import asyncio
import importlib.util
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from src.config import resolve_config
from src.manifest import load_manifest, resolve_video_path
from src.models import (
    AnalyseResult,
    PipelineConfig,
    RunMetadata,
    SessionManifest,
    SessionOutput,
    TriageResult,
)


def run_iteration(
    branch: str,
    iteration: int,
    sessions: tuple[str, ...] | None = None,
    cli_overrides: tuple[str, ...] = (),
    base_dir: Path = Path("."),
    force: bool = False,
) -> None:
    """Main entry point: resolve config, run pipeline for each session, write output."""
    started_at = datetime.now(timezone.utc).isoformat()

    config = resolve_config(branch, iteration, cli_overrides, base_dir)
    print(f"Config resolved for {branch}/{iteration}")

    input_dir = base_dir / "input_data"
    manifest = load_manifest(input_dir / "manifest.json")

    if sessions:
        manifest = tuple(s for s in manifest if s.identifier in sessions)

    if not manifest:
        print("No sessions to process.")
        return

    output_dir = base_dir / "experiments" / branch / str(iteration) / "output"
    stages = load_custom_stages(branch, iteration, base_dir)

    all_outputs: list[SessionOutput] = []
    errors: list[str] = []

    for session in manifest:
        print(f"\nProcessing session: {session.identifier}")
        try:
            output = _process_session(
                session, config, input_dir, output_dir, stages, branch, iteration, base_dir, force,
            )
            write_output(output_dir, output)
            all_outputs.append(output)
            print(f"  Done: {output.event_count} events detected")
        except Exception as e:
            error_msg = f"{session.identifier}: {e}"
            errors.append(error_msg)
            print(f"  Error: {e}")

    completed_at = datetime.now(timezone.utc).isoformat()

    metadata = RunMetadata(
        branch=branch,
        iteration=iteration,
        started_at=started_at,
        completed_at=completed_at,
        config=config.model_dump(),
        sessions_processed=tuple(o.recording_id for o in all_outputs),
        total_events=sum(o.event_count for o in all_outputs),
        total_input_tokens=sum(o.total_input_tokens for o in all_outputs),
        total_output_tokens=sum(o.total_output_tokens for o in all_outputs),
        errors=tuple(errors),
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / "metadata.json", "w") as f:
        json.dump(metadata.model_dump(), f, indent=2)

    print(f"\nRun complete: {len(all_outputs)} sessions, {metadata.total_events} total events")
    if errors:
        print(f"Errors: {len(errors)}")


def _load_stage_json(path: Path, model_cls: type) -> Any | None:
    """Load a stage output JSON file and validate it against a pydantic model."""
    if not path.exists():
        return None
    with open(path) as f:
        data = json.load(f)
    return model_cls.model_validate(data)


def _save_stage_json(path: Path, model: Any) -> None:
    """Save a pydantic model to a JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(model.model_dump(), f, indent=2)


def _process_session(
    session: SessionManifest,
    config: PipelineConfig,
    input_dir: Path,
    output_dir: Path,
    stages: dict[str, Callable],
    branch: str,
    iteration: int,
    base_dir: Path,
    force: bool,
) -> SessionOutput:
    """Run the full pipeline for a single session, resuming from cached stage outputs."""
    video_path = resolve_video_path(session, input_dir)
    session_dir = output_dir / session.identifier

    run_triage = stages.get("triage")
    run_analyse = stages.get("analyse")
    run_merge = stages.get("merge")

    if run_triage is None:
        from stages.triage import run_triage
    if run_analyse is None:
        from stages.analyse import run_analyse
    if run_merge is None:
        from stages.merge import run_merge

    # --- Triage ---
    triage_path = session_dir / "triage.json"
    triage_result: TriageResult | None = None

    if not force:
        triage_result = _load_stage_json(triage_path, TriageResult)
        if triage_result is not None:
            print(f"  Triage: loaded from cache ({len(triage_result.segments)} segments)")

    if triage_result is None:
        print(f"  Triage...")
        triage_result = run_triage(session, config, video_path)
        _save_stage_json(triage_path, triage_result)
        print(f"  Triage: {len(triage_result.segments)} segments ({triage_result.processing_time_ms:.0f}ms)")

    # --- Analyse ---
    analysis_path = session_dir / "analysis.json"
    analyse_result: AnalyseResult | None = None

    if not force:
        analyse_result = _load_stage_json(analysis_path, AnalyseResult)
        if analyse_result is not None:
            print(f"  Analyse: loaded from cache ({analyse_result.total_input_tokens} input tokens)")

    if analyse_result is None:
        print(f"  Analyse...")
        analyse_result = asyncio.run(
            run_analyse(
                session, config, triage_result, video_path,
                branch, iteration, base_dir, output_dir=output_dir,
            )
        )
        _save_stage_json(analysis_path, analyse_result)
        print(f"  Analyse: {analyse_result.total_input_tokens} input tokens ({analyse_result.processing_time_ms:.0f}ms)")

    # --- Merge ---
    print(f"  Merge...")
    session_output: SessionOutput = run_merge(session, config, analyse_result, triage_result)

    return session_output


def load_custom_stages(
    branch: str,
    iteration: int,
    base_dir: Path,
) -> dict[str, Callable]:
    """Import pipeline.py from iteration dir if present, extract stage functions."""
    pipeline_path = base_dir / "experiments" / branch / str(iteration) / "pipeline.py"
    if not pipeline_path.exists():
        return {}

    spec = importlib.util.spec_from_file_location("custom_pipeline", pipeline_path)
    if spec is None or spec.loader is None:
        return {}

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    stages: dict[str, Callable] = {}
    for name in ("run_triage", "run_analyse", "run_merge"):
        func = getattr(module, name, None)
        if func is not None:
            stage_name = name.replace("run_", "")
            stages[stage_name] = func

    return stages


def write_output(output_dir: Path, session_output: SessionOutput) -> None:
    """Write final JSON output files for a session."""
    session_dir = output_dir / session_output.recording_id
    session_dir.mkdir(parents=True, exist_ok=True)

    # Write events matching event-schema.json
    events_data = [
        {k: v for k, v in event.model_dump().items() if v is not None}
        for event in session_output.events
    ]
    with open(session_dir / "events.json", "w") as f:
        json.dump(events_data, f, indent=2)

    # Write full session output
    with open(session_dir / "session.json", "w") as f:
        json.dump(session_output.model_dump(), f, indent=2)
