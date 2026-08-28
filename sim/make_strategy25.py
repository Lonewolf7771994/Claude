"""Derive MEScalp.v2.5.strategy.pine from the indicator.

The point of this file is that the two are the SAME ENGINE. The strategy does
not re-implement anything: it takes `fired`, `tradeBuy`, `eEntry`, `eSl`, `eT1`,
`eT2`, `eT3` and `eBar` — the indicator's own plan variables — and turns them
into orders. If the strategy tester says it loses, the indicator loses.
"""
import io, sys

SRC = "/home/user/Claude/MEScalp.v2.5.pine"
P = "/home/user/Claude/MEScalp.v2.5.strategy.pine"
src = io.open(SRC, encoding="utf-8").read()


def sub1(old, new, tag):
    global src
    if src.count(old) != 1:
        sys.exit("PATCH %s: expected 1, found %d" % (tag, src.count(old)))
    src = src.replace(old, new)
    print("  ok  %s" % tag)


sub1('indicator("ME Scalp v2.5", shorttitle="ME Scalp v2.5", overlay=true, max_boxes_count=200, max_lines_count=500, max_labels_count=500, max_bars_back=500)',
'''strategy("ME Scalp v2.5 [strategy]", shorttitle="ME Scalp v2.5 S", overlay=true,
     initial_capital=10000,
     default_qty_type=strategy.percent_of_equity, default_qty_value=10,
     pyramiding=0,
     calc_on_every_tick=false,
     process_orders_on_close=true,
     slippage=20,
     commission_type=strategy.commission.percent, commission_value=0.0,
     max_boxes_count=200, max_lines_count=500, max_labels_count=500, max_bars_back=500)''',
     "declaration")

sub1("// © ME Institutional — ME Scalp v2.5",
     "// © ME Institutional — ME Scalp v2.5 [strategy]", "copyright")
sub1('"ME SCALP v2.5 — "', '"ME SCALP v2.5 S — "', "dash title")

# ── the header this file needs, ahead of everything inherited ─────────────────
sub1('''// ═══════════════════════════════════════════════════════════════════════════════
// v2.5 — THE CHART WAS UNDER-REPORTING WHAT THE TRADE ACTUALLY DID.''',
'''// ═══════════════════════════════════════════════════════════════════════════════
// THIS IS THE STRATEGY BUILD. READ THIS BLOCK BEFORE YOU READ A SINGLE NUMBER.
// ─────────────────────────────────────────────────────────────────────────────
// WHY IT EXISTS. Every measurement in every header below comes from a synthetic
// price generator, not from gold. That generator paid a naive momentum rule
// +0.21R, which is why all of its expectancy figures were withdrawn. It can
// find a BUG — the collapsed VWAP band, the untracked TP2 — but it cannot tell
// you whether this engine makes money on XAUUSD at your broker.
//
// TradingView's Strategy Tester can. This file is the same engine, wired to
// real orders, so it will run over real gold history and produce a net P&L, a
// profit factor, a win rate and a drawdown. Those are the numbers that decide
// whether the thing is worth trading, and I have never been able to compute a
// single one of them.
//
// IT IS THE SAME ENGINE, not a re-implementation. The order block at the very
// bottom reads the indicator's own plan variables — fired, tradeBuy, eEntry,
// eSl, eT1, eT2, eT3, eBar — and does nothing else. Every trigger, gate, score,
// stop rule and target in this file is byte-identical to the indicator. If this
// loses, the indicator loses.
//
// ─────────────────────────────────────────────────────────────────────────────
// SET THESE BEFORE YOU TRUST ANY RESULT. Strategy Tester -> Properties:
//
//   COMMISSION      Set it to what your broker actually charges. The default
//                   here is ZERO, which is wrong for every real account.
//   SLIPPAGE        Defaulted to 20 ticks in the declaration above, which on a
//                   0.01-tick XAUUSD feed is $0.20 a side, $0.40 the round
//                   turn. That is a realistic retail gold spread. If your
//                   broker is wider, RAISE IT. On a scalp with a 0.8 ATR first
//                   target, the spread is most of the answer.
//   ORDER SIZE      Ignored. Sizing is risk-based and comes from the "Risk per
//                   trade" input below, not from Properties.
//
// A scalp strategy that is profitable at zero cost and unprofitable at a real
// spread is unprofitable. Measured on the ME Pro line, the spread on XAUUSD is
// roughly 26% of a 1.5 ATR stop on 1m, 11% on 5m and 7% on 15m — which is why
// the 1m build lost money live and the 5m and 15m ones did not.
//
// ─────────────────────────────────────────────────────────────────────────────
// HOW THE ORDERS WORK. One position at a time, entered at the close of the
// signal bar. Three exits from the one entry: a third at TP1, a third at TP2,
// the rest at TP3, all sharing the stop. The stop is re-issued every bar, so
// when the engine moves it to breakeven after TP1 the live order moves with it.
// A position that has resolved nothing after i_timeStop bars is closed at
// market, the same backstop the indicator draws.
//
// TWO PLACES WHERE THE TESTER AND THE DRAWN PLAN CAN DISAGREE, both honest:
// the indicator resolves a plan on CLOSED bars, while the tester fills stops
// and limits INTRABAR, so a bar that spans two levels can be ordered
// differently. And bar_magnifier / "on bar close" settings in Properties change
// the intrabar assumption. The drawn plan is the engine's opinion; the tester
// is the money.
//
// ═══════════════════════════════════════════════════════════════════════════════
// v2.5 — THE CHART WAS UNDER-REPORTING WHAT THE TRADE ACTUALLY DID.''',
     "strategy header")

