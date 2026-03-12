from __future__ import annotations

from pathlib import Path
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
    normalizedScreenTrack: str | None = None


class SessionManifest(BaseModel, frozen=True):
    identifier: str
    team: str
    study: str
    studyId: str
    roomId: str
    participant: str
    userId: tuple[str, ...]
    screenTrackStartOffset: int
    fullSessionDurationMs: float | None = None
    screenTrackDurationMs: float | None = None
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
    batch_gap_ms: int = 5000


class MergeConfig(BaseModel, frozen=True):
    time_tolerance_ms: int = 2000
    similarity_threshold: float = 0.7
    discard_context_events: bool = True


class ObserveConfig(BaseModel, frozen=True):
    enabled: bool = False
    # Visual-change-driven pipeline
    visual_change_driven: bool = False
    cursor_tracking_enabled: bool = True
    # Visual change detection
    change_detect_fps: float = 4.0
    change_pixel_threshold: int = 20
    change_min_area_px: int = 1000
    change_blur_kernel: int = 5
    change_morph_kernel: int = 5
    scene_change_area_threshold: float = 0.3
    continuous_change_max_duration_ms: int = 3000
    # Cursor stop detection
    cursor_stop_min_ms: int = 300
    cursor_stop_radius_px: float = 15.0
    # Moment detection
    moment_merge_gap_ms: int = 500
    token_budget_per_minute: int = 50000
    tokens_full_frame: int = 1600
    tokens_roi_pair: int = 750
    tokens_roi_single: int = 300
    roi_min_size: int = 256
    # Moment candidate filtering
    moment_categories: tuple[str, ...] = (
        "scene_change", "pre_scene_change", "interaction", "scroll",
        "continuous", "cursor_stop", "cursor_only", "baseline",
    )
    min_visual_change_duration_ms: float = 0
    max_moments_per_minute: float = 0
    # Adaptive frame sampling
    moment_sample_interval_ms: int = 0
    moment_max_frames: int = 0
    # Cursor tracking — adaptive two-pass
    tracking_fps: float = 5.0  # legacy single-pass FPS
    tracking_base_fps: float = 2.0
    tracking_peak_fps: float = 15.0
    tracking_displacement_threshold_px: float = 30.0
    tracking_active_padding_ms: int = 500
    resolution_height: int = 720
    template_scales: tuple[float, ...] = (0.8, 1.0, 1.25, 1.5)
    match_threshold: float = 0.6
    early_exit_threshold: float = 0.9
    max_interpolation_gap_ms: int = 500
    smooth_window: int = 3
    smooth_displacement_threshold: float = 50.0
    # Optical flow
    flow_fps: float = 2.0
    flow_grid_step: int = 20
    flow_window_size_ms: int = 1000
    flow_window_step_ms: int = 500
    # Event synthesis — hover
    hover_min_ms: int = 300
    hover_max_ms: int = 2000
    hover_radius_px: float = 15.0
    # Event synthesis — dwell
    dwell_min_ms: int = 2000
    dwell_radius_px: float = 20.0
    # Event synthesis — thrash
    thrash_window_ms: int = 1000
    thrash_min_direction_changes: int = 4
    thrash_min_speed_px_per_sec: float = 500.0
    thrash_angle_threshold_deg: float = 90.0
    # Event synthesis — click candidate
    click_stop_max_ms: int = 200
    click_stop_radius_px: float = 5.0
    click_min_confidence: float = 0.3
    # Event synthesis — scroll
    scroll_min_flow_uniformity: float = 0.6
    scroll_min_magnitude: float = 3.0
    # Event synthesis — hesitation
    hesitation_min_ms: int = 500
    hesitation_max_ms: int = 2000
    hesitation_radius_px: float = 10.0
    # ROI
    roi_size: int = 512
    roi_padding: int = 64
    # Frame selection
    visual_scan_gap_ms: int = 3000
    visual_scan_fps: float = 1.0
    visual_change_threshold: float = 0.03
    baseline_max_gap_ms: int = 5000
    frame_dedup_ms: int = 200


class GenerateBaselinesConfig(BaseModel, frozen=True):
    model: str = "gemini-3-flash-preview"
    temperature: float = 0.2
    max_concurrent: int = 3
    video_fps: int = 20
    max_segment_duration_ms: int = 75000
    segment_overlap_ms: int = 5000
    source: str = "gemini_video_baseline"
    merge: MergeConfig = MergeConfig(
        time_tolerance_ms=2000,
        similarity_threshold=0.6,
        discard_context_events=False,
    )


class PipelineConfig(BaseModel, frozen=True):
    triage: TriageConfig = TriageConfig()
    analyse: AnalyseConfig = AnalyseConfig()
    merge: MergeConfig = MergeConfig()
    observe: ObserveConfig = ObserveConfig()


# --- Video ---

class VideoMetadata(BaseModel, frozen=True):
    duration_ms: float
    fps: float
    width: int
    height: int


class VideoSegment(BaseModel, frozen=True):
    index: int
    start_ms: float
    end_ms: float
    overlap_start_ms: float  # start of overlap with previous segment
    overlap_end_ms: float    # end of overlap with next segment
    path: Path               # path to extracted segment file


