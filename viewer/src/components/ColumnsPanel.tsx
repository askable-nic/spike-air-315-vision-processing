import { useState, useCallback } from "react";
import { SessionData, ColumnDef } from "../types";
import { TranscriptColumn } from "./TranscriptColumn";
import { ScenesColumn } from "./ScenesColumn";
import { EventsColumn } from "./EventsColumn";
import "./ColumnsPanel.css";

interface ColumnsPanelProps {
  readonly columns: SessionData;
  readonly currentTime: number;
  readonly duration: number;
  readonly seekTo: (seconds: number) => void;
}

const getColumnTitle = (col: ColumnDef): string => {
  switch (col.type) {
    case "speaker_utterances":
      return col.title;
    case "scenes":
      return "Scenes";
    case "events":
      return col.title ?? "Events";
  }
};

const renderColumn = (
  col: ColumnDef,
  currentTime: number,
  duration: number,
  seekTo: (seconds: number) => void,
  index: number,
) => {
  switch (col.type) {
    case "speaker_utterances":
      return (
        <TranscriptColumn
          key={index}
          utterances={col.utterances}
          currentTime={currentTime}
          duration={duration}
          seekTo={seekTo}
        />
      );
    case "scenes":
      return (
        <ScenesColumn
          key={index}
          scenes={col.scenes}
          currentTime={currentTime}
          duration={duration}
          seekTo={seekTo}
        />
      );
    case "events":
      return (
        <EventsColumn
          key={index}
          events={col.events}
          currentTime={currentTime}
          duration={duration}
          seekTo={seekTo}
        />
      );
  }
};

export const ColumnsPanel = ({ columns, currentTime, duration, seekTo }: ColumnsPanelProps) => {
  const [collapsed, setCollapsed] = useState<ReadonlySet<number>>(new Set());

  const toggle = useCallback((index: number) => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  }, []);

  return (
    <div className="columns-panel">
      {columns.map((col, i) =>
        collapsed.has(i) ? (
          <div key={i} className="column--collapsed" onClick={() => toggle(i)}>
            <div className="column__collapsed-label">
              {getColumnTitle(col)}
            </div>
          </div>
        ) : (
          <div key={i} className="column--wrapper">
            <div className="column__header">
              <span className="column__header-title">{getColumnTitle(col)}</span>
              <button
                className="column__collapse-btn"
                onClick={() => toggle(i)}
                title="Collapse column"
              >
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <path d="M9 3L5 7L9 11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </button>
            </div>
            {renderColumn(col, currentTime, duration, seekTo, i)}
          </div>
        ),
      )}
    </div>
  );
};
