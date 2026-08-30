# Design — live market-flow tool (XAUUSD / WTI / Brent / BTCUSD)

Status: authoritative build spec. The coder implements this literally.
Runtime: Node.js 22, ES modules (`"type": "module"`), no build step, no transpiler.
Every file stays under 500 lines. All external input is validated at the boundary.
Secrets come from environment variables only — never from a file in the repo.

**Read section 7 (Honest limitations) before writing any rendering code.** The
asymmetry between BTCUSD and the other three instruments is the single most
important fact in this design, and it must be visible in the output, not buried.

---

## 0. The constraint that shapes everything

The build container has no network route to market-data hosts. The tool is
written here and run on the user's machine. Therefore:

- **No test may perform live HTTP.** Tests run against committed fixtures at
  `tests/fixtures/` (owned by the integration owner; the coder reads them
  read-only and never edits them).
- **The same parsing code must run against a fixture and against a live
  endpoint.** This is achieved with an injected `transport` (section 2.1).
  Providers never call global `fetch`. A provider that calls `fetch` directly is
  a bug, and the review should reject it.
- **Fixtures are raw response bodies, byte-for-byte.** Not pretty-printed, not
  normalized, not the output of an MCP wrapper. The parser sees exactly what the
  vendor's HTTP endpoint returns. Fixture files captured from a normalized
  wrapper would make the tests pass while the live path fails — the precise
  failure this design exists to prevent.

---

## 1. Module breakdown

All source under `src/`. One-line responsibility each.

### Entry and configuration
| Path | Responsibility |
|---|---|
| `src/cli.js` | Argv parsing, command dispatch, exit codes, top-level error formatting. |
| `src/config.js` | Merge defaults + optional config file + env + flags into one frozen config object; report missing env per provider. |
| `src/instruments.js` | Static instrument table: id, kind, bucket size, band list, provider chain, size unit, proxy notes. |

### Transport (the injection seam)
| Path | Responsibility |
|---|---|
| `src/transport/httpTransport.js` | Real transport over `globalThis.fetch`; timeout via `AbortController`, retry with backoff, no redirect to non-https. |
| `src/transport/fixtureTransport.js` | Test transport; resolves a URL to a fixture file and returns its bytes as `body`. Uses `tests/fixtures/manifest.json` when present, else `fixtureMap.js`. Throws on an unmatched URL. |
| `src/transport/fixtureMap.js` | Default URL→fixture map, used when no manifest exists. Lives in `src/` because `tests/` is owned by the integration owner. |
| `src/transport/index.js` | `createTransport(kind, opts)` factory; the only place either implementation is constructed. |

### Providers (one file per vendor, all share one interface)
| Path | Responsibility |
|---|---|
| `src/providers/types.js` | JSDoc typedefs for every normalized shape + the `Provider` contract; no runtime logic. |
| `src/providers/registry.js` | Registers providers by id, resolves an instrument's provider chain, runs primary→fallback with per-provider error capture. |
| `src/providers/binance.js` | BTCUSD primary: REST `/api/v3/depth` + `/api/v3/aggTrades`. Real depth, exchange-tagged aggressor. |
| `src/providers/coinbase.js` | BTCUSD fallback: `/products/BTC-USD/book?level=2` + `/trades`. Real depth incl. order counts. |
| `src/providers/cryptocom.js` | BTCUSD third source: `/exchange/v1/public/get-book` + `get-trades`. Reachable from this container, so it is the source for capturing BTC fixtures. |
| `src/providers/oanda.js` | XAUUSD primary: v20 `/v3/accounts/{id}/pricing`. One broker's ladder — emits `provenance: 'BROKER'`. |
| `src/providers/twelvedata.js` | XAUUSD/WTI/Brent intraday bars: `/time_series` 15min. Bars only, no book. |
| `src/providers/eia.js` | WTI/Brent daily settlement anchor (RWTC / RBRTE). Reference series, not intraday. |
| `src/providers/fmp.js` | XAUUSD/Brent quote-only fallback: FMP `commodities-quote`. Snapshot quote + day OHLC. No book, no intraday bars. The only commodity source with a committed fixture. |

### Order-flow computation (pure functions, no I/O)
| Path | Responsibility |
|---|---|
| `src/flow/imbalance.js` | Depth-band bid/ask imbalance at a list of bps bands. |
| `src/flow/cvd.js` | Signed volume delta and cumulative delta; tick-rule inference kept in a separate exported function so the two can never be confused. |
| `src/flow/buckets.js` | Price→bucket index math, bucket-size selection, depth-level aggregation into buckets. |
| `src/flow/heatmap.js` | Builds the price-bucket x time-bucket x resting-size matrix from persisted snapshots. |
| `src/flow/profile.js` | Candle-derived volume-at-price profile, VWAP, HVN/LVN — the honest substitute for gold and oil. |
| `src/flow/signals.js` | Liquidity shelves (clusters of persistent resting size) and absorption flags; emits levels with a provenance tag. |

