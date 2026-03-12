import { useState, useCallback, useRef } from "react";
import { BoundingBox } from "../annotationTypes";

export type PickMode = "none" | "point" | "region";

export interface CoordinatePickState {
  readonly pickMode: PickMode;
  readonly isPickMode: boolean;
  readonly dragBox: BoundingBox | null;
  readonly startPick: () => void;
  readonly startRegionPick: () => void;
  readonly cancelPick: () => void;
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
}

const clientToVideo = (
  clientX: number,
  clientY: number,
  video: HTMLVideoElement
): { x: number; y: number } | null => {
  const rect = video.getBoundingClientRect();
  const nativeW = video.videoWidth;
  const nativeH = video.videoHeight;

  if (nativeW === 0 || nativeH === 0) return null;

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

  const renderedLeft = rect.left + (elementW - renderedW) / 2;
  const renderedTop = rect.top + (elementH - renderedH) / 2;

  const relX = clientX - renderedLeft;
  const relY = clientY - renderedTop;

  const x = Math.round(Math.max(0, Math.min(nativeW, (relX / renderedW) * nativeW)));
  const y = Math.round(Math.max(0, Math.min(nativeH, (relY / renderedH) * nativeH)));

  return { x, y };
};

export const useCoordinatePick = (): CoordinatePickState => {
  const [pickMode, setPickMode] = useState<PickMode>("none");
  const [dragBox, setDragBox] = useState<BoundingBox | null>(null);
  const dragStart = useRef<{ x: number; y: number } | null>(null);

  const isPickMode = pickMode !== "none";

  const startPick = useCallback(() => setPickMode("point"), []);
  const startRegionPick = useCallback(() => setPickMode("region"), []);
  const cancelPick = useCallback(() => {
    setPickMode("none");
    setDragBox(null);
    dragStart.current = null;
  }, []);

  const onVideoClick = useCallback(
    (
      clientX: number,
      clientY: number,
      videoElement: HTMLVideoElement
    ): { x: number; y: number } | null => {
      if (pickMode !== "point") return null;
      const coords = clientToVideo(clientX, clientY, videoElement);
      if (coords) setPickMode("none");
      return coords;
    },
    [pickMode]
  );

  const onVideoMouseDown = useCallback(
    (clientX: number, clientY: number, videoElement: HTMLVideoElement) => {
      if (pickMode !== "region") return;
      const coords = clientToVideo(clientX, clientY, videoElement);
      if (coords) {
        dragStart.current = coords;
        setDragBox(null);
      }
    },
    [pickMode]
  );

  const onVideoMouseMove = useCallback(
    (clientX: number, clientY: number, videoElement: HTMLVideoElement) => {
      if (pickMode !== "region" || !dragStart.current) return;
      const coords = clientToVideo(clientX, clientY, videoElement);
      if (!coords) return;
      const start = dragStart.current;
      const x = Math.min(start.x, coords.x);
      const y = Math.min(start.y, coords.y);
      const width = Math.abs(coords.x - start.x);
      const height = Math.abs(coords.y - start.y);
      setDragBox({ x, y, width, height });
    },
    [pickMode]
  );

  const onVideoMouseUp = useCallback(
    (clientX: number, clientY: number, videoElement: HTMLVideoElement): BoundingBox | null => {
      if (pickMode !== "region" || !dragStart.current) return null;
      const coords = clientToVideo(clientX, clientY, videoElement);
      if (!coords) {
        dragStart.current = null;
        setDragBox(null);
        return null;
      }
      const start = dragStart.current;
      const x = Math.min(start.x, coords.x);
      const y = Math.min(start.y, coords.y);
      const width = Math.abs(coords.x - start.x);
      const height = Math.abs(coords.y - start.y);
      dragStart.current = null;

      if (width < 5 || height < 5) {
        setDragBox(null);
        return null;
      }

      const box = { x, y, width, height };
      setDragBox(null);
      setPickMode("none");
      return box;
    },
    [pickMode]
  );

  return {
    pickMode,
    isPickMode,
    dragBox,
    startPick,
    startRegionPick,
    cancelPick,
    onVideoClick,
    onVideoMouseDown,
    onVideoMouseMove,
    onVideoMouseUp,
  };
};
