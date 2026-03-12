import { defineConfig, Plugin } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import fs from "fs";
import { execFile } from "child_process";
import { IncomingMessage, ServerResponse } from "http";

const projectRoot = path.resolve(__dirname, "..");
const experimentsDir = path.join(projectRoot, "experiments");
const inputDataDir = path.join(projectRoot, "input_data");
const baselinesDir = path.join(projectRoot, "baselines");

interface RawEvent {
  readonly type: string;
  readonly time_start: number;
  readonly time_end: number | null;
  readonly description: string;
  readonly confidence?: number;
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
  time_end: e.time_end != null ? e.time_end / 1000 : null,
  event_type: e.type,
  label: e.description,
  confidence: e.confidence ?? 0,
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

const readBody = (req: IncomingMessage): Promise<string> =>
  new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    req.on("data", (chunk: Buffer) => chunks.push(chunk));
    req.on("end", () => resolve(Buffer.concat(chunks).toString("utf-8")));
    req.on("error", reject);
  });

const serveVideoFile = (
  filePath: string,
  req: IncomingMessage,
  res: ServerResponse
): void => {
  const ext = path.extname(filePath).toLowerCase();
  const mimeTypes: Record<string, string> = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
  };
  res.setHeader("Content-Type", mimeTypes[ext] || "application/octet-stream");

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

          const baselinePath = path.join(baselinesDir, key, "events.json");
          const baselineColumn = fs.existsSync(baselinePath)
            ? [{
                type: "events" as const,
                title: "Baseline",
                events: (JSON.parse(fs.readFileSync(baselinePath, "utf-8")) as readonly RawEvent[]).map(transformEvent),
              }]
            : [];

          const columns = [...speakerColumns, { type: "events", title: "Events", events }, ...baselineColumn];

          res.setHeader("Content-Type", "application/json");
          res.end(JSON.stringify(columns));
          return;
        }

        // GET /video/:filename — serve video from input_data/full_sessions/
        if (url.pathname.startsWith("/video/") && !url.pathname.startsWith("/video/normalized/")) {
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

          serveVideoFile(filePath, req, res);
          return;
        }

        // GET /video/normalized/:filename — serve from input_data/screen_tracks_normalized/
        if (url.pathname.startsWith("/video/normalized/")) {
          const filename = decodeURIComponent(url.pathname.slice("/video/normalized/".length));
          const filePath = path.join(inputDataDir, "screen_tracks_normalized", filename);

          if (!filePath.startsWith(path.join(inputDataDir, "screen_tracks_normalized"))) {
            res.statusCode = 403;
            res.end("Forbidden");
            return;
          }

          if (!fs.existsSync(filePath)) {
            next();
            return;
          }

          serveVideoFile(filePath, req, res);
          return;
        }

        // GET /api/manifest — return manifest with hasBaseline per session
        if (url.pathname === "/api/manifest") {
          const manifestPath = path.join(inputDataDir, "manifest.json");
          if (!fs.existsSync(manifestPath)) {
            res.statusCode = 404;
            res.setHeader("Content-Type", "application/json");
            res.end(JSON.stringify({ error: "Manifest not found" }));
            return;
          }

          const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf-8"));
          const withBaseline = manifest.map((session: { identifier: string }) => ({
            ...session,
            hasBaseline: fs.existsSync(
              path.join(baselinesDir, session.identifier, "events.json")
            ),
          }));

          res.setHeader("Content-Type", "application/json");
          res.end(JSON.stringify(withBaseline));
          return;
        }

        // GET/PUT /api/baselines/:sessionId
        const baselinesMatch = url.pathname.match(/^\/api\/baselines\/([^/]+)$/);
        if (baselinesMatch) {
          const sessionId = decodeURIComponent(baselinesMatch[1]);
          const eventsPath = path.join(baselinesDir, sessionId, "events.json");

          if (req.method === "GET") {
            if (!fs.existsSync(eventsPath)) {
              res.statusCode = 404;
              res.setHeader("Content-Type", "application/json");
              res.end(JSON.stringify({ error: "Baseline not found" }));
              return;
            }
            res.setHeader("Content-Type", "application/json");
            res.end(fs.readFileSync(eventsPath, "utf-8"));
            return;
          }

          if (req.method === "PUT") {
            readBody(req).then((body) => {
              const dir = path.join(baselinesDir, sessionId);
              if (!fs.existsSync(dir)) {
                fs.mkdirSync(dir, { recursive: true });
              }
              fs.writeFileSync(eventsPath, body, "utf-8");
              res.setHeader("Content-Type", "application/json");
              res.end(JSON.stringify({ ok: true }));
            }).catch((err) => {
              res.statusCode = 500;
              res.setHeader("Content-Type", "application/json");
              res.end(JSON.stringify({ error: String(err) }));
            });
            return;
          }
        }

        // POST /api/describe-frame
        if (url.pathname === "/api/describe-frame" && req.method === "POST") {
          readBody(req).then((body) => {
            const { sessionId, timestampMs } = JSON.parse(body);

            execFile(
              "python3",
              ["-m", "src.cli", "describe-frame", "--session", sessionId, "--timestamp", String(timestampMs), "--base-dir", projectRoot],
              { cwd: projectRoot, timeout: 30000 },
              (error, stdout, stderr) => {
                if (error) {
                  res.statusCode = 500;
                  res.setHeader("Content-Type", "application/json");
                  res.end(JSON.stringify({ error: stderr || error.message }));
                  return;
                }
                res.setHeader("Content-Type", "application/json");
                res.end(stdout);
              }
            );
          }).catch((err) => {
            res.statusCode = 500;
            res.setHeader("Content-Type", "application/json");
            res.end(JSON.stringify({ error: String(err) }));
          });
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
