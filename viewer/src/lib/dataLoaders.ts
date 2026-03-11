import { SessionData } from "../types";

export interface Experiment {
  readonly branch: string;
  readonly iteration: string;
}

export const fetchExperiments = async (): Promise<readonly Experiment[]> => {
  const res = await fetch("/api/experiments");
  if (!res.ok) throw new Error(`Failed to load experiments: ${res.status}`);
  return res.json();
};

export const fetchSessions = async (
  branch: string,
  iteration: string
): Promise<readonly string[]> => {
  const res = await fetch(`/api/sessions/${branch}/${iteration}`);
  if (!res.ok) throw new Error(`Failed to load sessions: ${res.status}`);
  return res.json();
};

export const fetchSessionData = async (
  branch: string,
  iteration: string,
  key: string
): Promise<SessionData> => {
  const res = await fetch(`/api/data/${branch}/${iteration}/${key}`);
  if (!res.ok) throw new Error(`Failed to load session data: ${res.status}`);
  return res.json();
};
