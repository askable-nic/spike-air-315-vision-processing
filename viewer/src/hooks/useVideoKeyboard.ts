import { useEffect, RefObject } from "react";

const FRAME_STEP = 1 / 30;

interface UseVideoKeyboardOptions {
  readonly videoRef: RefObject<HTMLVideoElement | null>;
  readonly togglePlay: () => void;
  readonly playbackRate: number;
  readonly setPlaybackRate: (rate: number) => void;
}

export const useVideoKeyboard = ({
  videoRef,
  togglePlay,
  playbackRate,
  setPlaybackRate,
}: UseVideoKeyboardOptions): void => {
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
      } else if (e.ctrlKey || e.metaKey) {
        video.currentTime = Math.max(0, video.currentTime + direction * 0.25);
      } else if (e.altKey) {
        video.currentTime = Math.max(0, video.currentTime + direction * 3);
      } else {
        video.currentTime = Math.max(0, video.currentTime + direction * 1);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [videoRef, togglePlay, playbackRate, setPlaybackRate]);
};
