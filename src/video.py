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

    Uses sequential grab/retrieve to avoid expensive keyframe seeks on
    codecs like VP8/VP9 (webm).  Only decodes frames at the target interval.

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

        # Seek to start (single seek is fine)
        if start_frame > 0:
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        frames: list[tuple[float, np.ndarray]] = []
        current_frame = start_frame

        while current_frame <= end_frame:
            ret = cap.grab()
            if not ret:
                break

            if (current_frame - start_frame) % frame_interval == 0:
                ret2, frame = cap.retrieve()
                if not ret2:
                    current_frame += 1
                    continue

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


def compute_optical_flow(
    frame_a: np.ndarray,
    frame_b: np.ndarray,
    grid_step: int = 20,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Sparse Lucas-Kanade optical flow on a regular grid.

    Returns (points, displacements, status) where:
    - points: Nx2 array of grid point coordinates
    - displacements: Nx2 array of (dx, dy) displacements
    - status: Nx1 array of tracking status (1=found, 0=lost)
    """
    gray_a = cv2.cvtColor(frame_a, cv2.COLOR_BGR2GRAY) if len(frame_a.shape) == 3 else frame_a
    gray_b = cv2.cvtColor(frame_b, cv2.COLOR_BGR2GRAY) if len(frame_b.shape) == 3 else frame_b

    h, w = gray_a.shape[:2]
    ys = np.arange(grid_step // 2, h, grid_step)
    xs = np.arange(grid_step // 2, w, grid_step)
    grid = np.array([(x, y) for y in ys for x in xs], dtype=np.float32).reshape(-1, 1, 2)

    if len(grid) == 0:
        empty = np.empty((0, 2), dtype=np.float32)
        return empty, empty, np.empty((0, 1), dtype=np.uint8)

    lk_params = dict(
        winSize=(15, 15),
        maxLevel=2,
        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03),
    )

    next_pts, status, _err = cv2.calcOpticalFlowPyrLK(gray_a, gray_b, grid, None, **lk_params)

    points = grid.reshape(-1, 2)
    displacements = (next_pts.reshape(-1, 2) - points)
    return points, displacements, status.reshape(-1, 1)


def crop_frame(
    frame: np.ndarray,
    x: int,
    y: int,
    width: int,
    height: int,
) -> np.ndarray:
    """Crop a frame with boundary clamping."""
    h, w = frame.shape[:2]
    x0 = max(0, min(x, w - 1))
    y0 = max(0, min(y, h - 1))
    x1 = max(0, min(x + width, w))
    y1 = max(0, min(y + height, h))
    return frame[y0:y1, x0:x1]
