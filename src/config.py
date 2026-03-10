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
    },
    "merge": {
        "time_tolerance_ms": 2000,
        "similarity_threshold": 0.7,
        "discard_context_events": True,
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
