import { RefObject, useCallback } from "react";
import { formatTime } from "../lib/time";
import "./VideoPlayer.css";

const FRAME_STEP = 1 / 30;

interface VideoPlayerProps {
  readonly videoRef: RefObject<HTMLVideoElement | null>;
  readonly sessionKey: string;
  readonly currentTime: number;
  readonly duration: number;
  readonly isPlaying: boolean;
  readonly playbackRate: number;
  readonly onTogglePlay: () => void;
  readonly onSetPlaybackRate: (rate: number) => void;
}

export const VideoPlayer = ({
  videoRef,
  sessionKey,
  currentTime,
  isPlaying,
  playbackRate,
  onTogglePlay,
  onSetPlaybackRate,
}: VideoPlayerProps) => {
  const handleFrameStep = useCallback(
    (delta: number) => {
      const video = videoRef.current;
      if (video) {
        video.pause();
        video.currentTime = Math.max(0, video.currentTime + delta);
      }
    },
    [videoRef],
  );

  return (
    <div className="video-player__container">
      <video ref={videoRef} className="video-player" preload="metadata">
        <source src={`/video/${sessionKey}.mp4`} type="video/mp4" />
        <source src={`/video/${sessionKey}.webm`} type="video/webm" />
      </video>
      <div className="video-player__controls">
        <span className="video-player__nav">
          <button onClick={() => handleFrameStep(-FRAME_STEP)} title="Back 1 frame (Shift+Left)">
            ‹
          </button>
          <button onClick={onTogglePlay} title="Play/Pause (Space)">
            {isPlaying ? "⏸" : "▶"}
          </button>
          <button onClick={() => handleFrameStep(FRAME_STEP)} title="Forward 1 frame (Shift+Right)">
            ›
          </button>
        </span>
        <span className="video-player__timestamp">
          {formatTime(currentTime)}
        </span>
        <span className="video-player__speed">
          <button
            onClick={() => onSetPlaybackRate(playbackRate - 0.25)}
            disabled={playbackRate <= 0.25}
            title="Slower (-)"
          >
            −
          </button>
          <span
            className="video-player__speed-label"
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
