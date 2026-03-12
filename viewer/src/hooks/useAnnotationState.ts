import { useState, useEffect, useCallback, useRef } from "react";
import { AnnotationEvent, EventType } from "../annotationTypes";
export type { EventType } from "../annotationTypes";
import { fetchBaseline, saveBaseline } from "../lib/annotationApi";

interface UseAnnotationStateOptions {
  readonly sessionId: string;
  readonly transcriptId: string;
  readonly studyId?: string;
}

export interface AnnotationState {
  readonly events: readonly AnnotationEvent[];
  readonly selectedEventIndex: number | null;
  readonly isDirty: boolean;
  readonly isLoading: boolean;
  readonly error: string | null;
  readonly selectEvent: (index: number | null) => void;
  readonly updateEvent: (index: number, partial: Partial<AnnotationEvent>) => void;
  readonly addEvent: (timeStartMs: number, type?: EventType, viewport?: { width: number; height: number }) => void;
  readonly duplicateEvent: (index: number) => void;
  readonly deleteEvent: (index: number) => void;
  readonly save: () => Promise<void>;
  readonly exportJson: () => void;
}

const DRAFT_KEY = (id: string) => `annotation-draft-${id}`;

const sortByTime = (events: readonly AnnotationEvent[]): readonly AnnotationEvent[] =>
  [...events].sort((a, b) => a.time_start - b.time_start);

export const useAnnotationState = ({
  sessionId,
  transcriptId,
  studyId,
}: UseAnnotationStateOptions): AnnotationState => {
  const [events, setEvents] = useState<readonly AnnotationEvent[]>([]);
  const [selectedEventIndex, setSelectedEventIndex] = useState<number | null>(null);
  const [isDirty, setIsDirty] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const initialized = useRef(false);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    const load = async () => {
      try {
        const baseline = await fetchBaseline(sessionId);
        if (baseline) {
          setEvents(sortByTime(baseline));
          setIsLoading(false);
          return;
        }

        const draft = localStorage.getItem(DRAFT_KEY(sessionId));
        if (draft) {
          setEvents(sortByTime(JSON.parse(draft)));
          setIsDirty(true);
          setIsLoading(false);
          return;
        }

        setEvents([]);
        setIsLoading(false);
      } catch (err) {
        setError(String(err));
        setIsLoading(false);
      }
    };

    load();
  }, [sessionId]);

  const persistDraft = useCallback(
    (updated: readonly AnnotationEvent[]) => {
      localStorage.setItem(DRAFT_KEY(sessionId), JSON.stringify(updated));
    },
    [sessionId]
  );

  const mutate = useCallback(
    (updater: (prev: readonly AnnotationEvent[]) => readonly AnnotationEvent[]) => {
      setEvents((prev) => {
        const next = sortByTime(updater(prev));
        persistDraft(next);
        setIsDirty(true);
        return next;
      });
    },
    [persistDraft]
  );

  const selectEvent = useCallback((index: number | null) => {
    setSelectedEventIndex(index);
  }, []);

  const updateEvent = useCallback(
    (index: number, partial: Partial<AnnotationEvent>) => {
      mutate((prev) =>
        prev.map((evt, i) => (i === index ? { ...evt, ...partial } : evt))
      );
    },
    [mutate]
  );

  const addEvent = useCallback(
    (timeStartMs: number, type: EventType = "click", viewport?: { width: number; height: number }) => {
      const newEvent: AnnotationEvent = {
        type,
        source: "manual_annotation",
        time_start: timeStartMs,
        time_end: null,
        description: "",
        transcript_id: transcriptId,
        ...(studyId ? { study_id: studyId } : {}),
        ...(viewport ? { viewport_width: viewport.width, viewport_height: viewport.height } : {}),
      };
      mutate((prev) => {
        const next = [...prev, newEvent];
        const sorted = sortByTime(next);
        const newIndex = sorted.indexOf(newEvent);
        setTimeout(() => setSelectedEventIndex(newIndex), 0);
        return next;
      });
    },
    [mutate, transcriptId, studyId]
  );

  const duplicateEvent = useCallback(
    (index: number) => {
      mutate((prev) => {
        const source = prev[index];
        if (!source) return prev;
        const dupe = { ...source, time_start: source.time_start + 100 };
        const next = [...prev, dupe];
        const sorted = sortByTime(next);
        const newIndex = sorted.indexOf(dupe);
        setTimeout(() => setSelectedEventIndex(newIndex), 0);
        return next;
      });
    },
    [mutate]
  );

  const deleteEvent = useCallback(
    (index: number) => {
      mutate((prev) => prev.filter((_, i) => i !== index));
      setSelectedEventIndex(null);
    },
    [mutate]
  );

  const save = useCallback(async () => {
    try {
      await saveBaseline(sessionId, events);
      setIsDirty(false);
      localStorage.removeItem(DRAFT_KEY(sessionId));
    } catch (err) {
      setError(String(err));
    }
  }, [sessionId, events]);

  const exportJson = useCallback(() => {
    const blob = new Blob([JSON.stringify(events, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${sessionId}-baseline.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [events, sessionId]);

  return {
    events,
    selectedEventIndex,
    isDirty,
    isLoading,
    error,
    selectEvent,
    updateEvent,
    addEvent,
    duplicateEvent,
    deleteEvent,
    save,
    exportJson,
  };
};
