import { AnnotationEvent, ManifestSession } from "../annotationTypes";

export const fetchManifest = async (): Promise<readonly ManifestSession[]> => {
  const res = await fetch("/api/manifest");
  if (!res.ok) throw new Error(`Failed to load manifest: ${res.status}`);
  return res.json();
};

export const fetchBaseline = async (
  sessionId: string
): Promise<readonly AnnotationEvent[] | null> => {
  const res = await fetch(`/api/baselines/${encodeURIComponent(sessionId)}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Failed to load baseline: ${res.status}`);
  return res.json();
};

export const saveBaseline = async (
  sessionId: string,
  events: readonly AnnotationEvent[]
): Promise<void> => {
  const res = await fetch(`/api/baselines/${encodeURIComponent(sessionId)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(events),
  });
  if (!res.ok) throw new Error(`Failed to save baseline: ${res.status}`);
};

export const describeFrame = async (
  sessionId: string,
  timestampMs: number
): Promise<string> => {
  const res = await fetch("/api/describe-frame", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sessionId, timestampMs }),
  });
  if (!res.ok) throw new Error(`Failed to describe frame: ${res.status}`);
  const data = await res.json();
  return data.description;
};
