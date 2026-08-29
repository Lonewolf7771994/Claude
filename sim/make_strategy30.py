"""Derive MEScalp.v3.0.strategy.pine from the v3.0 indicator.

The point is that the two are the SAME ENGINE. The strategy re-implements
nothing: it takes `fired`, `tradeBuy`, `eEntry`, `eSl`, `eT1`, `eT2`, `eT3` and
`eBar` — the indicator's own plan variables — and turns them into orders. If the
tester says it loses, the indicator loses.
"""
import io, sys

SRC = "/home/user/Claude/MEScalp.v3.0.pine"
P = "/home/user/Claude/MEScalp.v3.0.strategy.pine"
src = io.open(SRC, encoding="utf-8").read()


def sub1(old, new, tag):
    global src
    if src.count(old) != 1:
        sys.exit("PATCH %s: expected 1, found %d" % (tag, src.count(old)))
    src = src.replace(old, new)
    print("  ok  %s" % tag)


sub1('indicator("ME Scalp v3.0", shorttitle="ME Scalp v3.0", overlay=true, max_lines_count=500, max_labels_count=500, max_bars_back=500)',
'''strategy("ME Scalp v3.0 [strategy]", shorttitle="ME Scalp v3.0 S", overlay=true,
     initial_capital=10000,
     default_qty_type=strategy.percent_of_equity, default_qty_value=10,
     pyramiding=0,
     calc_on_every_tick=false,
     process_orders_on_close=true,
     slippage=20,
     commission_type=strategy.commission.percent, commission_value=0.0,
     max_lines_count=500, max_labels_count=500, max_bars_back=500)''',
     "declaration")

sub1("// © ME Institutional — ME Scalp v3.0",
     "// © ME Institutional — ME Scalp v3.0 [strategy]", "copyright")
sub1('"ME SCALP v3.0 — "', '"ME SCALP v3.0 S — "', "dash title")

sub1('''// ═══════════════════════════════════════════════════════════════════════════════
// v3.0 — THE SAME ENGINE WITH TWO THIRDS OF IT DELETED.''',
'''// ═══════════════════════════════════════════════════════════════════════════════
// THIS IS THE STRATEGY BUILD. READ THIS BLOCK BEFORE YOU READ A SINGLE NUMBER.
// ─────────────────────────────────────────────────────────────────────────────
// WHY IT EXISTS. Every measurement in the header below comes from a synthetic
// price generator, not from gold. That generator once paid a naive momentum
// rule +0.21R, which is why all of its expectancy figures were withdrawn. It
// can prove a rule DEAD (the TP1 snap) or FREE (the fade triggers) — both are
// geometry — but it cannot tell you whether this engine makes money on XAUUSD
// at your broker.
//
// The Strategy Tester can. It will run this over real gold history and produce
// a net P&L, a profit factor, a win rate and a drawdown. Those are the numbers
// that decide whether the thing is worth trading, and none of them has ever
// been computed anywhere else in this project.
//
// IT IS THE SAME ENGINE, not a re-implementation. The order block at the very
// bottom reads the indicator's own plan variables — fired, tradeBuy, eEntry,
// eSl, eT1, eT2, eT3, eBar — and does nothing else. Every trigger, gate, score,
// stop rule and target above is byte-identical to the indicator. If this loses,
// the indicator loses.
//
// ─────────────────────────────────────────────────────────────────────────────
// SET THESE BEFORE YOU TRUST ANY RESULT. Strategy Tester -> Properties:
//
//   COMMISSION   Set it to what your broker actually charges. The default here
//                is ZERO, which is wrong for every real account.
//   SLIPPAGE     Defaulted to 20 ticks in the declaration above — on a
//                0.01-tick XAUUSD feed that is $0.20 a side, $0.40 the round
//                turn, a realistic retail gold spread. If your broker is wider,
//                RAISE IT. With a first target at 0.8 ATR the spread is most of
//                the answer on a scalp.
//   ORDER SIZE   Ignored. Sizing is risk-based and comes from the "Risk per
//                trade" input below, not from Properties.
//
// A scalp that is profitable at zero cost and unprofitable at a real spread is
// unprofitable. Measured on this symbol, the spread is roughly 26% of a 1.5 ATR
// stop on 1m, 11% on 5m and 7% on 15m — which is why an earlier build of this
// engine lost money live on 1m and did not on 5m and 15m. Run it on 5m or 15m.
//
// ─────────────────────────────────────────────────────────────────────────────
// HOW THE ORDERS WORK. One position at a time, entered at the close of the
// signal bar. Three exits from the one entry: a third at TP1, a third at TP2,
// the rest at TP3, all sharing the stop. The stop is re-issued every bar, so
// when the engine moves it to breakeven after TP1 the live order follows. A
// position that has resolved nothing after i_timeStop bars is closed at market.
//
// TWO PLACES WHERE THE TESTER AND THE DRAWN PLAN CAN DISAGREE, both honest.
// The indicator resolves a plan on CLOSED bars while the tester fills stops and
// limits INTRABAR, so a bar spanning two levels can be ordered differently.
// And the bar-magnifier and "fill on bar close" settings in Properties change
// that intrabar assumption. The drawn plan is the engine's opinion; the tester
// is the money.
//
// ═══════════════════════════════════════════════════════════════════════════════
// v3.0 — THE SAME ENGINE WITH TWO THIRDS OF IT DELETED.''',
     "strategy header")

