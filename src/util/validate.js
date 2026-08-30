/**
 * Boundary validators. Every field taken from a vendor response passes through
 * one of these. They throw ProviderParseError with a field path rather than
 * letting a null or a string silently become NaN three layers downstream.
 *
 * Vendors disagree about types for the same concept: Crypto.com returns prices
 * and quantities as STRINGS, FMP returns them as NUMBERS. `finiteNum` accepts
 * either and rejects everything else, which is why it exists rather than a
 * bare `Number()` call at each site.
 */
import { ProviderParseError } from './errors.js';

/** @param {string} msg @param {string} path @param {string|null} providerId */
function fail(msg, path, providerId) {
  throw new ProviderParseError(`${path}: ${msg}`, { fieldPath: path, providerId });
}

/**
 * A finite number, accepting a numeric string. Rejects null, undefined, '',
 * booleans, NaN and Infinity. Booleans are rejected explicitly because
 * Number(true) === 1 would otherwise sail through.
 * @param {unknown} v @param {string} path @param {string|null} [providerId]
 * @returns {number}
 */
export function finiteNum(v, path, providerId = null) {
  if (typeof v === 'number') {
    if (!Number.isFinite(v)) fail(`expected finite number, got ${v}`, path, providerId);
    return v;
  }
  if (typeof v === 'string') {
    const t = v.trim();
    if (t === '') fail('expected number, got empty string', path, providerId);
    const n = Number(t);
    if (!Number.isFinite(n)) fail(`expected numeric string, got ${JSON.stringify(v)}`, path, providerId);
    return n;
  }
  fail(`expected number, got ${v === null ? 'null' : typeof v}`, path, providerId);
}

/** Finite and >= 0. Sizes and volumes must never be negative. */
export function nonNegNum(v, path, providerId = null) {
  const n = finiteNum(v, path, providerId);
  if (n < 0) fail(`expected non-negative, got ${n}`, path, providerId);
  return n;
}

/** Finite and > 0. Prices must be strictly positive. */
export function posNum(v, path, providerId = null) {
  const n = finiteNum(v, path, providerId);
  if (n <= 0) fail(`expected positive, got ${n}`, path, providerId);
  return n;
}

/**
 * Optional finite number: null/undefined/'' pass through as null.
 * Absent is null, never 0 — an absent volume and a zero volume differ.
 */
export function optNum(v, path, providerId = null) {
  if (v === null || v === undefined || v === '') return null;
  return finiteNum(v, path, providerId);
}

/** @returns {string} */
export function str(v, path, providerId = null) {
  if (typeof v !== 'string') fail(`expected string, got ${v === null ? 'null' : typeof v}`, path, providerId);
  return v;
}

/** @returns {unknown[]} */
export function arr(v, path, providerId = null) {
  if (!Array.isArray(v)) fail(`expected array, got ${v === null ? 'null' : typeof v}`, path, providerId);
  return v;
}

/** A non-null, non-array object. */
export function obj(v, path, providerId = null) {
  if (v === null || typeof v !== 'object' || Array.isArray(v)) {
    fail(`expected object, got ${v === null ? 'null' : Array.isArray(v) ? 'array' : typeof v}`, path, providerId);
  }
  return /** @type {Record<string, unknown>} */ (v);
}

/**
 * Normalize a vendor timestamp to integer ms since epoch.
 * Handles: ISO-8601 string (Crypto.com), unix SECONDS (FMP), unix MILLIS
 * (Binance). Seconds vs millis is disambiguated by magnitude — anything below
 * 1e11 is seconds, which holds until the year 5138.
 * @returns {number}
 */
export function tsMs(v, path, providerId = null) {
  if (typeof v === 'string') {
    const t = v.trim();
    if (/^-?\d+$/.test(t)) return tsMs(Number(t), path, providerId);
    const ms = Date.parse(t);
    if (!Number.isFinite(ms)) fail(`unparseable timestamp ${JSON.stringify(v)}`, path, providerId);
    return ms;
  }
  const n = finiteNum(v, path, providerId);
  if (n <= 0) fail(`expected positive timestamp, got ${n}`, path, providerId);
  return Math.round(n < 1e11 ? n * 1000 : n);
}

/** Parse a raw HTTP body as JSON, reporting the provider and a body excerpt. */
export function parseJson(body, path, providerId = null) {
  if (typeof body !== 'string') fail('response body was not text', path, providerId);
  try {
    return JSON.parse(body);
  } catch (err) {
    const head = body.slice(0, 120).replace(/\s+/g, ' ');
    throw new ProviderParseError(`${path}: response was not valid JSON (starts: ${head})`, {
      fieldPath: path, providerId, cause: err,
    });
  }
}
