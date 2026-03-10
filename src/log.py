from __future__ import annotations

from datetime import datetime, timezone


def log(msg: str) -> None:
    """Print a timestamped log line."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"{ts}: {msg}")
