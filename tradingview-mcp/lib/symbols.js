// Maps a friendly instrument name to (a) the TradingView symbol used for charts
// and (b) the real data feed used for prices. TradingView publishes charts, not a
// public quote API, so every number here comes from a source that does.

const CRYPTO = (base, tvExchange = 'COINBASE') => ({
  tv: `${tvExchange}:${base}USD`,
  quote: { feed: 'cryptocom', instrument: `${base}_USDT` },
  candles: { feed: 'cryptocom', instrument: `${base}_USDT` },
  book: { feed: 'cryptocom', instrument: `${base}_USDT` },
});

const MAP = {
  XAUUSD: {
    tv: 'OANDA:XAUUSD',
    quote: { feed: 'alphavantage', fn: 'GOLD_SILVER_SPOT', params: { symbol: 'XAU' } },
    candles: { feed: 'alphavantage', fn: 'FX_INTRADAY', params: { from_symbol: 'XAU', to_symbol: 'USD' } },
  },
  XAGUSD: {
    tv: 'OANDA:XAGUSD',
    quote: { feed: 'alphavantage', fn: 'GOLD_SILVER_SPOT', params: { symbol: 'XAG' } },
    candles: { feed: 'alphavantage', fn: 'FX_INTRADAY', params: { from_symbol: 'XAG', to_symbol: 'USD' } },
  },
  USOIL: {
    tv: 'TVC:USOIL',
    quote: { feed: 'alphavantage', fn: 'WTI', params: { interval: 'daily' } },
    candles: { feed: 'alphavantage', fn: 'WTI', params: { interval: 'daily' } },
  },
  UKOIL: {
    tv: 'TVC:UKOIL',
    quote: { feed: 'alphavantage', fn: 'BRENT', params: { interval: 'daily' } },
    candles: { feed: 'alphavantage', fn: 'BRENT', params: { interval: 'daily' } },
  },
  NATGAS: {
    tv: 'TVC:NATURALGAS',
    quote: { feed: 'alphavantage', fn: 'NATURAL_GAS', params: { interval: 'daily' } },
    candles: { feed: 'alphavantage', fn: 'NATURAL_GAS', params: { interval: 'daily' } },
  },
  BTCUSD: CRYPTO('BTC'),
  ETHUSD: CRYPTO('ETH'),
  SOLUSD: CRYPTO('SOL'),
  XRPUSD: CRYPTO('XRP'),
};

// Everything a human might type for the instruments above.
const ALIASES = {
  GOLD: 'XAUUSD', XAU: 'XAUUSD', 'XAU/USD': 'XAUUSD', GC: 'XAUUSD',
  SILVER: 'XAGUSD', XAG: 'XAGUSD', 'XAG/USD': 'XAGUSD',
  OIL: 'USOIL', WTI: 'USOIL', CL: 'USOIL', CRUDE: 'USOIL', USOUSD: 'USOIL',
  BRENT: 'UKOIL', UKOUSD: 'UKOIL',
  NG: 'NATGAS', NATURALGAS: 'NATGAS', GAS: 'NATGAS',
  BTC: 'BTCUSD', 'BTC/USD': 'BTCUSD', XBTUSD: 'BTCUSD', BITCOIN: 'BTCUSD', BTCUSDT: 'BTCUSD',
  ETH: 'ETHUSD', 'ETH/USD': 'ETHUSD', ETHEREUM: 'ETHUSD', ETHUSDT: 'ETHUSD',
  SOL: 'SOLUSD', SOLUSDT: 'SOLUSD',
  XRP: 'XRPUSD', XRPUSDT: 'XRPUSD',
};

export function normalize(input) {
  if (typeof input !== 'string' || !input.trim()) {
    throw new Error('symbol is required');
  }
  return input.trim().toUpperCase().replace(/\s+/g, '');
}

export function resolve(input) {
  const raw = normalize(input);

  // An explicit TradingView symbol ("NASDAQ:AAPL", "OANDA:XAUUSD") is passed through.
  if (raw.includes(':')) {
    const ticker = raw.split(':')[1];
    const known = MAP[ALIASES[ticker] || ticker];
    if (known) return { key: ALIASES[ticker] || ticker, ...known, tv: raw };
    return equity(ticker, raw);
  }

  const key = ALIASES[raw] || raw;
  if (MAP[key]) return { key, ...MAP[key] };

  // Anything else is treated as an equity/ETF ticker; TradingView resolves bare tickers.
  return equity(raw, raw);
}

function equity(ticker, tv) {
  return {
    key: ticker,
    tv,
    quote: { feed: 'alphavantage', fn: 'GLOBAL_QUOTE', params: { symbol: ticker } },
    candles: { feed: 'alphavantage', fn: 'TIME_SERIES_INTRADAY', params: { symbol: ticker } },
  };
}

export function supported() {
  return Object.keys(MAP);
}

export { MAP, ALIASES };
