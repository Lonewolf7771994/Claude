#!/usr/bin/env node
// TradingView MCP server - stdio transport, no dependencies.
//
// TradingView publishes charts, not a public market-data API, so this server splits the
// two honestly: the chart tools return real TradingView links and embeds, and the data
// tools return real quotes/candles/depth from Crypto.com (keyless) and Alpha Vantage.
// Nothing here invents a price.
//
// Protocol note: stdout carries JSON-RPC only. All logging goes to stderr, because an
// MCP client parses stdout line by line and a stray log line kills the connection.

import { writeFile, mkdir } from 'node:fs/promises';
import { dirname, resolve as resolvePath } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';
import { resolve as resolveSymbol, supported } from './lib/symbols.js';
import { createFeeds, FeedError } from './lib/sources.js';
import { chartUrl, symbolUrl, widgetHtml } from './lib/chart.js';
import { bias, round } from './lib/indicators.js';

const SERVER_INFO = { name: 'tradingview-mcp', version: '1.0.0' };
const SUPPORTED_PROTOCOLS = ['2025-06-18', '2025-03-26', '2024-11-05'];
const feeds = createFeeds();

const log = (...a) => process.stderr.write(`[tradingview-mcp] ${a.join(' ')}\n`);

// ---------------------------------------------------------------- tool definitions

const TOOLS = [
  {
    name: 'tv_symbol',
    description:
      'Resolve a friendly instrument name (gold, btc, oil, XAUUSD, AAPL) to its TradingView symbol, its chart URL, and which data feed serves its prices. Call this first when unsure how an instrument is named.',
    inputSchema: {
      type: 'object',
      properties: { symbol: { type: 'string', description: 'Instrument name or ticker, e.g. "gold", "BTC", "NASDAQ:AAPL"' } },
      required: ['symbol'],
    },
    handler: async ({ symbol }) => {
      const s = resolveSymbol(symbol);
      return {
        input: symbol,
        resolved: s.key,
        tradingview_symbol: s.tv,
        chart_url: chartUrl(s.tv),
        symbol_page: symbolUrl(s.tv),
        quote_feed: s.quote.feed,
        candles_feed: s.candles.feed,
        order_book: Boolean(s.book),
        preset_instruments: supported(),
      };
    },
  },
  {
    name: 'tv_quote',
    description:
      'Live price for an instrument, from the real feed behind it: Crypto.com for crypto (no API key needed), Alpha Vantage for metals, energy, FX and equities. Returns the price with its source and timestamp.',
    inputSchema: {
      type: 'object',
      properties: { symbol: { type: 'string', description: 'Instrument, e.g. "BTCUSD", "XAUUSD", "oil", "AAPL"' } },
      required: ['symbol'],
    },
    handler: async ({ symbol }) => {
      const s = resolveSymbol(symbol);
      const q = await feeds.quote(s.quote);
      return { symbol: s.key, tradingview_symbol: s.tv, chart_url: chartUrl(s.tv), ...q };
    },
  },
  {
    name: 'tv_candles',
    description:
      'OHLCV candles for an instrument. Crypto intervals: 1m 5m 15m 30m 1h 4h 1d 1w. Alpha Vantage intervals: 1m 5m 15m 30m 1h. Commodity series (oil, natural gas) are daily settlement values only.',
    inputSchema: {
      type: 'object',
      properties: {
        symbol: { type: 'string' },
        interval: { type: 'string', description: 'Candle interval, default 5m' },
        limit: { type: 'number', description: 'How many candles, default 200' },
      },
      required: ['symbol'],
    },
    handler: async ({ symbol, interval = '5m', limit = 200 }) => {
      const s = resolveSymbol(symbol);
      const candles = await feeds.candles(s.candles, { interval, limit });
      return {
        symbol: s.key, tradingview_symbol: s.tv, interval,
        count: candles.length,
        first: candles[0]?.time, last: candles[candles.length - 1]?.time,
        candles,
      };
    },
  },
  {
    name: 'tv_orderbook',
    description:
      'Live order book depth for a crypto instrument, with bid/ask volume and the resting-size imbalance across the requested depth. Crypto symbols only - no public venue publishes a consolidated book for spot gold or oil.',
    inputSchema: {
      type: 'object',
      properties: {
        symbol: { type: 'string', description: 'BTCUSD, ETHUSD, SOLUSD or XRPUSD' },
        depth: { type: 'number', description: 'Levels per side, default 20, max 150' },
      },
      required: ['symbol'],
    },
    handler: async ({ symbol, depth = 20 }) => {
      const s = resolveSymbol(symbol);
      const book = await feeds.orderbook(s.book, { depth });
      return { symbol: s.key, tradingview_symbol: s.tv, depth, ...book };
    },
  },
  {
    name: 'tv_analysis',
    description:
      'Pull real candles and compute EMA20/50, RSI14, ATR14, VWAP and MACD, then report a bullish/bearish/sideways read with each individual check shown so the evidence is auditable. Read-only market description - not an instruction to trade.',
    inputSchema: {
      type: 'object',
      properties: {
        symbol: { type: 'string' },
        interval: { type: 'string', description: 'Candle interval, default 15m' },
        limit: { type: 'number', description: 'Candles to analyse, default 300' },
      },
      required: ['symbol'],
    },
    handler: async ({ symbol, interval = '15m', limit = 300 }) => {
      const s = resolveSymbol(symbol);
      const candles = await feeds.candles(s.candles, { interval, limit });
      if (candles.length < 60) {
        throw new FeedError(`only ${candles.length} candles available for ${s.key} at ${interval}; need at least 60 for a reliable read`);
      }
      const read = bias(candles);
      return {
        symbol: s.key, tradingview_symbol: s.tv, interval,
        candles_analysed: candles.length,
        as_of: candles[candles.length - 1].time,
        ...read,
        chart_url: chartUrl(s.tv, { interval }),
        disclaimer: 'Descriptive only. No entry, stop-loss or take-profit is implied.',
      };
    },
  },
  {
    name: 'tv_chart',
    description:
      'Build a TradingView chart for an instrument: a deep link plus a self-contained HTML page embedding TradingView\'s official advanced-chart widget. Optionally writes the HTML to a file you can open in a browser.',
    inputSchema: {
      type: 'object',
      properties: {
        symbol: { type: 'string' },
        interval: { type: 'string', description: 'Chart interval, default 15m' },
        theme: { type: 'string', enum: ['dark', 'light'], description: 'Default dark' },
        studies: { type: 'array', items: { type: 'string' }, description: 'TradingView study ids, e.g. ["STD;EMA","STD;RSI"]' },
        save_to: { type: 'string', description: 'Optional path to write the HTML page to' },
      },
      required: ['symbol'],
    },
    handler: async ({ symbol, interval = '15m', theme = 'dark', studies = [], save_to }) => {
      const s = resolveSymbol(symbol);
      const html = widgetHtml(s.tv, { interval, theme, studies });
      const out = { symbol: s.key, tradingview_symbol: s.tv, chart_url: chartUrl(s.tv, { interval }), symbol_page: symbolUrl(s.tv) };

      if (save_to) {
        const path = resolvePath(save_to.startsWith('~') ? save_to.replace('~', process.env.HOME ?? tmpdir()) : save_to);
        await mkdir(dirname(path), { recursive: true });
        await writeFile(path, html, 'utf8');
        out.saved_to = path;
      } else {
        out.html = html;
      }
      return out;
    },
  },
];