### Persistence
| Path | Responsibility |
|---|---|
| `src/store/stateDir.js` | Resolves and creates the state directory; refuses to write inside the repo working tree unless explicitly pointed there. |
| `src/store/snapshotStore.js` | Append-only NDJSON writes, day-file rotation, retention pruning, range reads for a time window. |
| `src/store/cursor.js` | Atomic (tmp+rename) read/write of the cross-run cursor: running CVD, last trade id, last price, last tick time. |

### Scheduling and collection
| Path | Responsibility |
|---|---|
| `src/scheduler/scheduler.js` | Wall-clock-aligned 15-minute loop, jitter, per-tick orchestration, graceful shutdown on SIGINT/SIGTERM. |
| `src/collector/wsCollector.js` | Optional Binance `depth@100ms` WebSocket collector for the true heat map (mode `stream`); BTC only. |

### Rendering
| Path | Responsibility |
|---|---|
| `src/render/table.js` | ANSI table report for `once` / `flow`, including the provenance badge column. |
| `src/render/heatmapRender.js` | ANSI colour-block heat map, plus CSV and JSON emitters for the same matrix. |
| `src/render/provenance.js` | Single source of truth for badge text/colour per provenance value — so no panel can render without one. |

### Utilities
| Path | Responsibility |
|---|---|
| `src/util/validate.js` | Boundary validators (`num`, `finiteNum`, `nonNegNum`, `str`, `arr`, `tsMs`) that throw `ProviderParseError` with a field path. |
| `src/util/errors.js` | `ProviderParseError`, `ProviderHttpError`, `ConfigError`, `RateLimitError` with a `retryable` flag. |
| `src/util/time.js` | UTC bucket floor/ceil, 15-min boundary math, ISO<->ms conversion. |
| `src/util/log.js` | Levelled logger writing to stderr so `--format json` on stdout stays machine-parseable. |

`tests/` mirrors `src/` (`tests/flow/imbalance.test.js`, etc.) using `node:test`
and `node:assert/strict`. No test framework dependency, no network.

---

## 2. The provider interface

### 2.1 Transport

```js
/**
 * @typedef {Object} HttpResponse
 * @property {number} status
 * @property {Record<string,string>} headers   // lowercased keys
 * @property {string} body                     // raw response text, unparsed
 * @property {string} url                      // final URL after redirects
 */

/**
 * @typedef {Object} RequestOptions
 * @property {'GET'} [method]                  // GET only; this tool never writes
 * @property {Record<string,string>} [headers]
 * @property {number} [timeoutMs]              // default 8000
 * @property {AbortSignal} [signal]
 */

/**
 * @typedef {Object} Transport
 * @property {(url: string, opts?: RequestOptions) => Promise<HttpResponse>} request
 */
```

`fixtureTransport` implements the identical signature and resolves via
`tests/fixtures/manifest.json`:

```json
{
  "entries": [
    { "match": "api.binance.com/api/v3/depth",     "file": "binance/depth-btcusdt-1000.json",  "status": 200 },
    { "match": "api.binance.com/api/v3/aggTrades", "file": "binance/aggtrades-btcusdt.json",   "status": 200 },
    { "match": "api.binance.com/api/v3/ticker",    "file": "errors/binance-429.json",          "status": 429,
      "headers": { "retry-after": "12" } }
  ]
}
```

`match` is a plain substring test against the request URL, first match wins. An
unmatched URL throws — a test can never silently fall through to the network.

### 2.2 The Provider contract

Every provider module default-exports exactly this object. One function.

```js
/**
 * @typedef {'OBSERVED'|'BROKER'|'INFERRED'|'PROXY'} Provenance
 *   OBSERVED - central-exchange book or exchange-tagged prints
 *   BROKER   - one dealer's internal ladder (OANDA XAUUSD); real, but not market-wide
 *   INFERRED - derived from candles/ticks, not from a book
 *   PROXY    - a different instrument standing in (USO for WTI, GLD for gold)
 */

/**
 * @typedef {Object} Capabilities
 * @property {boolean} depth           // returns a resting-size ladder
 * @property {boolean} trades          // returns individual prints
 * @property {boolean} aggressorSide   // prints carry an EXCHANGE-TAGGED side
 * @property {boolean} quote           // returns bid and ask
 * @property {boolean} bars            // returns OHLCV candles
 * @property {number}  minPollSeconds  // shortest safe polling interval
 * @property {number|null} dailyRequestBudget  // null = effectively unlimited
 */

/**
 * @typedef {Object} ProviderContext
 * @property {Transport} transport
 * @property {Record<string,string|undefined>} env
 * @property {() => number} now        // ms epoch; injectable for deterministic tests
 * @property {import('../util/log.js').Logger} log
 * @property {{ depthLimit:number, tradeLimit:number, timeoutMs:number }} opts
 */

/**
 * @typedef {Object} Provider
 * @property {string} id                  // 'binance'
 * @property {string} label               // 'Binance Spot'
 * @property {Capabilities} capabilities
 * @property {string[]} requiredEnv       // [] when the endpoint is public
 * @property {string[]} supports          // instrument ids this provider can serve
 * @property {(instrument: Instrument, ctx: ProviderContext) => Promise<ProviderResult>} fetchSnapshot
 */
```

