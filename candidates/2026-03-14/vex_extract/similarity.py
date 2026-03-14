from __future__ import annotations

import difflib

from vex_extract.models import ResolvedEvent


def string_similarity(a: str, b: str) -> float:
    """Compute string similarity using SequenceMatcher (0-1)."""
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


def events_are_duplicates(
    e1: ResolvedEvent,
    e2: ResolvedEvent,
    time_tolerance_ms: float = 2000,
    similarity_threshold: float = 0.7,
) -> bool:
    """Check if two events are duplicates based on type, time overlap, and description similarity."""
    if e1.type != e2.type:
        return False

    time_overlap = (
        e1.time_start <= e2.time_end + time_tolerance_ms
        and e2.time_start <= e1.time_end + time_tolerance_ms
    )
    if not time_overlap:
        return False

    return string_similarity(e1.description, e2.description) >= similarity_threshold
