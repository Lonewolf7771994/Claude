# Fixtures — provenance and a limitation you must read

Every value in this directory is **real market data**, captured live on
2026-08-30 through this session's MCP data connectors. Nothing here is
simulated, generated, or hand-invented.

## The limitation

These files are **connector-normalized payloads, NOT raw vendor HTTP response
bodies.**

That distinction matters and is not cosmetic. The Crypto.com REST API returns
book levels as positional arrays:

    "bids": [["78547.77", "0.01003", "1"], ...]

The MCP connector that produced these fixtures returns them as objects:

    "bids": [{"price": "78547.77", "qty": "0.01003"}, ...]

Same numbers, different shape. A provider written to parse these fixtures will
therefore **not** parse the vendor's live REST response without a second
transform.

## Why they were not captured raw

This container has no network route to any market-data host — `api.crypto.com`,
`api.binance.com`, `www.alphavantage.co`, `financialmodelingprep.com` and others
are all refused with HTTP 403 at the proxy gateway. The MCP connectors were the
only path to real data, so they are what these fixtures came from.

## What this means for the code

- Treat each fixture as the contract for a **connector-shaped source**, and give
  the vendor REST APIs their own parser.
- The claim "the same parsing code runs against a fixture and a live endpoint"
  holds only for a source whose live shape matches its fixture shape. It does
  **not** currently hold for Crypto.com REST.
- The live path must be verified on a machine with real network access before
  anyone claims it works. Green tests here are not evidence that it does.

## Files

| File | Source | Contents |
|---|---|---|
| `btc-usdt-orderbook.json` | Crypto.com connector | 25 levels/side, spread $0.01, captured 21:00:37Z |
| `btc-usdt-trades.json` | Crypto.com connector | 40 prints with the exchange's own aggressor `side` — real CVD input, not tick-rule inference |
| `commodities-quotes.json` | FMP connector | Gold `GCUSD` and Brent `BZUSD` quotes |

## Known gap

**WTI is absent and was deliberately not fabricated.** The FMP plan on this
connector denies `CLUSD`, and Alpha Vantage's WTI endpoint was out of its
25-request daily quota. Do not add a WTI fixture by copying Brent or by
inventing plausible numbers.