**`fetchSnapshot` is the entire interface.** It is the only function the registry
calls. It performs one or more `ctx.transport.request(...)` calls, validates,
and returns a `ProviderResult`. It throws `ProviderHttpError` or
`ProviderParseError` on failure; it never returns partial garbage and never
returns synthetic data as a stand-in for a failed fetch.

### 2.3 Normalized shapes

All prices and sizes are JS `number`. All timestamps are integer ms since epoch,
UTC. Anything absent is `null`, never `0`, never `undefined`.

```js
/**
 * @typedef {Object} Level
 * @property {number} price
 * @property {number} size            // resting size in Depth.sizeUnit
 * @property {number|null} orders     // level order count; null when the vendor omits it
 */

/**
 * @typedef {Object} Depth
 * @property {number} ts
 * @property {Level[]} bids           // sorted DESC by price; bids[0] is best bid
 * @property {Level[]} asks           // sorted ASC by price; asks[0] is best ask
 * @property {string} sizeUnit        // 'BTC' | 'contracts' | 'broker-liquidity'
 * @property {boolean} truncated      // vendor capped the ladder at the requested limit
 * @property {boolean} crossed        // best bid >= best ask (stale/bad snapshot)
 * @property {string|null} sequence   // vendor sequence/update id, when provided
 */

/**
 * @typedef {Object} Quote
 * @property {number} ts
 * @property {number|null} bid
 * @property {number|null} ask
 * @property {number|null} last
 * @property {number} mid             // (bid+ask)/2 when both present, else last
 * @property {number|null} spread     // ask - bid
 * @property {number|null} spreadBps  // spread / mid * 10000
 * @property {number|null} dayVolume
 */

/**
 * @typedef {Object} Trade
 * @property {number} ts
 * @property {number} price
 * @property {number} size
 * @property {'buy'|'sell'|'unknown'} side        // AGGRESSOR side, not maker side
 * @property {'exchange'|'tickRule'|'none'} sideSource
 * @property {string|null} id
 */

/**
 * @typedef {Object} Bar
 * @property {number} ts              // bar OPEN time
 * @property {number} open
 * @property {number} high
 * @property {number} low
 * @property {number} close
 * @property {number|null} volume
 * @property {'base'|'contracts'|'shares'|'tickCount'|null} volumeKind
 */

/**
 * @typedef {Object} ProviderResult
 * @property {string} providerId
 * @property {string} instrumentId    // 'BTCUSD' | 'XAUUSD' | 'WTI' | 'BRENT'
 * @property {string} sourceSymbol    // 'BTCUSDT' | 'XAU_USD' | 'USO'
 * @property {number} fetchedAt       // ctx.now() at request start
 * @property {Provenance} provenance
 * @property {Quote|null}  quote
 * @property {Depth|null}  depth
 * @property {Trade[]|null} trades
 * @property {Bar[]|null}  bars
 * @property {string[]} notes         // caveats rendered with the data, e.g. 'USO ETF proxy, not WTI barrels'
 */
```

`sideSource` and `provenance` are load-bearing, not decoration. `src/flow/cvd.js`
refuses to compute a true CVD unless every trade in the window has
`sideSource === 'exchange'`. `src/render/*` refuses to draw a panel whose
`provenance` it cannot badge.

### 2.4 Per-instrument provider chains and env vars

| Instrument | Chain (primary → fallback) | Env vars | Yields |
|---|---|---|---|
| BTCUSD | `binance` → `coinbase` → `cryptocom` | none (public); optional `BINANCE_BASE_URL`, `COINBASE_BASE_URL`, `CRYPTOCOM_BASE_URL` | depth + exchange-tagged tape |
| XAUUSD | `oanda` → `twelvedata` → `fmp` | `OANDA_API_TOKEN`, `OANDA_ACCOUNT_ID`, `OANDA_ENV` (`practice`\|`live`); `TWELVEDATA_API_KEY`; `FMP_API_KEY` | broker ladder (3–5 levels) / 15-min bars / quote-only |
| WTI | `twelvedata` → `eia` | `TWELVEDATA_API_KEY`, `EIA_API_KEY` | 15-min bars (CL front-month) / daily anchor |
| BRENT | `twelvedata` → `fmp` → `eia` | `TWELVEDATA_API_KEY`, `FMP_API_KEY`, `EIA_API_KEY` | 15-min bars (BZ front-month) / quote-only / daily anchor |

**Provenance of the FMP commodity symbols is not uniform, and must not be flattened to one badge:**
`BZUSD` is ICE Brent front-month — the instrument this tool means by "Brent", so it is `INFERRED`
(quote-derived, no book), *not* `PROXY`. `GCUSD` is COMEX **gold futures**, a different instrument from
XAUUSD spot with its own basis, roll and session — that one is `PROXY`, and its `notes` must name the
substitution. Over-badging is as inaccurate as under-badging; the badge must track the actual gap.

Optional: `ALPHAVANTAGE_API_KEY` — **anchor only.** The free tier is 25
requests/day against 96 polls/day/instrument, so it must never be placed in a
polling chain. `src/config.js` raises a `ConfigError` if it is.

A provider whose `requiredEnv` is unset is **disabled with a printed reason**.
It never degrades to fabricated data. `node src/cli.js providers` prints the
capability matrix and exactly which variables are missing.

---

## 3. Order-flow computations

