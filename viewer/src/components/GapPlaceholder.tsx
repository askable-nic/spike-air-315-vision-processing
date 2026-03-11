import { formatTime, isInRange } from "../lib/time";
import "./ColumnItem.css";

interface GapPlaceholderProps {
  readonly start: number;
  readonly end: number;
  readonly currentTime: number;
  readonly boundary?: boolean;
}

export const GapPlaceholder = ({ start, end, currentTime, boundary }: GapPlaceholderProps) => {
  const active = isInRange(currentTime, start, end);
  const className = [
    "column-item",
    "column-item--gap",
    active && "column-item--active",
    boundary && "column-item--gap-boundary",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={className} data-start-time={start}>
      <span className="column-item__time">
        {formatTime(start)}–{formatTime(end)}
      </span>
    </div>
  );
};
