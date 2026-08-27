"""ME Scalp v2.3 — TP1 was being reached and never said so."""
import io, sys, shutil

SRC = "/home/user/Claude/MEScalp.v2.2.pine"
P = "/home/user/Claude/MEScalp.v2.3.pine"
shutil.copy(SRC, P)
src = io.open(P, encoding="utf-8").read()


def sub1(old, new, tag):
    global src
    if src.count(old) != 1:
        sys.exit("PATCH %s: expected 1, found %d" % (tag, src.count(old)))
    src = src.replace(old, new)
    print("  ok  %s" % tag)


HDR = '''// ═══════════════════════════════════════════════════════════════════════════════
// v2.3 — TP1 WAS BEING REACHED AND THE CHART NEVER SAID SO.
// ─────────────────────────────────────────────────────────────────────────────
// Reported: on 5m and 15m the plan barely reaches TP1.
//
// THE DISPLAY DEFECT, read straight off v2.2's own source. A finished plan is
// stamped with exactly one of four labels:
//
//     closeTxt = tpHit ? "TP3 ✓" : slHit ? (eTp1Done ? "BE" : "SL ✕") : "TIME"
//
// There is no TP1 label anywhere in that line, and the TP1 price label never
// changes once drawn. So a trade that reaches TP1, arms breakeven and later
// comes back to entry is stamped "BE" — and BE IS THE EVIDENCE THAT TP1 WAS
// HIT. It is the only outcome that cannot happen without it.
//
// Read "BE" as a miss and the apparent TP1 rate is whatever share of trades
// ends at TP3. Measured on 5m at the default 0.8 ATR: that is 19%, against a
// true reach of 59%. The engine looked three times worse than it was, and I
// built the display that made it look that way.
//
// v2.3 marks it. The TP1 label becomes "TP1 ✓" the moment it trades, a small
// triangle prints on the bar that did it, and the dashboard carries a running
// TP1 hit rate for the session so the number can be checked on a real chart
// instead of taken from my synthetic generator.
//
// ─────────────────────────────────────────────────────────────────────────────
// WHERE TP1 ACTUALLY SITS, MEASURED. TP1 hit is BE + TP3, i.e. trades that
// demonstrably reached it:
//
//     5m                                  15m
//     TP1 (xATR)  hit    BE   TP3    SL   TP1 (xATR)  hit    BE   TP3    SL
//     0.40        77%   64%   14%    8%   0.40        61%   47%   14%   18%
//     0.50        72%   57%   15%    9%   0.50        57%   41%   15%   20%
//     0.60        68%   52%   16%   10%   0.60        54%   37%   16%   21%
//     0.80        59%   40%   19%   13%   0.80        48%   31%   17%   24%
//     1.00        52%   31%   21%   15%   1.00        42%   24%   19%   28%
//
// The dial is real and monotone. Moving TP1 from 0.8 to 0.5 ATR takes the 5m
// reach from 59% to 72% and costs 4 points of TP3. Reaching TP1 is what arms
// breakeven, so a trade that does not reach it carries full risk for its whole
// life — which is why this target is worth more attention than the other two.
//
// ─────────────────────────────────────────────────────────────────────────────
// THE SL BUFFER: TWO PADS WERE STACKING, AND NEITHER TOOLTIP SAID SO.
//
//     slRaw = min(invalidation, close - atr*i_minRisk) - atr*i_slBuf - atr*i_structPad
//
// i_slBuf (0.20) and i_structPad (0.25) are separate inputs doing the same job
// — clearance beyond the invalidation — and they ADD. The pad actually applied
// has always been 0.45 ATR, and you could not tell that from either input.
// v2.3 says so in both tooltips and shows the effective total on the dashboard.
//
// MEASURED, sweeping the buffer with the pad held at 0.25:
//
//     5m                                    15m
//     buf   total   trd/day  TP1   SL       buf   total  trd/day  TP1   SL
//     0.00   0.25      5.43  57%  17%       0.00   0.25     3.38  45%  29%
//     0.20   0.45      5.43  59%  13%       0.20   0.45     3.38  48%  24%
//     0.35   0.60      5.43  60%  11%       0.35   0.60     3.38  50%  21%
//     0.50   0.75      5.43  60%   9%       0.50   0.75     3.38  52%  20%
//
// I EXPECTED THE BUFFER TO CUT TRADE COUNT by pushing structural risk past the
// i_structMax backstop. IT DOES NOT — the count is identical at every setting,
// 5.43/day and 3.38/day throughout. That guess was wrong and the measurement
// says so.
//
// What the buffer does is lower stop-outs monotonically and lift TP1 reach
// slightly, at no cost this table can see. But there IS a cost this table
// cannot see, and it is not small: position size is derived from stop
// distance, so a wider stop means a SMALLER POSITION for the same money at
// risk, while the targets stay at fixed ATR distances. Every win therefore
// pays less. In R terms, TP1 at 0.8 ATR is 0.34R against a 2.33 ATR stop and
// 0.30R against a 2.63 ATR one.
//
// So the buffer trades fewer stop-outs for smaller wins. Outcome mix cannot
// settle that trade — only expectancy can, and this harness cannot produce
// expectancy. The defaults are UNCHANGED for that reason. The measurement is
// here so the choice is informed rather than blind.
//
// Counts and outcome geometry only. No expectancy computed or quoted;
// synthetic data.
// ═══════════════════════════════════════════════════════════════════════════════

'''

