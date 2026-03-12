import { useRef, useState, useCallback, useEffect } from "react";
import { Link } from "react-router-dom";
import { ManifestSession } from "../../annotationTypes";
import { useVideoTime } from "../../hooks/useVideoTime";
import { useAnnotationState } from "../../hooks/useAnnotationState";
import { useCoordinatePick } from "../../hooks/useCoordinatePick";
import { BoundingBox, EventType } from "../../annotationTypes";
import { videoMsToStoredMs } from "../../lib/time";
import { AnnotationVideoPlayer } from "./AnnotationVideoPlayer";
import { EventList } from "./EventList";
import { EventForm } from "./EventForm";
import { AnnotationTimeline } from "./AnnotationTimeline";
import "./AnnotationLayout.css";

interface AnnotationLayoutProps {
  readonly sessionId: string;
  readonly manifest: ManifestSession;
}

const MIN_PANEL_PERCENT = 20;

export const AnnotationLayout = ({ sessionId, manifest }: AnnotationLayoutProps) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const { currentTime, duration, isPlaying, playbackRate, seekTo, togglePlay, setPlaybackRate } = useVideoTime(videoRef);

  const offset = manifest.screenTrackStartOffset;

  const annotation = useAnnotationState({
    sessionId,
    transcriptId: manifest.identifier,
    studyId: manifest.studyId,
  });

  const coordinatePick = useCoordinatePick();
  const [editorWidthPercent, setEditorWidthPercent] = useState(40);
  const [isDragging, setIsDragging] = useState(false);

  const handlePointerDown = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.currentTarget.setPointerCapture(e.pointerId);
      setIsDragging(true);
    },
    []
  );

  const handlePointerMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (!isDragging || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const xPercent = ((e.clientX - rect.left) / rect.width) * 100;
      const editorPercent = Math.min(
        100 - MIN_PANEL_PERCENT,
        Math.max(MIN_PANEL_PERCENT, 100 - xPercent)
      );
      setEditorWidthPercent(editorPercent);
    },
    [isDragging]
  );

  const handlePointerUp = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      e.currentTarget.releasePointerCapture(e.pointerId);
      setIsDragging(false);
    },
    []
  );

  const handleEventSelect = useCallback(
    (index: number) => {
      annotation.selectEvent(index);
    },
    [annotation]
  );

  const handleSeekToEvent = useCallback(
    (index: number) => {
      const evt = annotation.events[index];
      if (evt) {
        const videoSec = (evt.time_start - offset) / 1000;
        if (videoSec >= 0) seekTo(videoSec);
      }
    },
    [annotation.events, offset, seekTo]
  );

  const handleAddEvent = useCallback((type?: EventType) => {
    const storedMs = videoMsToStoredMs(currentTime * 1000, offset);
    const video = videoRef.current;
    const viewport = video && video.videoWidth
      ? { width: video.videoWidth, height: video.videoHeight }
      : undefined;
    annotation.addEvent(storedMs, type, viewport);
  }, [currentTime, offset, annotation, videoRef]);

  const handleCoordinatePicked = useCallback(
    (coords: { x: number; y: number }) => {
      if (annotation.selectedEventIndex !== null) {
        annotation.updateEvent(annotation.selectedEventIndex, {
          cursor_position: coords,
        });
      }
    },
    [annotation]
  );

  const handleRegionPicked = useCallback(
    (box: BoundingBox) => {
      if (annotation.selectedEventIndex !== null) {
        const evt = annotation.events[annotation.selectedEventIndex];
        annotation.updateEvent(annotation.selectedEventIndex, {
          _metadata: { ...evt?._metadata, interaction_target_bbox: box },
        });
      }
    },
    [annotation]
  );

  const FRAME_STEP = 1 / 30;

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

      if (e.key === " ") {
        e.preventDefault();
        togglePlay();
        return;
      }

      if (e.key === "+" || e.key === "=") {
        e.preventDefault();
        setPlaybackRate(playbackRate + 0.25);
        return;
      }

      if (e.key === "-" || e.key === "_") {
        e.preventDefault();
        setPlaybackRate(playbackRate - 0.25);
        return;
      }

      if (e.key === "0") {
        e.preventDefault();
        setPlaybackRate(1);
        const video = videoRef.current;
        if (video) video.pause();
        return;
      }

      if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;

      e.preventDefault();
      const video = videoRef.current;
      if (!video) return;

      const direction = e.key === "ArrowRight" ? 1 : -1;

      if (e.shiftKey) {
        video.pause();
        video.currentTime = Math.max(0, video.currentTime + direction * FRAME_STEP);
      } else if (e.altKey) {
        video.currentTime = Math.max(0, video.currentTime + direction * 3);
      } else {
        video.currentTime = Math.max(0, video.currentTime + direction * 1);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [videoRef, togglePlay, playbackRate, setPlaybackRate]);

  const selectedEvent =
    annotation.selectedEventIndex !== null
      ? annotation.events[annotation.selectedEventIndex]
      : null;

  const videoWidthPercent = 100 - editorWidthPercent;

  return (
    <div className="annotation-layout">
      <div className="annotation-layout__toolbar">
        <Link to="/annotate" className="annotation-layout__back">
          ← Sessions
        </Link>
        <span className="annotation-layout__session-name">
          {sessionId.replace(/_/g, " ")}
        </span>
        <span className="annotation-layout__spacer" />
        {annotation.isDirty && (
          <span className="annotation-layout__dirty">Unsaved changes</span>
        )}
        <button
          className="annotation-layout__save"
          onClick={annotation.save}
          disabled={!annotation.isDirty}
        >
          Save
        </button>
        <button className="annotation-layout__export" onClick={annotation.exportJson}>
          Export
        </button>
      </div>

      {annotation.error && (
        <div className="annotation-layout__error">{annotation.error}</div>
      )}

      <div className="annotation-layout__main" ref={containerRef}>
        <div
          className="annotation-layout__video"
          style={{ flexBasis: `${videoWidthPercent}%` }}
        >
          <AnnotationVideoPlayer
            videoRef={videoRef}
            sessionId={sessionId}
            currentTime={currentTime}
            offset={offset}
            isPlaying={isPlaying}
            playbackRate={playbackRate}
            onTogglePlay={togglePlay}
            onSetPlaybackRate={setPlaybackRate}
            pickMode={coordinatePick.pickMode}
            dragBox={coordinatePick.dragBox}
            onVideoClick={coordinatePick.onVideoClick}
            onVideoMouseDown={coordinatePick.onVideoMouseDown}
            onVideoMouseMove={coordinatePick.onVideoMouseMove}
            onVideoMouseUp={coordinatePick.onVideoMouseUp}
            onCoordinatePicked={handleCoordinatePicked}
            onRegionPicked={handleRegionPicked}
          />
        </div>

        <div
          className={`annotation-layout__resize-handle${isDragging ? " annotation-layout__resize-handle--dragging" : ""}`}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
        />

        <div
          className="annotation-layout__editor"
          style={{ flexBasis: `${editorWidthPercent}%` }}
        >
          <div className="annotation-layout__event-list">
            <EventList
              events={annotation.events}
              selectedIndex={annotation.selectedEventIndex}
              onSelect={handleEventSelect}
              onSeekTo={handleSeekToEvent}
              onAdd={handleAddEvent}
            />
          </div>
          {selectedEvent && annotation.selectedEventIndex !== null && (
            <div className="annotation-layout__event-form">
              <EventForm
                event={selectedEvent}
                index={annotation.selectedEventIndex}
                sessionId={sessionId}
                currentVideoMs={currentTime * 1000}
                offset={offset}
                onUpdate={annotation.updateEvent}
                onDuplicate={annotation.duplicateEvent}
                onDelete={annotation.deleteEvent}
                onSave={annotation.save}
                onSeekTo={(ms: number) => { const s = (ms - offset) / 1000; if (s >= 0) seekTo(s); }}
                onStartPick={coordinatePick.startPick}
                onStartRegionPick={coordinatePick.startRegionPick}
              />
            </div>
          )}
        </div>
      </div>

      <div className="annotation-layout__timeline">
        <AnnotationTimeline
          currentTime={currentTime}
          duration={duration}
          events={annotation.events}
          offset={offset}
          selectedIndex={annotation.selectedEventIndex}
          seekTo={seekTo}
          onSelectEvent={handleEventSelect}
        />
      </div>
    </div>
  );
};
