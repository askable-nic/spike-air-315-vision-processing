import { SessionData } from "../types";
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

export const ColumnsPanel = ({ columns, currentTime, duration, seekTo }: ColumnsPanelProps) => (
  <div className="columns-panel">
    {columns.map((col, i) => {
      switch (col.type) {
        case "speaker_utterances":
          return (
            <TranscriptColumn
              key={i}
              title={col.title}
              utterances={col.utterances}
              currentTime={currentTime}
              duration={duration}
              seekTo={seekTo}
            />
          );
        case "scenes":
          return (
            <ScenesColumn
              key={i}
              scenes={col.scenes}
              currentTime={currentTime}
              duration={duration}
              seekTo={seekTo}
            />
          );
        case "events":
          return (
            <EventsColumn
              key={i}
              title={col.title}
              events={col.events}
              currentTime={currentTime}
              duration={duration}
              seekTo={seekTo}
            />
          );
      }
    })}
  </div>
);
