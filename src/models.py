from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


EventType = Literal[
    "click", "hover", "navigate", "input_text", "select",
    "dwell", "cursor_thrash", "scroll", "drag", "hesitate", "change_ui_state",
]

SourceType = Literal[
    "unmod_website_test_video", "ai_mod_website_test_video",
    "moderated_screen_recording", "unmod_figma_prototype_test",
    "unmod_tree_test", "unmod_card_sort",
]

ActivityTier = Literal["idle", "low", "medium", "high"]


# --- Manifest ---

class SessionData(BaseModel, frozen=True):
    fullSession: str
    screenTrack: str
    transcript: str


class SessionManifest(BaseModel, frozen=True):
    identifier: str
    team: str
    study: str
    studyId: str
    roomId: str
    participant: str
    userId: tuple[str, ...]
    screenTrackStartOffset: int
    data: SessionData


# --- Config ---

class TriageConfig(BaseModel, frozen=True):
    enabled: bool = True
    sample_fps: float = 5.0
    resolution_height: int = 480
    window_size_ms: int = 3000
    window_step_ms: int = 1000
    min_segment_duration_ms: int = 5000
    thresholds: dict[str, float] = {
        "idle": 0.005,
        "low": 0.02,
        "medium": 0.08,
    }
    fps_mapping: dict[str, float] = {
        "idle": 0.5,
        "low": 2.0,
        "medium": 4.0,
        "high": 10.0,
    }


class AnalyseConfig(BaseModel, frozen=True):
    model: str = "gemini-3-flash-preview"
    temperature: float = 0.1
    max_concurrent: int = 5
    token_budget_per_segment: int = 50000
    tokens_per_frame: int = 1548
    context_frames: int = 2
    jpeg_quality: int = 85
    source: SourceType = "unmod_website_test_video"


class MergeConfig(BaseModel, frozen=True):
    time_tolerance_ms: int = 2000
    similarity_threshold: float = 0.7
    discard_context_events: bool = True


class PipelineConfig(BaseModel, frozen=True):
    triage: TriageConfig = TriageConfig()
    analyse: AnalyseConfig = AnalyseConfig()
    merge: MergeConfig = MergeConfig()


# --- Video ---

class VideoMetadata(BaseModel, frozen=True):
    duration_ms: float
    fps: float
    width: int
    height: int


# --- Triage ---

class FrameDiff(BaseModel, frozen=True):
    frame_index: int
    timestamp_ms: float
    magnitude: float
    bbox: tuple[int, int, int, int] | None = None
    bbox_area_ratio: float = 0.0


class ActivityWindow(BaseModel, frozen=True):
    start_ms: float
    end_ms: float
    mean_magnitude: float
    tier: ActivityTier


class TriageSegment(BaseModel, frozen=True):
    segment_index: int
    start_ms: float
    end_ms: float
    tier: ActivityTier
    assigned_fps: float
    mean_activity: float


class TriageResult(BaseModel, frozen=True):
    recording_id: str
    segments: tuple[TriageSegment, ...]
    total_duration_ms: float
    processing_time_ms: float


# --- Analyse ---

class FrameRef(BaseModel, frozen=True):
    frame_index_in_request: int
    timestamp_ms: float
    is_context: bool = False


class RegionOfInterest(BaseModel, frozen=True):
    x: float
    y: float
    width: float
    height: float


class CursorPosition(BaseModel, frozen=True):
    x: float
    y: float


class RawEvent(BaseModel, frozen=True):
    frame_index_start: int
    frame_index_end: int
    type: EventType
    description: str
    confidence: float
    interaction_target: str | None = None
    region_of_interest: RegionOfInterest | None = None
    cursor_position: CursorPosition | None = None
    page_title: str | None = None
    page_location: str | None = None
    frame_description: str | None = None


class SegmentAnalysisResult(BaseModel, frozen=True):
    segment_index: int
    events: tuple[RawEvent, ...]
    frame_refs: tuple[FrameRef, ...]
    input_tokens: int = 0
    output_tokens: int = 0


class AnalyseResult(BaseModel, frozen=True):
    recording_id: str
    segments: tuple[SegmentAnalysisResult, ...]
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    processing_time_ms: float = 0


# --- Merge / Final Output ---

class ResolvedEvent(BaseModel, frozen=True):
    type: EventType
    source: SourceType
    time_start: float
    time_end: float
    description: str
    confidence: float
    interaction_target: str | None = None
    interaction_region_of_interest: dict | None = None
    cursor_position: dict | None = None
    page_title: str | None = None
    page_location: str | None = None
    frame_description: str | None = None
    transcript_id: str = ""
    study_id: str | None = None
    task_id: str | None = None


class StageMetrics(BaseModel, frozen=True):
    duration_ms: float = 0
    artifacts_created: int = 0


class SessionOutput(BaseModel, frozen=True):
    recording_id: str
    session: SessionManifest
    triage_metrics: StageMetrics = StageMetrics()
    analyse_metrics: StageMetrics = StageMetrics()
    merge_metrics: StageMetrics = StageMetrics()
    events: tuple[ResolvedEvent, ...]
    event_count: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0


class RunMetadata(BaseModel, frozen=True):
    branch: str
    iteration: int
    started_at: str
    completed_at: str
    config: dict
    sessions_processed: tuple[str, ...]
    total_events: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    errors: tuple[str, ...] = ()
