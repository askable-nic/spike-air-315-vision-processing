from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from google.genai import types

from src.gemini import create_client, make_request
from src.log import log
from src.manifest import load_manifest, resolve_video_path
from src.prompts import fill_template
from src.video import crop_frame, encode_jpeg, extract_frames_at_timestamps


_ENRICH_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "frame_description": {"type": "STRING"},
        "description": {"type": "STRING"},
        "interaction_target": {"type": "STRING"},
        "page_title": {"type": "STRING"},
        "page_location": {"type": "STRING"},
    },
    "required": ["frame_description", "description"],
}

_MODEL = "gemini-3-flash-preview"

_TYPE_INSTRUCTIONS: dict[str, str] = {
    "click": (
        "This is a CLICK event. Focus on identifying the exact UI element being clicked — "
        "its visible label, icon, or role (button, link, menu item, checkbox, etc.). "
        "If a cropped close-up is provided, use it to read the element's label precisely."
    ),
    "hover": (
        "This is a HOVER event. The cursor is lingering over a UI element. "
        "Identify what the user is hovering on — its label, type, and context. "
        "If a cropped close-up is provided, use it to identify the element precisely."
    ),
    "select": (
        "This is a SELECT event. The user is selecting from a dropdown, picker, or making a selection. "
        "Identify the control being used and what is being selected. "
        "If a cropped close-up is provided, use it to read the options or selected value."
    ),
    "navigate": (
        "This is a NAVIGATE event — a page navigation or tab switch. "
        "Pay special attention to the page title (browser tab or page heading) and "
        "the URL in the address bar. Describe the new page that has loaded."
    ),
    "input_text": (
        "This is an INPUT_TEXT event. The user is typing into a form field or text area. "
        "Identify the field label, placeholder text, and any visible typed content. "
        "Describe the form context (what form, what step)."
    ),
    "scroll": (
        "This is a SCROLL event. Describe the content being scrolled through — "
        "the page area, content type (search results, article, product listings, etc.), "
        "and what is currently visible on screen."
    ),
    "change_ui_state": (
        "This is a CHANGE_UI_STATE event — a visible UI change not directly caused by user action. "
        "Identify what changed: loading states, modals appearing/disappearing, tab switches, "
        "dynamic content loading, animations, popups, or layout shifts."
    ),
    "cursor_thrash": (
        "This is a CURSOR_THRASH event — rapid, unfocused cursor movement. "
        "Describe the area where the thrashing occurs and the surrounding content/UI context."
    ),
    "dwell": (
        "This is a DWELL event — the user paused to read or examine content. "
        "Describe what content is in the area of focus and its surrounding context."
    ),
    "hesitate": (
        "This is a HESITATE event — a brief pause before an action, suggesting uncertainty. "
        "Describe the area and surrounding context where the hesitation occurs."
    ),
    "drag": (
        "This is a DRAG event. Identify the element being dragged, "
        "and describe the start and end context of the drag operation."
    ),
}

_PROTECTED_FIELDS = frozenset({
    "_metadata", "source", "type", "time_start", "time_end",
    "cursor_position", "viewport_width", "viewport_height",
    "transcript_id", "study_id",
})

_CROP_PADDING = 32


@dataclass(frozen=True)
class EnrichmentNeeds:
    index: int
    needs_frame_description: bool
    needs_description: bool
    needs_interaction_target: bool
    needs_page_title: bool
    needs_page_location: bool
    has_bbox: bool

    @property
    def needs_any(self) -> bool:
        return self.needs_frame_description


def _needs_description_improvement(desc: Any) -> bool:
    if not isinstance(desc, str):
        return True
    stripped = desc.strip()
    return len(stripped) == 0 or len(stripped) < 15


def _classify_enrichment_needs(index: int, event: dict) -> EnrichmentNeeds:
    has_frame_desc = bool(event.get("frame_description", ""))
    has_desc = not _needs_description_improvement(event.get("description", ""))
    has_target = bool(event.get("interaction_target", ""))
    has_title = bool(event.get("page_title", ""))
    has_location = bool(event.get("page_location", ""))
    has_bbox = bool(
        event.get("_metadata", {}).get("interaction_target_bbox")
    )

    return EnrichmentNeeds(
        index=index,
        needs_frame_description=not has_frame_desc,
        needs_description=not has_desc,
        needs_interaction_target=not has_target,
        needs_page_title=not has_title,
        needs_page_location=not has_location,
        has_bbox=has_bbox,
    )


def _build_enrichment_prompt(event: dict, needs: EnrichmentNeeds, template: str) -> str:
    event_type = event.get("type", "unknown")
    type_instructions = _TYPE_INSTRUCTIONS.get(event_type, (
        f"This is a {event_type.upper()} event. "
        "Describe the screen context and what is happening at this moment."
    ))

    cursor = event.get("cursor_position", {})
    cursor_str = f"x={cursor.get('x', '?')}, y={cursor.get('y', '?')}" if cursor else "not recorded"

    return fill_template(template, {
        "event_type": event_type,
        "timestamp_ms": str(event.get("time_start", 0)),
        "current_description": event.get("description", "") or "(empty)",
        "current_interaction_target": event.get("interaction_target", "") or "(empty)",
        "cursor_position": cursor_str,
        "type_instructions": type_instructions,
    })


