import { useRef, useState, useCallback } from "react";
import { AnnotationEvent, EVENT_TYPES, EventType } from "../../annotationTypes";
import { formatTimeMs } from "../../lib/time";
import { EVENT_TYPE_COLORS } from "../../lib/eventColors";
import { useAutoScroll } from "../../hooks/useAutoScroll";
import "./EventList.css";

interface EventListProps {
  readonly events: readonly AnnotationEvent[];
  readonly selectedIndex: number | null;
  readonly onSelect: (index: number) => void;
  readonly onSeekTo: (index: number) => void;
  readonly onAdd: (type?: EventType) => void;
}

export const EventList = ({
  events,
  selectedIndex,
  onSelect,
  onSeekTo,
  onAdd,
}: EventListProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [showTypeMenu, setShowTypeMenu] = useState(false);
  useAutoScroll(containerRef, ".event-list__item--active");

  const handleTypeSelect = useCallback((type: EventType) => {
    onAdd(type);
    setShowTypeMenu(false);
  }, [onAdd]);

  return (
    <div className="event-list" ref={containerRef}>
      <div className="event-list__header">
        <span className="event-list__title">Events ({events.length})</span>
        <div className="event-list__add-wrapper" ref={dropdownRef}>
          <button className="event-list__add" onClick={() => onAdd()}>
            + New Event
          </button>
          <button
            className="event-list__add-caret"
            onClick={() => setShowTypeMenu((v) => !v)}
            aria-label="Select event type"
          >
            ▾
          </button>
          {showTypeMenu && (
            <div className="event-list__type-menu">
              {EVENT_TYPES.map((t) => (
                <button
                  key={t}
                  className="event-list__type-option"
                  onClick={() => handleTypeSelect(t)}
                >
                  <span
                    className="event-list__type-dot"
                    style={{ background: EVENT_TYPE_COLORS[t] || "#666" }}
                  />
                  {t}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
      <div className="event-list__body">
        {events.map((evt, i) => (
          <div
            key={i}
            className={`event-list__item${i === selectedIndex ? " event-list__item--active" : ""}`}
            onClick={() => onSelect(i)}
            onDoubleClick={() => onSeekTo(i)}
          >
            <button
              className="event-list__seek"
              onClick={(e) => { e.stopPropagation(); onSelect(i); onSeekTo(i); }}
              title="Seek to event"
            >
              ▶
            </button>
            <span
              className="event-list__type"
              style={{ background: EVENT_TYPE_COLORS[evt.type] || "#666" }}
            >
              {evt.type}
            </span>
            <span className="event-list__time">
              {formatTimeMs(evt.time_start)}{evt.time_end != null ? ` – ${formatTimeMs(evt.time_end)}` : ""}
            </span>
            <span className="event-list__desc">
              {evt.description
                ? evt.description.length > 60
                  ? evt.description.slice(0, 60) + "…"
                  : evt.description
                : "—"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
