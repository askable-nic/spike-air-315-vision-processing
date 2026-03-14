from __future__ import annotations

import math
from typing import NamedTuple

from vex_extract.models import CursorDetection, FlowWindow, VideoSegment


# ---------------------------------------------------------------------------
# Cursor rollup types and helpers
# ---------------------------------------------------------------------------

class _Span(NamedTuple):
    start_ms: float
    end_ms: float
    kind: str  # "not-detected" | "stationary" | "moved"
    x0: float | None
    y0: float | None
    x1: float | None  # only for "moved"
    y1: float | None  # only for "moved"


def _point_to_line_distance(
    px: float, py: float,
    x0: float, y0: float,
    x1: float, y1: float,
    line_len: float,
) -> float:
    """Perpendicular distance from (px, py) to the line through (x0,y0)-(x1,y1)."""
    return abs((y1 - y0) * px - (x1 - x0) * py + x1 * y0 - y1 * x0) / line_len


def _rollup_detected(
    detections: tuple[CursorDetection, ...],
    pos_tolerance_px: float = 1.0,
    confidence_tolerance: float = 0.1,
    collinear_tolerance_px: float = 5.0,
) -> tuple[_Span, ...]:
    """Roll up a contiguous run of detected entries into stationary/moved spans."""
    if not detections:
        return ()

    spans: list[_Span] = []
    i = 0
    n = len(detections)

    while i < n:
        anchor = detections[i]

        # Try stationary: extend while within tolerance of anchor
        j = i + 1
        while j < n:
            d = detections[j]
            if (abs(d.x - anchor.x) <= pos_tolerance_px
                    and abs(d.y - anchor.y) <= pos_tolerance_px
                    and abs(d.confidence - anchor.confidence) <= confidence_tolerance):
                j += 1
            else:
                break

        if j > i + 1:
            spans.append(_Span(
                start_ms=detections[i].timestamp_ms,
                end_ms=detections[j - 1].timestamp_ms,
                kind="stationary",
                x0=round(anchor.x, 1),
                y0=round(anchor.y, 1),
                x1=None,
                y1=None,
            ))
            i = j
            continue

        # Try straight-line movement: greedily extend while collinear
        best_k = i  # last index included in the line
        k = i + 1
        while k < n:
            x0, y0 = detections[i].x, detections[i].y
            x1, y1 = detections[k].x, detections[k].y
            line_len = math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2)

            if line_len < 1.0:
                break

            collinear = all(
                _point_to_line_distance(p.x, p.y, x0, y0, x1, y1, line_len)
                <= collinear_tolerance_px
                for p in detections[i + 1:k]
            )
            if collinear:
                best_k = k
                k += 1
            else:
                break

        if best_k > i:
            spans.append(_Span(
                start_ms=detections[i].timestamp_ms,
                end_ms=detections[best_k].timestamp_ms,
                kind="moved",
                x0=round(detections[i].x, 1),
                y0=round(detections[i].y, 1),
                x1=round(detections[best_k].x, 1),
                y1=round(detections[best_k].y, 1),
            ))
            i = best_k + 1
        else:
            # Single isolated point
            spans.append(_Span(
                start_ms=anchor.timestamp_ms,
                end_ms=anchor.timestamp_ms,
                kind="stationary",
                x0=round(anchor.x, 1),
                y0=round(anchor.y, 1),
                x1=None,
                y1=None,
            ))
            i += 1

    return tuple(spans)


def _rollup_trajectory(
    detections: tuple[CursorDetection, ...],
) -> tuple[_Span, ...]:
    """Roll up cursor detections into spans driven by the data, no fixed time windows."""
    if not detections:
        return ()

    spans: list[_Span] = []
    run_start = 0

    for idx in range(1, len(detections) + 1):
        if idx == len(detections) or detections[idx].detected != detections[run_start].detected:
            run = detections[run_start:idx]
            if not run[0].detected:
                spans.append(_Span(
                    start_ms=run[0].timestamp_ms,
                    end_ms=run[-1].timestamp_ms,
                    kind="not-detected",
                    x0=None, y0=None, x1=None, y1=None,
                ))
            else:
                spans.extend(_rollup_detected(run))
            run_start = idx

    return tuple(spans)


# ---------------------------------------------------------------------------
# Flow rollup
# ---------------------------------------------------------------------------

