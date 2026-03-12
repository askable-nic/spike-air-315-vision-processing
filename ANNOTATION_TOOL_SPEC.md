# Annotation Tool Spec

A web app for manually annotating key events in session screen recordings, producing baseline event data for evaluating extraction quality.

## Layout

Split-panel UI, similar to the existing viewer:

- **Left panel**: Video player showing the normalised screen track
- **Right panel**: Event editor — list of annotated events plus tools for creating/editing them
- **Bottom bar**: Timeline scrubber with event markers

Panels are resizable via drag handle (reuse the existing viewer pattern). The video player supports Picture-in-Picture so the annotator can keep it visible while scrolling through events.

## Navigation

```
/annotate                          → Session picker
/annotate/:sessionId               → Annotation workspace
```

The session picker lists all sessions from `manifest.json`. Each entry shows session identifier, participant name, study name, and whether a baseline file already exists for it.

## Video Player (left panel)

Plays the **normalised screen track** (`screen_tracks_normalized/{id}.mp4`).

Displayed timestamp = video playback position + `screenTrackStartOffset` from the manifest. All event times are stored/displayed in this offset-adjusted coordinate system (milliseconds relative to the full session / transcript start), matching the format used by the extraction pipeline.

The player shows:
- Standard playback controls (play/pause, seek, speed)
- Current timestamp in offset-adjusted ms
- Frame-step buttons (forward/back one frame)
- A **crosshair overlay** when coordinate-pick mode is active

### Coordinate picking

When the user activates coordinate-pick mode (toggle button or hold a modifier key), clicking on the video captures the click position as pixel coordinates relative to the video's native resolution (not the displayed size). The picked coordinates are written into whichever event field is currently awaiting a coordinate value (e.g. `cursor_position`).

## Event Editor (right panel)

### Event list

A scrollable list of all annotated events, ordered by `time_start`. Each row shows:
- Event type (colour-coded chip)
- Time range (`time_start` – `time_end`, formatted as `mm:ss.mmm`)
- Truncated description
- Confidence badge

The currently-playing event is highlighted. Clicking an event selects it for editing and seeks the video to its `time_start`. The list auto-scrolls to keep the current-time event visible during playback.

### Event form

When an event is selected, its full fields are editable in a form below the list:

| Field | Input | Notes |
|---|---|---|
| `type` | Dropdown | Enum from event-schema.json |
| `time_start` | Number input + **"Set from video"** button | Button captures current video time (offset-adjusted) |
| `time_end` | Number input + **"Set from video"** button | Same |
| `description` | Textarea | Free text |
| `confidence` | Slider 0–1 | Stepped at 0.05 |
| `cursor_position` | x/y number inputs + **"Pick from video"** button | Activates crosshair overlay, next click fills x/y |
| `interaction_target` | Text input | |
| `page_title` | Text input | |
| `page_location` | Text input | |
| `viewport_width` | Number input | Auto-populated from video dimensions on first pick |
| `viewport_height` | Number input | Auto-populated from video dimensions on first pick |
| `frame_description` | Textarea + **"Generate"** button | See AI-assisted description below |

Fields that are empty/null are hidden by default behind a "+ Add field" control to keep the form compact.

### Creating events

- **"+ New Event"** button creates a blank event with `time_start` pre-filled from the current video position
- **Duplicate**: copy an existing event as a starting point
- **Delete**: remove an event (with confirmation)

### AI-assisted frame description

The **"Generate"** button next to `frame_description` sends the current video frame (at the event's `time_start`) to an API endpoint that calls Gemini to describe what's visible on screen. The prompt should ask for a factual description of the UI state — what page is shown, what elements are visible, where the cursor is, etc. The returned description populates the field and can be manually edited.

## Timeline bar (bottom)

Reuse the existing `ProgressBar` component pattern. Enhancements:

- Event markers shown as coloured ticks (coloured by event type)
- Clicking a marker selects that event
- Drag-select a time range to pre-fill `time_start`/`time_end` for a new event

## Data persistence

### File format

Baseline annotations are stored as JSON files at:

```
baselines/{sessionId}/events.json
```

The file is an array of event objects conforming to `event-schema.json`, with two additions:

- `source` is always `"manual_annotation"`
- `transcript_id` and `study_id` are auto-populated from the manifest

### Load / save

- On navigating to a session, if `baselines/{sessionId}/events.json` exists, load it
- Save is explicit: a **"Save"** button writes the current event list to disk via API
- Auto-save draft to `localStorage` on every edit, with a "you have unsaved changes" indicator
- **Export**: download the current event list as JSON

### API endpoints

The annotation tool needs a small backend (can extend the existing Vite dev server or add a lightweight Express/Fastify server):

```
GET  /api/manifest                          → manifest.json contents
GET  /api/baselines/:sessionId              → baseline events (or 404)
PUT  /api/baselines/:sessionId              → write baseline events to disk
POST /api/describe-frame                    → { sessionId, timestampMs } → frame description via Gemini
GET  /video/:sessionId.mp4                  → serve normalised screen track (existing pattern)
```

## Timestamp handling

All timestamps in the UI and stored data are **milliseconds relative to the full session / transcript start** (i.e. the same coordinate system as `events.json` from the extraction pipeline).

Conversion:
```
video_playback_position_ms + screenTrackStartOffset = stored_timestamp_ms
stored_timestamp_ms - screenTrackStartOffset = video_playback_position_ms
```

The UI always displays the offset-adjusted timestamp so it matches transcript times and extracted events. A small label shows the raw video position as well, for debugging.

## Tech stack

Same as the existing viewer:
- React 19 + TypeScript + Vite
- No additional UI framework — plain CSS (follow existing viewer patterns)
- Backend: lightweight Node server (Express or Fastify), or Python FastAPI if closer integration with existing pipeline code is preferred (especially for the Gemini frame description endpoint which could reuse `src/gemini.py`)

## Out of scope (for now)

- Multi-user / collaborative annotation
- Comparing baseline events against extracted events (separate evaluation tool)
- Annotation of the full session video (only normalised screen track)
- Importing extracted events as a starting point (could be added later)
