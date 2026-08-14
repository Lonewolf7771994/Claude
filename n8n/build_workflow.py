#!/usr/bin/env python3
"""Generate the n8n workflow. Re-run after changing the alert payload."""
import json, os

VALIDATE = r'''// ME Pro — authenticate, parse, and check the trade plan is internally sound.
const EXPECTED_SECRET = '';   // must match the Pine "Webhook Shared Secret"

const out = [];
for (const item of $input.all()) {
  let p = item.json.body ?? item.json;
  if (typeof p === 'string') {
    try { p = JSON.parse(p); }
    catch (e) { throw new Error('Payload is not valid JSON: ' + e.message); }
  }

  if (EXPECTED_SECRET !== '' && p.secret !== EXPECTED_SECRET) {
    throw new Error('Rejected: bad or missing secret');
  }

  const required = ['action','symbol','tf','entry','sl','tp1','tp2','tp3','seq','bar_time'];
  const missing = required.filter(k => p[k] === undefined || p[k] === null || p[k] === '');
  if (missing.length) throw new Error('Missing fields: ' + missing.join(', '));
  if (p.action !== 'BUY' && p.action !== 'SELL') throw new Error('Bad action: ' + p.action);

  for (const k of ['entry','sl','tp1','tp2','tp3','risk_atr','confluence','seq','bar_time','rsi','delta','rel_vol','of_pct','poc','vah','val']) {
    if (p[k] !== undefined) {
      const v = Number(p[k]);
      if (!isFinite(v)) throw new Error('Non-numeric field ' + k + ': ' + p[k]);
      p[k] = v;
    }
  }

  // ---- trade-plan invariants -------------------------------------------
  // The engine shipped an INVERTED TP order for eleven versions (TP1 was the
  // furthest target; fixed Pine-side in v3.5.15). A receiver that trusts the
  // payload blindly would have placed and sized those exits backwards, and
  // nothing downstream would ever have noticed. Check the plan here too:
  // the sender is not the only place a plan can go wrong.
  const dir = p.action === 'BUY' ? 1 : -1;

  if ((p.entry - p.sl) * dir <= 0) {
    throw new Error(`SL ${p.sl} is on the wrong side of entry ${p.entry} for a ${p.action}`);
  }

  const tps = [p.tp1, p.tp2, p.tp3];
  tps.forEach((t, i) => {
    if ((t - p.entry) * dir <= 0) {
      throw new Error(`TP${i+1} ${t} is on the wrong side of entry ${p.entry} for a ${p.action}`);
    }
  });
  for (let i = 1; i < tps.length; i++) {
    if ((tps[i] - tps[i-1]) * dir <= 0) {
      throw new Error(`TP order inverted or duplicated: ${tps.join(' / ')} for a ${p.action}`);
    }
  }

  const risk = Math.abs(p.entry - p.sl);
  p.rr1 = Number((Math.abs(p.tp1 - p.entry) / risk).toFixed(2));
  p.rr2 = Number((Math.abs(p.tp2 - p.entry) / risk).toFixed(2));
  p.rr3 = Number((Math.abs(p.tp3 - p.entry) / risk).toFixed(2));
  p.risk_per_unit = risk;

  delete p.secret;
  p.received_at = new Date().toISOString();
  out.push({ json: p });
}
return out;'''

DEDUPE = r'''// ME Pro — drop duplicate deliveries.
// TradingView retries webhooks; the engine never re-sends, so any repeat of
// (symbol, tf, mode, seq, bar_time) is a duplicate.
const store = $getWorkflowStaticData('global');
store.seen = store.seen || {};

const now = Date.now();
const TTL_MS = 7 * 24 * 60 * 60 * 1000;
for (const k of Object.keys(store.seen)) {
  if (now - store.seen[k] > TTL_MS) delete store.seen[k];
}

const out = [];
for (const item of $input.all()) {
  const p = item.json;
  const key = [p.symbol, p.tf, p.mode, p.seq, p.bar_time].join('|');
  if (store.seen[key]) continue;
  store.seen[key] = now;
  out.push(item);
}
return out;'''

FILTER = r'''// ME Pro — quality gate. Policy only; tune here, not in Pine.
// Items are flagged rather than dropped, so rejections stay visible in the log.
const CFG = {
  minConfluence:         2,      // 0-3 (HTF side + VWAP side + value-area side)
  requireStructuralStop: true,   // reject stop_type === 'clamped'
  allowedModes:          [],     // [] = any, e.g. ['Scalp']
  allowedTriggers:       [],     // [] = any, e.g. ['SWEEP','MSS']
  minRiskAtr:            0.0,
  maxRiskAtr:            99.0,
  minRR1:                1.0,    // TP1 as a multiple of stop distance
  maxRR1:                99.0,   // guards against an absurdly distant first target
};

const out = [];
for (const item of $input.all()) {
  const p = { ...item.json };
  const why = [];

  if (p.confluence !== undefined && p.confluence < CFG.minConfluence) why.push(`confluence ${p.confluence}<${CFG.minConfluence}`);
  if (CFG.requireStructuralStop && p.stop_type === 'clamped')          why.push('stop is clamped, not structural');
  if (CFG.allowedModes.length    && !CFG.allowedModes.includes(p.mode))       why.push(`mode ${p.mode}`);
  if (CFG.allowedTriggers.length && !CFG.allowedTriggers.includes(p.trigger)) why.push(`trigger ${p.trigger}`);
  if (p.risk_atr !== undefined && (p.risk_atr < CFG.minRiskAtr || p.risk_atr > CFG.maxRiskAtr)) why.push(`risk_atr ${p.risk_atr}`);
  if (p.rr1 < CFG.minRR1) why.push(`TP1 ${p.rr1}R < ${CFG.minRR1}R`);
  if (p.rr1 > CFG.maxRR1) why.push(`TP1 ${p.rr1}R > ${CFG.maxRR1}R`);

  p.passed = why.length === 0;
  p.reject_reason = why.join('; ');
  out.push({ json: p });
}
return out;'''