Pure functions in `src/flow/`. Inputs are the normalized shapes above.

### 3.1 Depth-band bid/ask imbalance — `imbalance.js`

For a band of `B` basis points around `mid`:

```
lowerBound = mid * (1 - B/10000)
upperBound = mid * (1 + B/10000)

bidVol(B) = Σ level.size  for bids where level.price >= lowerBound
askVol(B) = Σ level.size  for asks where level.price <= upperBound

imbalance(B) = (bidVol(B) - askVol(B)) / (bidVol(B) + askVol(B))     ∈ [-1, +1]
```

Guards: if `bidVol + askVol === 0` return `null`, not `0` — an empty band and a
balanced band are different facts. If `depth.crossed` is true, return `null` and
attach a note. If `depth.truncated` is true and `upperBound` exceeds the last
returned ask price, set `bandClipped: true` — the band is wider than the ladder,
so the number understates one side.

Computed at bands `[5, 10, 25, 50]` bps. Output:

```js
{ bandBps, bidVol, askVol, imbalance, bandClipped, levelsUsed: {bids, asks} }
```

**Availability: BTCUSD only** (and XAUUSD in a 3–5-level, single-broker form that
must be badged `BROKER`). Never computed for WTI/Brent.

### 3.2 Cumulative volume delta — `cvd.js`

Per snapshot window, over trades newer than `cursor.lastTradeTs`:

```
delta      = Σ (side === 'buy' ? +size : side === 'sell' ? -size : 0)
buyVolume  = Σ size where side === 'buy'
sellVolume = Σ size where side === 'sell'
cvd_t      = cvd_{t-1} + delta_t
```

`cvd_{t-1}` is read from `src/store/cursor.js`, so CVD survives restarts. It
resets at 00:00 UTC and on `--reset-cvd`.

Two exported functions, deliberately not interchangeable:

- `computeCvd(trades, prevCvd)` — **throws** if any trade has
  `sideSource !== 'exchange'`. Output field is named `cvd`.
- `computeCvdProxy(trades, prevCvd)` — accepts tick-rule-signed trades. Output
  field is named `cvdProxy` and carries `provenance: 'INFERRED'`.

Tick rule (used only to produce `cvdProxy`, and only where a vendor gives
unsigned prints):

```
side = price > prevPrice ? 'buy'
     : price < prevPrice ? 'sell'
     : previousSide                      // carry forward; 'unknown' if none yet
```

The renderer must never plot `cvd` and `cvdProxy` with the same styling.

### 3.3 Depth-bucket aggregation — `buckets.js`

```
bucketIndex(price, bucketSize) = Math.floor(price / bucketSize)
bucketLowerEdge(index)         = index * bucketSize
```

Anchoring at absolute zero (rather than at mid) keeps bucket boundaries stable as
price drifts, so the same shelf lands in the same bucket across snapshots — which
is the whole point of the persistence measure in 3.4.

Default bucket sizes (`src/instruments.js`, overridable with `--bucket`):

| Instrument | bucketSize |
|---|---|
| BTCUSD | 10.0 (USD) |
| XAUUSD | 0.5 |
| WTI / BRENT | 0.05 |

Aggregate a `Depth` into:

```js
{
  bucketSize,
  bids: Map<number /*index*/, { size:number, levels:number, orders:number|null }>,
  asks: Map<number, { size:number, levels:number, orders:number|null }>,
  minIndex, maxIndex
}
```

Rounding: use `Math.round(price / bucketSize * 1e8) / 1e8` before `Math.floor`
to keep float error from pushing a level across a boundary.

### 3.4 Heat map — `heatmap.js`

Read section 7.3 first. There are two modes and they are **not** equivalent.

- **`ladder` (default, poll-driven).** Built from the 15-minute snapshots. Honest
  name: *depth-persistence ladder*. It answers "which price buckets held resting
  size across consecutive snapshots", not "how did the book evolve".
- **`stream` (opt-in).** Built from `src/collector/wsCollector.js` running a
  Binance `depth@100ms` feed on the user's machine. This is a genuine Bookmap-style
  heat map; the 15-minute cadence becomes the *refresh* rate, not the *sample* rate.

Both produce the same structure, distinguished by `mode` and `provenance`:

```js
/**
 * @typedef {Object} HeatMap
 * @property {string} instrumentId
 * @property {'ladder'|'stream'} mode
 * @property {Provenance} provenance
 * @property {number} bucketSize        // price units per row
 * @property {number} timeBucketMs      // 900000 for 15 min
 * @property {number[]} priceBuckets    // length P, ascending LOWER EDGE prices
 * @property {number[]} timeBuckets     // length T, ascending cell-start ms epoch
 * @property {number[][]} bid           // [T][P] mean resting bid size in the cell
 * @property {number[][]} ask           // [T][P] mean resting ask size in the cell
 * @property {number[][]} persistence   // [T][P] in [0,1]
 * @property {number[]}  samplesPerCell // length T
 * @property {number[]}  midByCell      // length T, mid price per cell (overlay line)
 * @property {number}    maxIntensity
 * @property {string[]}  notes
 */
```

