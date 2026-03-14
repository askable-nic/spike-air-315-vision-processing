from __future__ import annotations

import json
import logging
import math
import subprocess
from pathlib import Path

import cv2
import numpy as np

from vex_extract.models import VideoMetadata, VideoSegment

logger = logging.getLogger(__name__)


def _probe_reference_dimensions(path: Path, duration_ms: float) -> tuple[int, int]:
    """Probe frame dimensions near the end of the video.

    Samples ~3s before the end to capture the likely settled aspect ratio,
    since window resizing tends to happen near the start of recordings.
    Falls back to stream-level dimensions if probing fails.
    """
    seek_sec = max(0, duration_ms / 1000.0 - 3.0)
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-select_streams", "v:0",
                "-show_entries", "frame=width,height",
                "-read_intervals", f"{seek_sec:.3f}%+#1",
                "-print_format", "json",
                str(path),
            ],
            capture_output=True, text=True, check=True,
        )
        frames = json.loads(result.stdout).get("frames", [])
        if frames:
            return int(frames[0]["width"]), int(frames[0]["height"])
    except (subprocess.CalledProcessError, KeyError, IndexError, ValueError):
        pass

    meta = get_video_metadata(path)
    return meta.width, meta.height


def normalize_video(
    input_path: Path,
    output_path: Path,
    target_pixels: int = 2_073_600,
) -> Path:
    """Re-encode video to consistent-resolution MP4 using ffmpeg.

    Determines the output aspect ratio from a frame near the end of the video.
    Output dimensions are derived from target_pixels so that portrait and
    landscape recordings are downsampled equally. Frames with a different
    aspect ratio are scaled to fit and letterboxed with black bars.
    """
    meta = get_video_metadata(input_path)
    ref_w, ref_h = _probe_reference_dimensions(input_path, meta.duration_ms)

    aspect = ref_w / ref_h
    out_h = int(math.sqrt(target_pixels / aspect))
    out_w = int(out_h * aspect)
    # libx264 requires even dimensions
    out_w += out_w % 2
    out_h += out_h % 2

    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(input_path),
            "-vf", (
                f"scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,"
                f"pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2:color=black"
            ),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-an",
            str(output_path),
        ],
        capture_output=True,
        check=True,
    )
    return output_path


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

    Uses container PTS timestamps (CAP_PROP_POS_MSEC) so that returned
    timestamps are correct even for variable-frame-rate files.
    """
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {path}")

    try:
        start_ms = start_sec * 1000
        end_ms = end_sec * 1000
        interval_ms = 1000.0 / fps

        frames: list[tuple[float, np.ndarray]] = []
        next_capture_ms = start_ms

        while True:
            ret = cap.grab()
            if not ret:
                break

            current_ms = cap.get(cv2.CAP_PROP_POS_MSEC)

            if current_ms > end_ms:
                break

            if current_ms >= next_capture_ms:
                ret2, frame = cap.retrieve()
                if not ret2:
                    continue

                if scale_height is not None and frame.shape[0] != scale_height:
                    aspect = frame.shape[1] / frame.shape[0]
                    new_width = int(scale_height * aspect)
                    frame = cv2.resize(frame, (new_width, scale_height))

                frames.append((current_ms, frame))
                next_capture_ms = current_ms + interval_ms

        return tuple(frames)
    finally:
        cap.release()


def compute_optical_flow(
    frame_a: np.ndarray,
    frame_b: np.ndarray,
    grid_step: int = 20,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Sparse Lucas-Kanade optical flow on a regular grid.

    Returns (points, displacements, status).
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


def compute_segments(
    duration_ms: float,
    max_segment_duration_ms: int,
    segment_overlap_ms: int,
    segments_dir: Path,
) -> tuple[VideoSegment, ...]:
    """Split a video duration into close-to-equal segments with overlaps."""
    n_segments = math.ceil(duration_ms / max_segment_duration_ms)
    if n_segments < 1:
        n_segments = 1
    base_duration = duration_ms / n_segments

    segments: list[VideoSegment] = []
    for i in range(n_segments):
        content_start = i * base_duration
        content_end = (i + 1) * base_duration

        actual_start = max(0.0, content_start - segment_overlap_ms) if i > 0 else 0.0
        actual_end = min(duration_ms, content_end + segment_overlap_ms) if i < n_segments - 1 else duration_ms

        overlap_start_ms = content_start - actual_start if i > 0 else 0.0
        overlap_end_ms = actual_end - content_end if i < n_segments - 1 else 0.0

        segments.append(VideoSegment(
            index=i,
            start_ms=actual_start,
            end_ms=actual_end,
            overlap_start_ms=overlap_start_ms,
            overlap_end_ms=overlap_end_ms,
            path=segments_dir / f"segment_{i:03d}.mp4",
        ))

    return tuple(segments)


def extract_segment(video_path: Path, segment: VideoSegment) -> Path:
    """Extract a video segment using ffmpeg -c copy."""
    start_sec = segment.start_ms / 1000.0
    end_sec = segment.end_ms / 1000.0

    segment.path.parent.mkdir(parents=True, exist_ok=True)

    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-ss", f"{start_sec:.3f}",
                "-to", f"{end_sec:.3f}",
                "-i", str(video_path),
                "-c", "copy",
                str(segment.path),
            ],
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        logger.info("Segment %d: -c copy failed, falling back to re-encode", segment.index)
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-ss", f"{start_sec:.3f}",
                "-to", f"{end_sec:.3f}",
                "-i", str(video_path),
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-an",
                str(segment.path),
            ],
            capture_output=True,
            check=True,
        )

    return segment.path
