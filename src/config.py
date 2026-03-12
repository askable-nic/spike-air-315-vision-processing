from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.models import PipelineConfig


DEFAULTS: dict[str, Any] = {
    "triage": {
        "enabled": True,
        "sample_fps": 5.0,
        "resolution_height": 480,
        "window_size_ms": 3000,
        "window_step_ms": 1000,
        "min_segment_duration_ms": 5000,
        "thresholds": {"idle": 0.005, "low": 0.02, "medium": 0.08},
        "fps_mapping": {"idle": 0.5, "low": 2.0, "medium": 4.0, "high": 10.0},
    },
    "analyse": {
        "model": "gemini-3-flash-preview",
        "temperature": 0.1,
        "max_concurrent": 5,
        "token_budget_per_segment": 50000,
        "tokens_per_frame": 1548,
        "context_frames": 2,
        "jpeg_quality": 85,
        "source": "unmod_website_test_video",
        "batch_gap_ms": 5000,
    },
    "merge": {
        "time_tolerance_ms": 2000,
        "similarity_threshold": 0.7,
        "discard_context_events": True,
    },
    "observe": {
        "enabled": False,
        "visual_change_driven": False,
        "cursor_tracking_enabled": True,
        "change_detect_fps": 4.0,
        "change_pixel_threshold": 20,
        "change_min_area_px": 1000,
        "change_blur_kernel": 5,
        "change_morph_kernel": 5,
        "scene_change_area_threshold": 0.3,
        "continuous_change_max_duration_ms": 3000,
        "cursor_stop_min_ms": 300,
        "cursor_stop_radius_px": 15.0,
        "moment_merge_gap_ms": 500,
        "token_budget_per_minute": 50000,
        "tokens_full_frame": 1600,
        "tokens_roi_pair": 750,
        "tokens_roi_single": 300,
        "roi_min_size": 256,
        "moment_categories": [
            "scene_change", "pre_scene_change", "interaction", "scroll",
            "continuous", "cursor_stop", "cursor_only", "baseline",
        ],
        "min_visual_change_duration_ms": 0,
        "max_moments_per_minute": 0,
        "moment_sample_interval_ms": 0,
        "moment_max_frames": 0,
        "tracking_fps": 5.0,
        "tracking_base_fps": 2.0,
        "tracking_peak_fps": 15.0,
        "tracking_displacement_threshold_px": 30.0,
        "tracking_active_padding_ms": 500,
        "resolution_height": 720,
        "template_scales": [0.8, 1.0, 1.25, 1.5],
        "match_threshold": 0.6,
        "early_exit_threshold": 0.9,
        "max_interpolation_gap_ms": 500,
        "smooth_window": 3,
        "smooth_displacement_threshold": 50.0,
        "flow_fps": 2.0,
        "flow_grid_step": 20,
        "flow_window_size_ms": 1000,
        "flow_window_step_ms": 500,
        "hover_min_ms": 300,
        "hover_max_ms": 2000,
        "hover_radius_px": 15.0,
        "dwell_min_ms": 2000,
        "dwell_radius_px": 20.0,
        "thrash_window_ms": 1000,
        "thrash_min_direction_changes": 4,
        "thrash_min_speed_px_per_sec": 500.0,
        "thrash_angle_threshold_deg": 90.0,
        "click_stop_max_ms": 200,
        "click_stop_radius_px": 5.0,
        "click_min_confidence": 0.3,
        "scroll_min_flow_uniformity": 0.6,
        "scroll_min_magnitude": 3.0,
        "hesitation_min_ms": 500,
        "hesitation_max_ms": 2000,
        "hesitation_radius_px": 10.0,
        "roi_size": 512,
        "roi_padding": 64,
        "visual_scan_gap_ms": 3000,
        "visual_scan_fps": 1.0,
        "visual_change_threshold": 0.03,
        "baseline_max_gap_ms": 5000,
        "frame_dedup_ms": 200,
    },
}


def deep_merge(base: dict, overlay: dict) -> dict:
    """Recursively merge overlay into base, returning a new dict. Neither input is mutated."""
    result = dict(base)
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_yaml(path: Path) -> dict:
    """Load a YAML file, returning an empty dict if the file doesn't exist."""
    if not path.exists():
        return {}
    with open(path) as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def _expand_dotted_overrides(overrides: tuple[str, ...]) -> dict:
    """Expand dotted key=value pairs into nested dicts.

    Example: ("triage.sample_fps=3",) -> {"triage": {"sample_fps": 3}}
    """
    result: dict = {}
    for item in overrides:
        key, _, raw_value = item.partition("=")
        if not key or not raw_value:
            continue
        value: Any
        if raw_value.lower() in ("true", "false"):
            value = raw_value.lower() == "true"
        else:
            try:
                value = int(raw_value)
            except ValueError:
                try:
                    value = float(raw_value)
                except ValueError:
                    value = raw_value

        parts = key.split(".")
        node = result
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
    return result


def resolve_config(
    branch: str,
    iteration: int,
    cli_overrides: tuple[str, ...] = (),
    base_dir: Path = Path("."),
) -> PipelineConfig:
    """Apply 4-layer config precedence: defaults -> branch YAML -> iteration YAML -> CLI overrides."""
    experiments_dir = base_dir / "experiments"

    branch_config = load_yaml(experiments_dir / branch / "config.yaml")
    iteration_config = load_yaml(experiments_dir / branch / str(iteration) / "config.yaml")
    cli_config = _expand_dotted_overrides(cli_overrides)

    merged = deep_merge(DEFAULTS, branch_config)
    merged = deep_merge(merged, iteration_config)
    merged = deep_merge(merged, cli_config)

    return PipelineConfig(**merged)
