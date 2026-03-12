export type EventType =
  | "click"
  | "hover"
  | "navigate"
  | "input_text"
  | "select"
  | "dwell"
  | "cursor_thrash"
  | "scroll"
  | "drag"
  | "hesitate"
  | "change_ui_state";

export const EVENT_TYPES: readonly EventType[] = [
  "click",
  "hover",
  "navigate",
  "input_text",
  "select",
  "dwell",
  "cursor_thrash",
  "scroll",
  "drag",
  "hesitate",
  "change_ui_state",
] as const;

export type SourceType =
  | "unmod_website_test_video"
  | "ai_mod_website_test_video"
  | "moderated_screen_recording"
  | "unmod_figma_prototype_test"
  | "unmod_tree_test"
  | "unmod_card_sort"
  | "manual_annotation";

export interface CursorPosition {
  readonly x: number;
  readonly y: number;
}

export interface BoundingBox {
  readonly x: number;
  readonly y: number;
  readonly width: number;
  readonly height: number;
}

export interface AnnotationMetadata {
  readonly interaction_target_bbox?: BoundingBox;
}

export interface AnnotationEvent {
  readonly type: EventType;
  readonly source: string;
  readonly time_start: number;
  readonly time_end: number | null;
  readonly description: string;
  readonly transcript_id: string;
  readonly study_id?: string;
  readonly task_id?: string;
  readonly interaction_target?: string;
  readonly cursor_position?: CursorPosition;
  readonly page_title?: string;
  readonly page_location?: string;
  readonly viewport_width?: number;
  readonly viewport_height?: number;
  readonly frame_description?: string;
  readonly _metadata?: AnnotationMetadata;
}

export interface ManifestSession {
  readonly identifier: string;
  readonly team: string;
  readonly study: string;
  readonly studyId: string;
  readonly roomId: string;
  readonly participant: string;
  readonly userId: readonly string[];
  readonly screenTrackStartOffset: number;
  readonly data: {
    readonly fullSession: string;
    readonly screenTrack: string;
    readonly transcript: string;
    readonly normalizedScreenTrack?: string;
  };
  readonly hasBaseline?: boolean;
}