class _FlowSpan(NamedTuple):
    start_ms: float
    end_ms: float
    direction: str  # "scroll-up" | "scroll-down" | "scroll-left" | "scroll-right"
    avg_magnitude: float


_DIRECTION_MAP: dict[str, str] = {
    "N": "scroll-up", "NE": "scroll-up", "NW": "scroll-up",
    "S": "scroll-down", "SE": "scroll-down", "SW": "scroll-down",
    "E": "scroll-right",
    "W": "scroll-left",
}


def _rollup_flow(
    flow_windows: tuple[FlowWindow, ...],
    min_magnitude: float = 3.0,
    min_uniformity: float = 0.6,
) -> tuple[_FlowSpan, ...]:
    """Roll up flow windows into contiguous spans of the same scroll direction.

    Only windows with sufficient magnitude and uniformity are included.
    Consecutive windows with the same scroll direction are merged.
    """
    significant = tuple(
        fw for fw in flow_windows
        if fw.mean_flow_magnitude >= min_magnitude
        and fw.flow_uniformity >= min_uniformity
        and fw.dominant_direction in _DIRECTION_MAP
    )
    if not significant:
        return ()

    spans: list[_FlowSpan] = []
    i = 0
    while i < len(significant):
        fw = significant[i]
        direction = _DIRECTION_MAP[fw.dominant_direction]
        start_ms = fw.start_ms
        end_ms = fw.end_ms
        magnitudes = [fw.mean_flow_magnitude]

        j = i + 1
        while j < len(significant):
            nxt = significant[j]
            nxt_dir = _DIRECTION_MAP[nxt.dominant_direction]
            if nxt_dir == direction and nxt.start_ms <= end_ms + 500:
                end_ms = nxt.end_ms
                magnitudes.append(nxt.mean_flow_magnitude)
                j += 1
            else:
                break

        spans.append(_FlowSpan(
            start_ms=start_ms,
            end_ms=end_ms,
            direction=direction,
            avg_magnitude=round(sum(magnitudes) / len(magnitudes), 1),
        ))
        i = j

    return tuple(spans)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_cursor_summary(
    cursor_trajectory: tuple[CursorDetection, ...],
    segment: VideoSegment,
) -> str:
    """Roll up cursor trajectory data for a segment into a text summary."""
    seg_start = segment.start_ms
    seg_detections = tuple(
        d for d in cursor_trajectory
        if segment.start_ms <= d.timestamp_ms <= segment.end_ms
    )

    spans = _rollup_trajectory(seg_detections)

    lines: list[str] = []
    for span in spans:
        start = int(span.start_ms - seg_start)
        end = int(span.end_ms - seg_start)
        parts = [f"{start}-{end}ms: {span.kind}"]
        if span.kind == "stationary" and span.x0 is not None:
            parts.append(f"pos=({span.x0},{span.y0})")
        elif span.kind == "moved":
            parts.append(f"from ({span.x0},{span.y0}) to ({span.x1},{span.y1})")
        lines.append(" ".join(parts))

    return "\n".join(lines)


def generate_flow_summary(
    flow_windows: tuple[FlowWindow, ...],
    segment: VideoSegment,
) -> str:
    """Roll up optical flow data for a segment into a text summary."""
    seg_start = segment.start_ms
    seg_flow = tuple(
        fw for fw in flow_windows
        if fw.start_ms < segment.end_ms and fw.end_ms > segment.start_ms
    )

    spans = _rollup_flow(seg_flow)
    if not spans:
        return ""

    lines: list[str] = []
    for span in spans:
        start = int(span.start_ms - seg_start)
        end = int(span.end_ms - seg_start)
        lines.append(f"{start}-{end}ms: {span.direction} magnitude={span.avg_magnitude}")

    return "\n".join(lines)


def generate_cv_summary(
    cursor_trajectory: tuple[CursorDetection, ...],
    flow_windows: tuple[FlowWindow, ...],
    segment: VideoSegment,
    summary_window_ms: int = 250,  # kept for call-site compat, unused
) -> str:
    """Combined summary for backward compatibility. Prefer the individual functions."""
    cursor = generate_cursor_summary(cursor_trajectory, segment)
    flow = generate_flow_summary(flow_windows, segment)
    return f"{cursor}\n\n{flow}"
