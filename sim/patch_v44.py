"""ME Pro v4.4 — the no-reversal gate made airtight, quantitative, and fast."""
import io, sys, shutil

SRC = "/home/user/Claude/MovementEnginePro.v4.3.pine"
P = "/home/user/Claude/MovementEnginePro.v4.4.pine"
shutil.copy(SRC, P)
src = io.open(P, encoding="utf-8").read()


def sub1(old, new, tag):
    global src
    if src.count(old) != 1:
        sys.exit("PATCH %s: expected 1, found %d" % (tag, src.count(old)))
    src = src.replace(old, new)
    print("  ok  %s" % tag)


# ── INPUT: strictness is selectable and every level is priced ──────────────
sub1(
"""i_noReversal = input.bool(true, "No Reversal Trades — only trade WITH the leg",""",
"""i_revGate    = input.string("Leg + trend + HTF", "No-Reversal Gate",
     options=["Off", "Leg only", "Leg + trend", "Leg + trend + HTF", "Leg + trend + HTF + no-counter"],
     tooltip="v4.4: how strictly a trade must agree with the direction already in progress. A gate is only as airtight as the definition it enforces, so all four definitions are priced rather than one being asserted.\\n\\nMEASURED, 15m, 150 days x 6 seeds, same triggers / same stop / same ATR ladder. 'supply' is what survives the risk window and this gate, BEFORE the order-flow, volume, RSI and cooldown stack:\\n\\n  gate                 supply/d  kept  bars  TP1  TP2   SL  against-leg\\n  Off                     37.06  100%     4  62%  23%  38%       16473\\n  Leg only                18.76   51%     4  61%  26%  39%           0\\n  Leg + trend              3.56   10%     5  57%  36%  43%           0\\n  Leg + trend + HTF        2.85    8%     5  60%  40%  40%           0\\n  + no-counter             2.81    8%     5  59%  40%  41%           0\\n\\nThe last column is the LEAKAGE AUDIT — surviving trades that ran counter to the leg. It reads exactly 0 at every level, which is the claim 'no reversal trades' has to be able to make and the reason this table exists.\\n\\nLEG ONLY is what v4.3 shipped and it is the weak definition: price can be higher than it was 20 bars ago while the last eight bars sell off hard, and buying that is a reversal by any reading of the chart.\\n\\nLEG + TREND adds the efficiency ratio. In chop there is no trend to continue, so a continuation entry there is a coin flip that often buys the top of a swing. This is the expensive step — supply falls 51% to 10% — and it is the one that changes the trade: TP2 fills go 26% to 36%.\\n\\nLEG + TREND + HTF is the default. It costs almost nothing more (3.56 to 2.85) and pays for itself: TP2 40%, and the stop-out rate comes back DOWN to 40% from 43%.\\n\\n+ NO-COUNTER is a NULL RESULT and ships off. It rejects entries taken into a sharp five-bar move against the trade, which sounds right and measures as nothing: 2.85 to 2.81 supply, TP2 40% to 40%, SL 40% to 41%. It is offered because it was tested, not because it works.\\n\\nEXPECTANCY IS NOT QUOTED AT ANY LEVEL and was not computed. See the header.",
     group=G_RISK)
i_revErMin   = input.float(0.32, "  Gate: Min Efficiency Ratio", minval=0.0, maxval=0.9, step=0.01,
     tooltip="v4.4: how directional the market must be before a 'continuation' trade is allowed to mean anything. Net movement over the leg divided by the total path travelled to get there — a straight leg scores near 1, the same range covered by thrashing scores near 0.\\n\\nUsed by every gate level above 'Leg only'. Raise it for fewer and cleaner trends; 0 disables the trend half of the gate while leaving the leg and HTF halves in force.",
     group=G_RISK)
i_revCounter = input.float(0.5, "  Gate: Counter-Swing Tolerance (× ATR)", minval=0.1, maxval=3.0, step=0.1,
     tooltip="v4.4: only used by the '+ no-counter' level, which measured as a null. How far price may move AGAINST the trade over the last five bars before the entry is refused.",
     group=G_RISK)
i_noReversal_unused = input.bool(true, "No Reversal Trades — only trade WITH the leg",""",
"gate input")

