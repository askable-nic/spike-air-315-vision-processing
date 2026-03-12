"""Populate fullSessionDurationMs and screenTrackDurationMs in manifest.json."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


INPUT_DIR = Path(__file__).resolve().parent.parent / "input_data"
MANIFEST_PATH = INPUT_DIR / "manifest.json"


def probe_duration_ms(video_path: Path) -> float | None:
    """Return video duration in milliseconds via ffprobe, or None if unavailable."""
    if not video_path.exists():
        print(f"  WARNING: {video_path} not found")
        return None
    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", str(video_path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  WARNING: ffprobe failed for {video_path}")
        return None
    probe = json.loads(result.stdout)
    duration_s = float(probe.get("format", {}).get("duration", 0))
    if duration_s == 0:
        video_stream = next(
            (s for s in probe.get("streams", []) if s.get("codec_type") == "video"),
            None,
        )
        if video_stream and "duration" in video_stream:
            duration_s = float(video_stream["duration"])
    return round(duration_s * 1000, 1) if duration_s > 0 else None


def main() -> None:
    with open(MANIFEST_PATH) as f:
        entries = json.load(f)

    for entry in entries:
        identifier = entry["identifier"]
        data = entry["data"]

        full_session_path = INPUT_DIR / data["fullSession"]
        screen_track_path = INPUT_DIR / data["screenTrack"]

        print(f"{identifier}:")
        full_dur = probe_duration_ms(full_session_path)
        screen_dur = probe_duration_ms(screen_track_path)
        print(f"  fullSession:  {full_dur} ms")
        print(f"  screenTrack:  {screen_dur} ms")

        entry["fullSessionDurationMs"] = full_dur
        entry["screenTrackDurationMs"] = screen_dur

    with open(MANIFEST_PATH, "w") as f:
        json.dump(entries, f, indent=2)
        f.write("\n")
    print(f"\nUpdated {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
