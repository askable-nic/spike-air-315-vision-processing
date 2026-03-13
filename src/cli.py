from __future__ import annotations

import asyncio
import json
from pathlib import Path

import click

from src.runner import run_iteration


@click.group()
def main():
    """VEX — Video Event Extraction framework."""
    pass


@main.command()
@click.option("--branch", "-b", required=True, help="Experiment branch name")
@click.option("--iteration", "-i", required=True, type=int, help="Iteration number")
@click.option("--session", "-s", multiple=True, help="Session ID(s) to process (default: all)")
@click.option("--override", "-o", multiple=True, help="Config override as dotted.key=value")
@click.option("--force", "-f", is_flag=True, default=False, help="Re-run all stages, ignoring cached outputs")
@click.option("--base-dir", type=click.Path(exists=True, path_type=Path), default=".", help="Project base directory")
def run(branch: str, iteration: int, session: tuple[str, ...], override: tuple[str, ...], force: bool, base_dir: Path):
    """Run a pipeline iteration."""
    sessions = session if session else None
    run_iteration(
        branch=branch,
        iteration=iteration,
        sessions=sessions,
        cli_overrides=override,
        base_dir=base_dir,
        force=force,
    )


@main.command("list")
@click.option("--branch", "-b", default=None, help="Filter by branch name")
@click.option("--base-dir", type=click.Path(exists=True, path_type=Path), default=".", help="Project base directory")
def list_experiments(branch: str | None, base_dir: Path):
    """List experiment branches and iterations."""
    experiments_dir = base_dir / "experiments"
    if not experiments_dir.exists():
        click.echo("No experiments directory found.")
        return

    branches = sorted(experiments_dir.iterdir()) if branch is None else [experiments_dir / branch]

    for branch_dir in branches:
        if not branch_dir.is_dir() or branch_dir.name.startswith("."):
            continue

        click.echo(f"\n{branch_dir.name}/")

        for item in sorted(branch_dir.iterdir()):
            if item.is_dir() and item.name.isdigit():
                metadata_path = item / "output" / "metadata.json"
                if metadata_path.exists():
                    with open(metadata_path) as f:
                        meta = json.load(f)
                    sessions = len(meta.get("sessions_processed", []))
                    events = meta.get("total_events", 0)
                    click.echo(f"  {item.name}/ — {sessions} sessions, {events} events")
                else:
                    click.echo(f"  {item.name}/ — no output")


@main.command()
@click.option("--branch", "-b", default=None, help="Branch name (default: all branches)")
@click.option("--iterations", default=None, help="Comma-separated iteration numbers (default: all iterations)")
@click.option("--session", "-s", default=None, help="Filter by session ID")
@click.option("--base-dir", type=click.Path(exists=True, path_type=Path), default=".", help="Project base directory")
def compare(branch: str | None, iterations: str | None, session: str | None, base_dir: Path):
    """Compare event counts between iterations.

    When called with no flags, compares all branches and iterations that have output.
    """
    experiments_dir = base_dir / "experiments"
    if not experiments_dir.exists():
        click.echo("No experiments directory found.")
        return

    # Discover branch/iteration pairs to compare
    pairs: list[tuple[str, int]] = []

    if branch is not None and iterations is not None:
        iter_nums = [int(x.strip()) for x in iterations.split(",")]
        pairs = [(branch, n) for n in iter_nums]
    elif branch is not None:
        branch_dir = experiments_dir / branch
        if branch_dir.is_dir():
            pairs = [
                (branch, int(item.name))
                for item in sorted(branch_dir.iterdir())
                if item.is_dir() and item.name.isdigit()
            ]
    else:
        for branch_dir in sorted(experiments_dir.iterdir()):
            if not branch_dir.is_dir() or branch_dir.name.startswith("."):
                continue
            iter_nums_for_branch = [
                int(item.name)
                for item in sorted(branch_dir.iterdir())
                if item.is_dir() and item.name.isdigit()
            ]
            if iterations is not None:
                requested = {int(x.strip()) for x in iterations.split(",")}
                iter_nums_for_branch = [n for n in iter_nums_for_branch if n in requested]
            pairs.extend((branch_dir.name, n) for n in iter_nums_for_branch)

    if not pairs:
        click.echo("No iterations found to compare.")
        return

    for branch_name, iter_num in pairs:
        output_dir = experiments_dir / branch_name / str(iter_num) / "output"
        metadata_path = output_dir / "metadata.json"

        click.echo(f"\n--- {branch_name}/{iter_num} ---")

        if not metadata_path.exists():
            click.echo("  No output found.")
            continue

        with open(metadata_path) as f:
            meta = json.load(f)

        click.echo(f"  Sessions: {len(meta.get('sessions_processed', []))}")
        click.echo(f"  Total events: {meta.get('total_events', 0)}")
        click.echo(f"  Input tokens: {meta.get('total_input_tokens', 0):,}")
        click.echo(f"  Output tokens: {meta.get('total_output_tokens', 0):,}")
        budget = meta.get('total_input_token_budget', 0)
        utilisation = meta.get('total_input_token_budget_utilisation', 0.0)
        click.echo(f"  Token budget: {budget:,} ({utilisation}% used)")

        if session:
            events_path = output_dir / session / "events.json"
            if events_path.exists():
                with open(events_path) as f:
                    events = json.load(f)
                type_counts: dict[str, int] = {}
                for evt in events:
                    t = evt.get("type", "unknown")
                    type_counts[t] = type_counts.get(t, 0) + 1
                click.echo(f"  Events for {session}:")
                for t, c in sorted(type_counts.items()):
                    click.echo(f"    {t}: {c}")


