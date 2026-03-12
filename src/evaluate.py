"""Pure evaluation functions: matching baseline events to experiment events, computing metrics."""

from __future__ import annotations

from dataclasses import dataclass

from src.similarity import string_similarity


def normalize_time_end(event: dict) -> float:
    """Return time_end, falling back to time_start when None or 0."""
    end = event.get("time_end")
    return end if end else event["time_start"]


def match_score(
    baseline: dict,
    experiment: dict,
    time_tolerance_ms: float,
) -> float | None:
    """Score a baseline-experiment pair. Returns None if incompatible."""
    if baseline["type"] != experiment["type"]:
        return None

    b_start = baseline["time_start"]
    b_end = normalize_time_end(baseline)
    e_start = experiment["time_start"]
    e_end = normalize_time_end(experiment)

    time_overlap = (
        b_start <= e_end + time_tolerance_ms
        and e_start <= b_end + time_tolerance_ms
    )
    if not time_overlap:
        return None

    desc_sim = string_similarity(
        baseline.get("description", ""),
        experiment.get("description", ""),
    )

    midpoint_b = (b_start + b_end) / 2
    midpoint_e = (e_start + e_end) / 2
    time_distance = abs(midpoint_b - midpoint_e)
    time_closeness = max(0.0, 1.0 - time_distance / (time_tolerance_ms * 2))

    return desc_sim * 0.7 + time_closeness * 0.3


def greedy_match(
    baselines: list[dict],
    experiments: list[dict],
    time_tolerance_ms: float,
    similarity_threshold: float,
) -> tuple[list[tuple[int, int, float]], list[int], list[int]]:
    """Greedily match baselines to experiments 1:1 by descending score.

    Returns (matched_pairs, unmatched_baseline_indices, unmatched_experiment_indices).
    Each matched pair is (baseline_idx, experiment_idx, score).
    """
    candidates = []
    for bi, b in enumerate(baselines):
        for ei, e in enumerate(experiments):
            score = match_score(b, e, time_tolerance_ms)
            if score is not None and score >= similarity_threshold:
                candidates.append((bi, ei, score))

    candidates.sort(key=lambda x: x[2], reverse=True)

    matched_b: set[int] = set()
    matched_e: set[int] = set()
    matched_pairs: list[tuple[int, int, float]] = []

    for bi, ei, score in candidates:
        if bi not in matched_b and ei not in matched_e:
            matched_pairs.append((bi, ei, score))
            matched_b.add(bi)
            matched_e.add(ei)

    unmatched_baselines = [i for i in range(len(baselines)) if i not in matched_b]
    unmatched_experiments = [i for i in range(len(experiments)) if i not in matched_e]

    return matched_pairs, unmatched_baselines, unmatched_experiments


@dataclass(frozen=True)
class TypeMetrics:
    event_type: str
    baseline_count: int
    experiment_count: int
    matched: int
    precision: float
    recall: float
    f1: float


@dataclass(frozen=True)
class TimingMetrics:
    mean_start_error_ms: float
    mean_end_error_ms: float | None  # None when no baseline has valid time_end
    matched_count: int


@dataclass(frozen=True)
class EvaluationResult:
    session_id: str
    baseline_count: int
    experiment_count: int
    matched_count: int
    precision: float
    recall: float
    f1: float
    mean_description_similarity: float
    timing: TimingMetrics
    per_type: list[TypeMetrics]


def compute_metrics(
    baselines: list[dict],
    experiments: list[dict],
    matched_pairs: list[tuple[int, int, float]],
    unmatched_baselines: list[int],
    unmatched_experiments: list[int],
    session_id: str,
) -> EvaluationResult:
    """Compute evaluation metrics from matching results."""
    n_matched = len(matched_pairs)
    n_baseline = len(baselines)
    n_experiment = len(experiments)

    precision = n_matched / n_experiment if n_experiment > 0 else 0.0
    recall = n_matched / n_baseline if n_baseline > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    # Description similarity across matched pairs
    desc_sims = [
        string_similarity(
            baselines[bi].get("description", ""),
            experiments[ei].get("description", ""),
        )
        for bi, ei, _ in matched_pairs
    ]
    mean_desc_sim = sum(desc_sims) / len(desc_sims) if desc_sims else 0.0

    # Timing errors
    start_errors = []
    end_errors = []
    for bi, ei, _ in matched_pairs:
        b, e = baselines[bi], experiments[ei]
        start_errors.append(abs(b["time_start"] - e["time_start"]))
        b_end = b.get("time_end")
        if b_end is not None and b_end != 0:
            end_errors.append(abs(b_end - normalize_time_end(experiments[ei])))

    timing = TimingMetrics(
        mean_start_error_ms=sum(start_errors) / len(start_errors) if start_errors else 0.0,
        mean_end_error_ms=sum(end_errors) / len(end_errors) if end_errors else None,
        matched_count=n_matched,
    )

    # Per-type metrics
    all_types = sorted({e["type"] for e in baselines} | {e["type"] for e in experiments})
    per_type = []
    for t in all_types:
        t_baseline = sum(1 for e in baselines if e["type"] == t)
        t_experiment = sum(1 for e in experiments if e["type"] == t)
        t_matched = sum(1 for bi, ei, _ in matched_pairs if baselines[bi]["type"] == t)
        t_prec = t_matched / t_experiment if t_experiment > 0 else 0.0
        t_rec = t_matched / t_baseline if t_baseline > 0 else 0.0
        t_f1 = 2 * t_prec * t_rec / (t_prec + t_rec) if (t_prec + t_rec) > 0 else 0.0
        per_type.append(TypeMetrics(
            event_type=t,
            baseline_count=t_baseline,
            experiment_count=t_experiment,
            matched=t_matched,
            precision=t_prec,
            recall=t_rec,
            f1=t_f1,
        ))

    return EvaluationResult(
        session_id=session_id,
        baseline_count=n_baseline,
        experiment_count=n_experiment,
        matched_count=n_matched,
        precision=precision,
        recall=recall,
        f1=f1,
        mean_description_similarity=mean_desc_sim,
        timing=timing,
        per_type=per_type,
    )


