import { RefObject, useCallback } from "react";
import { BoundingBox, CursorPosition } from "../../annotationTypes";
import { PickMode } from "../../hooks/useCoordinatePick";
import { formatTimeMs, videoMsToStoredMs } from "../../lib/time";
import "./AnnotationVideoPlayer.css";

interface AnnotationVideoPlayerProps {
  readonly videoRef: RefObject<HTMLVideoElement | null>;
  readonly sessionId: string;
  readonly currentTime: number;
  readonly offset: number;
  readonly isPlaying: boolean;
  readonly playbackRate: number;
  readonly onTogglePlay: () => void;
  readonly onSetPlaybackRate: (rate: number) => void;
  readonly pickMode: PickMode;
  readonly dragBox: BoundingBox | null;
  readonly onVideoClick: (
    clientX: number,
    clientY: number,
    videoElement: HTMLVideoElement
  ) => { x: number; y: number } | null;
  readonly onVideoMouseDown: (
    clientX: number,
    clientY: number,
    videoElement: HTMLVideoElement
  ) => void;
  readonly onVideoMouseMove: (
    clientX: number,
    clientY: number,
    videoElement: HTMLVideoElement
  ) => void;
  readonly onVideoMouseUp: (
    clientX: number,
    clientY: number,
    videoElement: HTMLVideoElement
  ) => BoundingBox | null;
  readonly onCoordinatePicked?: (coords: { x: number; y: number }) => void;
  readonly onRegionPicked?: (box: BoundingBox) => void;
  readonly cursorPosition?: CursorPosition;
  readonly targetBbox?: BoundingBox;
}

const videoToClient = (
  vx: number,
  vy: number,
  video: HTMLVideoElement
): { left: number; top: number } => {
  const rect = video.getBoundingClientRect();
  const nativeW = video.videoWidth;
  const nativeH = video.videoHeight;
  const elementW = rect.width;
  const elementH = rect.height;
  const videoAspect = nativeW / nativeH;
  const elementAspect = elementW / elementH;

  let renderedW: number;
  let renderedH: number;
  if (elementAspect > videoAspect) {
    renderedH = elementH;
    renderedW = elementH * videoAspect;
  } else {
    renderedW = elementW;
    renderedH = elementW / videoAspect;
  }

  const renderedLeft = (elementW - renderedW) / 2;
  const renderedTop = (elementH - renderedH) / 2;

  return {
    left: renderedLeft + (vx / nativeW) * renderedW,
    top: renderedTop + (vy / nativeH) * renderedH,
  };
};

