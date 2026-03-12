import { useRef, useState, useCallback, useEffect } from "react";
import { useVideoTime } from "../hooks/useVideoTime";
import { useVideoKeyboard } from "../hooks/useVideoKeyboard";
import { SessionData } from "../types";
import { VideoPlayer } from "./VideoPlayer";
import { ColumnsPanel } from "./ColumnsPanel";
import { ProgressBar } from "./ProgressBar";
import "./Layout.css";

interface LayoutProps {
  readonly sessionKey: string;
  readonly columns: SessionData;
}

const DEFAULT_COLUMNS_WIDTH_PERCENT = 60;
const MIN_PANEL_PERCENT = 15;

export const Layout = ({ sessionKey, columns }: LayoutProps) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const { currentTime, duration, isPlaying, playbackRate, seekTo, togglePlay, setPlaybackRate } = useVideoTime(videoRef);
  useVideoKeyboard({ videoRef, togglePlay, playbackRate, setPlaybackRate });
  const containerRef = useRef<HTMLDivElement>(null);

  const [columnsWidthPercent, setColumnsWidthPercent] = useState(DEFAULT_COLUMNS_WIDTH_PERCENT);
  const [isDragging, setIsDragging] = useState(false);
  const [isPiP, setIsPiP] = useState(false);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleEnterPiP = () => setIsPiP(true);
    const handleLeavePiP = () => setIsPiP(false);

    video.addEventListener("enterpictureinpicture", handleEnterPiP);
    video.addEventListener("leavepictureinpicture", handleLeavePiP);

    return () => {
      video.removeEventListener("enterpictureinpicture", handleEnterPiP);
      video.removeEventListener("leavepictureinpicture", handleLeavePiP);
    };
  }, []);

  const togglePiP = useCallback(async () => {
    const video = videoRef.current;
    if (!video) return;

    try {
      if (document.pictureInPictureElement) {
        await document.exitPictureInPicture();
      } else {
        await video.requestPictureInPicture();
      }
    } catch {
      // PiP request can fail if denied or unsupported
    }
  }, []);

  const handlePointerDown = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      e.preventDefault();
      const target = e.currentTarget;
      target.setPointerCapture(e.pointerId);
      setIsDragging(true);
    },
    [],
  );

  const handlePointerMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (!isDragging || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const xPercent = ((e.clientX - rect.left) / rect.width) * 100;
      const columnsPercent = Math.min(
        100 - MIN_PANEL_PERCENT,
        Math.max(MIN_PANEL_PERCENT, 100 - xPercent),
      );
      setColumnsWidthPercent(columnsPercent);
    },
    [isDragging],
  );

  const handlePointerUp = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      e.currentTarget.releasePointerCapture(e.pointerId);
      setIsDragging(false);
    },
    [],
  );

  const scenesCol = columns.find((c) => c.type === "scenes");
  const scenes = scenesCol?.type === "scenes" ? scenesCol.scenes : [];

  const videoWidthPercent = 100 - columnsWidthPercent;

  return (
    <div className="layout">
      {isPiP && (
        <div className="layout__pip-bar">
          <span>Playing in Picture-in-Picture</span>
          <button className="layout__pip-bar-exit" onClick={togglePiP}>
            Exit PiP
          </button>
        </div>
      )}
      <div className="layout__main" ref={containerRef}>
        <div
          className={`layout__video${isPiP ? " layout__video--pip" : ""}`}
          style={isPiP ? undefined : { flexBasis: `${videoWidthPercent}%` }}
        >
          <VideoPlayer
            videoRef={videoRef}
            sessionKey={sessionKey}
            currentTime={currentTime}
            duration={duration}
            isPlaying={isPlaying}
            playbackRate={playbackRate}
            onTogglePlay={togglePlay}
            onSetPlaybackRate={setPlaybackRate}
          />
          {!isPiP && document.pictureInPictureEnabled && (
            <button className="layout__pip-button" onClick={togglePiP} title="Picture-in-Picture">
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                <rect x="1" y="3" width="16" height="12" rx="1.5" stroke="currentColor" strokeWidth="1.5" />
                <rect x="9" y="8" width="7" height="5.5" rx="1" fill="currentColor" />
              </svg>
            </button>
          )}
        </div>
        {!isPiP && (
          <div
            className={`layout__resize-handle${isDragging ? " layout__resize-handle--dragging" : ""}`}
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
          />
        )}
        <div
          className="layout__columns"
          style={{ flexBasis: isPiP ? "100%" : `${columnsWidthPercent}%` }}
        >
          <ColumnsPanel columns={columns} currentTime={currentTime} duration={duration} seekTo={seekTo} />
        </div>
      </div>
      <div className="layout__progress">
        <ProgressBar
          currentTime={currentTime}
          duration={duration}
          scenes={scenes}
          seekTo={seekTo}
        />
      </div>
    </div>
  );
};
