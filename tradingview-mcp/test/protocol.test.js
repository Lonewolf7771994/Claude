import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const SERVER = join(dirname(fileURLToPath(import.meta.url)), '..', 'server.js');

// Drives the real server process over stdio, exactly as an MCP client does.
function client() {
  const proc = spawn(process.execPath, [SERVER], { stdio: ['pipe', 'pipe', 'pipe'] });
  const pending = new Map();
  let buffer = '';
  let stderr = '';

  proc.stdout.setEncoding('utf8');
  proc.stdout.on('data', (chunk) => {
    buffer += chunk;
    let nl;
    while ((nl = buffer.indexOf('\n')) !== -1) {
      const line = buffer.slice(0, nl).trim();
      buffer = buffer.slice(nl + 1);
      if (!line) continue;
      const msg = JSON.parse(line);            // stdout must be pure JSON-RPC
      const resolve = pending.get(msg.id);
      if (resolve) { pending.delete(msg.id); resolve(msg); }
    }
  });
  proc.stderr.setEncoding('utf8');
  proc.stderr.on('data', (c) => { stderr += c; });

  let nextId = 1;
  return {
    request(method, params) {
      const id = nextId++;
      return new Promise((resolve, reject) => {
        pending.set(id, resolve);
        proc.stdin.write(JSON.stringify({ jsonrpc: '2.0', id, method, params }) + '\n');
        setTimeout(() => reject(new Error(`timeout waiting for ${method}; stderr: ${stderr}`)), 10000).unref?.();
      });
    },
    notify(method, params) {
      proc.stdin.write(JSON.stringify({ jsonrpc: '2.0', method, params }) + '\n');
    },
    writeRaw(text) { proc.stdin.write(text); },
    get stderr() { return stderr; },
    close() { proc.stdin.end(); proc.kill(); },
  };
}

test('the server completes the MCP initialize handshake', async () => {
  const c = client();
  try {
    const res = await c.request('initialize', {
      protocolVersion: '2025-06-18',
      capabilities: {},
      clientInfo: { name: 'test', version: '1.0' },
    });
    assert.equal(res.jsonrpc, '2.0');
    assert.equal(res.result.protocolVersion, '2025-06-18');
    assert.equal(res.result.serverInfo.name, 'tradingview-mcp');
    assert.ok(res.result.capabilities.tools, 'must advertise the tools capability');
    assert.match(res.result.instructions, /TradingView/);
  } finally { c.close(); }
});

test('an unknown protocol version falls back to one the server supports', async () => {
  const c = client();
  try {
    const res = await c.request('initialize', { protocolVersion: '1999-01-01', capabilities: {}, clientInfo: { name: 't', version: '1' } });
    assert.equal(res.result.protocolVersion, '2025-06-18');
  } finally { c.close(); }
});

test('tools/list advertises every tool with a usable schema', async () => {
  const c = client();
  try {
    await c.request('initialize', { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 't', version: '1' } });
    c.notify('notifications/initialized');
    const res = await c.request('tools/list');

    const names = res.result.tools.map((t) => t.name).sort();
    assert.deepEqual(names, ['tv_analysis', 'tv_candles', 'tv_chart', 'tv_orderbook', 'tv_quote', 'tv_symbol']);
    for (const t of res.result.tools) {
      assert.ok(t.description.length > 40, `${t.name} needs a description a model can act on`);
      assert.equal(t.inputSchema.type, 'object');
      assert.ok(t.inputSchema.properties.symbol, `${t.name} must take a symbol`);
      assert.deepEqual(t.inputSchema.required, ['symbol']);
    }
  } finally { c.close(); }
});

test('tv_symbol resolves an alias without touching the network', async () => {
  const c = client();
  try {
    await c.request('initialize', { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 't', version: '1' } });
    const res = await c.request('tools/call', { name: 'tv_symbol', arguments: { symbol: 'gold' } });
    const payload = JSON.parse(res.result.content[0].text);

    assert.equal(payload.resolved, 'XAUUSD');
    assert.equal(payload.tradingview_symbol, 'OANDA:XAUUSD');
    assert.match(payload.chart_url, /^https:\/\/www\.tradingview\.com\/chart\/\?symbol=OANDA%3AXAUUSD/);
    assert.equal(payload.quote_feed, 'alphavantage');
    assert.ok(payload.preset_instruments.includes('BTCUSD'));
  } finally { c.close(); }
});

test('tv_chart builds a real TradingView embed offline', async () => {
  const c = client();
  try {
    await c.request('initialize', { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 't', version: '1' } });
    const res = await c.request('tools/call', { name: 'tv_chart', arguments: { symbol: 'btc', interval: '4h', theme: 'dark' } });
    const payload = JSON.parse(res.result.content[0].text);

    assert.equal(payload.tradingview_symbol, 'COINBASE:BTCUSD');
    assert.match(payload.chart_url, /interval=240/, '4h must map to TradingView interval 240');
    assert.match(payload.html, /embed-widget-advanced-chart\.js/);
    assert.match(payload.html, /"symbol": "COINBASE:BTCUSD"/);
    assert.match(payload.html, /<!doctype html>/i);
  } finally { c.close(); }
});

test('a tool failure is returned as isError, not as a dead connection', async () => {
  const c = client();
  try {
    await c.request('initialize', { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 't', version: '1' } });
    // Order book on a metal is unsupported by design; the server must say so and stay alive.
    const res = await c.request('tools/call', { name: 'tv_orderbook', arguments: { symbol: 'XAUUSD' } });
    assert.equal(res.result.isError, true);
    assert.match(res.result.content[0].text, /only available for crypto/);

    const still = await c.request('tools/list');
    assert.ok(still.result.tools.length === 6, 'the server must survive a failed tool call');
  } finally { c.close(); }
});

test('an unknown tool is a protocol error', async () => {
  const c = client();
  try {
    await c.request('initialize', { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 't', version: '1' } });
    const res = await c.request('tools/call', { name: 'tv_nonsense', arguments: {} });
    assert.equal(res.error.code, -32602);
    assert.match(res.error.message, /unknown tool/);
  } finally { c.close(); }
});

test('malformed input does not kill the server', async () => {
  const c = client();
  try {
    c.writeRaw('this is not json\n');
    const res = await c.request('initialize', { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 't', version: '1' } });
    assert.equal(res.result.serverInfo.name, 'tradingview-mcp');
  } finally { c.close(); }
});

test('logs go to stderr so stdout stays parseable', async () => {
  const c = client();
  try {
    await c.request('initialize', { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 't', version: '1' } });
    await new Promise((r) => setTimeout(r, 100));
    assert.match(c.stderr, /\[tradingview-mcp\] ready/, 'the ready banner belongs on stderr');
  } finally { c.close(); }
});

test('ping is answered', async () => {
  const c = client();
  try {
    await c.request('initialize', { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 't', version: '1' } });
    const res = await c.request('ping');
    assert.deepEqual(res.result, {});
  } finally { c.close(); }
});