@main.command("describe-frame")
@click.option("--session", "-s", required=True, help="Session identifier")
@click.option("--timestamp", "-t", required=True, type=float, help="Timestamp in ms (relative to session start)")
@click.option("--base-dir", type=click.Path(exists=True, path_type=Path), default=".", help="Project base directory")
def describe_frame(session: str, timestamp: float, base_dir: Path):
    """Describe the visual content of a video frame at a given timestamp."""
    from src.gemini import create_client, make_request
    from src.manifest import load_manifest, resolve_video_path
    from src.video import extract_frames_at_timestamps, encode_jpeg

    manifest = load_manifest(base_dir / "input_data" / "manifest.json")
    session_manifest = next((s for s in manifest if s.identifier == session), None)
    if session_manifest is None:
        click.echo(json.dumps({"error": f"Session '{session}' not found in manifest"}))
        raise SystemExit(1)

    video_path = resolve_video_path(session_manifest, base_dir / "input_data")
    video_relative_ms = timestamp - session_manifest.screenTrackStartOffset

    if video_relative_ms < 0:
        click.echo(json.dumps({"error": "Timestamp is before video start"}))
        raise SystemExit(1)

    frames = extract_frames_at_timestamps(video_path, (video_relative_ms,))
    if not frames:
        click.echo(json.dumps({"error": "Could not extract frame at timestamp"}))
        raise SystemExit(1)

    _, frame = frames[0]
    jpeg_bytes = encode_jpeg(frame)

    system_prompt = "Describe what is shown in this screenshot in a short paragraph. Focus on the page layout, content, and key UI elements visible."

    client = create_client()
    from google.genai import types
    image_part = types.Part.from_bytes(data=jpeg_bytes, mime_type="image/jpeg")

    result = asyncio.run(make_request(
        client=client,
        model="gemini-3-flash-preview",
        system_prompt=system_prompt,
        content_parts=[image_part],
    ))

    click.echo(json.dumps({"description": result["text"]}))