async def _enrich_single_event(
    client: Any,
    event: dict,
    needs: EnrichmentNeeds,
    frame: Any,
    template: str,
    semaphore: asyncio.Semaphore,
) -> dict | None:
    async with semaphore:
        try:
            prompt_text = _build_enrichment_prompt(event, needs, template)

            content_parts: list[Any] = []

            # Full frame
            jpeg_bytes = encode_jpeg(frame)
            content_parts.append(
                types.Part.from_bytes(data=jpeg_bytes, mime_type="image/jpeg")
            )

            # Cropped close-up if bbox available
            if needs.has_bbox:
                bbox = event["_metadata"]["interaction_target_bbox"]
                cropped = crop_frame(
                    frame,
                    x=bbox["x"] - _CROP_PADDING,
                    y=bbox["y"] - _CROP_PADDING,
                    width=bbox["width"] + 2 * _CROP_PADDING,
                    height=bbox["height"] + 2 * _CROP_PADDING,
                )
                crop_jpeg = encode_jpeg(cropped)
                content_parts.append(
                    types.Part.from_bytes(data=crop_jpeg, mime_type="image/jpeg")
                )

            content_parts.append(prompt_text)

            result = await make_request(
                client=client,
                model=_MODEL,
                system_prompt="You are a UX research analyst examining screenshots from screen recordings.",
                content_parts=content_parts,
                response_schema=_ENRICH_SCHEMA,
            )

            return json.loads(result["text"])

        except Exception as e:
            log(f"  Failed to enrich event {needs.index}: {e}")
            return None


def _merge_enrichment(event: dict, enrichment: dict) -> dict:
    merged = {**event}

    # Always set frame_description
    if enrichment.get("frame_description"):
        merged["frame_description"] = enrichment["frame_description"]

    # Only improve description if current one is weak
    if _needs_description_improvement(event.get("description", "")):
        new_desc = enrichment.get("description", "")
        if new_desc and not _needs_description_improvement(new_desc):
            merged["description"] = new_desc

    # Only set if currently missing
    if not event.get("interaction_target") and enrichment.get("interaction_target"):
        merged["interaction_target"] = enrichment["interaction_target"]

    if not event.get("page_title") and enrichment.get("page_title"):
        merged["page_title"] = enrichment["page_title"]

    if not event.get("page_location") and enrichment.get("page_location"):
        merged["page_location"] = enrichment["page_location"]

    return merged


async def enrich_session(
    session_id: str,
    events: list[dict],
    video_path: Path,
    screen_track_start_offset: float,
    template: str,
    max_concurrent: int = 5,
    dry_run: bool = False,
) -> list[dict]:
    """Enrich baseline events for a single session.

    Returns the full events list with enriched fields merged in.
    """
    # Classify needs for each event
    needs_list: list[EnrichmentNeeds] = []
    for i, event in enumerate(events):
        needs = _classify_enrichment_needs(i, event)
        if needs.needs_any:
            needs_list.append(needs)

    log(f"  {session_id}: {len(needs_list)}/{len(events)} events need enrichment")

    if dry_run:
        _print_dry_run_summary(session_id, events, needs_list)
        return events

    if not needs_list:
        return events

    # Extract all frames in one video pass
    timestamps_ms = tuple(
        max(0.0, events[n.index].get("time_start", 0) - screen_track_start_offset)
        for n in needs_list
    )
    log(f"  Extracting {len(timestamps_ms)} frames...")
    frames = extract_frames_at_timestamps(video_path, timestamps_ms)

    # Build timestamp → frame lookup
    frame_lookup: dict[float, Any] = {ts: frame for ts, frame in frames}

    client = create_client()
    semaphore = asyncio.Semaphore(max_concurrent)

    # Run enrichment concurrently
    tasks = []
    for needs, target_ts in zip(needs_list, timestamps_ms):
        frame = frame_lookup.get(target_ts)
        if frame is None:
            log(f"  Skipping event {needs.index}: no frame extracted")
            continue
        tasks.append((
            needs,
            _enrich_single_event(
                client=client,
                event=events[needs.index],
                needs=needs,
                frame=frame,
                template=template,
                semaphore=semaphore,
            ),
        ))

    log(f"  Enriching {len(tasks)} events (concurrency={max_concurrent})...")
    results = await asyncio.gather(*(t[1] for t in tasks))

    # Merge results
    enriched_events = list(events)
    enriched_count = 0
    for (needs, _), enrichment in zip(tasks, results):
        if enrichment is not None:
            enriched_events[needs.index] = _merge_enrichment(
                enriched_events[needs.index], enrichment
            )
            enriched_count += 1

    log(f"  {session_id}: enriched {enriched_count}/{len(tasks)} events")
    return enriched_events


def _print_dry_run_summary(
    session_id: str,
    events: list[dict],
    needs_list: list[EnrichmentNeeds],
) -> None:
    print(f"\n  Dry-run summary for {session_id}:")
    print(f"    Total events: {len(events)}")
    print(f"    Need enrichment: {len(needs_list)}")
    print(f"    Already enriched (have frame_description): {len(events) - len(needs_list)}")

    field_counts = {
        "frame_description": sum(1 for n in needs_list if n.needs_frame_description),
        "description": sum(1 for n in needs_list if n.needs_description),
        "interaction_target": sum(1 for n in needs_list if n.needs_interaction_target),
        "page_title": sum(1 for n in needs_list if n.needs_page_title),
        "page_location": sum(1 for n in needs_list if n.needs_page_location),
    }
    print("    Missing fields:")
    for field, count in field_counts.items():
        print(f"      {field}: {count}")

    type_counts: dict[str, int] = {}
    for n in needs_list:
        t = events[n.index].get("type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1
    print("    By event type:")
    for t, c in sorted(type_counts.items()):
        print(f"      {t}: {c}")

    bbox_count = sum(1 for n in needs_list if n.has_bbox)
    print(f"    Events with bbox (will send crop): {bbox_count}")
