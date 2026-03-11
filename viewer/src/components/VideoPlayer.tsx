import { RefObject } from "react";

interface VideoPlayerProps {
  readonly videoRef: RefObject<HTMLVideoElement | null>;
  readonly sessionKey: string;
}

export const VideoPlayer = ({ videoRef, sessionKey }: VideoPlayerProps) => (
  <video ref={videoRef} className="video-player" controls preload="metadata">
    <source src={`/video/${sessionKey}.mp4`} type="video/mp4" />
    <source src={`/video/${sessionKey}.webm`} type="video/webm" />
  </video>
);
