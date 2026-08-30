import test from 'node:test';
import assert from 'node:assert/strict';
import { resolve, normalize, supported } from '../lib/symbols.js';

test('common spellings all land on the same instrument', () => {
  for (const alias of ['gold', 'GOLD', ' xau ', 'XAU/USD', 'xauusd']) {
    assert.equal(resolve(alias).key, 'XAUUSD', `${alias} should resolve to XAUUSD`);
  }
  for (const alias of ['btc', 'BITCOIN', 'BTC/USD', 'btcusdt', 'XBTUSD']) {
    assert.equal(resolve(alias).key, 'BTCUSD', `${alias} should resolve to BTCUSD`);
  }
  for (const alias of ['oil', 'WTI', 'crude', 'USOIL']) {
    assert.equal(resolve(alias).key, 'USOIL', `${alias} should resolve to USOIL`);
  }
});

test('crypto routes to the keyless feed, metals and energy to Alpha Vantage', () => {
  assert.equal(resolve('BTCUSD').quote.feed, 'cryptocom');
  assert.equal(resolve('ETHUSD').quote.feed, 'cryptocom');
  assert.equal(resolve('XAUUSD').quote.feed, 'alphavantage');
  assert.equal(resolve('oil').quote.feed, 'alphavantage');
});

test('only crypto instruments advertise an order book', () => {
  assert.ok(resolve('BTCUSD').book, 'crypto has a public book');
  assert.equal(resolve('XAUUSD').book, undefined, 'no public consolidated book exists for spot gold');
  assert.equal(resolve('AAPL').book, undefined);
});

test('an explicit TradingView symbol is preserved but still gets a data feed', () => {
  const r = resolve('NASDAQ:AAPL');
  assert.equal(r.tv, 'NASDAQ:AAPL');
  assert.equal(r.quote.params.symbol, 'AAPL');

  const g = resolve('OANDA:XAUUSD');
  assert.equal(g.key, 'XAUUSD');
  assert.equal(g.quote.fn, 'GOLD_SILVER_SPOT', 'a known instrument keeps its curated feed');
});

test('an unknown ticker is treated as an equity rather than rejected', () => {
  const r = resolve('nvda');
  assert.equal(r.key, 'NVDA');
  assert.equal(r.tv, 'NVDA');
  assert.equal(r.quote.fn, 'GLOBAL_QUOTE');
});

test('empty input is rejected outright', () => {
  for (const bad of ['', '   ', null, undefined, 42]) {
    assert.throws(() => resolve(bad), /symbol is required/);
  }
});

test('normalize strips whitespace and upper-cases', () => {
  assert.equal(normalize('  btc usd '), 'BTCUSD');
});

test('the preset list is non-empty and covers the headline instruments', () => {
  const list = supported();
  for (const s of ['XAUUSD', 'BTCUSD', 'USOIL']) assert.ok(list.includes(s));
});