sub1('''i_dash = input.bool(true, "Show dashboard", group=G_DISP)''',
'''// ── STRATEGY SIZING. Position size is derived from the stop distance, so every
// trade risks the same fraction of equity however wide the structural stop is.
// Properties -> Order Size is IGNORED.
i_riskPct = input.float(0.5, "Risk per trade (% of equity)", minval=0.01, maxval=10.0, step=0.05, group=G_RISK,
     tooltip="Money at risk if the stop fills, as a percentage of current equity.\\n\\n  qty = equity × risk% ÷ stop distance\\n\\nThis is why the stop clearance inputs are not free: the targets stay at fixed ATR distances while a wider stop shrinks the position, so every win pays less. That trade-off is invisible in an outcome-mix table and visible in the P&L below.")
i_maxQty  = input.float(0.0, "Cap position size (0 = uncapped)", minval=0.0, step=0.01, group=G_RISK,
     tooltip="Hard ceiling on contracts/ounces per trade, applied after the risk calculation. Use it when the risk-based size would exceed what the account could actually hold.")

i_dash = input.bool(true, "Show dashboard", group=G_DISP)''',
     "risk inputs")

sub1('''alertcondition(buySignal,  "ME Scalp — BUY",  "ME Scalp BUY")
alertcondition(sellSignal, "ME Scalp — SELL", "ME Scalp SELL")''',
'''alertcondition(buySignal,  "ME Scalp — BUY",  "ME Scalp BUY")
alertcondition(sellSignal, "ME Scalp — SELL", "ME Scalp SELL")


// ═══════════════════════════════════════════════════════════════════════════════
// ORDERS — the only thing in this file the indicator does not have
// ─────────────────────────────────────────────────────────────────────────────
// Nothing is recomputed here. `fired`, `tradeBuy`, `eEntry`, `eSl`, `eT1`, `eT2`,
// `eT3` and `eBar` are the indicator's own plan variables, assigned in the TRADE
// STATE block above. This turns them into orders and does nothing else, so the
// tester measures the engine rather than a second implementation of it.
// ═══════════════════════════════════════════════════════════════════════════════

// Risk-based size, taken at entry from the ORIGINAL stop. After TP1 the engine
// sets eSl to the entry, and this distance would collapse to zero.
riskPx = tradeBuy ? (eEntry - eSl) : (eSl - eEntry)
qtyRaw = riskPx > 0 ? (strategy.equity * i_riskPct / 100.0) / riskPx : 0.0
qtyNow = i_maxQty > 0 ? math.min(qtyRaw, i_maxQty) : qtyRaw

// `fired` already requires the engine to be flat. The position check guards the
// case where the tester still holds a fill the drawn plan has closed.
if fired and strategy.position_size == 0 and qtyNow > 0
    if tradeBuy
        strategy.entry("L", strategy.long, qty=qtyNow, comment=eName)
    else
        strategy.entry("S", strategy.short, qty=qtyNow, comment=eName)

// Exits are re-issued every bar the position is open, deliberately: eSl becomes
// eEntry when the engine arms breakeven after TP1, and re-issuing is how the
// live stop follows it. qty_percent is a share of the position REMAINING when
// the order fills, so 33 / 50 / rest is a third each.
if strategy.position_size > 0
    strategy.exit("L1", "L", qty_percent=33, limit=eT1, stop=eSl, comment_profit="TP1", comment_loss="SL")
    strategy.exit("L2", "L", qty_percent=50, limit=eT2, stop=eSl, comment_profit="TP2", comment_loss="SL")
    strategy.exit("L3", "L", limit=eT3, stop=eSl, comment_profit="TP3", comment_loss="SL")
if strategy.position_size < 0
    strategy.exit("S1", "S", qty_percent=33, limit=eT1, stop=eSl, comment_profit="TP1", comment_loss="SL")
    strategy.exit("S2", "S", qty_percent=50, limit=eT2, stop=eSl, comment_profit="TP2", comment_loss="SL")
    strategy.exit("S3", "S", limit=eT3, stop=eSl, comment_profit="TP3", comment_loss="SL")

// The same time backstop the indicator draws.
if strategy.position_size != 0 and i_timeStop > 0 and not na(eBar) and (bar_index - eBar) >= i_timeStop
    strategy.close_all(comment="TIME")''',
     "order block")

io.open(P, "w", encoding="utf-8").write(src)
print("\nwrote %d bytes" % len(src))