Row-major: `bid[timeIndex][priceIndex]`. Cells with no observation are `0` with
`persistence = 0`; a consumer distinguishes "no size" from "not sampled" via
`samplesPerCell[t] === 0`.

Per cell `(t, p)`, over the `S = samplesPerCell[t]` snapshots in that time bucket:

```
observed(t,p)     = count of snapshots in cell t whose ladder contained bucket p with size > 0
meanSize(t,p)     = (Σ size of bucket p across those snapshots) / S      // S, not observed —
                    // a wall present in 1 of 6 snapshots must not score like one present in 6
persistence(t,p)  = observed(t,p) / S
intensity(t,p)    = meanSize(t,p) * persistence(t,p)
maxIntensity      = max over all cells of intensity
```

Dividing by `S` rather than `observed` is deliberate: it is what stops a single
transient print from rendering as a solid wall. Colour scale is
`intensity / maxIntensity`, gamma-corrected at 0.45 so mid-range size stays
visible.

In `ladder` mode, `S` is at most 1 per 15-minute cell by definition, so
`persistence` is 0 or 1 and the map is a sequence of stills. **`heatmap.js` must
set `notes: ['ladder mode: one snapshot per cell; between-snapshot pulls, spoofs
and absorption are not observable']` and the renderer must print it above the
map.** If `--interval` is set below 15 minutes, `S` rises and persistence becomes
meaningful — that is the honest way to get a better map from polling.

### 3.5 Volume-at-price profile — `profile.js`

The substitute for gold and oil, where no book exists. From 15-minute bars:

```
typicalPrice(bar) = (high + low + close) / 3
VWAP              = Σ(typicalPrice * volume) / Σ(volume)
```

Distribute each bar's volume across the buckets its `[low, high]` range spans,
weighted by overlap (uniform-within-range assumption — an approximation, and
labelled as one). Then:

```
POC  = bucket with the highest accumulated volume
HVN  = buckets above the 70th percentile of accumulated volume
LVN  = buckets below the 30th percentile
```

Always emitted with `provenance: 'INFERRED'` and the note
`'volume-at-price derived from 15-minute candles, not from an order book'`.

### 3.6 Signals — `signals.js`

- **Liquidity shelf**: a run of adjacent buckets on one side where
  `persistence >= 0.6` and `meanSize >= 3 x median(meanSize)` across the window.
  Emitted as `{ side, priceLow, priceHigh, meanSize, persistence, provenance }`.
- **Absorption**: in a cell where `|delta|` is in the top decile of the window but
  `|midByCell[t] - midByCell[t-1]| < 0.1 x ATR15`, flag `absorption: true`.
  Requires exchange-tagged tape — **BTCUSD only**.

Shelves are rendered as candidate support/resistance levels. They are levels
where resting size was observed, and the output labels them exactly that. The
renderer must not present them as entry, take-profit or stop-loss
recommendations, and `signals.js` must not emit a field named `tp` or `sl`.

---

## 4. Scheduler and persistence

### 4.1 The 15-minute loop — `scheduler/scheduler.js`

Aligned to wall-clock UTC boundaries (`:00 :15 :30 :45`), not to process start —
so snapshots from separate runs land in the same time buckets and the heat map
stitches across restarts.

```
nextBoundary = ceil(now / intervalMs) * intervalMs
delay        = nextBoundary - now + jitter          // jitter = random 0..5000 ms
```

`setTimeout(delay)`, never `setInterval` — recompute the boundary each tick so
drift and clock changes self-correct. Jitter avoids hammering a vendor on the
exact boundary.

Each tick, per enabled instrument, in sequence (not parallel — respects the
tightest rate limit in the chain):

1. Resolve the provider chain; skip providers with missing `requiredEnv`.
2. Call `fetchSnapshot`. On `ProviderHttpError` with `retryable`, retry up to
   `--retries` with exponential backoff (500ms, 1s, 2s) plus honour `Retry-After`.
3. On exhaustion, fall through to the next provider in the chain and record the
   failure in the snapshot's `notes`.
4. If every provider fails, write a **failure record** (`ok: false`, with the
   error chain) — never a fabricated snapshot, and never a silently skipped tick.
   A gap must be visible in the heat map as a gap.
5. Compute flow metrics, update the cursor, append the snapshot.

`--once` runs a single tick and exits. SIGINT/SIGTERM finish the in-flight tick,
flush the cursor, then exit 0.

### 4.2 Snapshot persistence — `store/snapshotStore.js`

Append-only NDJSON, one file per instrument per UTC day:

```
<stateDir>/snapshots/<instrumentId>/<YYYY-MM-DD>.ndjson
<stateDir>/cursor.json
<stateDir>/collector/<instrumentId>/<YYYY-MM-DD>.ndjson    # stream mode only
```

`stateDir` resolves from `--state-dir`, else `MARKETFLOW_STATE_DIR`, else
`~/.marketflow`. It defaults **outside the repo** so market data is never
accidentally committed. `store/stateDir.js` warns if the resolved path is inside
a git working tree.

One line per tick:

