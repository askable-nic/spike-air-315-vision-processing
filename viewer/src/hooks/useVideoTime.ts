import { useState, useCallback, useEffect, RefObject } from "react";

export interface VideoTimeState {
  readonly currentTime: number;
  readonly duration: number;
  readonly isPlaying: boolean;
  readonly playbackRate: number;
  readonly seekTo: (seconds: number) => void;
  readonly togglePlay: () => void;
  readonly setPlaybackRate: (rate: number) => void;
}

export const useVideoTime = (videoRef: RefObject<HTMLVideoElement | null>): VideoTimeState => {
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackRate, setPlaybackRateState] = useState(1);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const onTimeUpdate = () => setCurrentTime(video.currentTime);
    const onDurationChange = () => setDuration(video.duration || 0);
    const onPlay = () => setIsPlaying(true);
    const onPause = () => setIsPlaying(false);
    const onLoadedMetadata = () => setDuration(video.duration || 0);

    video.addEventListener("timeupdate", onTimeUpdate);
    video.addEventListener("durationchange", onDurationChange);
    video.addEventListener("loadedmetadata", onLoadedMetadata);
    video.addEventListener("play", onPlay);
    video.addEventListener("pause", onPause);

    return () => {
      video.removeEventListener("timeupdate", onTimeUpdate);
      video.removeEventListener("durationchange", onDurationChange);
      video.removeEventListener("loadedmetadata", onLoadedMetadata);
      video.removeEventListener("play", onPlay);
      video.removeEventListener("pause", onPause);
    };
  }, [videoRef]);

  const seekTo = useCallback(
    (seconds: number) => {
      const video = videoRef.current;
      if (video) video.currentTime = seconds;
    },
    [videoRef]
  );

  const togglePlay = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused) {
      video.play();
    } else {
      video.pause();
    }
  }, [videoRef]);

  const setPlaybackRate = useCallback(
    (rate: number) => {
      const clamped = Math.min(5, Math.max(0.25, rate));
      const rounded = Math.round(clamped * 100) / 100;
      const video = videoRef.current;
      if (video) video.playbackRate = rounded;
      setPlaybackRateState(rounded);
    },
    [videoRef]
  );

  return { currentTime, duration, isPlaying, playbackRate, seekTo, togglePlay, setPlaybackRate };
};
