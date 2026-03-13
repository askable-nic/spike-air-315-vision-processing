"""Pydantic models for the experiment runner: per-session evaluation, full-set judgment, and summary."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class SessionMetrics(BaseModel, frozen=True):
    """Step 1a: greedy_match + compute_metrics results with threshold pass/fail."""
    session_id: str
    baseline_count: int
    experiment_count: int
    matched_count: int
    precision: float
    recall: float
    f1: float
    mean_description_similarity: float
    mean_start_error_ms: float
    mean_end_error_ms: float | None
    per_type: list[dict[str, Any]]
    f1_pass: bool
    recall_pass: bool
    precision_pass: bool


class QualitativeIssue(BaseModel, frozen=True):
    """A single issue identified by the qualitative LLM analysis."""
    category: str
    severity: Literal["noise", "acceptable", "systematic", "critical"]
    description: str
    affected_events: list[int] = []
    examples: list[str] = []


class SessionQualitativeAssessment(BaseModel, frozen=True):
    """Step 1b: LLM qualitative analysis of baseline vs experiment differences."""
    overall_severity: Literal["noise", "acceptable", "systematic", "critical"]
    summary: str
    issues: list[QualitativeIssue]
    noise_fraction: float
    acceptable_fraction: float
    systematic_fraction: float
    critical_fraction: float
    input_tokens: int = 0
    output_tokens: int = 0


class CumulativeMetrics(BaseModel, frozen=True):
    """Running aggregates across sessions processed so far."""
    sessions_completed: int
    cumulative_f1: float
    cumulative_recall: float
    cumulative_precision: float
    cumulative_matched: int
    cumulative_baseline: int
    cumulative_experiment: int
    f1_trend: Literal["improving", "stable", "declining"]
    f1_history: list[float]


class EarlyBreakDecision(BaseModel, frozen=True):
    """Step 1c: whether to stop processing further sessions."""
    should_break: bool
    reason: str
    explanation: str


class SessionEvaluationResult(BaseModel, frozen=True):
    """Complete evaluation for a single session: metrics + qualitative + cumulative + break."""
    session_id: str
    metrics: SessionMetrics
    qualitative: SessionQualitativeAssessment | None = None
    cumulative: CumulativeMetrics | None = None
    break_decision: EarlyBreakDecision | None = None


class FullSetJudgment(BaseModel, frozen=True):
    """Step 2: cross-session LLM evaluation across all processed sessions."""
    overall_score: float
    coverage_score: float
    type_accuracy_score: float
    timing_score: float
    systematic_patterns: list[str]
    root_cause_analysis: str
    strengths: list[str]
    weaknesses: list[str]
    recommendations: list[RecommendedChange]
    input_tokens: int = 0
    output_tokens: int = 0


class RecommendedChange(BaseModel, frozen=True):
    """A specific config change recommendation from the full-set judge."""
    config_key: str
    current_value: Any = None
    recommended_value: Any = None
    rationale: str
    confidence: float


# Rebuild FullSetJudgment now that RecommendedChange is defined
FullSetJudgment.model_rebuild()


class ExperimentSummary(BaseModel, frozen=True):
    """Complete experiment run summary."""
    branch: str
    iteration: int
    sessions_requested: list[str]
    sessions_completed: list[str]
    sessions_skipped: list[str]
    early_break: bool
    early_break_reason: str | None = None
    session_results: list[SessionEvaluationResult]
    aggregate_f1: float
    aggregate_recall: float
    aggregate_precision: float
    judgment: FullSetJudgment | None = None
    config: dict[str, Any] = {}
    experiment_config: dict[str, Any] = {}
    auto_iteration: AutoIterationResult | None = None


class AutoIterationResult(BaseModel, frozen=True):
    """Step 4: result of auto-iteration config generation."""
    source_iteration: int
    new_iteration: int
    changes_applied: list[RecommendedChange]
    changelog: str


class AgentSessionReport(BaseModel, frozen=True):
    """Raw output from a claude -p session agent, before folding into SessionEvaluationResult."""
    session_id: str
    status: Literal["success", "error", "aborted"]
    metrics: SessionMetrics | None = None
    qualitative: SessionQualitativeAssessment | None = None
    error: str | None = None


# Rebuild ExperimentSummary now that AutoIterationResult is defined
ExperimentSummary.model_rebuild()
