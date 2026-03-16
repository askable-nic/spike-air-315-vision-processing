from __future__ import annotations

import logging
import os
import shutil
import sys
from pathlib import Path

import click
from dotenv import load_dotenv

from vex_extract.config import load_config
from vex_extract.pipeline import run_pipeline


@click.command()
@click.option("--video", required=True, type=click.Path(exists=True, path_type=Path), help="Path to screen track video")
@click.option("--offset", required=True, type=int, help="screenTrackStartOffset in milliseconds")
@click.option("--config", "config_path", default=None, type=click.Path(path_type=Path), help="Path to config YAML")
def cli(
    video: Path,
    offset: int,
    config_path: Path | None,
) -> None:
    """Extract user interaction events from a screen recording video.

    \b
    Stages (in order):
      normalize  Normalize video to consistent resolution
      cursor     Two-pass adaptive cursor tracking
      flow       Optical flow analysis
      segment    Split video into segments for Gemini
      prompt     Render prompts and CV summaries (no API calls)
      gemini     Send segments to Gemini for event detection
      merge      Merge, deduplicate, and enrich events
    """
    app_root = Path(__file__).resolve().parent.parent
    load_dotenv(app_root / ".env")

    if config_path is None:
        config_path = app_root / "config.yaml"
    config = load_config(config_path)

    api_key_env = config.gemini.api_key_env
    if not os.environ.get(api_key_env):
        click.echo(f"Error: {api_key_env} environment variable is not set.", err=True)
        click.echo(f"Set it with: export {api_key_env}=your-key-here", err=True)
        sys.exit(1)

    if not shutil.which("ffmpeg"):
        click.echo("Error: ffmpeg not found on PATH. Install with: brew install ffmpeg", err=True)
        sys.exit(1)
    if not shutil.which("ffprobe"):
        click.echo("Error: ffprobe not found on PATH. Install with: brew install ffmpeg", err=True)
        sys.exit(1)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )

    output_dir = run_pipeline(
        video_path=video.resolve(),
        offset=offset,
        config=config,
        app_root=app_root,
    )

    click.echo(f"\nOutput: {output_dir}")
