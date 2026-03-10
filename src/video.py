from __future__ import annotations

import json
import subprocess
from pathlib import Path

import cv2
import numpy as np

from src.models import VideoMetadata


def get_video_metadata(path: Path) -> VideoMetadata:
    """Get video metadata via ffprobe."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    probe = json.loads(result.stdout)

    video_stream = next(
        (s for s in probe.get("streams", []) if s.get("codec_type") == "video"),
        None,
    )
    if video_stream is None:
        raise ValueError(f"No video stream found in {path}")

    duration_s = float(probe.get("format", {}).get("duration", 0))
    if duration_s == 0 and "duration" in video_stream:
        duration_s = float(video_stream["duration"])

    fps_parts = video_stream.get("r_frame_rate", "30/1").split("/")
    fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 else float(fps_parts[0])

    return VideoMetadata(
        duration_ms=duration_s * 1000,
        fps=fps,
        width=int(video_stream.get("width", 0)),
        height=int(video_stream.get("height", 0)),
    )


def extract_frames(
    path: Path,
    start_sec: float,
    end_sec: float,
    fps: float,
    scale_height: int | None = None,
) -> tuple[tuple[float, np.ndarray], ...]:
    """Extract frames from a video at given FPS within a time range.

    Returns a tuple of (timestamp_ms, frame_array) pairs.
    """
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {path}")

    try:
        source_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        start_frame = int(start_sec * source_fps)
        end_frame = int(end_sec * source_fps)
        frame_interval = max(1, int(source_fps / fps))

        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        frames: list[tuple[float, np.ndarray]] = []
        current_frame = start_frame

        while current_frame <= end_frame:
            ret, frame = cap.read()
            if not ret:
                break

            if (current_frame - start_frame) % frame_interval == 0:
                timestamp_ms = (current_frame / source_fps) * 1000

                if scale_height is not None and frame.shape[0] != scale_height:
                    aspect = frame.shape[1] / frame.shape[0]
                    new_width = int(scale_height * aspect)
                    frame = cv2.resize(frame, (new_width, scale_height))

                frames.append((timestamp_ms, frame))

            current_frame += 1

        return tuple(frames)
    finally:
        cap.release()


def compute_frame_diff(
    frame_a: np.ndarray,
    frame_b: np.ndarray,
) -> tuple[float, tuple[int, int, int, int] | None]:
    """Compute grayscale mean absolute diff normalised 0-1, plus bounding box of change region.

    Returns (magnitude, bbox) where bbox is (x, y, w, h) or None if no change.
    """
    gray_a = cv2.cvtColor(frame_a, cv2.COLOR_BGR2GRAY) if len(frame_a.shape) == 3 else frame_a
    gray_b = cv2.cvtColor(frame_b, cv2.COLOR_BGR2GRAY) if len(frame_b.shape) == 3 else frame_b

    diff = cv2.absdiff(gray_a, gray_b)
    magnitude = float(np.mean(diff) / 255.0)

    _, thresh = cv2.threshold(diff, 15, 255, cv2.THRESH_BINARY)
    coords = cv2.findNonZero(thresh)

    bbox: tuple[int, int, int, int] | None = None
    if coords is not None:
        x, y, w, h = cv2.boundingRect(coords)
        bbox = (x, y, w, h)

    return magnitude, bbox


def encode_jpeg(frame: np.ndarray, quality: int = 85) -> bytes:
    """Encode a frame as JPEG bytes."""
    success, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not success:
        raise ValueError("Failed to encode frame as JPEG")
    return bytes(buffer)