@main.command("enrich-baselines")
@click.option("--session", "-s", default=None, help="Session ID to enrich (default: all in baselines/)")
@click.option("--max-concurrent", default=5, type=int, help="Max concurrent Gemini requests")
@click.option("--dry-run", is_flag=True, default=False, help="Print enrichment summary without calling Gemini")
@click.option("--base-dir", type=click.Path(exists=True, path_type=Path), default=".", help="Project base directory")
def enrich_baselines(session: str | None, max_concurrent: int, dry_run: bool, base_dir: Path):
    """Enrich baseline event annotations with Gemini-generated descriptions."""
    from src.manifest import load_manifest, resolve_video_path
    from stages.enrich_baselines import enrich_session

    baselines_dir = base_dir / "baselines"
    if not baselines_dir.exists():
        click.echo("No baselines/ directory found.")
        raise SystemExit(1)

    # Discover sessions
    if session:
        session_dirs = [baselines_dir / session]
        if not session_dirs[0].exists():
            click.echo(f"Session directory not found: {session_dirs[0]}")
            raise SystemExit(1)
    else:
        session_dirs = sorted(
            d for d in baselines_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        )

    if not session_dirs:
        click.echo("No session directories found in baselines/.")
        return

    # Load manifest for video paths and offsets
    manifest = load_manifest(base_dir / "input_data" / "manifest.json")
    manifest_lookup = {s.identifier: s for s in manifest}

    # Load prompt template
    prompt_path = base_dir / "prompts" / "enrich_baseline.txt"
    if not prompt_path.exists():
        click.echo(f"Prompt template not found: {prompt_path}")
        raise SystemExit(1)
    template = prompt_path.read_text()

    for session_dir in session_dirs:
        session_id = session_dir.name
        events_path = session_dir / "events.json"

        if not events_path.exists():
            click.echo(f"Skipping {session_id}: no events.json")
            continue

        session_manifest = manifest_lookup.get(session_id)
        if session_manifest is None:
            click.echo(f"Skipping {session_id}: not found in manifest")
            continue

        video_path = resolve_video_path(session_manifest, base_dir / "input_data")
        if not video_path.exists():
            click.echo(f"Skipping {session_id}: video not found at {video_path}")
            continue

        with open(events_path) as f:
            events = json.load(f)

        click.echo(f"Processing {session_id} ({len(events)} events)...")

        enriched = asyncio.run(enrich_session(
            session_id=session_id,
            events=events,
            video_path=video_path,
            screen_track_start_offset=session_manifest.screenTrackStartOffset,
            template=template,
            max_concurrent=max_concurrent,
            dry_run=dry_run,
        ))

        if not dry_run:
            with open(events_path, "w") as f:
                json.dump(enriched, f, indent=2)
            click.echo(f"  Written enriched events to {events_path}")

    click.echo("Done.")


@main.command("generate-baselines")
@click.option("--session", "-s", default=None, help="Process single session by identifier")
@click.option("--dry-run", is_flag=True, default=False, help="Show segments and estimated tokens without calling API")
@click.option("--force", is_flag=True, default=False, help="Overwrite existing baselines")
@click.option("--override", "-o", multiple=True, help="Config overrides (e.g. generate_baselines.model=gemini-3-flash-preview)")
@click.option("--base-dir", type=click.Path(exists=True, path_type=Path), default=".", help="Project base directory")
def generate_baselines(session: str | None, dry_run: bool, force: bool, override: tuple[str, ...], base_dir: Path):
    """Generate draft baselines from video using Gemini video input."""
    from src.config import resolve_generate_baselines_config
    from src.manifest import load_manifest, resolve_video_path
    from stages.generate_baselines import generate_session_baseline

    config = resolve_generate_baselines_config(override)
    manifest = load_manifest(base_dir / "input_data" / "manifest.json")

    # Filter to requested session or all
    if session:
        sessions = tuple(s for s in manifest if s.identifier == session)
        if not sessions:
            click.echo(f"Session '{session}' not found in manifest.")
            raise SystemExit(1)
    else:
        sessions = manifest

    # Load prompt template
    prompt_path = base_dir / "prompts" / "generate_baseline.txt"
    if not prompt_path.exists():
        click.echo(f"Prompt template not found: {prompt_path}")
        raise SystemExit(1)
    prompt_template = prompt_path.read_text()

    total_tokens = 0
    results: list[dict] = []

    for session_manifest in sessions:
        video_path = resolve_video_path(session_manifest, base_dir / "input_data")
        if not video_path.exists():
            click.echo(f"Skipping {session_manifest.identifier}: video not found at {video_path}")
            continue

        result = asyncio.run(generate_session_baseline(
            session_manifest=session_manifest,
            video_path=video_path,
            config=config,
            prompt_template=prompt_template,
            base_dir=base_dir,
            dry_run=dry_run,
            force=force,
        ))

        if result is not None:
            results.append(result)
            total_tokens += result.get("estimated_tokens", 0) if dry_run else result.get("total_input_tokens", 0)

    if dry_run and results:
        print(f"\nTotal estimated tokens: ~{total_tokens:,}")
    elif results:
        total_events = sum(r.get("total_events_deduped", 0) for r in results)
        click.echo(f"\nDone. {len(results)} sessions, {total_events} total events, {total_tokens:,} input tokens.")
    else:
        click.echo("No sessions processed.")


