from __future__ import annotations

import logging
import os
import shutil
import sys
from pathlib import Path

import click
from dotenv import load_dotenv

from vex_extract.config import load_config
from vex_extract.pipeline import STAGES, run_pipeline

_SKIPPABLE = ("cursor", "flow", "segment", "prompt", "gemini", "merge")


@click.command()
@click.option("--video", required=True, type=click.Path(exists=True, path_type=Path), help="Path to screen track video")
@click.option("--offset", required=True, type=int, help="screenTrackStartOffset in milliseconds")
@click.option("--config", "config_path", default=None, type=click.Path(path_type=Path), help="Path to config YAML")
@click.option(
    "--stop-after",
    type=click.Choice(STAGES, case_sensitive=False),
    default=None,
    help="Run the pipeline up to and including this stage, then stop.",
)
@click.option(
    "--skip",
    "skip_stages",
    type=click.Choice(_SKIPPABLE, case_sensitive=False),
    multiple=True,
    help="Skip a stage (repeatable). Downstream stages degrade gracefully.",
)
def cli(
    video: Path,
    offset: int,
    config_path: Path | None,
    stop_after: str | None,
    skip_stages: tuple[str, ...],
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

    \b
    Examples:
      # Run only CV stages (no Gemini cost):
      python -m vex_extract --video v.mp4 --offset 0 --stop-after flow

      # Prepare everything including prompts, but don't call Gemini:
      python -m vex_extract --video v.mp4 --offset 0 --stop-after prompt

      # Full pipeline but skip cursor tracking:
      python -m vex_extract --video v.mp4 --offset 0 --skip cursor

      # Skip all CV, just run Gemini analysis:
      python -m vex_extract --video v.mp4 --offset 0 --skip cursor --skip flow
    """
    app_root = Path(__file__).resolve().parent.parent
    load_dotenv(app_root / ".env")

    if config_path is None:
        config_path = app_root / "config.yaml"
    config = load_config(config_path)

    skip = frozenset(skip_stages)

    # Only require API key if gemini stage will actually run
    needs_gemini = "gemini" not in skip and (
        stop_after is None or STAGES.index(stop_after) >= STAGES.index("gemini")
    )
    if needs_gemini:
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
        stop_after=stop_after,
        skip=skip,
    )

    click.echo(f"\nOutput: {output_dir}")
