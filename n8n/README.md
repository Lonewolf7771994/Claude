# ME Pro → n8n

Receives Movement Engine Pro alerts from TradingView, authenticates them,
drops duplicates, applies a quality gate, sizes the position, and notifies.

Import `me-pro-signal-handler.json` (n8n → Workflows → Import from File).

## Pipeline

```
TradingView Webhook
  → Validate & Authenticate   secret check, required fields, SL-side sanity
  → Deduplicate               drops repeats of (symbol, tf, mode, seq, bar_time)
  → Quality Gate              confluence / stop type / mode / trigger / risk / R:R
  → Passed?  ── true  → Position Size & Message → Notify
             └─ false → Rejected (reject_reason says which rule fired)
```

## Setup

1. **Activate the workflow** and copy the production webhook URL.
2. **Pine:** set *Alerts → Webhook Shared Secret* to a long random string.
3. **n8n:** open *Validate & Authenticate* and set `EXPECTED_SECRET` to the same string.
4. **TradingView alert:** condition `ME Pro — Any Signal`, "Once Per Bar Close",
   message `{{strategy.order.alert_message}}` is **not** used — the engine calls
   `alert()` itself, so leave the message box empty and paste the webhook URL
   into *Notifications → Webhook URL*.
5. **Notify node:** replace the placeholder URL with your Discord/Slack webhook,
   or your Telegram bot endpoint. The body is `{"content": "..."}` (Discord
   shape); for Slack change it to `{"text": "..."}`, for Telegram use
   `{"chat_id": "...", "text": "..."}`.
6. **Position sizing:** set `ACCOUNT.equity` and `ACCOUNT.riskPct` in the
   *Position Size & Message* node. Size is derived from stop distance, so every
   trade risks the same fraction of equity regardless of how wide the stop is.

## Tuning the gate

All policy lives in the `CFG` block of *Quality Gate* — no Pine edits needed:

| key | default | meaning |
|---|---|---|
| `minConfluence` | 2 | of 3 (HTF side, VWAP side, value-area side) |
| `requireStructuralStop` | true | rejects `stop_type: "clamped"` — a stop the engine moved rather than took from structure |
| `allowedModes` / `allowedTriggers` | `[]` (any) | e.g. `['Balanced','Strict']`, `['MSS','SWEEP']` |
| `minRiskAtr` / `maxRiskAtr` | 0 / 99 | stop distance in ATR |
| `minRR1` | 1.0 | TP1 distance as a multiple of stop distance |

Rejected items are flagged, never dropped, so `reject_reason` in the execution
log tells you exactly which rule fired.

## Sample payload

```json
{
  "secret": "…", "action": "BUY", "trigger": "MSS", "mode": "Balanced",
  "symbol": "XAUUSD", "tf": "15", "entry": 4100.5, "sl": 4035.58,
  "tp1": 4118.0, "tp2": 4180.0, "tp3": 4209.07, "risk_atr": 1.2,
  "of_pct": 72.5, "delta": 0.45, "rel_vol": 1.8, "rsi": 61.3,
  "cvd": "BULL", "htf": "BULL", "vwap": "ABOVE", "frvp": "IN VA+",
  "poc": 4053.29, "vah": 4082.31, "val": 3998.45, "regime": "NORMAL",
  "stop_type": "structural", "confluence": 3, "seq": 42,
  "bar_time": 1754323200000
}
```

## Adding execution

Append an HTTP Request node after *Position Size & Message* and post to your
broker/exchange API using `$json.qty`, `$json.entry`, `$json.sl`, `$json.tp1`.
Two cautions before you do:

- The secret is cleartext in the payload. It stops casual forgery by someone who
  has the URL; it is not a signature and does not survive someone who can read
  your alert configuration. Never let an unauthenticated endpoint place orders.
- Test against a paper/demo endpoint until you have seen the gate reject the
  things you expect it to reject. Nothing in this repo has been backtested.
