"""Experiment runner: extraction + per-session mechanical evaluation + summary.

Qualitative analysis and full-set LLM judgment are handled by Claude Code
via the /evaluate skill, not by calling an external LLM API.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from src.config import resolve_config, resolve_experiment_config
from src.evaluate import greedy_match, compute_metrics
from src.experiment_models import (
    CumulativeMetrics,
    EarlyBreakDecision,
    ExperimentSummary,
    SessionEvaluationResult,
    SessionMetrics,
)
from src.log import log
from src.manifest import load_manifest
from src.models import ExperimentConfig, PipelineConfig
from src.runner import _process_session, load_custom_stages, write_output


# --- Step 1a: Shallow metrics ---


def _compute_session_metrics(
    session_id: str,
    baseline_events: list[dict],
    experiment_events: list[dict],
    experiment_config: ExperimentConfig,
) -> SessionMetrics:
    """Compute greedy_match + compute_metrics and check thresholds."""
    matched_pairs, unmatched_b, unmatched_e = greedy_match(
        baseline_events,
        experiment_events,
        experiment_config.time_tolerance_ms,
        experiment_config.similarity_threshold,
    )
    result = compute_metrics(
        baseline_events, experiment_events,
        matched_pairs, unmatched_b, unmatched_e,
        session_id,
    )

    return SessionMetrics(
        session_id=session_id,
        baseline_count=result.baseline_count,
        experiment_count=result.experiment_count,
        matched_count=result.matched_count,
        precision=result.precision,
        recall=result.recall,
        f1=result.f1,
        mean_description_similarity=result.mean_description_similarity,
        mean_start_error_ms=result.timing.mean_start_error_ms,
        mean_end_error_ms=result.timing.mean_end_error_ms,
        per_type=[
            {
                "type": t.event_type,
                "baseline_count": t.baseline_count,
                "experiment_count": t.experiment_count,
                "matched": t.matched,
                "precision": round(t.precision, 4),
                "recall": round(t.recall, 4),
                "f1": round(t.f1, 4),
            }
            for t in result.per_type
        ],
        f1_pass=result.f1 >= experiment_config.f1_threshold,
        recall_pass=result.recall >= experiment_config.recall_threshold,
        precision_pass=result.precision >= experiment_config.precision_threshold,
    )


# --- Cumulative metrics and early-break ---


def _compute_f1_trend(f1_history: list[float]) -> str:
    """Compute F1 trend via linear regression slope over history."""
    n = len(f1_history)
    if n < 3:
        return "stable"
    xs = list(range(n))
    x_mean = sum(xs) / n
    y_mean = sum(f1_history) / n
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, f1_history))
    denominator = sum((x - x_mean) ** 2 for x in xs)
    slope = numerator / denominator if denominator != 0 else 0.0
    if slope > 0.02:
        return "improving"
    elif slope < -0.02:
        return "declining"
    return "stable"


def _compute_cumulative_metrics(
    prior_results: list[SessionEvaluationResult],
    current_metrics: SessionMetrics,
) -> CumulativeMetrics:
    """Aggregate metrics across all completed sessions including current."""
    all_matched = sum(r.metrics.matched_count for r in prior_results) + current_metrics.matched_count
    all_baseline = sum(r.metrics.baseline_count for r in prior_results) + current_metrics.baseline_count
    all_experiment = sum(r.metrics.experiment_count for r in prior_results) + current_metrics.experiment_count

    cum_precision = all_matched / all_experiment if all_experiment > 0 else 0.0
    cum_recall = all_matched / all_baseline if all_baseline > 0 else 0.0
    cum_f1 = (
        2 * cum_precision * cum_recall / (cum_precision + cum_recall)
        if (cum_precision + cum_recall) > 0
        else 0.0
    )

    f1_history = [r.metrics.f1 for r in prior_results] + [current_metrics.f1]
    f1_trend = _compute_f1_trend(f1_history)

    return CumulativeMetrics(
        sessions_completed=len(prior_results) + 1,
        cumulative_f1=cum_f1,
        cumulative_recall=cum_recall,
        cumulative_precision=cum_precision,
        cumulative_matched=all_matched,
        cumulative_baseline=all_baseline,
        cumulative_experiment=all_experiment,
        f1_trend=f1_trend,
        f1_history=f1_history,
    )


def _decide_early_break(
    cumulative: CumulativeMetrics,
    prior_results: list[SessionEvaluationResult],
    experiment_config: ExperimentConfig,
    sessions_remaining: int,
) -> EarlyBreakDecision:
    """Decide whether to stop processing further sessions based on metrics."""
    # Never break too early or on the last session
    if cumulative.sessions_completed < experiment_config.min_sessions_before_break:
        return EarlyBreakDecision(
            should_break=False,
            reason="too_early",
            explanation=f"Only {cumulative.sessions_completed} sessions completed, minimum is {experiment_config.min_sessions_before_break}.",
        )
    if sessions_remaining <= 1:
        return EarlyBreakDecision(
            should_break=False,
            reason="last_session",
            explanation="This is the last (or only remaining) session.",
        )

    # F1 decline trend
    if (
        cumulative.f1_trend == "declining"
        and len(cumulative.f1_history) >= 3
        and (cumulative.f1_history[0] - cumulative.cumulative_f1) >= experiment_config.f1_decline_threshold
    ):
        return EarlyBreakDecision(
            should_break=True,
            reason="metric_decline",
            explanation=(
                f"F1 trend is declining over {len(cumulative.f1_history)} sessions. "
                f"Cumulative F1 dropped from {cumulative.f1_history[0]:.3f} to {cumulative.cumulative_f1:.3f} "
                f"(threshold: {experiment_config.f1_decline_threshold})."
            ),
        )

    return EarlyBreakDecision(
        should_break=False,
        reason="continue",
        explanation="No early-break conditions met.",
    )


# --- Summary generation ---


def _format_summary_markdown(summary: ExperimentSummary) -> str:
    """Generate a human-readable markdown report from the experiment summary."""
    lines = [
        f"# Experiment: {summary.branch}/{summary.iteration}",
        "",
        f"**Sessions**: {len(summary.sessions_completed)}/{len(summary.sessions_requested)}",
        f"**Early break**: {'Yes — ' + (summary.early_break_reason or '') if summary.early_break else 'No'}",
        "",
        "## Aggregate Metrics",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| F1 | {summary.aggregate_f1:.3f} |",
        f"| Recall | {summary.aggregate_recall:.3f} |",
        f"| Precision | {summary.aggregate_precision:.3f} |",
        "",
        "## Per-Session Results",
        "",
        "| Session | F1 | Recall | Precision | Severity |",
        "|---------|------|--------|-----------|----------|",
    ]

    for r in summary.session_results:
        severity = r.qualitative.overall_severity if r.qualitative else "n/a"
        lines.append(
            f"| {r.session_id} | {r.metrics.f1:.3f} | {r.metrics.recall:.3f} | "
            f"{r.metrics.precision:.3f} | {severity} |"
        )

    if summary.judgment:
        j = summary.judgment
        lines.extend([
            "",
            "## Full-Set Judgment",
            "",
            f"| Score | Value |",
            f"|-------|-------|",
            f"| Overall | {j.overall_score:.2f} |",
            f"| Coverage | {j.coverage_score:.2f} |",
            f"| Type accuracy | {j.type_accuracy_score:.2f} |",
            f"| Timing | {j.timing_score:.2f} |",
        ])

        if j.systematic_patterns:
            lines.extend(["", "### Systematic Patterns", ""])
            for p in j.systematic_patterns:
                lines.append(f"- {p}")

        if j.root_cause_analysis:
            lines.extend(["", "### Root Cause Analysis", "", j.root_cause_analysis])

        if j.strengths:
            lines.extend(["", "### Strengths", ""])
            for s in j.strengths:
                lines.append(f"- {s}")

        if j.weaknesses:
            lines.extend(["", "### Weaknesses", ""])
            for w in j.weaknesses:
                lines.append(f"- {w}")

        if j.recommendations:
            lines.extend(["", "### Recommendations", ""])
            for rec in j.recommendations:
                lines.append(
                    f"- **{rec.config_key}**: {rec.current_value} -> {rec.recommended_value} "
                    f"(confidence: {rec.confidence:.2f}) — {rec.rationale}"
                )

    if summary.auto_iteration:
        ai = summary.auto_iteration
        lines.extend([
            "",
            f"## Auto-Iteration: {ai.source_iteration} -> {ai.new_iteration}",
            "",
            ai.changelog,
        ])

    return "\n".join(lines)


def _save_experiment_summary(summary: ExperimentSummary, output_dir: Path) -> None:
    """Write experiment_summary.json and experiment_summary.md."""
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "experiment_summary.json", "w") as f:
        json.dump(summary.model_dump(), f, indent=2)

    markdown = _format_summary_markdown(summary)
    with open(output_dir / "experiment_summary.md", "w") as f:
        f.write(markdown)


# --- Per-session orchestration ---


def _load_session_eval_cache(output_dir: Path, session_id: str) -> SessionEvaluationResult | None:
    """Load cached session evaluation result if available."""
    path = output_dir / session_id / "session_eval.json"
    if not path.exists():
        return None
    with open(path) as f:
        data = json.load(f)
    return SessionEvaluationResult.model_validate(data)


def _save_session_eval(output_dir: Path, result: SessionEvaluationResult) -> None:
    """Save session evaluation result to cache."""
    session_dir = output_dir / result.session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    with open(session_dir / "session_eval.json", "w") as f:
        json.dump(result.model_dump(), f, indent=2)


def _save_progress(output_dir: Path, results: list[SessionEvaluationResult]) -> None:
    """Save experiment progress checkpoint."""
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / "experiment_progress.json", "w") as f:
        json.dump([r.model_dump() for r in results], f, indent=2)


def _load_progress(output_dir: Path) -> list[SessionEvaluationResult]:
    """Load experiment progress checkpoint."""
    path = output_dir / "experiment_progress.json"
    if not path.exists():
        return []
    with open(path) as f:
        data = json.load(f)
    return [SessionEvaluationResult.model_validate(item) for item in data]


def _run_and_evaluate_session(
    session_id: str,
    branch: str,
    iteration: int,
    pipeline_config: PipelineConfig,
    experiment_config: ExperimentConfig,
    prior_results: list[SessionEvaluationResult],
    base_dir: Path,
    force: bool,
    sessions_remaining: int,
) -> SessionEvaluationResult:
    """Run extraction for a session + compute mechanical metrics against baseline."""
    input_dir = base_dir / "input_data"
    output_dir = base_dir / "experiments" / branch / str(iteration) / "output"
    baselines_dir = base_dir / "baselines"

    manifest = load_manifest(input_dir / "manifest.json")
    session_manifest = next((s for s in manifest if s.identifier == session_id), None)
    if session_manifest is None:
        raise ValueError(f"Session '{session_id}' not found in manifest")

    stages = load_custom_stages(branch, iteration, base_dir)

    # Run extraction
    log(f"Extracting: {session_id}")
    session_output = _process_session(
        session_manifest, pipeline_config, input_dir, output_dir, stages,
        branch, iteration, base_dir, force,
    )
    write_output(output_dir, session_output)
    log(f"  Extracted {session_output.event_count} events")

    # Load baseline + experiment events
    with open(baselines_dir / session_id / "events.json") as f:
        baseline_events = json.load(f)
    experiment_events = [
        {k: v for k, v in event.model_dump().items() if v is not None}
        for event in session_output.events
    ]

    # Mechanical metrics
    metrics = _compute_session_metrics(session_id, baseline_events, experiment_events, experiment_config)
    log(f"  Metrics: F1={metrics.f1:.3f} Recall={metrics.recall:.3f} Precision={metrics.precision:.3f}")

    # Cumulative metrics + early-break (metric-based only)
    cumulative = _compute_cumulative_metrics(prior_results, metrics)
    break_decision = _decide_early_break(
        cumulative, prior_results, experiment_config, sessions_remaining,
    )

    if break_decision.should_break:
        log(f"  Early break: {break_decision.reason} — {break_decision.explanation}")

    return SessionEvaluationResult(
        session_id=session_id,
        metrics=metrics,
        cumulative=cumulative,
        break_decision=break_decision,
    )


# --- Top-level orchestrator ---


def _discover_sessions_with_baselines(
    sessions: tuple[str, ...] | None,
    base_dir: Path,
    output_dir: Path,
) -> list[str]:
    """Discover sessions that have both baselines and experiment output (or can be run)."""
    baselines_dir = base_dir / "baselines"

    if sessions:
        # Validate requested sessions have baselines
        result = []
        for sid in sessions:
            if (baselines_dir / sid / "events.json").exists():
                result.append(sid)
            else:
                log(f"Warning: no baseline for {sid}, skipping")
        return result

    # Auto-discover: all sessions with baselines
    return sorted(
        d.name
        for d in baselines_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".") and (d / "events.json").exists()
    )


def _find_latest_iteration(branch: str, base_dir: Path) -> int:
    """Find the latest iteration number for a branch."""
    branch_dir = base_dir / "experiments" / branch
    if not branch_dir.exists():
        raise FileNotFoundError(f"Branch '{branch}' not found in experiments/")
    iterations = [
        int(d.name) for d in branch_dir.iterdir()
        if d.is_dir() and d.name.isdigit()
    ]
    if not iterations:
        raise FileNotFoundError(f"No iterations found for branch '{branch}'")
    return max(iterations)


def run_experiment(
    branch: str,
    iteration: int | None = None,
    sessions: tuple[str, ...] | None = None,
    cli_overrides: tuple[str, ...] = (),
    base_dir: Path = Path("."),
    force: bool = False,
    resume: bool = False,
    dry_run: bool = False,
) -> ExperimentSummary:
    """Top-level experiment orchestrator.

    Runs extraction + mechanical metrics. Qualitative analysis and
    full-set LLM judgment are handled by the /evaluate skill.
    """
    # Resolve iteration
    if iteration is None:
        iteration = _find_latest_iteration(branch, base_dir)
    log(f"Experiment: {branch}/{iteration}")

    # Resolve configs
    pipeline_config = resolve_config(branch, iteration, cli_overrides, base_dir)
    experiment_config = resolve_experiment_config(cli_overrides)

    output_dir = base_dir / "experiments" / branch / str(iteration) / "output"

    # Discover sessions
    session_ids = _discover_sessions_with_baselines(sessions, base_dir, output_dir)
    if not session_ids:
        raise ValueError("No sessions with baselines found")

    log(f"Sessions to evaluate: {len(session_ids)} — {', '.join(session_ids)}")

    if dry_run:
        log("Dry run — would evaluate these sessions:")
        for sid in session_ids:
            baselines_dir = base_dir / "baselines"
            with open(baselines_dir / sid / "events.json") as f:
                baseline = json.load(f)
            log(f"  {sid}: {len(baseline)} baseline events")
        return ExperimentSummary(
            branch=branch,
            iteration=iteration,
            sessions_requested=session_ids,
            sessions_completed=[],
            sessions_skipped=session_ids,
            early_break=False,
            session_results=[],
            aggregate_f1=0.0,
            aggregate_recall=0.0,
            aggregate_precision=0.0,
            config=pipeline_config.model_dump(),
            experiment_config=experiment_config.model_dump(),
        )

    # Check for resume state
    completed_results: list[SessionEvaluationResult] = []
    if resume:
        completed_results = _load_progress(output_dir)
        if completed_results:
            completed_ids = {r.session_id for r in completed_results}
            log(f"Resuming: {len(completed_results)} sessions already evaluated")
            session_ids = [sid for sid in session_ids if sid not in completed_ids]

    # Per-session loop — batched for parallelism
    early_break = False
    early_break_reason: str | None = None
    skipped: list[str] = []

    SESSION_BATCH_SIZE = 3
    batches = [session_ids[i:i + SESSION_BATCH_SIZE] for i in range(0, len(session_ids), SESSION_BATCH_SIZE)]

    for batch_idx, batch in enumerate(batches):
        sessions_remaining_after_batch = sum(len(b) for b in batches[batch_idx + 1:])

        # Snapshot prior results so all sessions in the batch see the same baseline
        prior_snapshot = list(completed_results)

        def _run_session(session_id: str, prior: list[SessionEvaluationResult] = prior_snapshot) -> SessionEvaluationResult:
            if not force:
                cached = _load_session_eval_cache(output_dir, session_id)
                if cached is not None:
                    log(f"Session {session_id}: loaded from cache (F1={cached.metrics.f1:.3f})")
                    return cached
            result = _run_and_evaluate_session(
                session_id, branch, iteration, pipeline_config, experiment_config,
                prior, base_dir, force, sessions_remaining_after_batch,
            )
            _save_session_eval(output_dir, result)
            return result

        if len(batch) == 1:
            batch_results = [_run_session(batch[0])]
        else:
            log(f"Batch {batch_idx + 1}/{len(batches)}: {', '.join(batch)}")
            with ThreadPoolExecutor(max_workers=SESSION_BATCH_SIZE) as executor:
                futures = {executor.submit(_run_session, sid): sid for sid in batch}
                batch_results = [future.result() for future in as_completed(futures)]

        completed_results.extend(batch_results)
        _save_progress(output_dir, completed_results)

        # Check early break for any result in this batch
        for result in batch_results:
            if result.break_decision and result.break_decision.should_break:
                early_break = True
                early_break_reason = result.break_decision.reason
                skipped = [sid for b in batches[batch_idx + 1:] for sid in b]
                log(f"Early break after batch {batch_idx + 1}: {early_break_reason}")
                break

        if early_break:
            break

    # Compute aggregate metrics
    total_matched = sum(r.metrics.matched_count for r in completed_results)
    total_baseline = sum(r.metrics.baseline_count for r in completed_results)
    total_experiment = sum(r.metrics.experiment_count for r in completed_results)
    agg_prec = total_matched / total_experiment if total_experiment > 0 else 0.0
    agg_rec = total_matched / total_baseline if total_baseline > 0 else 0.0
    agg_f1 = 2 * agg_prec * agg_rec / (agg_prec + agg_rec) if (agg_prec + agg_rec) > 0 else 0.0

    log(f"Aggregate: F1={agg_f1:.3f} Recall={agg_rec:.3f} Precision={agg_prec:.3f}")

    # Build summary (qualitative analysis + full-set judgment handled by /evaluate skill)
    all_requested = (
        [r.session_id for r in completed_results]
        + skipped
        + ([sid for sid in (sessions or []) if sid not in [r.session_id for r in completed_results] and sid not in skipped])
    )

    summary = ExperimentSummary(
        branch=branch,
        iteration=iteration,
        sessions_requested=all_requested,
        sessions_completed=[r.session_id for r in completed_results],
        sessions_skipped=skipped,
        early_break=early_break,
        early_break_reason=early_break_reason,
        session_results=completed_results,
        aggregate_f1=agg_f1,
        aggregate_recall=agg_rec,
        aggregate_precision=agg_prec,
        config=pipeline_config.model_dump(),
        experiment_config=experiment_config.model_dump(),
    )

    # Save summary
    _save_experiment_summary(summary, output_dir)
    log(f"Summary saved to {output_dir / 'experiment_summary.json'}")

    return summary
