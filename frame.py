"""Extract a single frame from a video and save as PNG for inspection.

Usage:
    python frame.py <video_path> <frame_or_timestamp> [--out path.png]

    frame_or_timestamp can be:
        123       — frame number (0-indexed)
        1.5s      — seconds into video
        1500ms    — milliseconds into video
        01:23     — mm:ss timestamp
        01:23.5   — mm:ss.fraction

Examples:
    python frame.py video.mp4 0           # first frame
    python frame.py video.mp4 100         # frame 100
    python frame.py video.mp4 5.2s        # 5.2 seconds in
    python frame.py video.mp4 1500ms      # 1500ms in
    python frame.py video.mp4 01:23       # 1 min 23 sec in
"""

import sys
import re
import cv2
import numpy as np
from pathlib import Path


def parse_position(raw: str, fps: float) -> float:
    """Parse a frame/timestamp string into milliseconds."""
    # mm:ss or mm:ss.f
    mm_ss = re.match(r"^(\d+):(\d+(?:\.\d+)?)$", raw)
    if mm_ss:
        minutes, seconds = float(mm_ss.group(1)), float(mm_ss.group(2))
        return (minutes * 60 + seconds) * 1000

    # milliseconds
    if raw.endswith("ms"):
        return float(raw[:-2])

    # seconds
    if raw.endswith("s"):
        return float(raw[:-1]) * 1000

    # bare number = frame index
    frame_num = int(raw)
    return (frame_num / fps) * 1000


def extract_frame(video_path: Path, position_ms: float) -> np.ndarray:
    """Extract a single frame at the given millisecond position."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    cap.set(cv2.CAP_PROP_POS_MSEC, position_ms)
    ok, frame = cap.read()
    actual_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
    cap.release()

    if not ok:
        raise RuntimeError(f"Failed to read frame at {position_ms}ms")

    print(f"Extracted frame at {actual_ms:.0f}ms (requested {position_ms:.0f}ms)")
    return frame


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    video_path = Path(sys.argv[1])
    position_raw = sys.argv[2]

    # Parse optional --out flag
    out_path = None
    if "--out" in sys.argv:
        idx = sys.argv.index("--out")
        out_path = Path(sys.argv[idx + 1])

    if not video_path.exists():
        print(f"Video not found: {video_path}")
        sys.exit(1)

    # Get fps for frame-number conversion
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration_ms = (total_frames / fps) * 1000 if fps > 0 else 0
    cap.release()

    print(f"Video: {video_path.name} ({width}x{height}, {fps:.1f}fps, {total_frames} frames, {duration_ms/1000:.1f}s)")

    position_ms = parse_position(position_raw, fps)

    frame = extract_frame(video_path, position_ms)

    if out_path is None:
        out_path = Path("/tmp") / f"frame_{video_path.stem}_{position_ms:.0f}ms.png"

    cv2.imwrite(str(out_path), frame)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
