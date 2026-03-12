export interface Utterance {
  readonly start: number; // milliseconds
  readonly end: number;   // milliseconds
  readonly text: string;
}

export interface Scene {
  readonly start: number; // milliseconds
  readonly end: number;   // milliseconds
  readonly initial_url?: string;
  readonly description?: string;
}

export interface AnalysisEvent {
  readonly time_start: number; // seconds
  readonly time_end: number | null;   // seconds
  readonly event_type: string;
  readonly label: string;
  readonly confidence: number;
  readonly frame_description?: string;
  readonly url?: string;
  readonly page_title?: string;
  readonly interaction_target?: string;
}

export interface SpeakerUtterancesColumn {
  readonly type: "speaker_utterances";
  readonly title: string;
  readonly utterances: readonly Utterance[];
}

export interface ScenesColumn {
  readonly type: "scenes";
  readonly scenes: readonly Scene[];
}

export interface EventsColumn {
  readonly type: "events";
  readonly title?: string;
  readonly events: readonly AnalysisEvent[];
}

export type ColumnDef = SpeakerUtterancesColumn | ScenesColumn | EventsColumn;

export type SessionData = readonly ColumnDef[];
