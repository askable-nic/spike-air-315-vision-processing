from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel


EventType = Literal[
    "click", "hover", "navigate", "input_text", "select",
    "dwell", "cursor_thrash", "scroll", "drag", "hesitate", "change_ui_state",
]


class VideoMetadata(BaseModel, frozen=True):
    duration_ms: float
    fps: float
    width: int
    height: int


class VideoSegment(BaseModel, frozen=True):
    index: int
    start_ms: float
    end_ms: float
    overlap_start_ms: float
    overlap_end_ms: float
    path: Path


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
