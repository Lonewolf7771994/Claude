// Indicators computed from real candles. Same formulas TradingView's built-ins use
// (Wilder smoothing for RSI/ATR) so the numbers line up with what you see on a chart.

export function ema(values, period) {
  if (!Array.isArray(values) || values.length < period || period < 1) return null;
  const k = 2 / (period + 1);
  let acc = values.slice(0, period).reduce((a, b) => a + b, 0) / period;
  for (let i = period; i < values.length; i++) acc = values[i] * k + acc * (1 - k);
  return acc;
}

export function sma(values, period) {
  if (!Array.isArray(values) || values.length < period || period < 1) return null;
  return values.slice(-period).reduce((a, b) => a + b, 0) / period;
}

export function rsi(closes, period = 14) {
  if (!Array.isArray(closes) || closes.length < period + 1) return null;
  let gain = 0, loss = 0;
  for (let i = 1; i <= period; i++) {
    const d = closes[i] - closes[i - 1];
    if (d >= 0) gain += d; else loss -= d;
  }
  gain /= period; loss /= period;
  for (let i = period + 1; i < closes.length; i++) {
    const d = closes[i] - closes[i - 1];
    gain = (gain * (period - 1) + Math.max(d, 0)) / period;
    loss = (loss * (period - 1) + Math.max(-d, 0)) / period;
  }
  if (loss === 0) return gain === 0 ? 50 : 100;
  return 100 - 100 / (1 + gain / loss);
}

export function atr(candles, period = 14) {
  if (!Array.isArray(candles) || candles.length < period + 1) return null;
  const tr = [];
  for (let i = 1; i < candles.length; i++) {
    const c = candles[i], p = candles[i - 1];
    tr.push(Math.max(c.high - c.low, Math.abs(c.high - p.close), Math.abs(c.low - p.close)));
  }
  let acc = tr.slice(0, period).reduce((a, b) => a + b, 0) / period;
  for (let i = period; i < tr.length; i++) acc = (acc * (period - 1) + tr[i]) / period;
  return acc;
}

export function vwap(candles) {
  if (!Array.isArray(candles) || candles.length === 0) return null;
  let pv = 0, vol = 0;
  for (const c of candles) {
    const typical = (c.high + c.low + c.close) / 3;
    const v = Number(c.volume) || 0;
    pv += typical * v; vol += v;
  }
  return vol > 0 ? pv / vol : null;
}

export function macd(closes, fast = 12, slow = 26, signalPeriod = 9) {
  if (!Array.isArray(closes) || closes.length < slow + signalPeriod) return null;
  const line = [];
  for (let i = slow; i <= closes.length; i++) {
    const win = closes.slice(0, i);
    const f = ema(win, fast), s = ema(win, slow);
    if (f === null || s === null) continue;
    line.push(f - s);
  }
  const signal = ema(line, signalPeriod);
  const value = line[line.length - 1];
  if (signal === null || value === undefined) return null;
  return { macd: value, signal, histogram: value - signal };
}

// A transparent, rule-by-rule read of the tape. Every component is reported so the
// caller can see which evidence produced the score - no hidden weighting.
//
// Each check votes +1, -1, or 0. The zero matters: when two quantities differ by less
// than the noise floor (a fraction of ATR), that is not evidence of anything, and
// counting it as a vote would manufacture conviction out of a flat tape.
export function bias(candles) {
  const closes = candles.map((c) => c.close);
  const last = closes[closes.length - 1];
  const e20 = ema(closes, 20), e50 = ema(closes, 50);
  const r = rsi(closes, 14), a = atr(candles, 14), v = vwap(candles.slice(-288));
  const m = macd(closes);

  // Noise floor: a tenth of the average true range, or 0.05% of price if ATR is unavailable.
  const noise = a !== null && a > 0 ? a * 0.1 : Math.abs(last) * 0.0005;

  const checks = [];
  const add = (name, vote, detail) => checks.push({ name, vote, detail });
  const cmp = (x, y, tol = noise) => {
    if (x === null || y === null) return 0;
    if (Math.abs(x - y) < tol) return 0;
    return x > y ? 1 : -1;
  };
  const why = (x, y, label) =>
    x === null || y === null ? 'insufficient data'
      : Math.abs(x - y) < noise ? `${label}: within noise floor ${round(noise)}`
      : label;

  add('price_above_ema20', cmp(last, e20), why(last, e20, `close ${round(last)} vs EMA20 ${round(e20)}`));
  add('ema20_above_ema50', cmp(e20, e50), why(e20, e50, `EMA20 ${round(e20)} vs EMA50 ${round(e50)}`));
  add('price_above_vwap', cmp(last, v), v === null ? 'no volume data' : why(last, v, `close ${round(last)} vs VWAP ${round(v)}`));

  // RSI carries its own conventional neutral band rather than an ATR-derived one.
  add('rsi_above_50', r === null ? 0 : r > 55 ? 1 : r < 45 ? -1 : 0,
    r === null ? 'insufficient data' : `RSI14 ${round(r, 2)}${r >= 45 && r <= 55 ? ' (neutral band 45-55)' : ''}`);

  add('macd_above_signal', m === null ? 0 : cmp(m.macd, m.signal, noise * 0.5),
    m === null ? 'insufficient data' : why(m.macd, m.signal, `MACD ${round(m.macd, 4)} vs signal ${round(m.signal, 4)}`));

  const score = checks.reduce((acc, c) => acc + c.vote, 0);
  const counted = checks.filter((c) => c.vote !== 0).length;
  const direction = score >= 2 ? 'bullish' : score <= -2 ? 'bearish' : 'sideways';

  return {
    direction,
    score,
    votes_cast: counted,
    checks_total: checks.length,
    checks,
    indicators: {
      close: last,
      ema20: round(e20), ema50: round(e50),
      rsi14: round(r, 2), atr14: round(a), vwap: round(v),
      noise_floor: round(noise),
      macd: m ? { macd: round(m.macd, 4), signal: round(m.signal, 4), histogram: round(m.histogram, 4) } : null,
    },
  };
}

function round(n, dp = 4) {
  if (n === null || n === undefined || Number.isNaN(n)) return null;
  return Number(n.toFixed(dp));
}

export { round };
