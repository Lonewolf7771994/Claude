// Real data feeds. TradingView is the chart layer; these are the quote layer.
//   - Crypto.com public market data: no API key, no quota.
//   - Alpha Vantage: needs ALPHAVANTAGE_API_KEY (free tier is 25 requests/day).

const CRYPTOCOM = 'https://api.crypto.com/exchange/v1/public';
const ALPHAVANTAGE = 'https://www.alphavantage.co/query';

const CRYPTOCOM_TF = {
  '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
  '1h': '1h', '4h': '4h', '1d': '1D', '1D': '1D', '1w': '7D',
};

const AV_INTRADAY = { '1m': '1min', '5m': '5min', '15m': '15min', '30m': '30min', '1h': '60min' };

export class FeedError extends Error {
  constructor(message, { retryable = false } = {}) {
    super(message);
    this.name = 'FeedError';
    this.retryable = retryable;
  }
}

// Injectable so tests never touch the network.
export function createFeeds({ fetchImpl = globalThis.fetch, apiKey = process.env.ALPHAVANTAGE_API_KEY } = {}) {
  async function getJson(url) {
    let res;
    try {
      res = await fetchImpl(url, { headers: { accept: 'application/json' } });
    } catch (err) {
      throw new FeedError(`network error contacting ${new URL(url).host}: ${err.message}`, { retryable: true });
    }
    if (!res.ok) {
      throw new FeedError(`${new URL(url).host} returned HTTP ${res.status}`, { retryable: res.status >= 500 || res.status === 429 });
    }
    return res.json();
  }

  async function alphaVantage(fn, params) {
    if (!apiKey) {
      throw new FeedError(
        'ALPHAVANTAGE_API_KEY is not set. Crypto symbols work without it; metals, energy, FX and equities need a free key from https://www.alphavantage.co/support/#api-key'
      );
    }
    const url = new URL(ALPHAVANTAGE);
    url.searchParams.set('function', fn);
    for (const [k, v] of Object.entries(params)) url.searchParams.set(k, String(v));
    url.searchParams.set('apikey', apiKey);

    const body = await getJson(url.toString());
    // Alpha Vantage signals every failure with HTTP 200 and a prose field.
    if (body['Error Message']) throw new FeedError(`Alpha Vantage: ${body['Error Message']}`);
    if (body.Note) throw new FeedError(`Alpha Vantage rate limit: ${body.Note}`, { retryable: true });
    if (body.Information) throw new FeedError(`Alpha Vantage: ${body.Information}`, { retryable: true });
    return body;
  }

  return {
    async quote(spec) {
      if (spec.feed === 'cryptocom') {
        const body = await getJson(`${CRYPTOCOM}/get-tickers?instrument_name=${encodeURIComponent(spec.instrument)}`);
        const t = body?.result?.data?.[0];
        if (!t) throw new FeedError(`Crypto.com returned no ticker for ${spec.instrument}`);
        return {
          price: num(t.a ?? t.last),
          bid: num(t.b ?? t.best_bid),
          ask: num(t.k ?? t.best_ask),
          high_24h: num(t.h ?? t.high),
          low_24h: num(t.l ?? t.low),
          change_24h_pct: t.c !== undefined ? num(t.c) * 100 : num(t.change),
          volume_24h: num(t.v ?? t.volume),
          as_of: new Date(Number(t.t ?? Date.now())).toISOString(),
          source: `crypto.com ${spec.instrument}`,
        };
      }

      const body = await alphaVantage(spec.fn, spec.params);

      if (spec.fn === 'GOLD_SILVER_SPOT') {
        const d = body?.data ?? body;
        const price = num(d?.price ?? d?.spot_price ?? d?.value);
        if (price === null) throw new FeedError(`Alpha Vantage returned no spot price (payload keys: ${Object.keys(body).join(', ')})`);
        return { price, as_of: d?.timestamp ?? d?.date ?? new Date().toISOString(), source: `alphavantage ${spec.fn} ${spec.params.symbol}` };
      }

      if (spec.fn === 'GLOBAL_QUOTE') {
        const q = body['Global Quote'] ?? {};
        const price = num(q['05. price']);
        if (price === null) throw new FeedError(`no quote returned for ${spec.params.symbol}`);
        return {
          price,
          open: num(q['02. open']), high_24h: num(q['03. high']), low_24h: num(q['04. low']),
          previous_close: num(q['08. previous close']),
          change_24h_pct: num(String(q['10. change percent'] ?? '').replace('%', '')),
          volume_24h: num(q['06. volume']),
          as_of: q['07. latest trading day'] ?? new Date().toISOString(),
          source: `alphavantage GLOBAL_QUOTE ${spec.params.symbol}`,
        };
      }

      // WTI / BRENT / NATURAL_GAS all return { data: [{ date, value }, ...] } newest first.
      const rows = body?.data;
      if (!Array.isArray(rows) || rows.length === 0) throw new FeedError(`Alpha Vantage returned no series for ${spec.fn}`);
      const latest = rows.find((r) => num(r.value) !== null);
      if (!latest) throw new FeedError(`Alpha Vantage series for ${spec.fn} has no numeric values`);
      const prev = rows.slice(rows.indexOf(latest) + 1).find((r) => num(r.value) !== null);
      const price = num(latest.value);
      return {
        price,
        previous_close: prev ? num(prev.value) : null,
        change_24h_pct: prev && num(prev.value) ? ((price - num(prev.value)) / num(prev.value)) * 100 : null,
        as_of: latest.date,
        source: `alphavantage ${spec.fn}`,
        note: 'settlement series - one value per day, not an intraday tick',
      };
    },

    async candles(spec, { interval = '5m', limit = 200 } = {}) {
      if (spec.feed === 'cryptocom') {
        const tf = CRYPTOCOM_TF[interval];
        if (!tf) throw new FeedError(`unsupported interval "${interval}" (crypto: ${Object.keys(CRYPTOCOM_TF).join(', ')})`);
        const body = await getJson(
          `${CRYPTOCOM}/get-candlestick?instrument_name=${encodeURIComponent(spec.instrument)}&timeframe=${tf}&count=${clamp(limit, 1, 1000)}`
        );
        const rows = body?.result?.data ?? [];
        if (rows.length === 0) throw new FeedError(`Crypto.com returned no candles for ${spec.instrument} ${tf}`);
        return rows.map((r) => ({
          time: new Date(Number(r.t)).toISOString(),
          open: num(r.o), high: num(r.h), low: num(r.l), close: num(r.c), volume: num(r.v),
        }));
      }

      if (spec.fn === 'FX_INTRADAY' || spec.fn === 'TIME_SERIES_INTRADAY') {
        const avInterval = AV_INTRADAY[interval];
        if (!avInterval) throw new FeedError(`unsupported interval "${interval}" (alphavantage: ${Object.keys(AV_INTRADAY).join(', ')})`);
        const body = await alphaVantage(spec.fn, { ...spec.params, interval: avInterval, outputsize: limit > 100 ? 'full' : 'compact' });
        const key = Object.keys(body).find((k) => k.startsWith('Time Series'));
        if (!key) throw new FeedError(`Alpha Vantage returned no time series (keys: ${Object.keys(body).join(', ')})`);
        const rows = Object.entries(body[key])
          .map(([time, o]) => ({
            time: new Date(time.replace(' ', 'T') + 'Z').toISOString(),
            open: num(o['1. open']), high: num(o['2. high']), low: num(o['3. low']),
            close: num(o['4. close']), volume: num(o['5. volume'] ?? 0) ?? 0,
          }))
          .sort((a, b) => a.time.localeCompare(b.time));
        return rows.slice(-clamp(limit, 1, 5000));
      }

      // Daily commodity series.
      const body = await alphaVantage(spec.fn, spec.params);
      const rows = (body?.data ?? [])
        .filter((r) => num(r.value) !== null)
        .map((r) => ({ time: new Date(r.date + 'T00:00:00Z').toISOString(), open: num(r.value), high: num(r.value), low: num(r.value), close: num(r.value), volume: 0 }))
        .sort((a, b) => a.time.localeCompare(b.time));
      if (rows.length === 0) throw new FeedError(`Alpha Vantage returned no series for ${spec.fn}`);
      return rows.slice(-clamp(limit, 1, 5000));
    },

    async orderbook(spec, { depth = 20 } = {}) {
      if (spec?.feed !== 'cryptocom') {
        throw new FeedError('order book depth is only available for crypto symbols (BTCUSD, ETHUSD, SOLUSD, XRPUSD)');
      }
      const body = await getJson(
        `${CRYPTOCOM}/get-book?instrument_name=${encodeURIComponent(spec.instrument)}&depth=${clamp(depth, 1, 150)}`
      );
      const book = body?.result?.data?.[0];
      if (!book) throw new FeedError(`Crypto.com returned no book for ${spec.instrument}`);
      const level = (row) => ({ price: num(row[0]), size: num(row[1]), orders: row[2] !== undefined ? Number(row[2]) : null });
      const bids = (book.bids ?? []).map(level);
      const asks = (book.asks ?? []).map(level);
      const bidVol = bids.reduce((a, b) => a + (b.size ?? 0), 0);
      const askVol = asks.reduce((a, b) => a + (b.size ?? 0), 0);
      return {
        bids, asks,
        spread: asks[0] && bids[0] ? asks[0].price - bids[0].price : null,
        bid_volume: bidVol,
        ask_volume: askVol,
        // >0 means resting bid size outweighs ask size across the requested depth.
        imbalance: bidVol + askVol > 0 ? (bidVol - askVol) / (bidVol + askVol) : null,
        as_of: new Date(Number(book.t ?? Date.now())).toISOString(),
        source: `crypto.com ${spec.instrument}`,
      };
    },
  };
}

function num(v) {
  if (v === null || v === undefined || v === '') return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function clamp(n, lo, hi) {
  return Math.min(hi, Math.max(lo, Number(n) || lo));
}

export { num, clamp };