sub1("// ═══════════════════════════════════════════════════════════════════════════════\n// ME SCALP v2.2 — THE STOP WAS IN THE WRONG PLACE. Measured, then fixed.",
     HDR + "// ═══════════════════════════════════════════════════════════════════════════════\n// ME SCALP v2.2 — THE STOP WAS IN THE WRONG PLACE. Measured, then fixed.",
     "header")

# ── the TP1 tooltip gains the measured reach table ────────────────────────
sub1('''i_tp1R      = input.float(0.8, "TP1 (× ATR, or × risk in R modes)", minval=0.3, maxval=5.0, step=0.1, group=G_RISK,
     tooltip="Distance to the first target.''',
'''i_tp1R      = input.float(0.8, "TP1 (× ATR, or × risk in R modes)", minval=0.3, maxval=5.0, step=0.1, group=G_RISK,
     tooltip="v2.3 MEASURED REACH. TP1 hit = trades that demonstrably reached it (ended BE or TP3):\\n\\n  TP1     5m hit   5m SL     15m hit   15m SL\\n  0.40      77%%      8%%         61%%     18%%\\n  0.50      72%%      9%%         57%%     20%%\\n  0.60      68%%     10%%         54%%     21%%\\n  0.80      59%%     13%%         48%%     24%%\\n  1.00      52%%     15%%         42%%     28%%\\n\\nMonotone and real: 0.8 -> 0.5 lifts the 5m reach from 59%% to 72%% and costs about 4 points of TP3.\\n\\nWHY THIS TARGET MATTERS MORE THAN THE OTHER TWO. Reaching TP1 is what arms the breakeven move. A trade that never reaches it carries full risk for its entire life, so TP1 reach is the difference between a scratch and a full loss.\\n\\nIf the chart appears never to reach TP1, check the new TP1 hit counter on the dashboard before changing this — through v2.2 the chart had no way to SAY TP1 was hit, and stamped such trades \\"BE\\".\\n\\nORIGINAL NOTE — Distance to the first target.''',
     "tp1 tooltip")

# ── the SL buffer tooltip finally admits the stacking ─────────────────────
sub1('''i_slBuf     = input.float(0.20, "SL Buffer Past Invalidation (× ATR)", minval=0.0, maxval=1.0, step=0.05, group=G_RISK)''',
'''i_slBuf     = input.float(0.20, "SL Buffer Past Invalidation (× ATR)", minval=0.0, maxval=1.0, step=0.05, group=G_RISK,
     tooltip="v2.3: THIS ADDS TO THE STRUCTURE PAD. Both push the stop past the invalidation and the engine applies BOTH:\\n\\n  stop = min(invalidation, close - minRisk) - slBuf - structPad\\n\\nAt defaults that is 0.20 + 0.25 = 0.45 ATR of clearance, and neither input said so before now. The dashboard shows the effective total.\\n\\nMEASURED, sweeping this with the pad held at 0.25:\\n\\n  buf   total   5m trd/day  5m TP1  5m SL   15m SL\\n  0.00   0.25         5.43     57%%    17%%      29%%\\n  0.20   0.45         5.43     59%%    13%%      24%%\\n  0.35   0.60         5.43     60%%    11%%      21%%\\n  0.50   0.75         5.43     60%%     9%%      20%%\\n\\nTrade count does NOT change — I expected the wider stop to be rejected by the Structure Backstop and it is not; the count is identical at every setting. That guess was wrong.\\n\\nTHE COST THIS TABLE CANNOT SHOW. Position size is derived from stop distance, so a wider stop means a smaller position for the same money at risk while the targets stay at fixed ATR distances. Every win pays less: TP1 at 0.8 ATR is 0.34R against a 2.33 ATR stop and 0.30R against a 2.63 ATR one.\\n\\nFewer stop-outs, smaller wins. Outcome mix cannot settle that — only expectancy can, and it has not been measured. Default left unchanged for that reason.")''',
     "slbuf tooltip")

