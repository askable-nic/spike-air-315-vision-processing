import { useState, useCallback } from "react";
import { AnnotationEvent, EVENT_TYPES } from "../../annotationTypes";
import { formatTimeMs, videoMsToStoredMs } from "../../lib/time";
import { describeFrame } from "../../lib/annotationApi";
import "./EventForm.css";

interface EventFormProps {
  readonly event: AnnotationEvent;
  readonly index: number;
  readonly sessionId: string;
  readonly currentVideoMs: number;
  readonly offset: number;
  readonly onUpdate: (index: number, partial: Partial<AnnotationEvent>) => void;
  readonly onDuplicate: (index: number) => void;
  readonly onDelete: (index: number) => void;
  readonly onSave: () => void;
  readonly onSeekTo: (ms: number) => void;
  readonly onStartPick: () => void;
  readonly onStartRegionPick: () => void;
}

export const EventForm = ({
  event,
  index,
  sessionId,
  currentVideoMs,
  offset,
  onUpdate,
  onDuplicate,
  onDelete,
  onSave,
  onSeekTo,
  onStartPick,
  onStartRegionPick,
}: EventFormProps) => {
  const hasOptionalValues = !!(
    event.interaction_target || event.page_title || event.page_location ||
    event.viewport_width || event.viewport_height || event.frame_description
  );
  const [showOptional, setShowOptional] = useState(hasOptionalValues);
  const [describingFrame, setDescribingFrame] = useState(false);

  const setFromVideo = useCallback(
    (field: "time_start" | "time_end") => {
      onUpdate(index, { [field]: videoMsToStoredMs(currentVideoMs, offset) });
    },
    [index, currentVideoMs, offset, onUpdate]
  );

  const handleDescribeFrame = useCallback(async () => {
    setDescribingFrame(true);
    try {
      const description = await describeFrame(sessionId, event.time_start);
      onUpdate(index, { frame_description: description });
    } catch {
      // error silently handled — user sees field unchanged
    } finally {
      setDescribingFrame(false);
    }
  }, [sessionId, event.time_start, index, onUpdate]);

  const handleBlur = useCallback(
    (e: React.FocusEvent<HTMLDivElement>) => {
      if (!e.currentTarget.contains(e.relatedTarget)) {
        onSave();
      }
    },
    [onSave]
  );

  return (
    <div className="event-form" onBlur={handleBlur}>
      <div className="event-form__field">
        <label>Type</label>
        <select
          value={event.type}
          onChange={(e) => onUpdate(index, { type: e.target.value as AnnotationEvent["type"] })}
        >
          {EVENT_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </div>

      <div className="event-form__row">
        <div className="event-form__field event-form__field--grow">
          <label>Start ({formatTimeMs(event.time_start)})</label>
          <div className="event-form__input-row">
            <input
              type="number"
              value={event.time_start}
              onChange={(e) => onUpdate(index, { time_start: Number(e.target.value) })}
            />
            <button className="event-form__btn-sm" onClick={() => setFromVideo("time_start")}>
              Set from video
            </button>
            <button className="event-form__btn-sm" onClick={() => onSeekTo(event.time_start)} title="Seek video to start">
              Seek
            </button>
          </div>
        </div>
        <div className="event-form__field event-form__field--grow">
          <label>End {event.time_end != null ? `(${formatTimeMs(event.time_end)})` : "(not set)"}</label>
          <div className="event-form__input-row">
            <input
              type="number"
              value={event.time_end ?? ""}
              onChange={(e) => onUpdate(index, { time_end: e.target.value ? Number(e.target.value) : null })}
            />
            <button className="event-form__btn-sm" onClick={() => setFromVideo("time_end")}>
              Set from video
            </button>
            {event.time_end != null && (
              <button className="event-form__btn-sm" onClick={() => onSeekTo(event.time_end!)} title="Seek video to end">
                Seek
              </button>
            )}
            {event.time_end != null && (
              <button className="event-form__btn-sm" onClick={() => onUpdate(index, { time_end: null })}>
                Clear
              </button>
            )}
          </div>
        </div>
      </div>

      {event.time_end != null && (
        <div className="event-form__field">
          <label>Time Range</label>
          <input
            type="range"
            min={event.time_start}
            max={event.time_end}
            step={1000 / 30}
            value={Math.min(Math.max(currentVideoMs + offset, event.time_start), event.time_end)}
            onChange={(e) => onSeekTo(Number(e.target.value))}
          />
        </div>
      )}

      <div className="event-form__field">
        <label>Description</label>
        <textarea
          rows={3}
          value={event.description}
          onChange={(e) => onUpdate(index, { description: e.target.value })}
        />
      </div>

      <div className="event-form__field">
        <label>Cursor Position</label>
        <div className="event-form__input-row">
          <input
            type="number"
            placeholder="x"
            value={event.cursor_position?.x ?? ""}
            onChange={(e) =>
              onUpdate(index, {
                cursor_position: {
                  x: Number(e.target.value),
                  y: event.cursor_position?.y ?? 0,
                },
              })
            }
          />
          <input
            type="number"
            placeholder="y"
            value={event.cursor_position?.y ?? ""}
            onChange={(e) =>
              onUpdate(index, {
                cursor_position: {
                  x: event.cursor_position?.x ?? 0,
                  y: Number(e.target.value),
                },
              })
            }
          />
          <button className="event-form__btn-sm" onClick={onStartPick}>
            Pick from video
          </button>
        </div>
      </div>

      <div className="event-form__field">
        <label>Interaction Target Region</label>
        <div className="event-form__input-row">
          {event._metadata?.interaction_target_bbox ? (
            <span className="event-form__bbox-label">
              {event._metadata.interaction_target_bbox.width}x{event._metadata.interaction_target_bbox.height}
              {" @ "}
              ({event._metadata.interaction_target_bbox.x}, {event._metadata.interaction_target_bbox.y})
            </span>
          ) : (
            <span className="event-form__bbox-label event-form__bbox-label--empty">Not set</span>
          )}
          <button className="event-form__btn-sm" onClick={onStartRegionPick}>
            Pick region
          </button>
          {event._metadata?.interaction_target_bbox && (
            <button
              className="event-form__btn-sm"
              onClick={() => {
                const { interaction_target_bbox: _, ...rest } = event._metadata!;
                const hasKeys = Object.keys(rest).length > 0;
                onUpdate(index, { _metadata: hasKeys ? rest : undefined });
              }}
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {!showOptional && (
        <button
          className="event-form__toggle"
          onClick={() => setShowOptional(true)}
        >
          + Optional fields
        </button>
      )}

      {showOptional && (
        <>
          <div className="event-form__field">
            <label>Interaction Target</label>
            <input
              type="text"
              value={event.interaction_target ?? ""}
              onChange={(e) => onUpdate(index, { interaction_target: e.target.value || undefined })}
            />
          </div>

          <div className="event-form__field">
            <label>Page Title</label>
            <input
              type="text"
              value={event.page_title ?? ""}
              onChange={(e) => onUpdate(index, { page_title: e.target.value || undefined })}
            />
          </div>

          <div className="event-form__field">
            <label>Page Location</label>
            <input
              type="text"
              value={event.page_location ?? ""}
              onChange={(e) => onUpdate(index, { page_location: e.target.value || undefined })}
            />
          </div>

          <div className="event-form__row">
            <div className="event-form__field event-form__field--grow">
              <label>Viewport Width</label>
              <input
                type="number"
                value={event.viewport_width ?? ""}
                onChange={(e) =>
                  onUpdate(index, {
                    viewport_width: e.target.value ? Number(e.target.value) : undefined,
                  })
                }
              />
            </div>
            <div className="event-form__field event-form__field--grow">
              <label>Viewport Height</label>
              <input
                type="number"
                value={event.viewport_height ?? ""}
                onChange={(e) =>
                  onUpdate(index, {
                    viewport_height: e.target.value ? Number(e.target.value) : undefined,
                  })
                }
              />
            </div>
          </div>

          <div className="event-form__field">
            <label>
              Frame Description
              <button
                className="event-form__btn-sm"
                onClick={handleDescribeFrame}
                disabled={describingFrame}
                style={{ marginLeft: 8 }}
              >
                {describingFrame ? "Generating…" : "Generate"}
              </button>
            </label>
            <textarea
              rows={3}
              value={event.frame_description ?? ""}
              onChange={(e) => onUpdate(index, { frame_description: e.target.value || undefined })}
            />
          </div>
        </>
      )}

      <div className="event-form__actions">
        <button className="event-form__btn" onClick={() => onDuplicate(index)}>
          Duplicate
        </button>
        <button className="event-form__btn event-form__btn--danger" onClick={() => onDelete(index)}>
          Delete
        </button>
      </div>
    </div>
  );
};
