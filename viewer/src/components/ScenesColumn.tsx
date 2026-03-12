import { useMemo, useRef } from "react";
import { Scene } from "../types";
import { msToSeconds, isInRange, formatTime, findGaps, TimeRange } from "../lib/time";
import { useAutoScroll } from "../hooks/useAutoScroll";
import { ColumnItem } from "./ColumnItem";
import { GapPlaceholder } from "./GapPlaceholder";

interface ScenesColumnProps {
  readonly scenes: readonly Scene[];
  readonly currentTime: number;
  readonly duration: number;
  readonly seekTo: (seconds: number) => void;
}

type ListEntry =
  | { readonly kind: "scene"; readonly scene: Scene; readonly index: number; readonly startS: number; readonly endS: number }
  | { readonly kind: "gap"; readonly range: TimeRange };

export const ScenesColumn = ({ scenes, currentTime, duration, seekTo }: ScenesColumnProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  useAutoScroll(containerRef, ".column-item--active");

  const entries: readonly ListEntry[] = useMemo(() => {
    const ranges: readonly TimeRange[] = scenes.map((s) => ({
      start: msToSeconds(s.start),
      end: msToSeconds(s.end),
    }));
    const gaps = findGaps(ranges, { boundsEnd: duration });

    const items: readonly ListEntry[] = scenes.map((scene, index) => ({
      kind: "scene" as const,
      scene,
      index,
      startS: msToSeconds(scene.start),
      endS: msToSeconds(scene.end),
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
  }, [scenes, duration]);

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
              <span className="column-item__time">
                {formatTime(entry.startS)}–{formatTime(entry.endS)}
              </span>
              {entry.scene.initial_url && (
                <span className="column-item__url">{entry.scene.initial_url}</span>
              )}
              {entry.scene.description && (
                <span className="column-item__text">{entry.scene.description}</span>
              )}
              {!entry.scene.description && (
                <span className="column-item__text">Scene {entry.index + 1}</span>
              )}
            </ColumnItem>
          ),
        )}
    </div>
  );
};