SIZING = r'''// ME Pro — risk-normalised size + a readable message.
// Size follows stop distance, so every trade risks the same slice of equity
// regardless of how wide the stop is. Note p.sl already includes whatever
// Spread + Slippage Buffer is set in Pine (v3.5.16), so risk here is the real
// distance to the stop, not the idealised structural one.
const ACCOUNT = { equity: 10000, riskPct: 1.0, qtyDecimals: 4 };

const out = [];
for (const item of $input.all()) {
  const p = { ...item.json };
  const risk = p.risk_per_unit || Math.abs(p.entry - p.sl);
  const qty  = risk > 0 ? (ACCOUNT.equity * ACCOUNT.riskPct / 100) / risk : 0;

  p.qty            = Number(qty.toFixed(ACCOUNT.qtyDecimals));
  p.risk_amount    = Number((ACCOUNT.equity * ACCOUNT.riskPct / 100).toFixed(2));
  p.account_equity = ACCOUNT.equity;

  p.message = [
    `${p.action === 'BUY' ? 'LONG' : 'SHORT'} ${p.symbol} ${p.tf}m  (${p.mode} / ${p.trigger})`,
    `entry ${p.entry}   SL ${p.sl}  [${p.stop_type}]   risk ${p.risk_atr}x ATR`,
    `TP1 ${p.tp1} (${p.rr1}R)   TP2 ${p.tp2} (${p.rr2}R)   TP3 ${p.tp3} (${p.rr3}R)`,
    `confluence ${p.confluence}/3   HTF ${p.htf}  VWAP ${p.vwap}  CVD ${p.cvd}  ${p.regime}`,
    `size ${p.qty}  (risking ${p.risk_amount} of ${p.account_equity})`,
  ].join('\n');

  out.push({ json: p });
}
return out;'''

def code(name, js, x, y):
    return {"parameters": {"jsCode": js}, "id": name.lower().replace(" ", "-").replace("&",""),
            "name": name, "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [x, y]}

wf = {
  "name": "ME Pro — TradingView Signal Handler",
  "nodes": [
    {"parameters": {"httpMethod": "POST", "path": "me-pro-signal",
                    "responseMode": "lastNode", "options": {}},
     "id": "webhook", "name": "TradingView Webhook", "type": "n8n-nodes-base.webhook",
     "typeVersion": 2, "position": [-260, 300], "webhookId": "me-pro-signal"},
    code("Validate & Check Plan", VALIDATE, -40, 300),
    code("Deduplicate", DEDUPE, 180, 300),
    code("Quality Gate", FILTER, 400, 300),
    {"parameters": {"conditions": {"options": {"caseSensitive": True, "leftValue": "",
                     "typeValidation": "loose", "version": 2},
       "conditions": [{"id": "passed", "leftValue": "={{ $json.passed }}", "rightValue": "",
                       "operator": {"type": "boolean", "operation": "true", "singleValue": True}}],
       "combinator": "and"}, "options": {}},
     "id": "route", "name": "Passed?", "type": "n8n-nodes-base.if",
     "typeVersion": 2, "position": [620, 300]},
    code("Position Size & Message", SIZING, 840, 200),
    {"parameters": {"method": "POST", "url": "https://REPLACE-ME.example.com/webhook",
                    "sendBody": True, "specifyBody": "json",
                    "jsonBody": "={{ JSON.stringify({ content: $json.message }) }}",
                    "options": {}},
     "id": "notify", "name": "Notify (Discord/Slack/Telegram)",
     "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2, "position": [1060, 200]},
    {"parameters": {}, "id": "rejected", "name": "Rejected (see reject_reason)",
     "type": "n8n-nodes-base.noOp", "typeVersion": 1, "position": [840, 420]},
  ],
  "connections": {
    "TradingView Webhook": {"main": [[{"node": "Validate & Check Plan", "type": "main", "index": 0}]]},
    "Validate & Check Plan": {"main": [[{"node": "Deduplicate", "type": "main", "index": 0}]]},
    "Deduplicate": {"main": [[{"node": "Quality Gate", "type": "main", "index": 0}]]},
    "Quality Gate": {"main": [[{"node": "Passed?", "type": "main", "index": 0}]]},
    "Passed?": {"main": [
        [{"node": "Position Size & Message", "type": "main", "index": 0}],
        [{"node": "Rejected (see reject_reason)", "type": "main", "index": 0}]]},
    "Position Size & Message": {"main": [[{"node": "Notify (Discord/Slack/Telegram)", "type": "main", "index": 0}]]},
  },
  "settings": {"executionOrder": "v1"}, "pinData": {},
}

os.makedirs("n8n", exist_ok=True)
with open("n8n/me-pro-signal-handler.json", "w", encoding="utf-8") as f:
    json.dump(wf, f, indent=2, ensure_ascii=False)
print("wrote n8n/me-pro-signal-handler.json —", len(wf["nodes"]), "nodes")