```json
{"v":1,"ts":1787950800000,"instrumentId":"BTCUSD","providerId":"binance",
 "provenance":"OBSERVED","ok":true,"sourceSymbol":"BTCUSDT",
 "quote":{...},"depthBuckets":{"bucketSize":10,"bids":[[7852,1.24],[7853,0.61]],"asks":[[7854,0.90]]},
 "flow":{"imbalance":[{"bandBps":5,"imbalance":0.12,...}],"delta":-3.42,"cvd":118.7,
         "buyVolume":41.2,"sellVolume":44.6,"sideSource":"exchange"},
 "notes":[]}
```

The **bucketed** ladder is persisted, not the raw thousands of levels — bounded
file growth, and buckets are what the heat map consumes. Raw depth is kept only
in memory for the current tick. Bucket entries are `[index, size]` pairs to keep
lines compact.

Append with a single `fs.appendFile` call per line (atomic for the small sizes
here). The cursor is written tmp+rename so a crash mid-write cannot corrupt CVD
continuity.

Retention: `--retain-days` (default 7) prunes older day files at the start of
each tick. `heatmap`/`flow` read only the day files intersecting the requested
window.

---

## 5. CLI surface

```
node src/cli.js <command> [flags]
```

| Command | Purpose |
|---|---|
| `once` | One snapshot per enabled instrument; print the report; exit. |
| `watch` | Run the 15-minute scheduler until interrupted. |
| `flow` | Order-flow metrics from persisted snapshots. |
| `heatmap` | Build and render the heat map from persisted snapshots. |
| `collect` | Run the WebSocket depth collector (BTCUSD only, feeds `--mode stream`). |
| `providers` | Print the capability matrix and which env vars are set or missing. |
| `replay` | Run the whole pipeline against a fixture directory, zero network. |

**Global flags**

| Flag | Default | Meaning |
|---|---|---|
| `--instruments <ids>` | all configured | Comma list: `XAUUSD,WTI,BRENT,BTCUSD`. |
| `--state-dir <path>` | `~/.marketflow` | Snapshot/cursor root. |
| `--format <table\|json\|ndjson>` | `table` | Machine formats go to stdout; logs to stderr. |
| `--config <path>` | none | Optional JSON config, lowest precedence after defaults. |
| `--timeout <ms>` | `8000` | Per-request timeout. |
| `--retries <n>` | `2` | Retryable-error attempts per provider. |
| `--verbose` / `--quiet` | — | Log level. |
| `--no-color` | auto | Also honours `NO_COLOR`. |

**`once` / `watch`**

| Flag | Default | Meaning |
|---|---|---|
| `--interval <minutes>` | `15` | Tick interval. Values under 15 improve heat-map persistence (3.4). |
| `--depth-limit <n>` | `1000` | Ladder depth requested. |
| `--trade-limit <n>` | `1000` | Prints requested per tick. |
| `--retain-days <n>` | `7` | Day-file retention. |
| `--no-align` | off | Do not align to wall-clock boundaries. |
| `--reset-cvd` | off | Zero the running CVD before starting. |

**`flow`**

| Flag | Default |
|---|---|
| `--window <hours>` | `6` |
| `--band-bps <list>` | `5,10,25,50` |

**`heatmap`**

| Flag | Default | Meaning |
|---|---|---|
| `--mode <ladder\|stream>` | `ladder` | See 3.4. `stream` errors out if no collector data exists. |
| `--window <hours>` | `6` | Time span. |
| `--bucket <price>` | per-instrument | Override bucket size. |
| `--rows <n>` | `40` | Price buckets rendered, centred on current mid. |
| `--render <ansi\|json\|csv>` | `ansi` | Output form. |

**`replay`**

| Flag | Default |
|---|---|
| `--fixtures <dir>` | `tests/fixtures` |

**Exit codes**: `0` success · `1` runtime/fetch failure · `2` bad usage or
config · `3` all providers failed for every requested instrument.

---

## 6. Fixtures

Owned by the integration owner. The coder reads them read-only and never edits
`tests/`.

### 6.1 What actually exists

Three flat files. This is the real inventory as of the current commit — earlier
drafts of this section listed a vendor-subdirectory tree that was a *capture
request*, not a description of disk. That was wrong and is corrected here.

| File | Source | Shape notes |
|---|---|---|
| `tests/fixtures/btc-usdt-orderbook.json` | Crypto.com `get_book`, BTC_USDT, live 2026-08-30 | 25 levels/side. **`price` and `qty` are STRINGS.** |
| `tests/fixtures/btc-usdt-trades.json` | Crypto.com `get_trades`, BTC_USDT, live | 40 prints. **Exchange-tagged `side`** → true CVD. ISO-8601 timestamps, string numerics. |
| `tests/fixtures/commodities-quotes.json` | FMP `commodities-quote`, live | `GCUSD` (gold futures) + `BZUSD` (Brent). **Numeric fields, `timestamp` is UNIX SECONDS.** |

There is no `manifest.json`, and none of the Binance / Coinbase / OANDA /
Twelve Data / EIA / `errors/` / `malformed/` / `series/*.ndjson` files listed in
earlier drafts. Code must not assume any of them.

### 6.2 Two deviations from §0 — read before writing a parser

**(a) The fixtures carry added metadata keys.** Each file has `_source`, `_note`
and (for commodities) `_gap` keys that the vendor never sent, and the payloads are
truncated for repository size. Every provider parser and every validator must
**ignore keys whose name begins with `_`** and must not treat a truncated ladder
as a malformed one. Set `Depth.truncated = true` when parsing these.

