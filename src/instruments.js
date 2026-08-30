/**
 * Static instrument table. Bucket sizes come from design section 3.3.
 *
 * `providerChain` is primary -> fallback. A provider that cannot serve an
 * instrument (missing env, denied symbol, no fixture) is skipped with a printed
 * reason; it is never replaced by fabricated data.
 */

/**
 * @typedef {Object} Instrument
 * @property {string} id
 * @property {string} label
 * @property {'crypto'|'metal'|'energy'} kind
 * @property {number} bucketSize      price units per heat-map row
 * @property {number[]} bandsBps      imbalance bands, design 3.1
 * @property {string[]} providerChain provider ids, primary first
 * @property {string} priceUnit
 * @property {string[]} notes         caveats that travel with every render
 */

/** @type {Record<string, Instrument>} */
export const INSTRUMENTS = Object.freeze({
  BTCUSD: Object.freeze({
    id: 'BTCUSD',
    label: 'Bitcoin / USD',
    kind: 'crypto',
    bucketSize: 10.0,
    bandsBps: Object.freeze([5, 10, 25, 50]),
    providerChain: Object.freeze(['cryptocom', 'binance']),
    priceUnit: 'USD',
    notes: Object.freeze([
      'BTCUSDT is quoted against a stablecoin, not USD; a few bps of basis applies.',
      'Single venue, not consolidated crypto-wide flow.',
    ]),
  }),

  XAUUSD: Object.freeze({
    id: 'XAUUSD',
    label: 'Gold / USD',
    kind: 'metal',
    bucketSize: 0.5,
    bandsBps: Object.freeze([5, 10, 25, 50]),
    providerChain: Object.freeze(['fmp']),
    priceUnit: 'USD/oz',
    notes: Object.freeze([
      'Spot gold is OTC: no central order book exists anywhere, for anyone.',
      'No bid/ask imbalance, no CVD and no heat map are produced for this instrument.',
    ]),
  }),

  WTI: Object.freeze({
    id: 'WTI',
    label: 'WTI Crude Oil',
    kind: 'energy',
    bucketSize: 0.05,
    bandsBps: Object.freeze([5, 10, 25, 50]),
    providerChain: Object.freeze(['fmp']),
    priceUnit: 'USD/bbl',
    notes: Object.freeze([
      'No retail-accessible order book exists for WTI.',
      'No data source is currently available for this instrument; ticks record an explicit failure.',
    ]),
  }),

  BRENT: Object.freeze({
    id: 'BRENT',
    label: 'Brent Crude Oil',
    kind: 'energy',
    bucketSize: 0.05,
    bandsBps: Object.freeze([5, 10, 25, 50]),
    providerChain: Object.freeze(['fmp']),
    priceUnit: 'USD/bbl',
    notes: Object.freeze([
      'No retail-accessible order book exists for Brent.',
      'Quote only: no depth, no tape, no heat map.',
    ]),
  }),
});

export const ALL_INSTRUMENT_IDS = Object.freeze(Object.keys(INSTRUMENTS));

/** Instruments for which an order book is even theoretically obtainable. */
export const BOOK_CAPABLE_IDS = Object.freeze(['BTCUSD']);

/** @param {string} id @returns {Instrument|null} */
export function getInstrument(id) {
  return INSTRUMENTS[String(id).toUpperCase()] ?? null;
}

/** Resolve a comma list into instruments, throwing on an unknown id. */
export function resolveInstruments(ids) {
  const out = [];
  for (const raw of ids) {
    const inst = getInstrument(raw);
    if (!inst) {
      throw new Error(
        `unknown instrument ${JSON.stringify(raw)}; known: ${ALL_INSTRUMENT_IDS.join(', ')}`,
      );
    }
    if (!out.includes(inst)) out.push(inst);
  }
  return out;
}
