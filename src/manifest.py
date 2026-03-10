from __future__ import annotations

import json
from pathlib import Path

from src.models import SessionManifest


def load_manifest(path: Path) -> tuple[SessionManifest, ...]:
    """Parse manifest.json into a tuple of SessionManifest models."""
    with open(path) as f:
        data = json.load(f)
    return tuple(SessionManifest(**entry) for entry in data)


def resolve_video_path(session: SessionManifest, input_dir: Path) -> Path:
    """Resolve the screen track video path for a session."""
    return input_dir / session.data.screenTrack
