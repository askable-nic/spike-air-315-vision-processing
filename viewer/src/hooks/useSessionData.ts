import { useState, useEffect } from "react";
import { SessionData } from "../types";
import { fetchSessionData } from "../lib/dataLoaders";

interface UseSessionDataResult {
  readonly data: SessionData | null;
  readonly loading: boolean;
  readonly error: string | null;
}

export const useSessionData = (
  branch: string,
  iteration: string,
  key: string
): UseSessionDataResult => {
  const [data, setData] = useState<SessionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setData(null);

    fetchSessionData(branch, iteration, key)
      .then((columns) => {
        if (!cancelled) setData(columns);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [branch, iteration, key]);

  return { data, loading, error };
};
