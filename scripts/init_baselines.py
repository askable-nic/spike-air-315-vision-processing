"""Generate initial baseline events from observe.json scene changes and scroll data.

Reads visual_changes and flow_events from an experiment's observe output,
converts them to the baseline annotation format, and writes to baselines/.

Usage:
    python -m scripts.init_baselines \
        --branch visual-change-driven --iteration 3 \
        --session travel_expert_veronika
"""
from __future__ import annotations

import json
from pathlib import Path

import click

from src.manifest import load_manifest
from src.models import FlowEvent, ObserveResult, SessionManifest, VisualChangeEvent


def visual_change_to_event(
    vc: VisualChangeEvent,
    manifest: SessionManifest,
    video_width: int,
    video_height: int,
) -> dict:
    offset = manifest.screenTrackStartOffset
    stored_start = vc.time_start_ms + offset
    stored_end = vc.time_end_ms + offset
    x, y, w, h = vc.bounding_box

    event: dict = {
        "type": "change_ui_state",
        "source": "manual_annotation",
        "time_start": round(stored_start, 1),
        "time_end": round(stored_end, 1),
        "description": "",
        "transcript_id": manifest.identifier,
        "study_id": manifest.studyId,
        "viewport_width": video_width,
        "viewport_height": video_height,
    }

    if vc.category == "scene_change":
        event["description"] = "Scene change"
    elif vc.category == "continuous_change":
        event["description"] = "Continuous change"
    elif vc.category == "local_change":
        event["description"] = "Local change"
        event["_metadata"] = {
            "interaction_target_bbox": {
                "x": x, "y": y, "width": w, "height": h,
            },
        }

    return event


def flow_event_to_event(
    fe: FlowEvent,
    manifest: SessionManifest,
    video_width: int,
    video_height: int,
) -> dict:
    offset = manifest.screenTrackStartOffset
    stored_start = fe.time_start_ms + offset
    stored_end = fe.time_end_ms + offset

    return {
        "type": "scroll",
        "source": "manual_annotation",
        "time_start": round(stored_start, 1),
        "time_end": round(stored_end, 1),
        "description": f"{fe.category} {fe.dominant_direction}",
        "transcript_id": manifest.identifier,
        "study_id": manifest.studyId,
        "viewport_width": video_width,
        "viewport_height": video_height,
    }


def build_baseline(
    observe: ObserveResult,
    manifest: SessionManifest,
    include_scene_changes: bool,
    include_local_changes: bool,
    include_continuous_changes: bool,
    include_scrolls: bool,
    min_scene_change_area: float,
) -> list[dict]:
    """Build baseline events from observe data."""
    from src.video import get_video_metadata
    from src.manifest import resolve_video_path

    video_path = resolve_video_path(manifest, Path("input_data"))
    if video_path.exists():
        meta = get_video_metadata(video_path)
        video_width, video_height = meta.width, meta.height
    else:
        video_width, video_height = 1920, 1080

    events: list[dict] = []

    for vc in observe.visual_changes:
        if vc.category == "scene_change" and include_scene_changes:
            if vc.peak_changed_area_fraction >= min_scene_change_area:
                events.append(visual_change_to_event(vc, manifest, video_width, video_height))
        elif vc.category == "local_change" and include_local_changes:
            events.append(visual_change_to_event(vc, manifest, video_width, video_height))
        elif vc.category == "continuous_change" and include_continuous_changes:
            events.append(visual_change_to_event(vc, manifest, video_width, video_height))

    if include_scrolls:
        for fe in observe.flow_events:
            if fe.category in ("scroll", "pan"):
                events.append(flow_event_to_event(fe, manifest, video_width, video_height))

    events.sort(key=lambda e: e["time_start"])
    return events


@click.command()
@click.option("--branch", "-b", required=True, help="Experiment branch name")
@click.option("--iteration", "-i", required=True, type=int, help="Iteration number")
@click.option("--session", "-s", multiple=True, help="Session ID(s) (default: all in experiment)")
@click.option("--no-scene-changes", is_flag=True, default=False, help="Exclude scene changes")
@click.option("--no-local-changes", is_flag=True, default=False, help="Exclude local changes")
@click.option("--no-continuous-changes", is_flag=True, default=False, help="Exclude continuous changes")
@click.option("--no-scrolls", is_flag=True, default=False, help="Exclude scroll/pan events")
@click.option("--min-scene-change-area", type=float, default=0.0, help="Min peak area fraction for scene changes (0-1)")
@click.option("--merge", is_flag=True, default=False, help="Merge with existing baseline instead of overwriting")
@click.option("--dry-run", is_flag=True, default=False, help="Print events without writing")
@click.option("--base-dir", type=click.Path(exists=True, path_type=Path), default=".", help="Project base directory")
def main(
    branch: str,
    iteration: int,
    session: tuple[str, ...],
    no_scene_changes: bool,
    no_local_changes: bool,
    no_continuous_changes: bool,
    no_scrolls: bool,
    min_scene_change_area: float,
    merge: bool,
    dry_run: bool,
    base_dir: Path,
):
    """Generate initial baseline events from observe.json scene changes and scroll data."""
    experiments_dir = base_dir / "experiments"
    baselines_dir = base_dir / "baselines"
    output_dir = experiments_dir / branch / str(iteration) / "output"

    if not output_dir.exists():
        click.echo(f"Output directory not found: {output_dir}")
        raise SystemExit(1)

    manifest = load_manifest(base_dir / "input_data" / "manifest.json")
    manifest_lookup = {s.identifier: s for s in manifest}

    # Discover sessions
    if session:
        session_ids = list(session)
    else:
        session_ids = sorted(
            d.name for d in output_dir.iterdir()
            if d.is_dir() and (d / "observe.json").exists()
        )

    if not session_ids:
        click.echo("No sessions found with observe.json output.")
        return

    for session_id in session_ids:
        observe_path = output_dir / session_id / "observe.json"
        if not observe_path.exists():
            click.echo(f"Skipping {session_id}: no observe.json")
            continue

        session_manifest = manifest_lookup.get(session_id)
        if session_manifest is None:
            click.echo(f"Skipping {session_id}: not in manifest")
            continue

        with open(observe_path) as f:
            observe = ObserveResult(**json.load(f))

        events = build_baseline(
            observe=observe,
            manifest=session_manifest,
            include_scene_changes=not no_scene_changes,
            include_local_changes=not no_local_changes,
            include_continuous_changes=not no_continuous_changes,
            include_scrolls=not no_scrolls,
            min_scene_change_area=min_scene_change_area,
        )

        # Summarise
        type_counts: dict[str, int] = {}
        for e in events:
            t = e["type"]
            type_counts[t] = type_counts.get(t, 0) + 1
        summary = ", ".join(f"{t}: {c}" for t, c in sorted(type_counts.items()))
        click.echo(f"{session_id}: {len(events)} events ({summary})")

        if dry_run:
            click.echo(json.dumps(events[:5], indent=2))
            if len(events) > 5:
                click.echo(f"  ... and {len(events) - 5} more")
            continue

        # Write or merge
        events_path = baselines_dir / session_id / "events.json"

        if merge and events_path.exists():
            with open(events_path) as f:
                existing = json.load(f)
            combined = existing + events
            combined.sort(key=lambda e: e["time_start"])
            events = combined
            click.echo(f"  Merged with {len(existing)} existing events -> {len(events)} total")

        events_path.parent.mkdir(parents=True, exist_ok=True)
        with open(events_path, "w") as f:
            json.dump(events, f, indent=2)
        click.echo(f"  Written to {events_path}")

    click.echo("Done.")


if __name__ == "__main__":
    main()
