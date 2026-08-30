/** UTC bucket math. All boundaries are wall-clock UTC so snapshots from
 *  separate runs land in the same time buckets and a heat map stitches
 *  across restarts. */

export const MINUTE_MS = 60_000;
export const FIFTEEN_MIN_MS = 15 * MINUTE_MS;
export const DAY_MS = 24 * 60 * MINUTE_MS;

/** Largest multiple of `sizeMs` <= ts. */
export function floorTo(ts, sizeMs) {
  if (!Number.isFinite(ts) || !Number.isFinite(sizeMs) || sizeMs <= 0) {
    throw new RangeError(`floorTo(${ts}, ${sizeMs}): both must be finite, size > 0`);
  }
  return Math.floor(ts / sizeMs) * sizeMs;
}

/** Smallest multiple of `sizeMs` strictly greater than ts (the next boundary). */
export function nextBoundary(ts, sizeMs) {
  return floorTo(ts, sizeMs) + sizeMs;
}

/** 'YYYY-MM-DD' in UTC — the day-file key. */
export function dayKey(ts) {
  return new Date(ts).toISOString().slice(0, 10);
}

/** Midnight UTC of the day containing ts. CVD resets here. */
export function startOfUtcDay(ts) {
  return floorTo(ts, DAY_MS);
}

/** Inclusive list of 'YYYY-MM-DD' keys spanning [fromTs, toTs]. */
export function dayKeysInRange(fromTs, toTs) {
  const keys = [];
  for (let d = startOfUtcDay(fromTs); d <= toTs; d += DAY_MS) keys.push(dayKey(d));
  return keys;
}

export function toIso(ts) {
  return new Date(ts).toISOString();
}

/** 'HH:MM' UTC, for compact table and heat-map axes. */
export function hhmm(ts) {
  return new Date(ts).toISOString().slice(11, 16);
}

/** Human duration for reports: 1500 -> '1.5s', 90000 -> '1m30s'. */
export function humanMs(ms) {
  if (!Number.isFinite(ms)) return 'n/a';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;
  const m = Math.floor(ms / 60_000);
  const s = Math.round((ms % 60_000) / 1000);
  return `${m}m${String(s).padStart(2, '0')}s`;
}
