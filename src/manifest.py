from __future__ import annotations

import json
from pathlib import Path

from src.models import SessionManifest


def load_manifest(path: Path) -> tuple[SessionManifest, ...]:
    """Parse manifest.json into a tuple of SessionManifest models."""
    with open(path) as f:
        data = json.load(f)
    return tuple(SessionManifest(**entry) for entry in data)


def save_manifest(path: Path, sessions: tuple[SessionManifest, ...]) -> None:
    """Write manifest back to JSON."""
    with open(path, "w") as f:
        json.dump([s.model_dump() for s in sessions], f, indent=2)


def resolve_video_path(session: SessionManifest, input_dir: Path) -> Path:
    """Resolve the screen track video path, preferring the normalized version."""
    if session.data.normalizedScreenTrack:
        normalized = input_dir / session.data.normalizedScreenTrack
        if normalized.exists():
            return normalized
    return input_dir / session.data.screenTrack
