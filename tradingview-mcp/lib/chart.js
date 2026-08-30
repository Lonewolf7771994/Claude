// The TradingView side: deep links and the official embeddable advanced-chart widget.
// TradingView exposes charts publicly; it does not expose a public quote API, which is
// why prices come from lib/sources.js instead.

const TV_INTERVAL = {
  '1m': '1', '3m': '3', '5m': '5', '15m': '15', '30m': '30',
  '1h': '60', '2h': '120', '4h': '240', '1d': 'D', '1D': 'D', '1w': 'W', '1M': 'M',
};

export function chartUrl(tvSymbol, { interval = '15m' } = {}) {
  const url = new URL('https://www.tradingview.com/chart/');
  url.searchParams.set('symbol', tvSymbol);
  const iv = TV_INTERVAL[interval];
  if (iv) url.searchParams.set('interval', iv);
  return url.toString();
}

export function symbolUrl(tvSymbol) {
  return `https://www.tradingview.com/symbols/${tvSymbol.replace(':', '-')}/`;
}

export function widgetHtml(tvSymbol, { interval = '15m', theme = 'dark', studies = [], height = 620, title } = {}) {
  const config = {
    autosize: true,
    symbol: tvSymbol,
    interval: TV_INTERVAL[interval] ?? '15',
    timezone: 'Etc/UTC',
    theme: theme === 'light' ? 'light' : 'dark',
    style: '1',
    locale: 'en',
    enable_publishing: false,
    allow_symbol_change: true,
    studies,
    support_host: 'https://www.tradingview.com',
  };
  const heading = title ?? `${tvSymbol} · ${interval}`;

  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${escapeHtml(heading)}</title>
<style>
  :root { color-scheme: ${theme === 'light' ? 'light' : 'dark'}; }
  body { margin: 0; background: ${theme === 'light' ? '#ffffff' : '#0d1117'}; color: ${theme === 'light' ? '#1a1a1a' : '#e6edf3'};
         font: 14px/1.5 -apple-system, "Segoe UI", system-ui, sans-serif; }
  header { padding: 16px 20px 8px; }
  h1 { margin: 0; font-size: 16px; font-weight: 600; letter-spacing: .01em; }
  .chart { height: ${Number(height) || 620}px; padding: 0 12px 12px; }
  .tradingview-widget-container, .tradingview-widget-container__widget { height: 100%; width: 100%; }
  footer { padding: 8px 20px 20px; font-size: 12px; opacity: .7; }
  a { color: ${theme === 'light' ? '#0969da' : '#58a6ff'}; }
</style>
</head>
<body>
<header><h1>${escapeHtml(heading)}</h1></header>
<div class="chart">
  <div class="tradingview-widget-container">
    <div class="tradingview-widget-container__widget"></div>
  </div>
</div>
<footer>
  Chart by <a href="${symbolUrl(tvSymbol)}" rel="noopener nofollow" target="_blank">TradingView</a>.
  Candles are rendered by TradingView's own feed; nothing on this page is synthesised.
</footer>
<script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
${JSON.stringify(config, null, 2)}
</script>
</body>
</html>`;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

export { TV_INTERVAL, escapeHtml };
