from __future__ import annotations

import json
import subprocess
from pathlib import Path

import cv2
import numpy as np

from src.models import ChangeRegion, VideoMetadata, VisualChangeFrame


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
    timestamps are correct even for variable-frame-rate files like VP8/WebM.
    Decodes one frame per ``1000/fps`` ms interval within the range.

    Returns a tuple of (timestamp_ms, frame_array) pairs.
    """
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {path}")

    try:
        start_ms = start_sec * 1000
        end_ms = end_sec * 1000
        interval_ms = 1000.0 / fps

        # No seek — walk from the start so PTS-based timing is correct even
        # for variable-frame-rate containers (VP8/WebM).  For typical screen
        # recordings (~3 000 frames) the sequential grab is negligible.
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


def extract_frames_at_timestamps(
    path: Path,
    timestamps_ms: tuple[float, ...],
    scale_height: int | None = None,
) -> tuple[tuple[float, np.ndarray], ...]:
    """Extract frames at specific timestamps (ms) from a video.

    Uses container PTS (CAP_PROP_POS_MSEC) for positioning, so timestamps
    are correct even for variable-frame-rate files.  Walks forward through
    the video and decodes when PTS is within tolerance of a target.
    """
    if not timestamps_ms:
        return ()

    sorted_targets = sorted(timestamps_ms)

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {path}")

    try:
        # Walk from the start (no seek — unreliable for VFR/WebM) and decode
        # the frame closest to each target.  Sequential grab is fast (~3k
        # frames for a 5-min screen recording).
        frames: list[tuple[float, np.ndarray]] = []
        target_idx = 0
        prev_ms: float = -1.0
        prev_frame: np.ndarray | None = None

        while target_idx < len(sorted_targets):
            ret = cap.grab()
            if not ret:
                # End of video — emit previous frame for remaining target
                if prev_frame is not None:
                    frames.append((sorted_targets[target_idx], prev_frame))
                break

            current_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
            target_ms = sorted_targets[target_idx]

            if current_ms < target_ms:
                # Haven't reached target yet — snapshot this frame as candidate
                ret2, frame = cap.retrieve()
                if ret2:
                    if scale_height is not None and frame.shape[0] != scale_height:
                        aspect = frame.shape[1] / frame.shape[0]
                        new_width = int(scale_height * aspect)
                        frame = cv2.resize(frame, (new_width, scale_height))
                    prev_ms = current_ms
                    prev_frame = frame
                continue

            # current_ms >= target_ms — pick the closer of prev and current
            ret2, frame = cap.retrieve()
            if ret2:
                if scale_height is not None and frame.shape[0] != scale_height:
                    aspect = frame.shape[1] / frame.shape[0]
                    new_width = int(scale_height * aspect)
                    frame = cv2.resize(frame, (new_width, scale_height))
            else:
                frame = prev_frame

            if prev_frame is not None and abs(prev_ms - target_ms) < abs(current_ms - target_ms):
                chosen = prev_frame
            else:
                chosen = frame

            if chosen is not None:
                frames.append((target_ms, chosen))

            target_idx += 1
            prev_ms = current_ms
            prev_frame = frame

            # Handle consecutive targets that this same frame covers
            while target_idx < len(sorted_targets) and current_ms >= sorted_targets[target_idx]:
                frames.append((sorted_targets[target_idx], frame))
                target_idx += 1

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


def detect_visual_changes(
    path: Path,
    fps: float,
    pixel_threshold: int = 20,
    min_area_px: int = 1000,
    blur_kernel: int = 5,
    morph_kernel: int = 5,
    scale_height: int | None = None,
) -> tuple[VisualChangeFrame, ...]:
    """Detect visual changes between consecutive frames extracted at the given FPS.

    For each consecutive frame pair:
    - Grayscale → absdiff → GaussianBlur → threshold → morphological close
    - connectedComponentsWithStats to find change regions
    - Emit VisualChangeFrame for pairs with qualifying regions (area >= min_area_px)
    """
    meta = get_video_metadata(path)
    total_end = meta.duration_ms / 1000.0
    frames = extract_frames(path, 0.0, total_end, fps, scale_height=scale_height)

    if len(frames) < 2:
        return ()

    frame_h, frame_w = frames[0][1].shape[:2]
    frame_area = frame_w * frame_h

    results: list[VisualChangeFrame] = []

    for i in range(len(frames) - 1):
        ts_a, frame_a = frames[i]
        ts_b, frame_b = frames[i + 1]

        gray_a = cv2.cvtColor(frame_a, cv2.COLOR_BGR2GRAY) if len(frame_a.shape) == 3 else frame_a
        gray_b = cv2.cvtColor(frame_b, cv2.COLOR_BGR2GRAY) if len(frame_b.shape) == 3 else frame_b

        diff = cv2.absdiff(gray_a, gray_b)
        blurred = cv2.GaussianBlur(diff, (blur_kernel, blur_kernel), 0)
        _, binary = cv2.threshold(blurred, pixel_threshold, 255, cv2.THRESH_BINARY)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (morph_kernel, morph_kernel))
        closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        num_labels, labels, stats, _centroids = cv2.connectedComponentsWithStats(closed)

        regions: list[ChangeRegion] = []
        total_changed = 0

        # Label 0 is background, skip it
        for label_idx in range(1, num_labels):
            area = int(stats[label_idx, cv2.CC_STAT_AREA])
            if area < min_area_px:
                continue

            x = int(stats[label_idx, cv2.CC_STAT_LEFT])
            y = int(stats[label_idx, cv2.CC_STAT_TOP])
            w = int(stats[label_idx, cv2.CC_STAT_WIDTH])
            h = int(stats[label_idx, cv2.CC_STAT_HEIGHT])

            # Mean magnitude within the component
            component_mask = (labels == label_idx).astype(np.uint8)
            mean_mag = float(cv2.mean(diff, mask=component_mask)[0])

            regions.append(ChangeRegion(
                x=x, y=y, width=w, height=h,
                area_px=area, mean_magnitude=mean_mag,
            ))
            total_changed += area

        if regions:
            results.append(VisualChangeFrame(
                timestamp_a_ms=ts_a,
                timestamp_b_ms=ts_b,
                regions=tuple(regions),
                total_changed_area_px=total_changed,
                frame_area_fraction=total_changed / frame_area if frame_area > 0 else 0.0,
            ))

    return tuple(results)
