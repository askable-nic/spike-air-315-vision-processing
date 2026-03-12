import { useMemo, useRef } from "react";
import { AnalysisEvent } from "../types";
import { isInRange, formatTime, findGaps, TimeRange } from "../lib/time";
import { useAutoScroll } from "../hooks/useAutoScroll";
import { ColumnItem } from "./ColumnItem";
import { GapPlaceholder } from "./GapPlaceholder";

interface EventsColumnProps {
  readonly title?: string;
  readonly events: readonly AnalysisEvent[];
  readonly currentTime: number;
  readonly duration: number;
  readonly seekTo: (seconds: number) => void;
}

type ListEntry =
  | { readonly kind: "event"; readonly event: AnalysisEvent }
  | { readonly kind: "gap"; readonly range: TimeRange };

export const EventsColumn = ({ title = "Events", events, currentTime, duration, seekTo }: EventsColumnProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  useAutoScroll(containerRef, ".column-item--active");

  const entries: readonly ListEntry[] = useMemo(() => {
    const ranges: readonly TimeRange[] = events.map((e) => ({
      start: e.time_start,
      end: e.time_end ?? e.time_start,
    }));
    const gaps = findGaps(ranges, { boundsEnd: duration });

    const items: readonly ListEntry[] = events.map((event) => ({
      kind: "event" as const,
      event,
    }));
    const gapItems: readonly ListEntry[] = gaps.map((range) => ({
      kind: "gap" as const,
      range,
    }));

    return [...items, ...gapItems].sort((a, b) => {
      const aStart = a.kind === "gap" ? a.range.start : a.event.time_start;
      const bStart = b.kind === "gap" ? b.range.start : b.event.time_start;
      return aStart - bStart;
    });
  }, [events, duration]);

  return (
    <div className="column">
      <div className="column__header">{title}</div>
      <div className="column__body" ref={containerRef}>
        {entries.map((entry, i) =>
          entry.kind === "gap" ? (
            <GapPlaceholder
              key={`gap-${i}`}
              start={entry.range.start}
              end={entry.range.end}
              currentTime={currentTime}
              boundary={i === 0 || i === entries.length - 1}
            />
          ) : (
            <ColumnItem
              key={i}
              active={isInRange(currentTime, entry.event.time_start, entry.event.time_end ?? entry.event.time_start)}
              startTime={entry.event.time_start}
              onClick={() => seekTo(entry.event.time_start)}
            >
              <span className="column-item__time">
                {formatTime(entry.event.time_start)}{entry.event.time_end != null ? `–${formatTime(entry.event.time_end)}` : ""}
              </span>
              <span className="column-item__badge">{entry.event.event_type}</span>
              {entry.event.page_title && (
                <span className="column-item__url">{entry.event.page_title}</span>
              )}
              <span className="column-item__text">{entry.event.label}</span>
              {entry.event.interaction_target && (
                <span className="column-item__signal">{entry.event.interaction_target}</span>
              )}
            </ColumnItem>
          ),
        )}
      </div>
    </div>
  );
};