# ── TP1 hit is now visible on the chart ───────────────────────────────────
sub1("""            eTp1Done := true
            if i_beAfterTp1
                eSl := eEntry""",
"""            eTp1Done := true
            // v2.3: SAY SO. Through v2.2 nothing on the chart marked TP1, and
            // a trade that reached it and returned to entry was stamped "BE" —
            // which meant TP1 had been hit, but read as a miss.
            tp1HitBar := bar_index
            nTp1 := nTp1 + 1
            if not na(lbT1)
                label.set_text(lbT1, "TP1 ✓ " + str.tostring(eT1, format.mintick))
                label.set_color(lbT1, color.new(#00E676, 0))
                label.set_textcolor(lbT1, color.black)
            if i_beAfterTp1
                eSl := eEntry""",
     "tp1 mark")

sub1("""var int   nWin      = 0
var int   nLoss     = 0
var int   nTrades   = 0""",
"""var int   nWin      = 0
var int   nLoss     = 0
var int   nTrades   = 0
// v2.3: TP1 reach, counted on the chart in front of you rather than taken from
// a synthetic generator. nTp1 counts trades that reached TP1; nTrades counts
// trades taken, so the ratio is the reach rate for this symbol and timeframe.
var int   nTp1      = 0
var int   tp1HitBar = na""",
     "tp1 counters")

# marker on the bar that reached it
sub1('plotshape(buySignal  and not inTrade[1], "BUY",  shape.labelup,',
'''// v2.3: a small mark on the bar where TP1 actually traded. The plan freezes
// with an outcome stamp, but the moment TP1 fills is the one that decides
// whether the rest of the trade can lose, and it was invisible.
plotshape(not na(tp1HitBar) and tp1HitBar == bar_index and tradeBuy,  "TP1 hit (long)",  shape.triangleup,   location.belowbar, color.new(#00E676, 20), size=size.tiny)
plotshape(not na(tp1HitBar) and tp1HitBar == bar_index and not tradeBuy, "TP1 hit (short)", shape.triangledown, location.abovebar, color.new(#00E676, 20), size=size.tiny)

plotshape(buySignal  and not inTrade[1], "BUY",  shape.labelup,''',
     "tp1 marker")

# ── dashboard: the reach rate, and the effective pad ──────────────────────
sub1("dash := table.new(pos, 3, 12, bgcolor=color.rgb(10, 10, 15, 5), border_width=1, border_color=color.rgb(40, 40, 50))",
     "dash := table.new(pos, 3, 13, bgcolor=color.rgb(10, 10, 15, 5), border_width=1, border_color=color.rgb(40, 40, 50))",
     "table size")

sub1('    table.cell(dash, 0, 10, "Since load"',
'''    // v2.3 THE ROW THIS VERSION EXISTS FOR. Through v2.2 the chart could not
    // say TP1 had been hit, so a reach of 59% looked like 19%. This counts it
    // on your own symbol, which beats trusting my generator.
    table.cell(dash, 0, 11, "TP1 reach", text_color=dim, text_size=size.tiny, text_halign=text.align_left, bgcolor=color.rgb(15, 15, 22))
    tp1Txt = nTrades > 0 ? str.tostring(math.round(100.0 * nTp1 / nTrades)) + "%  (" + str.tostring(nTp1) + "/" + str.tostring(nTrades) + ")" : "—"
    table.cell(dash, 1, 11, tp1Txt, text_color=nTrades == 0 ? dim : (nTp1 * 2 >= nTrades ? grn : yel), text_size=size.tiny)
    table.cell(dash, 2, 11, "pad " + str.tostring(i_slBuf + i_structPad, "#.##") + " ATR", text_color=dim, text_size=size.tiny)

    table.cell(dash, 0, 10, "Since load"''',
     "tp1 dashboard row")

src = src.replace('indicator("ME Scalp v2.2", shorttitle="ME Scalp v2.2"',
                  'indicator("ME Scalp v2.3", shorttitle="ME Scalp v2.3"')
src = src.replace("// © ME Institutional — ME Scalp v2.2",
                  "// © ME Institutional — ME Scalp v2.3")
src = src.replace('"ME SCALP v2.2 — "', '"ME SCALP v2.3 — "')

io.open(P, "w", encoding="utf-8").write(src)
print("\nwrote %d bytes" % len(src))