# ── the risk input ────────────────────────────────────────────────────────────
sub1('''i_showZones = input.bool(true,  "Show VWAP bands",   group=G_DISP)''',
'''// ── STRATEGY SIZING. Position size is derived from the stop distance, so every
// trade risks the same fraction of equity regardless of how wide the structural
// stop happens to be. Properties -> Order Size is IGNORED.
i_riskPct = input.float(0.5, "Risk per trade (% of equity)", minval=0.01, maxval=10.0, step=0.05, group=G_RISK,
     tooltip="Money at risk if the stop fills, as a percentage of current equity.\\n\\nqty = equity * risk% / stop distance\\n\\nThis is why a wider stop pays less per win and the pad inputs are not free: the targets stay at fixed ATR distances while the position shrinks. That trade-off is invisible in an outcome-mix table and visible in the P&L below.")
i_maxQty  = input.float(0.0, "Cap position size (0 = uncapped)", minval=0.0, step=0.01, group=G_RISK,
     tooltip="Hard ceiling on contracts/ounces per trade, applied after the risk calculation. Use it when the risk-based size would exceed what your account could actually hold.")

i_showZones = input.bool(true,  "Show VWAP bands",   group=G_DISP)''',
     "risk input")

# ── the order block ───────────────────────────────────────────────────────────
sub1('''alertcondition(buySignal,  "ME Scalp — BUY",  "ME Scalp BUY")
alertcondition(sellSignal, "ME Scalp — SELL", "ME Scalp SELL")''',
'''alertcondition(buySignal,  "ME Scalp — BUY",  "ME Scalp BUY")
alertcondition(sellSignal, "ME Scalp — SELL", "ME Scalp SELL")


// ═══════════════════════════════════════════════════════════════════════════════
// ORDERS — the only thing in this file that the indicator does not have
// ─────────────────────────────────────────────────────────────────────────────
// Nothing is recomputed here. `fired`, `tradeBuy`, `eEntry`, `eSl`, `eT1`, `eT2`,
// `eT3` and `eBar` are the indicator's own plan variables, assigned in the TRADE
// STATE block above. This turns them into orders and does nothing else, so the
// tester is measuring the engine rather than a second implementation of it.
// ═══════════════════════════════════════════════════════════════════════════════

// Risk-based size, taken at the moment of entry from the ORIGINAL stop — after
// TP1 the stop becomes the entry and this distance would collapse to zero.
riskPx = tradeBuy ? (eEntry - eSl) : (eSl - eEntry)
qtyRaw = riskPx > 0 ? (strategy.equity * i_riskPct / 100.0) / riskPx : 0.0
qtyNow = i_maxQty > 0 ? math.min(qtyRaw, i_maxQty) : qtyRaw

// `fired` already requires the engine to be flat; the position check guards the
// case where the tester is still holding a fill the drawn plan has closed.
if fired and strategy.position_size == 0 and qtyNow > 0
    if tradeBuy
        strategy.entry("L", strategy.long, qty=qtyNow, comment=eName)
    else
        strategy.entry("S", strategy.short, qty=qtyNow, comment=eName)

// Exits are re-issued every bar the position is open. That is deliberate: eSl
// becomes eEntry when the engine arms breakeven after TP1, and re-issuing is
// how the live stop follows it. qty_percent is a share of the position REMAINING
// when the order fills, so 33 / 50 / rest is a third each.
if strategy.position_size > 0
    strategy.exit("L1", "L", qty_percent=33, limit=eT1, stop=eSl, comment_profit="TP1", comment_loss="SL")
    strategy.exit("L2", "L", qty_percent=50, limit=eT2, stop=eSl, comment_profit="TP2", comment_loss="SL")
    strategy.exit("L3", "L", limit=eT3, stop=eSl, comment_profit="TP3", comment_loss="SL")
if strategy.position_size < 0
    strategy.exit("S1", "S", qty_percent=33, limit=eT1, stop=eSl, comment_profit="TP1", comment_loss="SL")
    strategy.exit("S2", "S", qty_percent=50, limit=eT2, stop=eSl, comment_profit="TP2", comment_loss="SL")
    strategy.exit("S3", "S", limit=eT3, stop=eSl, comment_profit="TP3", comment_loss="SL")

// The same time backstop the indicator draws. Only 3-5% of trades reach it.
if strategy.position_size != 0 and i_timeStop > 0 and not na(eBar) and (bar_index - eBar) >= i_timeStop
    strategy.close_all(comment="TIME")''',
     "order block")

io.open(P, "w", encoding="utf-8").write(src)
print("\nwrote %d bytes" % len(src))