class VideoAnalysisEvent(BaseModel, frozen=True):
    """Event detected from video segment analysis."""
    type: str
    time_start_ms: float
    time_end_ms: float
    description: str
    confidence: float
    interaction_target: str | None = None
    cursor_position_x: int | None = None
    cursor_position_y: int | None = None
    page_title: str | None = None
    page_location: str | None = None
    frame_description: str | None = None


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


class CursorDetection(BaseModel, frozen=True):
    timestamp_ms: float
    x: float
    y: float
    confidence: float
    template_id: str = ""
    detected: bool = True


class FlowWindow(BaseModel, frozen=True):
    start_ms: float
    end_ms: float
    mean_flow_magnitude: float
    dominant_direction: str = ""
    flow_uniformity: float = 0.0
    cursor_flow_divergence: float = 0.0


class ChangeRegion(BaseModel, frozen=True):
    x: int
    y: int
    width: int
    height: int
    area_px: int
    mean_magnitude: float


class VisualChangeFrame(BaseModel, frozen=True):
    timestamp_a_ms: float
    timestamp_b_ms: float
    regions: tuple[ChangeRegion, ...]
    total_changed_area_px: int
    frame_area_fraction: float


class VisualChangeEvent(BaseModel, frozen=True):
    time_start_ms: float
    time_end_ms: float
    frames: tuple[VisualChangeFrame, ...]
    peak_changed_area_fraction: float
    bounding_box: tuple[int, int, int, int]
    category: str  # "scene_change", "local_change", "continuous_change"


class FlowEvent(BaseModel, frozen=True):
    time_start_ms: float
    time_end_ms: float
    dominant_direction: str
    mean_magnitude: float
    flow_uniformity: float
    category: str  # "scroll", "pan", "mixed"


MomentCategory = Literal[
    "scene_change", "pre_scene_change", "interaction", "scroll",
    "continuous", "cursor_stop", "cursor_only", "baseline",
]


class Moment(BaseModel, frozen=True):
    time_start_ms: float
    time_end_ms: float
    visual_change: VisualChangeEvent | None = None
    flow_event: FlowEvent | None = None
    cursor_before: CursorPosition | None = None
    cursor_after: CursorPosition | None = None
    cursor_associated: bool = False
    category: MomentCategory = "baseline"
    priority: int = 5
    estimated_tokens: int = 1600
    frame_count: int = 0


class SceneDescription(BaseModel, frozen=True):
    frame_index: int
    timestamp_ms: float
    page_title: str = ""
    page_location: str = ""
    page_description: str = ""
    visible_interactive_elements: tuple[str, ...] = ()


class LocalEvent(BaseModel, frozen=True):
    type: EventType
    time_start_ms: float
    time_end_ms: float
    cursor_positions: tuple[CursorPosition, ...] = ()
    confidence: float = 0.5
    synthesis_method: str = ""
    description: str = ""
    needs_enrichment: bool = True


class ROIRect(BaseModel, frozen=True):
    timestamp_ms: float
    x: int
    y: int
    width: int
    height: int
    cursor_x: float = 0.0
    cursor_y: float = 0.0


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
    viewport_width: int | None = None
    viewport_height: int | None = None
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


# --- Observe ---

class SelectedFrame(BaseModel, frozen=True):
    timestamp_ms: float
    reason: str  # "event_start", "event_end", "event_mid", "visual_change", "baseline"
    event_index: int | None = None
    roi: ROIRect | None = None


class ObserveResult(BaseModel, frozen=True):
    recording_id: str
    cursor_trajectory: tuple[CursorDetection, ...] = ()
    flow_summary: tuple[FlowWindow, ...] = ()
    local_events: tuple[LocalEvent, ...] = ()
    roi_rects: tuple[ROIRect, ...] = ()
    selected_frames: tuple[SelectedFrame, ...] = ()
    # Visual-change-driven fields
    visual_changes: tuple[VisualChangeEvent, ...] = ()
    flow_events: tuple[FlowEvent, ...] = ()
    moments: tuple[Moment, ...] = ()
    scene_descriptions: tuple[SceneDescription, ...] = ()
    token_budget: int = 0
    token_budget_used: int = 0
    processing_time_ms: float = 0
    frames_analysed: int = 0
    cursor_detection_rate: float = 0.0


# --- Merge / Final Output ---

class ResolvedEvent(BaseModel, frozen=True):
    type: EventType
    time_start: float
    time_end: float
    description: str
    confidence: float
    interaction_target: str | None = None
    cursor_position: dict | None = None
    page_title: str | None = None
    page_location: str | None = None
    viewport_width: int | None = None
    viewport_height: int | None = None
    frame_description: str | None = None
    task_id: str | None = None


class StageMetrics(BaseModel, frozen=True):
    duration_ms: float = 0
    artifacts_created: int = 0


class SessionOutput(BaseModel, frozen=True):
    recording_id: str
    session: SessionManifest
    triage_metrics: StageMetrics = StageMetrics()
    observe_metrics: StageMetrics = StageMetrics()
    analyse_metrics: StageMetrics = StageMetrics()
    merge_metrics: StageMetrics = StageMetrics()
    events: tuple[ResolvedEvent, ...]
    event_count: int = 0
    total_input_token_budget: int = 0
    total_input_token_budget_utilisation: float = 0.0
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
    total_input_token_budget: int = 0
    total_input_token_budget_utilisation: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    errors: tuple[str, ...] = ()
