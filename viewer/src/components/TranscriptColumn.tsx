import { useMemo, useRef } from "react";
import { Utterance } from "../types";
import { msToSeconds, isInRange, formatTime, findGaps, TimeRange } from "../lib/time";
import { useAutoScroll } from "../hooks/useAutoScroll";
import { ColumnItem } from "./ColumnItem";
import { GapPlaceholder } from "./GapPlaceholder";

interface TranscriptColumnProps {
  readonly utterances: readonly Utterance[];
  readonly currentTime: number;
  readonly duration: number;
  readonly seekTo: (seconds: number) => void;
}

type ListEntry =
  | { readonly kind: "utterance"; readonly utterance: Utterance; readonly startS: number; readonly endS: number }
  | { readonly kind: "gap"; readonly range: TimeRange };

export const TranscriptColumn = ({
  utterances,
  currentTime,
  duration,
  seekTo,
}: TranscriptColumnProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  useAutoScroll(containerRef, ".column-item--active");

  const entries: readonly ListEntry[] = useMemo(() => {
    const ranges: readonly TimeRange[] = utterances.map((u) => ({
      start: msToSeconds(u.start),
      end: msToSeconds(u.end),
    }));
    const gaps = findGaps(ranges, { boundsEnd: duration });

    const items: readonly ListEntry[] = utterances.map((u) => ({
      kind: "utterance" as const,
      utterance: u,
      startS: msToSeconds(u.start),
      endS: msToSeconds(u.end),
    }));
    const gapItems: readonly ListEntry[] = gaps.map((range) => ({
      kind: "gap" as const,
      range,
    }));

    return [...items, ...gapItems].sort((a, b) => {
      const aStart = a.kind === "gap" ? a.range.start : a.startS;
      const bStart = b.kind === "gap" ? b.range.start : b.startS;
      return aStart - bStart;
    });
  }, [utterances, duration]);

  return (
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
              active={isInRange(currentTime, entry.startS, entry.endS)}
              startTime={entry.startS}
              onClick={() => seekTo(entry.startS)}
            >
              <span className="column-item__time">{formatTime(entry.startS)}</span>
              <span className="column-item__text">{entry.utterance.text}</span>
            </ColumnItem>
          ),
        )}
    </div>
  );
};