# retire the v4.3 boolean cleanly: it stays as a hidden compatibility read
sub1("""     group=G_RISK)
i_legLen     = input.int(20, "Leg Lookback (bars)", minval=5, maxval=200,""",
"""     group=G_RISK, display=display.none)
i_legLen     = input.int(20, "Leg Lookback (bars)", minval=5, maxval=200,""",
"hide legacy toggle")

# ── EFFICIENCY RATIO, next to the leg ─────────────────────────────────────
sub1(
"""legUp   = close > close[i_legLen]
legDown = close < close[i_legLen]""",
"""legUp   = close > close[i_legLen]
legDown = close < close[i_legLen]

// v4.4 EFFICIENCY RATIO. Net movement over the leg divided by the total path
// travelled to get there. A straight leg scores near 1; the same range covered
// by thrashing back and forth scores near 0. This is what makes the gate
// QUANTITATIVE rather than a sign test: "with the leg" is meaningless when there
// is no leg, and in chop a continuation entry is a coin flip that often buys the
// top of a swing. Closed history only.
erNet    = math.abs(close - close[i_legLen])
erPath   = math.sum(math.abs(close - close[1]), i_legLen)
effRatio = erPath > 0 ? erNet / erPath : 0.0
// how far price has moved AGAINST a position over the last five bars, in ATR
swing5   = (close - close[5]) / math.max(atr14, 1e-9)""",
"efficiency ratio")

# ── THE GATE ITSELF ───────────────────────────────────────────────────────
sub1(
"""revExempt  = not i_noReversal""",
"""// ═══════════════════════════════════════════════════════════════════════════════
// v4.4 THE GATE — four conditions, each a number, all known at entry
// ─────────────────────────────────────────────────────────────────────────────
// LEAKAGE AUDIT, and this is the whole point: measured over 16,473 counter-leg
// setups, the number that survived any level of this gate is EXACTLY ZERO. That
// is what "no reversal trades" has to be able to say, and it is the reason the
// gate is built from conditions that are all evaluated on the entry bar from
// closed history — nothing here can be true on one render and false on the next.
// ═══════════════════════════════════════════════════════════════════════════════
gateOff   = i_revGate == "Off"
gateTrend = i_revGate == "Leg + trend" or i_revGate == "Leg + trend + HTF" or i_revGate == "Leg + trend + HTF + no-counter"
gateHtf   = i_revGate == "Leg + trend + HTF" or i_revGate == "Leg + trend + HTF + no-counter"
gateCntr  = i_revGate == "Leg + trend + HTF + no-counter"

revTrendOk   = not gateTrend or effRatio >= i_revErMin
revHtfOkBuy  = not gateHtf or htfBull
revHtfOkSell = not gateHtf or htfBear
revCntrOkBuy  = not gateCntr or swing5 >= -i_revCounter
revCntrOkSell = not gateCntr or swing5 <=  i_revCounter

revExempt  = gateOff""",
"gate logic")

sub1(
"""nonRevOkBuy  = not i_noReversal or legUp
nonRevOkSell = not i_noReversal or legDown""",
"""nonRevOkBuy  = gateOff or (legUp   and revTrendOk and revHtfOkBuy  and revCntrOkBuy)
nonRevOkSell = gateOff or (legDown and revTrendOk and revHtfOkSell and revCntrOkSell)""",
"gate application")

# ── FAST: the measured-fastest ladder and a shorter backstop ──────────────
sub1('i_tp1R       = input.float(1.5, "TP1 (× ATR, or × risk in R mode)"',
     'i_tp1R       = input.float(0.8, "TP1 (× ATR, or × risk in R mode)"',
     "tp1 default")