export const AnnotationVideoPlayer = ({
  videoRef,
  sessionId,
  currentTime,
  offset,
  isPlaying,
  playbackRate,
  onTogglePlay,
  onSetPlaybackRate,
  pickMode,
  dragBox,
  onVideoClick,
  onVideoMouseDown,
  onVideoMouseMove,
  onVideoMouseUp,
  onCoordinatePicked,
  onRegionPicked,
  cursorPosition,
  targetBbox,
}: AnnotationVideoPlayerProps) => {
  const videoMs = currentTime * 1000;
  const storedMs = videoMsToStoredMs(videoMs, offset);
  const isPickMode = pickMode !== "none";

  const handleFrameStep = useCallback(
    (delta: number) => {
      const video = videoRef.current;
      if (video) video.currentTime += delta;
    },
    [videoRef]
  );

  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (pickMode !== "point") return;
      const video = videoRef.current;
      if (!video) return;
      const coords = onVideoClick(e.clientX, e.clientY, video);
      if (coords && onCoordinatePicked) {
        onCoordinatePicked(coords);
      }
    },
    [pickMode, videoRef, onVideoClick, onCoordinatePicked]
  );

  const handleMouseDown = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (pickMode !== "region") return;
      const video = videoRef.current;
      if (!video) return;
      onVideoMouseDown(e.clientX, e.clientY, video);
    },
    [pickMode, videoRef, onVideoMouseDown]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (pickMode !== "region") return;
      const video = videoRef.current;
      if (!video) return;
      onVideoMouseMove(e.clientX, e.clientY, video);
    },
    [pickMode, videoRef, onVideoMouseMove]
  );

  const handleMouseUp = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (pickMode !== "region") return;
      const video = videoRef.current;
      if (!video) return;
      const box = onVideoMouseUp(e.clientX, e.clientY, video);
      if (box && onRegionPicked) {
        onRegionPicked(box);
      }
    },
    [pickMode, videoRef, onVideoMouseUp, onRegionPicked]
  );

  const renderDragOverlay = () => {
    if (!dragBox || !videoRef.current) return null;
    const video = videoRef.current;
    const topLeft = videoToClient(dragBox.x, dragBox.y, video);
    const bottomRight = videoToClient(
      dragBox.x + dragBox.width,
      dragBox.y + dragBox.height,
      video
    );
    return (
      <div
        className="annotation-video__drag-rect"
        style={{
          left: topLeft.left,
          top: topLeft.top,
          width: bottomRight.left - topLeft.left,
          height: bottomRight.top - topLeft.top,
        }}
      />
    );
  };

  return (
    <div
      className={`annotation-video${isPickMode ? " annotation-video--pick" : ""}`}
      onClick={handleClick}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
    >
      <video
        ref={videoRef}
        className="video-player"
        preload="metadata"
      >
        <source
          src={`/video/normalized/${sessionId}.mp4`}
          type="video/mp4"
        />
      </video>
      {isPickMode && (
        <div className="annotation-video__pick-overlay">
          {pickMode === "point" ? "Click to pick coordinates" : "Drag to select region"}
        </div>
      )}
      {renderDragOverlay()}
      {cursorPosition && videoRef.current && (() => {
        const pos = videoToClient(cursorPosition.x, cursorPosition.y, videoRef.current!);
        return <div className="annotation-video__cursor" style={{ left: pos.left, top: pos.top }} />;
      })()}
      {targetBbox && videoRef.current && (() => {
        const tl = videoToClient(targetBbox.x, targetBbox.y, videoRef.current!);
        const br = videoToClient(targetBbox.x + targetBbox.width, targetBbox.y + targetBbox.height, videoRef.current!);
        return (
          <div
            className="annotation-video__target-bbox"
            style={{ left: tl.left, top: tl.top, width: br.left - tl.left, height: br.top - tl.top }}
          />
        );
      })()}
      <div className="annotation-video__info">
        <span className="annotation-video__controls">
          <button onClick={(e) => { e.stopPropagation(); handleFrameStep(-1 / 30); }} title="Back 1 frame (Shift+←)">
            ‹
          </button>
          <button onClick={(e) => { e.stopPropagation(); onTogglePlay(); }} title="Play/Pause (Space)">
            {isPlaying ? "⏸" : "▶"}
          </button>
          <button onClick={(e) => { e.stopPropagation(); handleFrameStep(1 / 30); }} title="Forward 1 frame (Shift+→)">
            ›
          </button>
        </span>
        <span className="annotation-video__timestamp">
          {formatTimeMs(storedMs)}
        </span>
        <span className="annotation-video__speed" onClick={(e) => e.stopPropagation()}>
          <button
            onClick={() => onSetPlaybackRate(playbackRate - 0.25)}
            disabled={playbackRate <= 0.25}
            title="Slower (-)"
          >
            −
          </button>
          <span
            className="annotation-video__speed-label"
            onClick={() => onSetPlaybackRate(1)}
            title="Reset to 1x (0)"
          >
            {playbackRate}x
          </span>
          <button
            onClick={() => onSetPlaybackRate(playbackRate + 0.25)}
            disabled={playbackRate >= 5}
            title="Faster (+)"
          >
            +
          </button>
        </span>
      </div>
    </div>
  );
};