**(b) The crypto fixtures are the MCP wrapper's flattened shape, not raw
Crypto.com REST — and this is the exact failure §0 exists to prevent.** The
fixture has `asks` / `bids` / `timestamp` at the top level with `{price, qty}`
objects. The live Crypto.com Exchange REST endpoint returns a
`{code, method, result:{...}}` envelope with the ladder nested under
`result.data[0]` and levels as **positional arrays**, not objects. A parser
written to satisfy the fixture alone will parse nothing on the user's machine.

Required handling — `providers/cryptocom.js` shape-detects and supports both:

```
if (json.result?.data?.[0])  -> LIVE branch: envelope + positional level arrays
else if (json.bids)          -> FIXTURE branch: flattened, {price, qty} objects
else                         -> throw ProviderParseError
```

Both branches converge on the same normalized `Depth` / `Trade`. **Only the
fixture branch is test-covered.** The live branch is written from vendor
documentation and is *unverified from this container* — the exact field names in
the live envelope must be confirmed against Crypto.com's API docs on first real
run, and the provider must fail loudly (`ProviderParseError` naming the field
path) rather than coercing an unexpected shape into a plausible-looking number.
Mark the live branch with a `// UNVERIFIED:` comment so review can find it.

The durable fix is to recapture fixtures as raw HTTP response bodies. Until then
this dual-branch parser is the honest accommodation, not a preference.

### 6.3 Provider verification status

`node src/cli.js providers` prints this column, so the gap is visible at runtime
rather than living only in this document.

| Provider | Fixture | Status |
|---|---|---|
| `cryptocom` | yes (flattened) | fixture branch verified; **live branch unverified** |
| `fmp` | yes | verified (quote only) |
| `binance` | none | **written to spec, unverified** — incl. the `aggTrades` / `isBuyerMaker` aggressor path |
| `coinbase`, `oanda`, `twelvedata`, `eia` | none | **written to spec, unverified** |

An unverified provider is not disabled — it is labelled. Shipping it silently as
if it were tested would be the dishonest option.

### 6.4 Not yet captured

Blocked, with the reason. None of these may be fabricated.

- **WTI** — FMP denies `CLUSD` on the current plan tier and Alpha Vantage's WTI
  endpoint is out of its 25-request daily quota. WTI stays configured in
  `instruments.js` and yields a **visible failure record** (`ok:false`, §4.1
  step 4), never a synthetic snapshot.
- **Intraday bars for any commodity** — `commodities-quote` is a snapshot with
  day OHLC, not a bar series. `flow/profile.js` (VWAP / POC / HVN / LVN, §3.5)
  therefore has **no input it can be exercised against**. Implement it to spec
  and mark it unverified.
- **Multi-tick series** — with one book snapshot and one trade batch,
  `samplesPerCell` is 1, so `persistence` is only ever 0 or 1. The heat map and
  §3.6 absorption cannot be meaningfully verified. `heatmap` must **report the
  one-sample limitation in its rendered output** rather than drawing a
  convincing-looking map from a single frame.
- **Error and malformed responses** — no 429 / 401 / truncated-JSON fixtures, so
  the retry, backoff and `Retry-After` paths are unverified. Unit-test them by
  constructing a stub `Transport` inline (returning a chosen `status`/`body`)
  rather than by adding files to `tests/fixtures/`.

### 6.5 Test coverage

**Verifiable against the committed fixtures — required:**

1. `cryptocom` parses the book fixture into a `Depth` with **string→number**
   coercion, bids DESC, asks ASC, `truncated:true`, `sizeUnit:'BTC'`.
2. `cryptocom` parses the trades fixture into `Trade[]` with
   `sideSource:'exchange'` and ISO→ms timestamps.
3. `computeCvd` succeeds on those exchange-tagged trades and **throws** on
   tick-rule-signed ones; `computeCvdProxy` accepts them.
4. `fmp` parses `GCUSD` with `provenance:'PROXY'` plus a note naming the
   futures-for-spot substitution, and `BZUSD` with `provenance:'INFERRED'`.
5. `fmp` converts the UNIX-**seconds** `timestamp` to ms (a x1000 bug here is
   silent and corrupts every time bucket — assert the absolute value).
6. Both parsers ignore `_`-prefixed metadata keys.
7. Imbalance on the real book returns a finite value in [-1,1]; returns `null`
   (not `0`) for an empty band and for a crossed book; sets `bandClipped` when a
   band exceeds the 25-level ladder.
8. Bucket indices are stable across two snapshots at different price levels.
9. `fixtureTransport` **throws on an unmatched URL**.
10. No unit test opens a socket — assert `globalThis.fetch` is never called.

**Implement but mark unverified:** every non-`cryptocom`/`fmp` provider,
`profile.js`, stream-mode heat map, absorption, retry/backoff.

---

## 7. Honest limitations

This section is a build requirement, not a disclaimer appended at the end. The
`provenance` badge exists to carry it into the running tool. Every rendered panel
shows one of `OBSERVED` / `BROKER` / `INFERRED` / `PROXY`.

