export const msToSeconds = (ms: number): number => ms / 1000;

export const formatTime = (seconds: number): string => {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
};

export const isInRange = (
  current: number,
  start: number,
  end: number
): boolean => current >= start && current < end;

export interface TimeRange {
  readonly start: number;
  readonly end: number;
}

const GAP_THRESHOLD_S = 3;

interface FindGapsOptions {
  readonly threshold?: number;
  readonly boundsStart?: number;
  readonly boundsEnd?: number;
}

export const findGaps = (
  ranges: readonly TimeRange[],
  options: FindGapsOptions = {},
): readonly TimeRange[] => {
  const { threshold = GAP_THRESHOLD_S, boundsStart = 0, boundsEnd } = options;

  const between = ranges.reduce<readonly TimeRange[]>(
    (gaps, range, i) =>
      i === 0
        ? gaps
        : range.start - ranges[i - 1].end > threshold
          ? [...gaps, { start: ranges[i - 1].end, end: range.start }]
          : gaps,
    [],
  );

  const leadingEnd = ranges.length > 0 ? ranges[0].start : boundsEnd ?? boundsStart;
  const leading = [{ start: boundsStart, end: leadingEnd }];

  const trailingStart = ranges.length > 0 ? ranges[ranges.length - 1].end : boundsStart;
  const trailing =
    boundsEnd !== undefined ? [{ start: trailingStart, end: boundsEnd }] : [];

  return [...leading, ...between, ...trailing];
};
