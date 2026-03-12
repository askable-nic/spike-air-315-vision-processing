"""Verify effective frame rate and resolution of baseline Gemini requests.

Back-calculates from token usage to determine whether Gemini is actually
processing video at the requested FPS and what resolution it's using.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

BASELINES_DIR = Path(__file__).resolve().parent.parent / "baselines"

# Known Gemini token-per-frame constants for different resolutions
# (from Gemini docs: each video frame is treated as an image)
TOKENS_PER_FRAME_ESTIMATES = {
    "258": 258,   # standard Gemini video frame
    "263": 263,    # estimate used in _estimate_tokens
}


def probe_video(path: Path) -> dict | None:
    if not path.exists():
        return None
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", "-show_streams", "-count_frames", str(path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    data = json.loads(result.stdout)
    fmt = data.get("format", {})
    vs = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    duration = float(fmt.get("duration", 0))
    nb_frames = int(vs.get("nb_read_frames", vs.get("nb_frames", 0)))
    width = int(vs.get("width", 0))
    height = int(vs.get("height", 0))
    return {
        "duration_s": duration,
        "nb_frames": nb_frames,
        "actual_fps": nb_frames / duration if duration > 0 else 0,
        "width": width,
        "height": height,
    }


def main() -> None:
    metadata_paths = sorted(BASELINES_DIR.glob("*/artifacts/run_metadata.json"))

    print("=" * 120)
    print("Baseline FPS & Token Verification")
    print("=" * 120)

    for meta_path in metadata_paths:
        with open(meta_path) as f:
            meta = json.load(f)

        session = meta["session"]
        requested_fps = meta["config"]["video_fps"]
        segments = meta["segments"]
        artifacts_dir = meta_path.parent

        print(f"\n{'─' * 120}")
        print(f"Session: {session}  |  Requested FPS: {requested_fps}  |  Segments: {len(segments)}")
        print(f"{'─' * 120}")
        print(
            f"{'Seg':>3}  {'Duration':>8}  {'Resolution':>12}  "
            f"{'Frames':>7}  {'NativeFPS':>9}  "
            f"{'InTokens':>10}  "
            f"{'@258t/f':>10}  {'@258fps':>8}  "
            f"{'@263t/f':>10}  {'@263fps':>8}  "
            f"{'Prompt~':>8}"
        )

        total_input_tokens = 0
        total_duration_s = 0
        total_frames_at_258 = 0
        total_frames_at_263 = 0

        for seg in segments:
            seg_video = artifacts_dir / f"segment_{seg['index']:03d}" / "video.mp4"
            video_info = probe_video(seg_video)

            input_tokens = seg["input_tokens"]
            total_input_tokens += input_tokens

            if video_info:
                dur = video_info["duration_s"]
                total_duration_s += dur
                res = f"{video_info['width']}x{video_info['height']}"
                native_fps = video_info["actual_fps"]
                nb_frames = video_info["nb_frames"]

                # Back-calculate frames from tokens, subtracting estimated prompt overhead
                # Prompt overhead: system prompt + schema ~ a few thousand tokens
                # Try different prompt overhead estimates
                prompt_overhead = input_tokens % 258 if input_tokens % 258 < 3000 else 0
                frames_258 = input_tokens / 258
                frames_263 = input_tokens / 263
                fps_258 = frames_258 / dur if dur > 0 else 0
                fps_263 = frames_263 / dur if dur > 0 else 0
                total_frames_at_258 += frames_258
                total_frames_at_263 += frames_263

                print(
                    f"{seg['index']:>3}  {dur:>7.1f}s  {res:>12}  "
                    f"{nb_frames:>7}  {native_fps:>9.1f}  "
                    f"{input_tokens:>10,}  "
                    f"{frames_258:>9.0f}f  {fps_258:>7.1f}  "
                    f"{frames_263:>9.0f}f  {fps_263:>7.1f}  "
                    f"{'':>8}"
                )
            else:
                print(
                    f"{seg['index']:>3}  {'?':>8}  {'?':>12}  "
                    f"{'?':>7}  {'?':>9}  "
                    f"{input_tokens:>10,}  "
                    f"{'?':>10}  {'?':>8}  "
                    f"{'?':>10}  {'?':>8}  "
                    f"{'?':>8}"
                )

        if total_duration_s > 0:
            avg_fps_258 = total_frames_at_258 / total_duration_s
            avg_fps_263 = total_frames_at_263 / total_duration_s
            print(f"\n  Summary: {total_input_tokens:,} total input tokens over {total_duration_s:.0f}s")
            print(f"  Effective FPS (assuming 258 tok/frame): {avg_fps_258:.1f}")
            print(f"  Effective FPS (assuming 263 tok/frame): {avg_fps_263:.1f}")
            print(f"  Requested FPS: {requested_fps}")
            expected_tokens_258 = total_duration_s * requested_fps * 258
            expected_tokens_263 = total_duration_s * requested_fps * 263
            print(f"  Expected tokens at {requested_fps}fps (@258): {expected_tokens_258:,.0f}  "
                  f"(actual is {total_input_tokens / expected_tokens_258 * 100:.0f}%)")
            print(f"  Expected tokens at {requested_fps}fps (@263): {expected_tokens_263:,.0f}  "
                  f"(actual is {total_input_tokens / expected_tokens_263 * 100:.0f}%)")


if __name__ == "__main__":
    main()