@main.command("cv-augmented")
@click.option("--session", "-s", default=None, help="Process single session by identifier")
@click.option("--dry-run", is_flag=True, default=False, help="Show segments and estimated tokens without calling API")
@click.option("--force", is_flag=True, default=False, help="Overwrite existing output")
@click.option("--override", "-o", multiple=True, help="Config overrides (e.g. cv_augmented.model=gemini-3-flash-preview)")
@click.option("--output-dir", type=click.Path(path_type=Path), default="experiments/cv-augmented/1/output", help="Output directory")
@click.option("--base-dir", type=click.Path(exists=True, path_type=Path), default=".", help="Project base directory")
def cv_augmented(session: str | None, dry_run: bool, force: bool, override: tuple[str, ...], output_dir: Path, base_dir: Path):
    """Generate event annotations using video + CV cursor/scroll context."""
    from src.config import resolve_cv_augmented_config
    from src.manifest import load_manifest, resolve_video_path
    from stages.generate_cv_augmented import generate_session_cv_augmented

    config = resolve_cv_augmented_config(override)
    manifest = load_manifest(base_dir / "input_data" / "manifest.json")

    # Filter to requested session or all
    if session:
        sessions = tuple(s for s in manifest if s.identifier == session)
        if not sessions:
            click.echo(f"Session '{session}' not found in manifest.")
            raise SystemExit(1)
    else:
        sessions = manifest

    # Load prompt template
    prompt_path = base_dir / "prompts" / "cv_augmented.txt"
    if not prompt_path.exists():
        click.echo(f"Prompt template not found: {prompt_path}")
        raise SystemExit(1)
    prompt_template = prompt_path.read_text()

    # Resolve output dir relative to base_dir
    resolved_output_dir = output_dir if output_dir.is_absolute() else base_dir / output_dir

    total_tokens = 0
    results: list[dict] = []

    for session_manifest in sessions:
        video_path = resolve_video_path(session_manifest, base_dir / "input_data")
        if not video_path.exists():
            click.echo(f"Skipping {session_manifest.identifier}: video not found at {video_path}")
            continue

        result = asyncio.run(generate_session_cv_augmented(
            session_manifest=session_manifest,
            video_path=video_path,
            config=config,
            prompt_template=prompt_template,
            base_dir=base_dir,
            output_dir=resolved_output_dir,
            dry_run=dry_run,
            force=force,
        ))

        if result is not None:
            results.append(result)
            total_tokens += result.get("estimated_tokens", 0) if dry_run else result.get("total_input_tokens", 0)

    if dry_run and results:
        print(f"\nTotal estimated tokens: ~{total_tokens:,}")
    elif results:
        total_events = sum(r.get("total_events_deduped", 0) for r in results)
        click.echo(f"\nDone. {len(results)} sessions, {total_events} total events, {total_tokens:,} input tokens.")
        click.echo(f"Output: {resolved_output_dir}")
    else:
        click.echo("No sessions processed.")


