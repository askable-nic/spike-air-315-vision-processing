import { useRef, useCallback, MouseEvent } from "react";
import { AnnotationEvent } from "../../annotationTypes";
import { storedMsToVideoSeconds, formatTimeMs } from "../../lib/time";
import { EVENT_TYPE_COLORS } from "../../lib/eventColors";
import { formatTime } from "../../lib/time";
import "./AnnotationTimeline.css";

interface AnnotationTimelineProps {
  readonly currentTime: number;
  readonly duration: number;
  readonly events: readonly AnnotationEvent[];
  readonly offset: number;
  readonly selectedIndex: number | null;
  readonly seekTo: (seconds: number) => void;
  readonly onSelectEvent: (index: number) => void;
}

export const AnnotationTimeline = ({
  currentTime,
  duration,
  events,
  offset,
  selectedIndex,
  seekTo,
  onSelectEvent,
}: AnnotationTimelineProps) => {
  const barRef = useRef<HTMLDivElement>(null);
  const dragging = useRef(false);

  const seekFromEvent = useCallback(
    (clientX: number) => {
      const bar = barRef.current;
      if (!bar || duration === 0) return;
      const rect = bar.getBoundingClientRect();
      const ratio = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
      seekTo(ratio * duration);
    },
    [duration, seekTo]
  );

  const onMouseDown = useCallback(
    (e: MouseEvent) => {
      dragging.current = true;
      seekFromEvent(e.clientX);

      const onMouseMove = (ev: globalThis.MouseEvent) => seekFromEvent(ev.clientX);
      const onMouseUp = () => {
        dragging.current = false;
        document.removeEventListener("mousemove", onMouseMove);
        document.removeEventListener("mouseup", onMouseUp);
      };
      document.addEventListener("mousemove", onMouseMove);
      document.addEventListener("mouseup", onMouseUp);
    },
    [seekFromEvent]
  );

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0;

  return (
    <div className="annotation-timeline">
      <span className="annotation-timeline__time">
        {formatTime(currentTime)} / {formatTime(duration)}
      </span>
      <div className="annotation-timeline__track" ref={barRef} onMouseDown={onMouseDown}>
        <div className="annotation-timeline__fill" style={{ width: `${progress}%` }} />
        {events.map((evt, i) => {
          const videoSec = storedMsToVideoSeconds(evt.time_start, offset);
          const pos = duration > 0 ? (videoSec / duration) * 100 : 0;
          if (pos < 0 || pos > 100) return null;
          const color = EVENT_TYPE_COLORS[evt.type] || "#666";
          return (
            <div
              key={i}
              className={`annotation-timeline__marker${i === selectedIndex ? " annotation-timeline__marker--selected" : ""}`}
              style={{ left: `${pos}%`, background: color }}
              title={`${evt.type} — ${formatTimeMs(evt.time_start)}`}
              onClick={(e) => {
                e.stopPropagation();
                onSelectEvent(i);
              }}
            />
          );
        })}
      </div>
    </div>
  );
};