def _fmt_time(ms: float) -> str:
    """Format milliseconds as m:ss.s for readability."""
    s = ms / 1000
    return f"{int(s // 60)}:{s % 60:04.1f}"


def _fmt_event(event: dict) -> str:
    """One-line summary of an event."""
    t = event["type"]
    start = _fmt_time(event["time_start"])
    end = _fmt_time(normalize_time_end(event))
    desc = event.get("description", "")
    if len(desc) > 80:
        desc = desc[:77] + "..."
    return f"[{t:<20}] {start}-{end}  {desc}"


def format_results(
    result: EvaluationResult,
    baselines: list[dict] | None = None,
    experiments: list[dict] | None = None,
    matched_pairs: list[tuple[int, int, float]] | None = None,
    unmatched_baselines: list[int] | None = None,
    unmatched_experiments: list[int] | None = None,
    verbose: bool = False,
) -> str:
    """Format evaluation results as a readable table, with optional event-level detail."""
    lines = [
        f"Session: {result.session_id}",
        f"  Baseline events:   {result.baseline_count}",
        f"  Experiment events: {result.experiment_count}",
        f"  Matched:           {result.matched_count}",
        "",
        f"  Precision: {result.precision:.3f}",
        f"  Recall:    {result.recall:.3f}",
        f"  F1:        {result.f1:.3f}",
        f"  Desc sim:  {result.mean_description_similarity:.3f}",
        "",
        f"  Timing (matched pairs):",
        f"    Mean start error: {result.timing.mean_start_error_ms:,.0f} ms",
    ]
    if result.timing.mean_end_error_ms is not None:
        lines.append(f"    Mean end error:   {result.timing.mean_end_error_ms:,.0f} ms")
    else:
        lines.append(f"    Mean end error:   n/a (no baseline time_end)")

    lines.append("")
    lines.append(f"  {'Type':<20} {'Base':>5} {'Exp':>5} {'Match':>5} {'Prec':>6} {'Rec':>6} {'F1':>6}")
    lines.append(f"  {'-'*20} {'-'*5} {'-'*5} {'-'*5} {'-'*6} {'-'*6} {'-'*6}")
    for t in result.per_type:
        lines.append(
            f"  {t.event_type:<20} {t.baseline_count:>5} {t.experiment_count:>5} "
            f"{t.matched:>5} {t.precision:>6.3f} {t.recall:>6.3f} {t.f1:>6.3f}"
        )

    if verbose and baselines is not None and experiments is not None:
        if matched_pairs:
            lines.append("")
            lines.append("  MATCHED PAIRS:")
            for bi, ei, score in sorted(matched_pairs, key=lambda x: baselines[x[0]]["time_start"]):
                b, e = baselines[bi], experiments[ei]
                desc_sim = string_similarity(b.get("description", ""), e.get("description", ""))
                start_err = abs(b["time_start"] - e["time_start"])
                lines.append(f"    score={score:.3f}  desc_sim={desc_sim:.3f}  start_err={start_err:,.0f}ms")
                lines.append(f"      B: {_fmt_event(b)}")
                lines.append(f"      E: {_fmt_event(e)}")

        if unmatched_baselines:
            lines.append("")
            lines.append("  MISSED BASELINE EVENTS (false negatives):")
            for bi in sorted(unmatched_baselines, key=lambda i: baselines[i]["time_start"]):
                lines.append(f"    {_fmt_event(baselines[bi])}")

        if unmatched_experiments:
            lines.append("")
            lines.append("  UNMATCHED EXPERIMENT EVENTS (false positives):")
            for ei in sorted(unmatched_experiments, key=lambda i: experiments[i]["time_start"]):
                lines.append(f"    {_fmt_event(experiments[ei])}")

    return "\n".join(lines)


def result_to_dict(result: EvaluationResult) -> dict:
    """Convert EvaluationResult to a JSON-serialisable dict."""
    return {
        "session_id": result.session_id,
        "baseline_count": result.baseline_count,
        "experiment_count": result.experiment_count,
        "matched_count": result.matched_count,
        "precision": round(result.precision, 4),
        "recall": round(result.recall, 4),
        "f1": round(result.f1, 4),
        "mean_description_similarity": round(result.mean_description_similarity, 4),
        "timing": {
            "mean_start_error_ms": round(result.timing.mean_start_error_ms, 1),
            "mean_end_error_ms": round(result.timing.mean_end_error_ms, 1) if result.timing.mean_end_error_ms is not None else None,
            "matched_count": result.timing.matched_count,
        },
        "per_type": [
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
    }