@main.command()
@click.option("--branch", "-b", required=True, help="Experiment branch name")
@click.option("--iteration", "-i", default=None, type=int, help="Iteration number (default: latest)")
@click.option("--session", "-s", multiple=True, help="Session ID(s) to evaluate (default: all with baselines)")
@click.option("--override", "-o", multiple=True, help="Config override as dotted.key=value")
@click.option("--force", "-f", is_flag=True, default=False, help="Re-run extraction, ignoring cached outputs")
@click.option("--resume", is_flag=True, default=False, help="Resume from experiment_progress.json checkpoint")
@click.option("--dry-run", is_flag=True, default=False, help="Show what would be evaluated without running")
@click.option("--base-dir", type=click.Path(exists=True, path_type=Path), default=".", help="Project base directory")
def experiment(
    branch: str,
    iteration: int | None,
    session: tuple[str, ...],
    override: tuple[str, ...],
    force: bool,
    resume: bool,
    dry_run: bool,
    base_dir: Path,
):
    """Run experiment: extract + mechanical evaluation.

    Qualitative analysis and LLM judgment are handled by the /evaluate skill in Claude Code.
    """
    from src.experiment import run_experiment

    sessions = session if session else None
    summary = run_experiment(
        branch=branch,
        iteration=iteration,
        sessions=sessions,
        cli_overrides=override,
        base_dir=base_dir,
        force=force,
        resume=resume,
        dry_run=dry_run,
    )

    # Print summary
    click.echo(f"\n{'=' * 60}")
    click.echo(f"Experiment: {summary.branch}/{summary.iteration}")
    click.echo(f"Sessions: {len(summary.sessions_completed)}/{len(summary.sessions_requested)}")
    if summary.early_break:
        click.echo(f"Early break: {summary.early_break_reason}")
    click.echo(f"F1: {summary.aggregate_f1:.3f}  Recall: {summary.aggregate_recall:.3f}  Precision: {summary.aggregate_precision:.3f}")

    output_dir = base_dir / "experiments" / summary.branch / str(summary.iteration) / "output"
    click.echo(f"\nFull report: {output_dir / 'experiment_summary.md'}")
    click.echo("Run /evaluate to perform qualitative analysis and LLM judgment.")


