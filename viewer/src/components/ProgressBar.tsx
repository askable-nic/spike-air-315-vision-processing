import { useRef, useCallback, MouseEvent } from "react";
import { Scene } from "../types";
import { msToSeconds, formatTime } from "../lib/time";
import "./ProgressBar.css";

interface ProgressBarProps {
  readonly currentTime: number;
  readonly duration: number;
  readonly scenes: readonly Scene[];
  readonly seekTo: (seconds: number) => void;
}

export const ProgressBar = ({ currentTime, duration, scenes, seekTo }: ProgressBarProps) => {
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
    <div className="progress-bar">
      <span className="progress-bar__time">
        {formatTime(currentTime)} / {formatTime(duration)}
      </span>
      <div className="progress-bar__track" ref={barRef} onMouseDown={onMouseDown}>
        <div className="progress-bar__fill" style={{ width: `${progress}%` }} />
        {scenes.map((scene, i) => {
          const pos = duration > 0 ? (msToSeconds(scene.start) / duration) * 100 : 0;
          return (
            <div
              key={i}
              className="progress-bar__marker"
              style={{ left: `${pos}%` }}
              title={`Scene ${i + 1} — ${formatTime(msToSeconds(scene.start))}`}
            />
          );
        })}
      </div>
    </div>
  );
};
