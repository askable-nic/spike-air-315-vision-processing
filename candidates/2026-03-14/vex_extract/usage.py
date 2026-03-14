"""Token usage and cost reporting across pipeline runs.

Usage:
    python -m vex_extract.usage [--config config.yaml] [--output-dir output/]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from vex_extract.config import load_config


def _load_runs(output_dir: Path) -> list[dict]:
    """Load all run_metadata.json files under *output_dir*, newest first."""
    runs: list[dict] = []
    for meta_path in sorted(output_dir.glob("*/run_metadata.json"), reverse=True):
        try:
            runs.append(json.loads(meta_path.read_text()))
        except (json.JSONDecodeError, OSError):
            continue
    return runs


def _format_duration(ms: float) -> str:
    total_s = ms / 1000
    minutes = int(total_s // 60)
    seconds = total_s % 60
    return f"{minutes}m{seconds:04.1f}s" if minutes else f"{seconds:.1f}s"


def _compute_cost(
    input_tokens: int,
    output_tokens: int,
    model: str,
    costs: dict,
) -> float | None:
    """Return total USD cost, or None if model has no cost entry."""
    entry = costs.get(model)
    if entry is None:
        return None
    return (input_tokens * entry.input_token_cost) + (output_tokens * entry.output_token_cost)


def _fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _fmt_cost(c: float | None) -> str:
    return f"${c:.4f}" if c is not None else "n/a"


def _print_table(headers: list[str], rows: list[list[str]], right_align: set[int] | None = None) -> None:
    """Print a simple aligned table."""
    right_align = right_align or set()
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def _fmt_row(cells: list[str]) -> str:
        parts = []
        for i, cell in enumerate(cells):
            parts.append(cell.rjust(widths[i]) if i in right_align else cell.ljust(widths[i]))
        return "  ".join(parts)

    click.echo(_fmt_row(headers))
    click.echo("  ".join("-" * w for w in widths))
    for row in rows:
        click.echo(_fmt_row(row))


@click.command("usage")
@click.option(
    "--config", "config_path", default=None,
    type=click.Path(path_type=Path),
    help="Path to config YAML (for model cost data). Defaults to config.yaml.",
)
@click.option(
    "--output-dir", default=None,
    type=click.Path(exists=True, path_type=Path),
    help="Output directory to scan. Defaults to output/.",
)
def report_usage(config_path: Path | None, output_dir: Path | None) -> None:
    """Report token usage and costs across pipeline runs."""
    app_root = Path(__file__).resolve().parent.parent

    if config_path is None:
        config_path = app_root / "config.yaml"
    config = load_config(config_path)
    costs = config.token_costs

    if output_dir is None:
        output_dir = app_root / "output"

    if not output_dir.exists():
        click.echo(f"No output directory found: {output_dir}", err=True)
        sys.exit(1)

    runs = [
        r for r in _load_runs(output_dir)
        if r.get("total_input_tokens", 0) > 0
    ]
    if not runs:
        click.echo(f"No runs with token usage found in {output_dir}", err=True)
        sys.exit(1)

    # Per-run table
    headers = ["Run", "Video", "Duration", "Model", "Input", "Output", "Cost", "$/min"]
    right_align = {4, 5, 6, 7}
    rows: list[list[str]] = []
    model_totals: dict[str, dict] = {}

    for run in runs:
        run_id = run["run_id"]
        video_name = Path(run.get("video_path", "unknown")).stem
        duration_ms = run.get("video_duration_ms", 0) or 0
        model = run.get("config", {}).get("gemini", {}).get("model", "unknown")
        input_tok = run.get("total_input_tokens", 0)
        output_tok = run.get("total_output_tokens", 0)

        cost = _compute_cost(input_tok, output_tok, model, costs)
        duration_min = duration_ms / 60_000 if duration_ms else 0
        cost_per_min = cost / duration_min if cost and duration_min > 0 else None

        rows.append([
            run_id,
            video_name,
            _format_duration(duration_ms),
            model,
            _fmt_tokens(input_tok),
            _fmt_tokens(output_tok),
            _fmt_cost(cost),
            _fmt_cost(cost_per_min),
        ])

        if model not in model_totals:
            model_totals[model] = {
                "runs": 0, "input_tokens": 0, "output_tokens": 0,
                "total_cost": 0.0, "total_duration_min": 0.0,
            }
        entry = model_totals[model]
        entry["runs"] += 1
        entry["input_tokens"] += input_tok
        entry["output_tokens"] += output_tok
        entry["total_duration_min"] += duration_min
        if cost is not None:
            entry["total_cost"] += cost

    _print_table(headers, rows, right_align)

    # Summary by model
    if model_totals:
        click.echo()
        summary_headers = ["Model", "Runs", "Duration", "Input", "Output", "Total Cost", "Avg $/min"]
        summary_rows: list[list[str]] = []
        for model, totals in sorted(model_totals.items()):
            avg_cost_per_min = (
                totals["total_cost"] / totals["total_duration_min"]
                if totals["total_duration_min"] > 0 else 0
            )
            summary_rows.append([
                model,
                str(totals["runs"]),
                _format_duration(totals["total_duration_min"] * 60_000),
                _fmt_tokens(totals["input_tokens"]),
                _fmt_tokens(totals["output_tokens"]),
                _fmt_cost(totals["total_cost"]),
                _fmt_cost(avg_cost_per_min),
            ])
        _print_table(summary_headers, summary_rows, {1, 2, 3, 4, 5, 6})


if __name__ == "__main__":
    report_usage()