@main.command()
@click.option("--branch", "-b", default=None, help="Experiment branch name")
@click.option("--iteration", "-i", default=None, type=int, help="Iteration number")
@click.option("--reference", type=click.Path(exists=True, path_type=Path), default=None, help="Path to reference events.json")
@click.option("--candidate", type=click.Path(exists=True, path_type=Path), default=None, help="Path to candidate events.json")
@click.option("--session", "-s", multiple=True, help="Session ID(s) to evaluate (default: all with baselines)")
@click.option("--time-tolerance", default=2000, type=float, help="Time tolerance in ms for matching (default: 2000)")
@click.option("--similarity-threshold", default=0.5, type=float, help="Min match score threshold (default: 0.5)")
@click.option("--llm-judge", is_flag=True, default=False, help="Use LLM to evaluate (type-agnostic, qualitative)")
@click.option("--verbose", "-v", is_flag=True, default=False, help="Show event-level match details")
@click.option("--output-json", is_flag=True, default=False, help="Output results as JSON")
@click.option("--base-dir", type=click.Path(exists=True, path_type=Path), default=".", help="Project base directory")
def evaluate(
    branch: str | None,
    iteration: int | None,
    reference: Path | None,
    candidate: Path | None,
    session: tuple[str, ...],
    time_tolerance: float,
    similarity_threshold: float,
    llm_judge: bool,
    verbose: bool,
    output_json: bool,
    base_dir: Path,
):
    """Evaluate experiment results against baseline annotations.

    Two modes:

      vex evaluate -b branch -i 1          # experiment vs baselines/

      vex evaluate --reference ref.json --candidate cand.json  # two files
    """
    from src.evaluate import (
        greedy_match,
        compute_metrics,
        format_results,
        result_to_dict,
        llm_judge_evaluate,
        format_judge_result,
    )

    # Build list of (session_id, reference_events, candidate_events) pairs
    pairs: list[tuple[str, list[dict], list[dict]]] = []

    if reference is not None and candidate is not None:
        # Direct file comparison mode
        with open(reference) as f:
            ref_events = json.load(f)
        with open(candidate) as f:
            cand_events = json.load(f)
        sid = reference.parent.name
        pairs.append((sid, ref_events, cand_events))

    elif branch is not None and iteration is not None:
        # Experiment vs baselines mode
        baselines_dir = base_dir / "baselines"
        experiment_dir = base_dir / "experiments" / branch / str(iteration) / "output"

        if not baselines_dir.exists():
            click.echo("No baselines/ directory found.")
            raise SystemExit(1)
        if not experiment_dir.exists():
            click.echo(f"No experiment output found at {experiment_dir}")
            raise SystemExit(1)

        if session:
            session_ids = list(session)
        else:
            baseline_sessions = {
                d.name for d in baselines_dir.iterdir()
                if d.is_dir() and not d.name.startswith(".") and (d / "events.json").exists()
            }
            experiment_sessions = {
                d.name for d in experiment_dir.iterdir()
                if d.is_dir() and not d.name.startswith(".") and (d / "events.json").exists()
            }
            session_ids = sorted(baseline_sessions & experiment_sessions)

        for sid in session_ids:
            bp = baselines_dir / sid / "events.json"
            ep = experiment_dir / sid / "events.json"
            if not bp.exists():
                click.echo(f"Skipping {sid}: no baseline events.json")
                continue
            if not ep.exists():
                click.echo(f"Skipping {sid}: no experiment events.json")
                continue
            with open(bp) as f:
                ref_events = json.load(f)
            with open(ep) as f:
                cand_events = json.load(f)
            pairs.append((sid, ref_events, cand_events))
    else:
        click.echo("Provide either --reference + --candidate, or --branch + --iteration.")
        raise SystemExit(1)

    if not pairs:
        click.echo("No sessions found to evaluate.")
        return

    all_results = []

    for sid, ref_events, cand_events in pairs:
        # Mechanical matching
        matched, unmatched_b, unmatched_e = greedy_match(
            ref_events, cand_events, time_tolerance, similarity_threshold,
        )
        result = compute_metrics(
            ref_events, cand_events, matched, unmatched_b, unmatched_e, sid,
        )
        all_results.append((result, ref_events, cand_events, matched, unmatched_b, unmatched_e))

        if not output_json:
            click.echo(f"\n{format_results(
                result,
                baselines=ref_events,
                experiments=cand_events,
                matched_pairs=matched,
                unmatched_baselines=unmatched_b,
                unmatched_experiments=unmatched_e,
                verbose=verbose,
            )}")

        # LLM judge
        if llm_judge:
            click.echo("\nRunning LLM judge...")
            judgment = asyncio.run(llm_judge_evaluate(ref_events, cand_events, sid))
            if output_json:
                click.echo(json.dumps(judgment, indent=2))
            else:
                click.echo(f"\n{format_judge_result(judgment, ref_events, cand_events)}")

    if not all_results:
        click.echo("No sessions evaluated.")
        return

    results_only = [r for r, *_ in all_results]

    # Aggregate summary for multiple sessions
    if len(results_only) > 1 and not output_json:
        total_b = sum(r.baseline_count for r in results_only)
        total_e = sum(r.experiment_count for r in results_only)
        total_m = sum(r.matched_count for r in results_only)
        agg_prec = total_m / total_e if total_e > 0 else 0.0
        agg_rec = total_m / total_b if total_b > 0 else 0.0
        agg_f1 = 2 * agg_prec * agg_rec / (agg_prec + agg_rec) if (agg_prec + agg_rec) > 0 else 0.0
        click.echo(f"\n--- Aggregate ({len(results_only)} sessions) ---")
        click.echo(f"  Baseline: {total_b}  Experiment: {total_e}  Matched: {total_m}")
        click.echo(f"  Precision: {agg_prec:.3f}  Recall: {agg_rec:.3f}  F1: {agg_f1:.3f}")

    if output_json and not llm_judge:
        output = [result_to_dict(r) for r in results_only]
        click.echo(json.dumps(output if len(output) > 1 else output[0], indent=2))


if __name__ == "__main__":
    main()