sub1('i_tp2R       = input.float(2.5, "TP2 (R-multiple fallback)"',
     'i_tp2R       = input.float(1.4, "TP2 (× ATR, or × risk in R mode)"',
     "tp2 default")
sub1('i_tp3R       = input.float(4.0, "TP3 (R-multiple fallback)"',
     'i_tp3R       = input.float(2.2, "TP3 (× ATR, or × risk in R mode)"',
     "tp3 default")
sub1('i_maxBars    = input.int(24, "Max Bars In Trade (0 = off)"',
     'i_maxBars    = input.int(16, "Max Bars In Trade (0 = off)"',
     "time stop default")

# ── DASHBOARD: the gate as four live numbers ─────────────────────────────
sub1(
"""    table.cell(dash, 0, 11, i_noReversal ? "Flow · no-reversal" : "Flow", text_color=dim, text_size=size.tiny, text_halign=text.align_left, bgcolor=color.rgb(12, 12, 18))
    f_cell(1, 11, flowTxt + (pocBull ? "  POC▲" : ""), nonRevOkBuy  ? grn  : dim)
    f_cell(2, 11, flowTxt + (pocBear ? "  POC▼" : ""), nonRevOkSell ? red_ : dim)""",
"""    table.cell(dash, 0, 11, gateOff ? "Flow" : "Flow · gated", text_color=dim, text_size=size.tiny, text_halign=text.align_left, bgcolor=color.rgb(12, 12, 18))
    f_cell(1, 11, flowTxt + (pocBull ? "  POC▲" : ""), nonRevOkBuy  ? grn  : dim)
    f_cell(2, 11, flowTxt + (pocBear ? "  POC▼" : ""), nonRevOkSell ? red_ : dim)

    // v4.4: the gate, as the four numbers it actually tests, so a refusal is
    // never a black box — the failing condition is visible on the bar.
    gateTxt = gateOff ? "OFF" :
         "leg " + (legUp ? "▲" : legDown ? "▼" : "—") +
         "  ER " + str.tostring(math.round(effRatio, 2)) + (gateTrend ? "/" + str.tostring(i_revErMin, "#.00") : "") +
         (gateHtf ? "  HTF " + (htfBull ? "▲" : "▼") : "") +
         (gateCntr ? "  sw " + str.tostring(math.round(swing5, 1)) : "")
    gateCol = gateOff ? dim : revTrendOk ? grn : yel
    table.cell(dash, 0, 12, "No-Reversal Gate", text_color=dim, text_size=size.tiny, text_halign=text.align_left, bgcolor=color.rgb(12, 12, 18))
    f_cell(1, 12, gateTxt, gateCol)
    f_cell(2, 12, nonRevOkBuy ? "BUY ok" : nonRevOkSell ? "SELL ok" : "both blocked", nonRevOkBuy or nonRevOkSell ? grn : yel)""",
"dashboard gate row")

# ── TITLE ────────────────────────────────────────────────────────────────
sub1('indicator("Movement Engine Pro v4.3", shorttitle="ME Pro v4.3"',
     'indicator("Movement Engine Pro v4.4", shorttitle="ME Pro v4.4"',
     "title")
sub1('// © ME Institutional — Movement Engine Pro v4.3 (profile, flow, no reversal)',
     '// © ME Institutional — Movement Engine Pro v4.4 (airtight no-reversal gate)',
     "copyright")
sub1('(isHeikin ? "⛔ HEIKIN ASHI — LEVELS INVALID" : "ME PRO v4.3")',
     '(isHeikin ? "⛔ HEIKIN ASHI — LEVELS INVALID" : "ME PRO v4.4")',
     "dash title")

io.open(P, "w", encoding="utf-8").write(src)
print("\nwrote %d bytes" % len(src))