### 7.1 BTCUSD — genuinely measured

Binance, Coinbase and Crypto.com are central limit order books with public REST
endpoints. The tool observes:

- **Real resting depth.** An actual ladder of resting limit orders, up to 5000
  levels on Binance.
- **Real aggressor side.** `aggTrades.m` (isBuyerMaker) gives the true taker side,
  so **CVD is measured, not inferred**.
- **Real absorption.** Large signed volume against a static mid is a real
  observation here.

Residual caveats, still worth stating: it is *one venue*, not consolidated
crypto-wide flow; BTCUSDT is not BTCUSD (a stablecoin basis of a few bps);
a REST snapshot is a still frame — orders placed and pulled between polls are
invisible regardless of venue.

### 7.2 XAUUSD and oil — approximated

**Spot gold has no central order book.** XAUUSD is OTC: each dealer quotes its
own book and no consolidated depth exists anywhere, at any price, for anyone.
The best available is OANDA's v20 pricing endpoint, which returns **one broker's
internal ladder of roughly 3–5 levels**. That is real data about *that dealer's*
liquidity and nothing more. It is badged `BROKER`, never `OBSERVED`, and it must
not be presented as market depth.

**WTI and Brent are worse.** There is no retail-accessible book at all.
Alpha Vantage's WTI/BRENT series are `daily|weekly|monthly` only — they cannot
drive a 15-minute tool. EIA's RWTC/RBRTE publish next business day: an anchor,
not a live feed. The only intraday option is Twelve Data on CL/BZ front-month, or
the USO/BNO ETFs — and **an ETF is a different instrument** with different
sessions, its own creation/redemption mechanics and roll drift. Anything sourced
that way is badged `PROXY` and names the substitution in `notes`.

In the currently committed fixture set the only gold source is FMP `GCUSD` — **COMEX gold futures, not
XAUUSD spot.** Futures and spot are different instruments: the basis moves with rates and storage, the
contract rolls, and the session calendar differs. That path is badged `PROXY` and names the substitution.
It is not a cheaper route to spot gold; it is a related instrument standing in for one the tool cannot
reach.

So for these three instruments the tool delivers: 15-minute OHLC, tick-count or
ETF volume, a candle-derived volume-at-price profile, VWAP, HVN/LVN, and (gold
only) one broker's spread and top-of-book liquidity. All badged `INFERRED` or
`PROXY`.

**What it does not deliver, and cannot:** real bid/ask imbalance, real CVD, real
absorption, or any heat map. A tick-rule "delta" on candle data is a guess about
direction dressed up as a measurement. `cvd.js` structurally refuses to produce a
`cvd` field for these instruments — the guard in 3.2 is the mechanism that keeps
this honest, and it must not be relaxed to make the panels look symmetrical.
**Never render a CVD line for gold or oil that looks like the BTC one.**

### 7.3 The heat map — what 15-minute polling cannot do

A Bookmap-style heat map is resting depth rebuilt continuously from order-book
diffs at sub-second resolution. Its entire value is watching walls appear, get
pulled, and get eaten. **Fifteen-minute polling cannot produce that**, and this
design does not pretend otherwise.

At 96 snapshots/day each cell holds one still frame. Every pull, every spoof,
every absorption between frames is invisible. A wall that appeared and vanished
inside a 15-minute window simply did not happen as far as the tool can tell.

What is built instead:

- **`ladder` (default)** — a *depth-persistence ladder*: price buckets where
  resting size was observed across consecutive snapshots. Genuinely useful for
  locating stable shelves; useless for order-book dynamics. Labelled coarse and
  snapshot-sampled in the rendered output, every time.
- **`stream` (opt-in, BTCUSD only)** — a real heat map. Because the tool runs on
  the user's machine, sampling can be decoupled from display: `collect` runs a
  Binance `depth@100ms` WebSocket into a local ring buffer, and `heatmap
  --mode stream` aggregates it into the same matrix. Fifteen minutes becomes the
  refresh cadence, not the sample rate. **This is the only configuration in which
  the tool produces a genuine liquidity heat map.**

For XAUUSD, WTI and Brent, **no heat map is produced in either mode** — there is
no book to sample. `heatmap` on those instruments renders the candle-derived
volume-at-price profile from 3.5 instead, under its own heading and its own
`INFERRED` badge. It is not the same object as the BTC heat map and is never
drawn to look like one.

### 7.4 Rate limits

| Source | Limit | Fits 15-min polling? |
|---|---|---|
| Binance public | 6000 weight/min per IP (depth limit 1000 = 50) | Yes, comfortably |
| Coinbase Exchange public | ~3 req/s sustained | Yes |
| Crypto.com public | ~100 req/s | Yes |
| OANDA v20 practice | ~120 req/s | Yes |
| Twelve Data free | 800/day, 8/min | Yes — 96 polls/day/instrument; 3 instruments ≈ 288/day |
| EIA v2 | 5000/hour | Yes (daily series anyway) |
| **Alpha Vantage free** | **25/day** | **No — 96 polls/day needed. Anchor use only.** |

`config.js` fails fast with a `ConfigError` if Alpha Vantage is placed in a
polling chain, rather than discovering the wall at runtime.