const BY_NAME = new Map(TOOLS.map((t) => [t.name, t]));

// ---------------------------------------------------------------- JSON-RPC plumbing

function send(msg) {
  process.stdout.write(JSON.stringify(msg) + '\n');
}

function result(id, value) {
  send({ jsonrpc: '2.0', id, result: value });
}

function failure(id, code, message) {
  send({ jsonrpc: '2.0', id, error: { code, message } });
}

async function handle(msg) {
  const { id, method, params } = msg;
  const isNotification = id === undefined || id === null;

  switch (method) {
    case 'initialize': {
      const asked = params?.protocolVersion;
      return result(id, {
        protocolVersion: SUPPORTED_PROTOCOLS.includes(asked) ? asked : SUPPORTED_PROTOCOLS[0],
        capabilities: { tools: { listChanged: false } },
        serverInfo: SERVER_INFO,
        instructions:
          'TradingView charts plus real market data. Chart links and embeds come from TradingView; ' +
          'prices come from Crypto.com (crypto, keyless) and Alpha Vantage (metals, energy, FX, equities - needs ALPHAVANTAGE_API_KEY). ' +
          'Start with tv_symbol if you are unsure how an instrument is named.',
      });
    }

    case 'notifications/initialized':
    case 'initialized':
      return; // notification, no reply

    case 'ping':
      return isNotification ? undefined : result(id, {});

    case 'tools/list':
      return result(id, {
        tools: TOOLS.map(({ name, description, inputSchema }) => ({ name, description, inputSchema })),
      });

    case 'tools/call': {
      const tool = BY_NAME.get(params?.name);
      if (!tool) return failure(id, -32602, `unknown tool: ${params?.name}`);
      try {
        const value = await tool.handler(params.arguments ?? {});
        return result(id, { content: [{ type: 'text', text: JSON.stringify(value, null, 2) }] });
      } catch (err) {
        // A tool that fails reports it inside the result, so the model can see why and adapt.
        log(`tool ${tool.name} failed: ${err.message}`);
        return result(id, {
          isError: true,
          content: [{ type: 'text', text: `${tool.name} failed: ${err.message}${err instanceof FeedError && err.retryable ? ' (retryable)' : ''}` }],
        });
      }
    }

    case 'resources/list':
      return result(id, { resources: [] });
    case 'prompts/list':
      return result(id, { prompts: [] });

    default:
      if (isNotification) return;
      return failure(id, -32601, `method not found: ${method}`);
  }
}

// Newline-delimited JSON-RPC on stdin.
export function start() {
  let buffer = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', (chunk) => {
    buffer += chunk;
    let nl;
    while ((nl = buffer.indexOf('\n')) !== -1) {
      const line = buffer.slice(0, nl).trim();
      buffer = buffer.slice(nl + 1);
      if (!line) continue;

      let msg;
      try {
        msg = JSON.parse(line);
      } catch {
        failure(null, -32700, 'parse error');
        continue;
      }
      Promise.resolve(handle(msg)).catch((err) => {
        log(`unhandled: ${err.stack ?? err.message}`);
        if (msg.id !== undefined && msg.id !== null) failure(msg.id, -32603, `internal error: ${err.message}`);
      });
    }
  });

  process.stdin.on('end', () => process.exit(0));
  log(`ready - ${TOOLS.length} tools, ${process.env.ALPHAVANTAGE_API_KEY ? 'Alpha Vantage key present' : 'no Alpha Vantage key (crypto only)'}`);
}

// Only listen when run as a server; importing this file in a test must not block.
if (process.argv[1] && resolvePath(process.argv[1]) === fileURLToPath(import.meta.url)) {
  start();
}

export { TOOLS, handle, round };
