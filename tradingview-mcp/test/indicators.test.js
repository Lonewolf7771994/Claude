import test from 'node:test';
import assert from 'node:assert/strict';
import { ema, sma, rsi, atr, vwap, macd, bias } from '../lib/indicators.js';

const candle = (close, high = close + 1, low = close - 1, volume = 10) => ({ open: close, high, low, close, volume });

test('sma is the plain mean of the last N values', () => {
  assert.equal(sma([1, 2, 3, 4, 5], 5), 3);
  assert.equal(sma([10, 20, 30], 2), 25);
  assert.equal(sma([1, 2], 5), null);
});

test('ema of a flat series equals that constant', () => {
  assert.equal(ema(Array(50).fill(7), 20), 7);
});

test('ema reacts to a recent step faster than sma does', () => {
  // 40 flat bars then a jump: the EMA must have travelled further toward the new level.
  const stepped = [...Array(40).fill(100), ...Array(5).fill(200)];
  assert.ok(ema(stepped, 20) > sma(stepped, 20),
    `ema ${ema(stepped, 20)} should lead sma ${sma(stepped, 20)}`);
});

test('rsi is 100 for an unbroken advance and 0 for an unbroken decline', () => {
  assert.equal(rsi(Array.from({ length: 40 }, (_, i) => 100 + i), 14), 100);
  assert.equal(rsi(Array.from({ length: 40 }, (_, i) => 100 - i), 14), 0);
});

test('rsi of a flat series is 50', () => {
  assert.equal(rsi(Array(40).fill(100), 14), 50);
});

test('rsi matches a hand-computed Wilder value', () => {
  // Classic Wilder worked example: 15 closes, first 14 changes seed the averages.
  const closes = [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42,
                  45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28];
  assert.ok(Math.abs(rsi(closes, 14) - 70.46) < 0.5, `got ${rsi(closes, 14)}`);
});

test('atr of constant-range candles equals that range', () => {
  const candles = Array.from({ length: 40 }, () => candle(100));
  assert.ok(Math.abs(atr(candles, 14) - 2) < 1e-9);
});

test('vwap is volume-weighted, not a simple average', () => {
  const candles = [
    { high: 10, low: 10, close: 10, volume: 1 },
    { high: 20, low: 20, close: 20, volume: 99 },
  ];
  assert.ok(vwap(candles) > 19, 'the 99-unit bar must dominate');
  assert.equal(vwap([{ high: 1, low: 1, close: 1, volume: 0 }]), null, 'no volume means no vwap');
});

test('macd histogram is the gap between the macd line and its signal', () => {
  const closes = Array.from({ length: 120 }, (_, i) => 100 + i * 0.5);
  const m = macd(closes);
  assert.ok(m, 'macd should compute with 120 closes');
  assert.ok(Math.abs(m.histogram - (m.macd - m.signal)) < 1e-9);
  assert.ok(m.macd > 0, 'a steady advance gives a positive macd line');
});

test('bias reads a sustained advance as bullish and shows its work', () => {
  const candles = Array.from({ length: 200 }, (_, i) => candle(100 + i * 0.4));
  const r = bias(candles);
  assert.equal(r.direction, 'bullish');
  assert.ok(r.score >= 2);
  assert.equal(r.checks.length, 5, 'every check must be reported, not just the passing ones');
  assert.equal(r.checks_total, 5);
  assert.ok(r.checks.every((c) => typeof c.detail === 'string'));
  assert.ok(r.indicators.ema20 > r.indicators.ema50);
});

test('bias reads a sustained decline as bearish', () => {
  const candles = Array.from({ length: 200 }, (_, i) => candle(200 - i * 0.4));
  const r = bias(candles);
  assert.equal(r.direction, 'bearish');
  assert.ok(r.score <= -2);
});

test('bias reads chop as sideways rather than forcing a call', () => {
  const candles = Array.from({ length: 200 }, (_, i) => candle(100 + (i % 2 === 0 ? 0.05 : -0.05)));
  const r = bias(candles);
  assert.equal(r.direction, 'sideways');
  assert.ok(r.votes_cast <= 1, `noise must not cast votes, got ${r.votes_cast}: ${JSON.stringify(r.checks)}`);
});

test('differences inside the noise floor are recorded as abstentions, not votes', () => {
  // A tape drifting by far less than its own ATR should produce no confident direction.
  const candles = Array.from({ length: 200 }, (_, i) => candle(100 + i * 0.0001, 101, 99));
  const r = bias(candles);
  const abstained = r.checks.filter((c) => c.vote === 0);
  assert.ok(abstained.length >= 3, `expected abstentions, got ${JSON.stringify(r.checks)}`);
  assert.equal(r.direction, 'sideways');
  assert.ok(r.indicators.noise_floor > 0);
});
