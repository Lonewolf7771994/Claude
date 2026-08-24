"""v4.6 part 2 — trail feeds the gate, graded labels, Prism dashboard rows."""
import io, sys

P = "/home/user/Claude/MovementEnginePro.v4.6.pine"
src = io.open(P, encoding="utf-8").read()


def sub1(old, new, tag):
    global src
    if src.count(old) != 1:
        sys.exit("PATCH %s: expected 1, found %d" % (tag, src.count(old)))
    src = src.replace(old, new)
    print("  ok  %s" % tag)


# ── THE TRAIL BECOMES THE LEG ──────────────────────────────────────────────
sub1("""nonRevOkBuy  = gateOff or (legUp   and revTrendOk and revHtfOkBuy  and revCntrOkBuy)
nonRevOkSell = gateOff or (legDown and revTrendOk and revHtfOkSell and revCntrOkSell)""",
"""// v4.6: the LEG half of the gate can be the trail's own state instead of the
// fixed-lookback comparison. `close > close[20]` answers a question nobody asks:
// it flips on any bar where the comparison bar happens to be higher, whether or
// not anything structural changed. The trail flips only when price CLOSES
// THROUGH a level that has been ratcheting one way — a state with a level behind
// it and an age. The leakage audit is unaffected: a long still requires the
// trend read to be up, so a long against it cannot pass.
gateLegBuy  = i_prismGate ? prismBull       : legUp
gateLegSell = i_prismGate ? (not prismBull) : legDown

nonRevOkBuy  = gateOff or (gateLegBuy  and revTrendOk and revHtfOkBuy  and revCntrOkBuy)
nonRevOkSell = gateOff or (gateLegSell and revTrendOk and revHtfOkSell and revCntrOkSell)""",
"trail feeds gate")

# ── GRADED SIGNAL LABELS ───────────────────────────────────────────────────
sub1("""if buySignal
    label.new(bar_index, low - atr14 * 0.8, "BUY #" + str.tostring(sigSeq), style=label.style_label_up, color=color.new(i_buyCol, 5), textcolor=color.rgb(0, 0, 0), size=size.normal)
if sellSignal
    label.new(bar_index, high + atr14 * 0.8, "SELL #" + str.tostring(sigSeq), style=label.style_label_down, color=color.new(i_sellCol, 5), textcolor=color.white, size=size.normal)""",
"""// v4.6 GRADED LABELS. Three named checks — momentum, participation, candle —
// read off values the engine already computes, printed on the arrow with the
// volatility regime and the live trail multiplier. No new logic; it makes the
// reason a signal was taken legible where you are actually looking.
gMomBuy  = momBullEff
gMomSell = momBearEff
gVol     = not volDataSeen or relVol >= 1.15
gCndBuy  = closePos >= 0.60 and bodySize >= atr14 * 0.40
gCndSell = closePos <= 0.40 and bodySize >= atr14 * 0.40
gradeBuy  = (gMomBuy  ? 1 : 0) + (gVol ? 1 : 0) + (gCndBuy  ? 1 : 0)
gradeSell = (gMomSell ? 1 : 0) + (gVol ? 1 : 0) + (gCndSell ? 1 : 0)
multTxt   = str.tostring(math.round(prismMult, 1)) + "x"

if buySignal
    txtB = i_prismGrade ? "BUY G" + str.tostring(gradeBuy) + "/3\\n" + prismRegime + " · " + multTxt : "BUY #" + str.tostring(sigSeq)
    label.new(bar_index, low - atr14 * 0.8, txtB, style=label.style_label_up, color=color.new(i_buyCol, 5), textcolor=color.rgb(0, 0, 0), size=size.small, textalign=text.align_center)
if sellSignal
    txtS = i_prismGrade ? "SELL G" + str.tostring(gradeSell) + "/3\\n" + prismRegime + " · " + multTxt : "SELL #" + str.tostring(sigSeq)
    label.new(bar_index, high + atr14 * 0.8, txtS, style=label.style_label_down, color=color.new(i_sellCol, 5), textcolor=color.white, size=size.small, textalign=text.align_center)""",
"graded labels")

# ── DASHBOARD: Prism rows at the top, in that readout style ───────────────
sub1("""    // v3.5: in Scalp the HTF gate is bypassed — show direction as info, never "BLOCKED\"""",
"""    // v4.6 PRISM ROWS. The trend, the live multiplier and the trail level, with
    // the bar meters the volatility rank and trail distance deserve — a
    // percentage is easier to read as a filled bar than as a number.
    f_meter(float v, int n) =>
        int filled = math.max(0, math.min(n, int(math.round(v * n))))
        string s = ""
        for _i = 0 to n - 1
            s := s + (_i < filled ? "▰" : "▱")
        s

    trendTxt = prismBull ? "▲ BULLISH" : "▼ BEARISH"
    table.cell(dash, 0, 1, "Trend", text_color=dim, text_size=size.tiny, text_halign=text.align_left, bgcolor=color.rgb(12, 12, 18))
    table.cell(dash, 1, 1, trendTxt, text_color=color.white, text_size=size.small, bgcolor=color.new(prismBull ? i_prismUpCol : i_prismDnCol, 25))
    f_cell(2, 1, "age " + str.tostring(prismAge) + " bars", dim)

    rankPct = str.tostring(math.round(nz(prismRank, 0.5) * 100)) + "%"
    table.cell(dash, 0, 2, "Vol Regime", text_color=dim, text_size=size.tiny, text_halign=text.align_left, bgcolor=color.rgb(12, 12, 18))
    f_cell(1, 2, str.upper(prismRegime) + " (" + rankPct + ")", prismRank >= 0.75 ? yel : prismRank <= 0.25 ? dim : wht)
    f_cell(2, 2, f_meter(nz(prismRank, 0.5), 7), prismRank >= 0.75 ? yel : grn)

    table.cell(dash, 0, 3, "Live Multiplier", text_color=dim, text_size=size.tiny, text_halign=text.align_left, bgcolor=color.rgb(12, 12, 18))
    f_cell(1, 3, str.tostring(math.round(prismMult, 2)) + "x ATR", wht)
    f_cell(2, 3, "base " + str.tostring(i_prismBase, "#.0") + " · refr " + str.tostring(i_prismRefr, "#.00"), dim)

    table.cell(dash, 0, 4, "Trail Level", text_color=dim, text_size=size.tiny, text_halign=text.align_left, bgcolor=color.rgb(12, 12, 18))
    f_cell(1, 4, str.tostring(prismLine, format.mintick), prismBull ? grn : red_)
    f_cell(2, 4, prismBull ? "support below" : "resistance above", dim)

    table.cell(dash, 0, 5, "Trail Distance", text_color=dim, text_size=size.tiny, text_halign=text.align_left, bgcolor=color.rgb(12, 12, 18))
    f_cell(1, 5, str.tostring(math.round(prismDist, 2)) + "x ATR", wht)
    f_cell(2, 5, f_meter(math.min(prismDist / 4.0, 1.0), 7), grn)

    // v3.5: in Scalp the HTF gate is bypassed — show direction as info, never "BLOCKED\"""",
"prism dashboard rows")

io.open(P, "w", encoding="utf-8").write(src)
print("\nwrote %d bytes" % len(src))
