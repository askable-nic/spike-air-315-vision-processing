from __future__ import annotations

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


if __name__ == "__main__":
    main()
