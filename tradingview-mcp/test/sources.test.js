import test from 'node:test';
import assert from 'node:assert/strict';
import { createFeeds, FeedError } from '../lib/sources.js';
import { resolve } from '../lib/symbols.js';

// A fetch stand-in: asserts what was requested and replays a canned payload.
function mockFetch(routes) {
  const calls = [];
  const impl = async (url) => {
    calls.push(url);
    for (const [match, payload] of routes) {
      if (url.includes(match)) {
        return { ok: true, status: 200, json: async () => payload };
      }
    }
    return { ok: false, status: 404, json: async () => ({}) };
  };
  impl.calls = calls;
  return impl;
}

test('crypto quotes are parsed from the Crypto.com ticker shape', async () => {
  const fetchImpl = mockFetch([['get-tickers', {
    result: { data: [{ i: 'BTC_USDT', a: '78324.14', b: '78324.13', k: '78324.15', h: '79408.51', l: '77950.32', c: '0.0014', v: '1037.99', t: 1788130204837 }] },
  }]]);
  const feeds = createFeeds({ fetchImpl, apiKey: null });
  const q = await feeds.quote(resolve('btc').quote);

  assert.equal(q.price, 78324.14);
  assert.equal(q.bid, 78324.13);
  assert.equal(q.ask, 78324.15);
  assert.ok(Math.abs(q.change_24h_pct - 0.14) < 1e-9, 'the c field is a ratio and must be scaled to percent');
  assert.match(q.source, /crypto\.com BTC_USDT/);
  assert.equal(q.as_of, new Date(1788130204837).toISOString());
  assert.ok(fetchImpl.calls[0].includes('instrument_name=BTC_USDT'));
});

test('crypto works with no Alpha Vantage key at all', async () => {
  const fetchImpl = mockFetch([['get-tickers', { result: { data: [{ a: '100', t: 1 }] } }]]);
  const feeds = createFeeds({ fetchImpl, apiKey: undefined });
  assert.equal((await feeds.quote(resolve('ETHUSD').quote)).price, 100);
});

test('a missing Alpha Vantage key is reported as a clear, actionable error', async () => {
  const feeds = createFeeds({ fetchImpl: mockFetch([]), apiKey: undefined });
  await assert.rejects(() => feeds.quote(resolve('XAUUSD').quote), (err) => {
    assert.ok(err instanceof FeedError);
    assert.match(err.message, /ALPHAVANTAGE_API_KEY/);
    assert.match(err.message, /support\/#api-key/, 'tell the user where to get one');
    return true;
  });
});

test('Alpha Vantage rate-limit prose is surfaced as a retryable error, not silent nulls', async () => {
  const feeds = createFeeds({
    fetchImpl: mockFetch([['alphavantage', { Information: 'standard API rate limit is 25 requests per day' }]]),
    apiKey: 'TESTKEY',
  });
  await assert.rejects(() => feeds.quote(resolve('gold').quote), (err) => {
    assert.match(err.message, /rate limit/i);
    assert.equal(err.retryable, true);
    return true;
  });
});

test('an Alpha Vantage Error Message is not treated as retryable', async () => {
  const feeds = createFeeds({
    fetchImpl: mockFetch([['alphavantage', { 'Error Message': 'Invalid API call' }]]),
    apiKey: 'TESTKEY',
  });
  await assert.rejects(() => feeds.quote(resolve('AAPL').quote), (err) => {
    assert.equal(err.retryable, false);
    return true;
  });
});

test('the API key is sent to Alpha Vantage and never to Crypto.com', async () => {
  const fetchImpl = mockFetch([
    ['alphavantage', { 'Global Quote': { '05. price': '190.10', '07. latest trading day': '2026-08-28' } }],
    ['get-tickers', { result: { data: [{ a: '1', t: 1 }] } }],
  ]);
  const feeds = createFeeds({ fetchImpl, apiKey: 'SECRETKEY' });

  await feeds.quote(resolve('AAPL').quote);
  await feeds.quote(resolve('BTCUSD').quote);

  const [avCall, cryptoCall] = fetchImpl.calls;
  assert.ok(avCall.includes('apikey=SECRETKEY'));
  assert.ok(!cryptoCall.includes('SECRETKEY'), 'the key must never leak to a feed that does not need it');
});

test('candles come back oldest-first with numeric OHLCV', async () => {
  const fetchImpl = mockFetch([['get-candlestick', {
    result: { data: [
      { t: 1788130000000, o: '100', h: '110', l: '90', c: '105', v: '5' },
      { t: 1788130300000, o: '105', h: '115', l: '95', c: '112', v: '7' },
    ] },
  }]]);
  const feeds = createFeeds({ fetchImpl, apiKey: null });
  const candles = await feeds.candles(resolve('btc').candles, { interval: '5m', limit: 2 });

  assert.equal(candles.length, 2);
  assert.deepEqual(Object.keys(candles[0]), ['time', 'open', 'high', 'low', 'close', 'volume']);
  assert.equal(candles[1].close, 112);
  assert.ok(candles[0].time < candles[1].time, 'oldest first');
  assert.ok(fetchImpl.calls[0].includes('timeframe=5m'));
});

test('an unsupported interval is rejected with the supported list', async () => {
  const feeds = createFeeds({ fetchImpl: mockFetch([]), apiKey: null });
  await assert.rejects(
    () => feeds.candles(resolve('btc').candles, { interval: '7m' }),
    (err) => { assert.match(err.message, /unsupported interval "7m"/); assert.match(err.message, /5m/); return true; }
  );
});

test('order book returns imbalance and rejects non-crypto symbols', async () => {
  const fetchImpl = mockFetch([['get-book', {
    result: { data: [{ bids: [['100', '3', 1], ['99', '1', 1]], asks: [['101', '1', 1]], t: 1788130204837 }] },
  }]]);
  const feeds = createFeeds({ fetchImpl, apiKey: null });

  const book = await feeds.orderbook(resolve('btc').book, { depth: 2 });
  assert.equal(book.bid_volume, 4);
  assert.equal(book.ask_volume, 1);
  assert.equal(book.spread, 1);
  assert.ok(Math.abs(book.imbalance - 0.6) < 1e-9, 'bid-heavy book gives a positive imbalance');

  await assert.rejects(
    () => feeds.orderbook(resolve('XAUUSD').book, {}),
    (err) => { assert.match(err.message, /only available for crypto/); return true; }
  );
});

test('an HTTP failure names the host and marks 5xx retryable', async () => {
  const feeds = createFeeds({ fetchImpl: async () => ({ ok: false, status: 503, json: async () => ({}) }), apiKey: null });
  await assert.rejects(() => feeds.quote(resolve('btc').quote), (err) => {
    assert.match(err.message, /api\.crypto\.com returned HTTP 503/);
    assert.equal(err.retryable, true);
    return true;
  });
});

test('a network error is retryable and names the host', async () => {
  const feeds = createFeeds({ fetchImpl: async () => { throw new Error('ECONNRESET'); }, apiKey: null });
  await assert.rejects(() => feeds.quote(resolve('btc').quote), (err) => {
    assert.match(err.message, /network error contacting api\.crypto\.com/);
    assert.equal(err.retryable, true);
    return true;
  });
});
