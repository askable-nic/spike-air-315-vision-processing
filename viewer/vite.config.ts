import { defineConfig, Plugin } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import fs from "fs";

const projectRoot = path.resolve(__dirname, "..");
const experimentsDir = path.join(projectRoot, "experiments");
const inputDataDir = path.join(projectRoot, "input_data");

interface RawEvent {
  readonly type: string;
  readonly time_start: number;
  readonly time_end: number;
  readonly description: string;
  readonly confidence: number;
  readonly frame_description?: string;
  readonly page_location?: string;
  readonly page_title?: string;
  readonly interaction_target?: string;
}

interface RawUtterance {
  readonly start: number;
  readonly end: number;
  readonly text: string;
  readonly speaker?: { readonly label?: string };
}

const transformEvent = (e: RawEvent) => ({
  time_start: e.time_start / 1000,
  time_end: e.time_end / 1000,
  event_type: e.type,
  label: e.description,
  confidence: e.confidence,
  frame_description: e.frame_description,
  url: e.page_location,
  page_title: e.page_title,
  interaction_target: e.interaction_target,
});

const groupTranscript = (utterances: readonly RawUtterance[]) => {
  const groups = new Map<string, Array<{ start: number; end: number; text: string }>>();
  for (const u of utterances) {
    const label = u.speaker?.label ?? "Unknown";
    const list = groups.get(label) ?? [];
    list.push({ start: u.start, end: u.end, text: u.text });
    groups.set(label, list);
  }
  return [...groups.entries()].map(([title, utts]) => ({
    type: "speaker_utterances" as const,
    title,
    utterances: utts,
  }));
};

function dataServerPlugin(): Plugin {
  return {
    name: "data-server",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const url = new URL(req.url!, `http://${req.headers.host}`);

        // GET /api/experiments — list available branch/iteration combos
        if (url.pathname === "/api/experiments") {
          const result: Array<{ branch: string; iteration: string }> = [];
          if (fs.existsSync(experimentsDir)) {
            for (const branch of fs.readdirSync(experimentsDir).sort()) {
              const branchPath = path.join(experimentsDir, branch);
              if (!fs.statSync(branchPath).isDirectory()) continue;
              for (const iteration of fs.readdirSync(branchPath).sort()) {
                const iterPath = path.join(branchPath, iteration, "output");
                if (fs.existsSync(iterPath) && fs.statSync(iterPath).isDirectory()) {
                  result.push({ branch, iteration });
                }
              }
            }
          }
          res.setHeader("Content-Type", "application/json");
          res.end(JSON.stringify(result));
          return;
        }

        // GET /api/sessions/:branch/:iteration — list session keys
        const sessionsMatch = url.pathname.match(/^\/api\/sessions\/([^/]+)\/([^/]+)$/);
        if (sessionsMatch) {
          const [, branch, iteration] = sessionsMatch;
          const outputDir = path.join(experimentsDir, branch, iteration, "output");
          if (!fs.existsSync(outputDir)) {
            res.setHeader("Content-Type", "application/json");
            res.end(JSON.stringify([]));
            return;
          }
          const sessions = fs.readdirSync(outputDir)
            .filter((d) => {
              const eventsPath = path.join(outputDir, d, "events.json");
              return fs.existsSync(eventsPath);
            })
            .sort();
          res.setHeader("Content-Type", "application/json");
          res.end(JSON.stringify(sessions));
          return;
        }

        // GET /api/data/:branch/:iteration/:key — transformed session data
        const dataMatch = url.pathname.match(/^\/api\/data\/([^/]+)\/([^/]+)\/([^/]+)$/);
        if (dataMatch) {
          const [, branch, iteration, key] = dataMatch;
          const eventsPath = path.join(
            experimentsDir, branch, iteration, "output", key, "events.json"
          );

          if (!fs.existsSync(eventsPath)) {
            res.statusCode = 404;
            res.setHeader("Content-Type", "application/json");
            res.end(JSON.stringify({ error: "Events not found" }));
            return;
          }

          const rawEvents: readonly RawEvent[] = JSON.parse(
            fs.readFileSync(eventsPath, "utf-8")
          );
          const events = rawEvents.map(transformEvent);

          const transcriptPath = path.join(inputDataDir, "transcripts", `${key}.json`);
          const speakerColumns = fs.existsSync(transcriptPath)
            ? groupTranscript(JSON.parse(fs.readFileSync(transcriptPath, "utf-8")))
            : [];

          const columns = [...speakerColumns, { type: "events", events }];

          res.setHeader("Content-Type", "application/json");
          res.end(JSON.stringify(columns));
          return;
        }

        // GET /video/:filename — serve video from input_data/full_sessions/
        if (url.pathname.startsWith("/video/")) {
          const filename = decodeURIComponent(url.pathname.slice("/video/".length));
          const filePath = path.join(inputDataDir, "full_sessions", filename);

          if (!filePath.startsWith(path.join(inputDataDir, "full_sessions"))) {
            res.statusCode = 403;
            res.end("Forbidden");
            return;
          }

          if (!fs.existsSync(filePath)) {
            next();
            return;
          }

          const ext = path.extname(filePath).toLowerCase();
          const mimeTypes: Record<string, string> = {
            ".mp4": "video/mp4",
            ".webm": "video/webm",
          };
          res.setHeader(
            "Content-Type",
            mimeTypes[ext] || "application/octet-stream"
          );

          const stat = fs.statSync(filePath);
          const range = req.headers.range;
          if (range) {
            const parts = range.replace(/bytes=/, "").split("-");
            const start = parseInt(parts[0], 10);
            const end = parts[1] ? parseInt(parts[1], 10) : stat.size - 1;
            res.statusCode = 206;
            res.setHeader("Content-Range", `bytes ${start}-${end}/${stat.size}`);
            res.setHeader("Accept-Ranges", "bytes");
            res.setHeader("Content-Length", end - start + 1);
            fs.createReadStream(filePath, { start, end }).pipe(res);
          } else {
            res.setHeader("Content-Length", stat.size);
            res.setHeader("Accept-Ranges", "bytes");
            fs.createReadStream(filePath).pipe(res);
          }
          return;
        }

        next();
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), dataServerPlugin()],
});
