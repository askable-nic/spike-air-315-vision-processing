"""Agent-based experiment orchestrator.

Launches claude -p subprocesses to run extraction + qualitative evaluation
for each session in parallel. Includes canary gating and abort monitoring.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path

from src.experiment import (
    _discover_sessions_with_baselines,
    _find_latest_iteration,
    _save_experiment_summary,
)
from src.experiment_models import (
    AgentSessionReport,
    ExperimentSummary,
    SessionEvaluationResult,
    SessionMetrics,
    SessionQualitativeAssessment,
)
from src.log import log


# --- Prompt interpolation ---


def _build_agent_prompt(
    session_id: str,
    branch: str,
    iteration: int,
    base_dir: Path,
    output_dir: Path,
    force: bool,
) -> str:
    """Read the agent_session.txt template and interpolate placeholders."""
    template_path = base_dir / "prompts" / "agent_session.txt"
    template = template_path.read_text()

    qualitative_path = base_dir / "prompts" / "experiment_session_analysis.txt"
    qualitative_instructions = qualitative_path.read_text()

    force_flag = "-f" if force else ""

    return template.format(
        session_id=session_id,
        branch=branch,
        iteration=iteration,
        base_dir=base_dir,
        output_dir=output_dir,
        force_flag=force_flag,
        qualitative_instructions=qualitative_instructions,
    )


# --- Subprocess management ---


def _launch_agent(
    prompt: str,
    budget: float,
    base_dir: Path,
) -> subprocess.Popen:
    """Launch a claude -p subprocess for a single session."""
    cmd = [
        "claude", "-p", prompt,
        "--allowedTools", "Bash Read Write Glob Grep",
        "--model", "sonnet",
        "--max-budget-usd", str(budget),
        "--no-session-persistence",
        "--permission-mode", "bypassPermissions",
    ]
    # Unset CLAUDECODE so nested claude -p doesn't refuse to launch
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    return subprocess.Popen(
        cmd,
        cwd=str(base_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )


def _wait_for_agent(proc: subprocess.Popen, session_id: str) -> int:
    """Wait for a subprocess to complete, returning the exit code."""
    returncode = proc.wait()
    if returncode != 0:
        stderr = proc.stderr.read().decode() if proc.stderr else ""
        log(f"  Agent for {session_id} exited with code {returncode}: {stderr[:500]}")
    return returncode


# --- Result loading ---


def _load_agent_result(output_dir: Path, session_id: str) -> AgentSessionReport | None:
    """Load agent_result.json for a session, returning None if not found."""
    path = output_dir / session_id / "agent_result.json"
    if not path.exists():
        return None
    with open(path) as f:
        data = json.load(f)
    return AgentSessionReport.model_validate(data)


def _agent_report_to_eval_result(report: AgentSessionReport) -> SessionEvaluationResult | None:
    """Convert an AgentSessionReport to a SessionEvaluationResult."""
    if report.metrics is None:
        return None
    return SessionEvaluationResult(
        session_id=report.session_id,
        metrics=report.metrics,
        qualitative=report.qualitative,
    )


# --- Abort monitoring ---


def _check_abort(output_dir: Path) -> str | None:
    """Check for the _abort sentinel file. Returns the reason if found."""
    abort_path = output_dir / "_abort"
    if abort_path.exists():
        return abort_path.read_text().strip()
    return None


def _poll_abort_and_wait(
    procs: dict[str, subprocess.Popen],
    output_dir: Path,
    poll_interval: float = 2.0,
) -> tuple[dict[str, int], str | None]:
    """Poll for abort sentinel while waiting for all subprocesses.

    Returns (exit_codes, abort_reason).
    """
    exit_codes: dict[str, int] = {}
    abort_reason: str | None = None

    while procs:
        # Check abort sentinel
        reason = _check_abort(output_dir)
        if reason is not None:
            abort_reason = reason
            log(f"Abort sentinel detected: {reason}")
            for sid, proc in procs.items():
                if proc.poll() is None:
                    log(f"  Terminating agent for {sid}")
                    proc.terminate()
            # Collect exit codes for terminated processes
            for sid, proc in procs.items():
                exit_codes[sid] = proc.wait()
            break

        # Check for completed processes
        completed = []
        for sid, proc in procs.items():
            ret = proc.poll()
            if ret is not None:
                exit_codes[sid] = ret
                completed.append(sid)
                if ret == 0:
                    log(f"  Agent completed: {sid}")
                else:
                    stderr = proc.stderr.read().decode() if proc.stderr else ""
                    log(f"  Agent failed: {sid} (exit {ret}): {stderr[:300]}")

        for sid in completed:
            del procs[sid]

        if procs:
            time.sleep(poll_interval)

    return exit_codes, abort_reason


# --- Aggregate metrics ---


def _compute_aggregate_metrics(
    results: list[SessionEvaluationResult],
) -> tuple[float, float, float]:
    """Compute aggregate F1, recall, precision from session results."""
    total_matched = sum(r.metrics.matched_count for r in results)
    total_baseline = sum(r.metrics.baseline_count for r in results)
    total_experiment = sum(r.metrics.experiment_count for r in results)

    precision = total_matched / total_experiment if total_experiment > 0 else 0.0
    recall = total_matched / total_baseline if total_baseline > 0 else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    return f1, recall, precision


# --- Main orchestrator ---


def run_agent_experiment(
    branch: str,
    iteration: int | None = None,
    sessions: tuple[str, ...] | None = None,
    base_dir: Path = Path("."),
    force: bool = False,
    budget: float = 0.50,
) -> ExperimentSummary:
    """Orchestrate agent-based experiment evaluation.

    1. Discover sessions with baselines
    2. Run canary session, gate on result
    3. Launch all remaining sessions in parallel
    4. Monitor for abort sentinel
    5. Collect results and build summary
    """
    if iteration is None:
        iteration = _find_latest_iteration(branch, base_dir)

    output_dir = base_dir / "experiments" / branch / str(iteration) / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    log(f"Agent experiment: {branch}/{iteration}")

    # Discover sessions
    session_ids = _discover_sessions_with_baselines(sessions, base_dir, output_dir)
    if not session_ids:
        raise ValueError("No sessions with baselines found")

    log(f"Sessions: {len(session_ids)} — {', '.join(session_ids)}")

    # --- Canary ---
    canary_id = random.choice(session_ids) if len(session_ids) > 1 else session_ids[0]
    log(f"Canary: {canary_id}")

    canary_prompt = _build_agent_prompt(canary_id, branch, iteration, base_dir, output_dir, force)
    canary_proc = _launch_agent(canary_prompt, budget, base_dir)
    _wait_for_agent(canary_proc, canary_id)

    canary_report = _load_agent_result(output_dir, canary_id)
    if canary_report is None:
        raise RuntimeError(f"Canary agent for {canary_id} produced no agent_result.json")

    if canary_report.status == "error":
        raise RuntimeError(f"Canary agent failed: {canary_report.error}")

    # Gate: abort if F1 < threshold AND severity is critical
    canary_f1 = canary_report.metrics.f1 if canary_report.metrics else 0.0
    canary_severity = canary_report.qualitative.overall_severity if canary_report.qualitative else "noise"

    if canary_f1 < 0.05 and canary_severity == "critical":
        log(f"Canary gate FAILED: F1={canary_f1:.3f}, severity={canary_severity}")
        log("Aborting experiment — canary indicates critical failure.")
        canary_eval = _agent_report_to_eval_result(canary_report)
        return ExperimentSummary(
            branch=branch,
            iteration=iteration,
            sessions_requested=session_ids,
            sessions_completed=[canary_id] if canary_eval else [],
            sessions_skipped=[s for s in session_ids if s != canary_id],
            early_break=True,
            early_break_reason=f"canary_gate: F1={canary_f1:.3f}, severity={canary_severity}",
            session_results=[canary_eval] if canary_eval else [],
            aggregate_f1=canary_f1,
            aggregate_recall=canary_report.metrics.recall if canary_report.metrics else 0.0,
            aggregate_precision=canary_report.metrics.precision if canary_report.metrics else 0.0,
        )

    log(f"Canary passed: F1={canary_f1:.3f}, severity={canary_severity}")

    # --- Remaining sessions ---
    remaining_ids = [sid for sid in session_ids if sid != canary_id]

    if remaining_ids:
        log(f"Launching {len(remaining_ids)} remaining agents...")
        procs: dict[str, subprocess.Popen] = {}
        for sid in remaining_ids:
            prompt = _build_agent_prompt(sid, branch, iteration, base_dir, output_dir, force)
            procs[sid] = _launch_agent(prompt, budget, base_dir)
            log(f"  Launched: {sid}")

        exit_codes, abort_reason = _poll_abort_and_wait(procs, output_dir)
    else:
        exit_codes = {}
        abort_reason = None

    # --- Collect results ---
    all_results: list[SessionEvaluationResult] = []
    completed_ids: list[str] = []
    skipped_ids: list[str] = []

    for sid in session_ids:
        report = _load_agent_result(output_dir, sid)
        if report is not None and report.status == "success":
            eval_result = _agent_report_to_eval_result(report)
            if eval_result is not None:
                all_results.append(eval_result)
                completed_ids.append(sid)
                continue
        skipped_ids.append(sid)

    if not all_results:
        raise RuntimeError("No sessions produced valid results")

    # --- Aggregate ---
    agg_f1, agg_recall, agg_precision = _compute_aggregate_metrics(all_results)

    log(f"Aggregate: F1={agg_f1:.3f} Recall={agg_recall:.3f} Precision={agg_precision:.3f}")
    log(f"Completed: {len(completed_ids)}/{len(session_ids)}")

    summary = ExperimentSummary(
        branch=branch,
        iteration=iteration,
        sessions_requested=session_ids,
        sessions_completed=completed_ids,
        sessions_skipped=skipped_ids,
        early_break=abort_reason is not None,
        early_break_reason=abort_reason,
        session_results=all_results,
        aggregate_f1=agg_f1,
        aggregate_recall=agg_recall,
        aggregate_precision=agg_precision,
    )

    _save_experiment_summary(summary, output_dir)
    log(f"Summary saved to {output_dir / 'experiment_summary.json'}")

    return summary


# --- CLI ---


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent-based experiment orchestrator")
    parser.add_argument("--branch", "-b", required=True, help="Experiment branch name")
    parser.add_argument("--iteration", "-i", type=int, default=None, help="Iteration number (default: latest)")
    parser.add_argument("--session", "-s", action="append", default=None, help="Session ID(s) (repeatable)")
    parser.add_argument("--force", "-f", action="store_true", help="Force re-extraction")
    parser.add_argument("--budget", type=float, default=0.50, help="Max budget per agent in USD (default: 0.50)")
    parser.add_argument("--base-dir", type=str, default=".", help="Project base directory")

    args = parser.parse_args()

    sessions = tuple(args.session) if args.session else None

    summary = run_agent_experiment(
        branch=args.branch,
        iteration=args.iteration,
        sessions=sessions,
        base_dir=Path(args.base_dir),
        force=args.force,
        budget=args.budget,
    )

    # Print summary
    print(f"\n{'=' * 60}")
    print(f"Agent Experiment: {summary.branch}/{summary.iteration}")
    print(f"Sessions: {len(summary.sessions_completed)}/{len(summary.sessions_requested)}")
    if summary.early_break:
        print(f"Early break: {summary.early_break_reason}")
    print(f"F1: {summary.aggregate_f1:.3f}  Recall: {summary.aggregate_recall:.3f}  Precision: {summary.aggregate_precision:.3f}")

    output_dir = Path(args.base_dir) / "experiments" / summary.branch / str(summary.iteration) / "output"
    print(f"\nFull report: {output_dir / 'experiment_summary.json'}")

    # Per-session summary
    for r in summary.session_results:
        severity = r.qualitative.overall_severity if r.qualitative else "n/a"
        print(f"  {r.session_id}: F1={r.metrics.f1:.3f} severity={severity}")


if __name__ == "__main__":
    main()
