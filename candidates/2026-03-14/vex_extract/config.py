from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel


class TokenCost(BaseModel, frozen=True):
    input_token_cost: float  # USD per token
    output_token_cost: float  # USD per token


class GeminiConfig(BaseModel, frozen=True):
    api_key_env: str = "GEMINI_API_KEY"
    model: str = "gemini-2.5-flash"
    temperature: float = 0.1
    max_concurrent: int = 3


class VideoConfig(BaseModel, frozen=True):
    target_pixels: int = 2_073_600
    video_fps: int = 20


class SegmentationConfig(BaseModel, frozen=True):
    max_segment_duration_ms: int = 75000
    segment_overlap_ms: int = 5000


class CursorConfig(BaseModel, frozen=True):
    tracking_base_fps: float = 2.0
    tracking_peak_fps: float = 15.0
    tracking_displacement_threshold_px: float = 10.0
    tracking_active_padding_ms: int = 500
    template_scales: tuple[float, ...] = (0.8, 1.0, 1.25, 1.5)
    match_threshold: float = 0.6
    early_exit_threshold: float = 0.9
    max_interpolation_gap_ms: int = 500
    smooth_window: int = 3
    smooth_displacement_threshold: float = 10.0


class FlowConfig(BaseModel, frozen=True):
    flow_fps: float = 2.0
    flow_grid_step: int = 20
    flow_window_size_ms: int = 1000
    flow_window_step_ms: int = 500
    resolution_height: int = 720


class CvSummaryConfig(BaseModel, frozen=True):
    summary_window_ms: int = 250


class MergeConfig(BaseModel, frozen=True):
    time_tolerance_ms: int = 2000
    similarity_threshold: float = 0.7
    cursor_event_types: tuple[str, ...] = (
        "click", "hover", "dwell", "cursor_thrash", "select", "drag",
    )


class AppConfig(BaseModel, frozen=True):
    gemini: GeminiConfig = GeminiConfig()
    video: VideoConfig = VideoConfig()
    segmentation: SegmentationConfig = SegmentationConfig()
    cursor: CursorConfig = CursorConfig()
    flow: FlowConfig = FlowConfig()
    cv_summary: CvSummaryConfig = CvSummaryConfig()
    merge: MergeConfig = MergeConfig()
    token_costs: dict[str, TokenCost] = {}


def load_config(path: Path) -> AppConfig:
    """Load AppConfig from a YAML file, falling back to defaults for missing keys."""
    if not path.exists():
        return AppConfig()

    with open(path) as f:
        raw: dict[str, Any] = yaml.safe_load(f) or {}

    return AppConfig(**raw)
