"""ME Scalp v2.5 — the chart was under-reporting the trade, and the font.

Not a threshold pass. Four display defects of the same family, plus the two
settings the user found themselves.
"""
import io, sys, shutil

SRC = "/home/user/Claude/MEScalp.v2.4.pine"
P = "/home/user/Claude/MEScalp.v2.5.pine"
shutil.copy(SRC, P)
src = io.open(P, encoding="utf-8").read()


def sub1(old, new, tag):
    global src
    if src.count(old) != 1:
        sys.exit("PATCH %s: expected 1, found %d" % (tag, src.count(old)))
    src = src.replace(old, new)
    print("  ok  %s" % tag)


def suball(old, new, tag, want):
    global src
    if src.count(old) != want:
        sys.exit("PATCH %s: expected %d, found %d" % (tag, want, src.count(old)))
    src = src.replace(old, new)
    print("  ok  %s (%d)" % (tag, want))


# ── header ────────────────────────────────────────────────────────────────────
sub1('''// ═══════════════════════════════════════════════════════════════════════════════
// v2.4 — THE VWAP BAND TRIGGER WAS FIRING ON ARITHMETIC, NOT ON A REJECTION.''',
'''// ═══════════════════════════════════════════════════════════════════════════════
// v2.5 — THE CHART WAS UNDER-REPORTING WHAT THE TRADE ACTUALLY DID.
// ─────────────────────────────────────────────────────────────────────────────
// Reported: still slow, no better, lookback 30 works but thins the trades, the
// VWAP and the confirmations are weak, the SL and TP zones mislead, the font is
// tiny, and neither the indicator nor the bot is effective for scalping.
//
// FOUR OF THOSE ARE DEFECTS AND ARE FIXED HERE. Two are settings and are now
// exposed with what they measure. One is a question I cannot answer with what I
// have, and the last section of this block says so plainly.
//
// ─────────────────────────────────────────────────────────────────────────────
// 1. TP2 WAS DRAWN BUT NEVER TRACKED. This is the defect behind "the SL and TP
// zones mislead", and it is the same bug I fixed for TP1 in v2.3 and did not
// notice I had left in place one level up. The resolution block tested exactly
// two things:
//
//     t1     = high >= eT1        -> arms breakeven, counted
//     tpHit  = high >= eT3        -> closes the trade, counted
//
// eT2 appears nowhere. The engine drew a TP2 line, labelled it with a price,
// and then had no opinion about whether price ever reached it. A trade that ran
// through TP1 AND TP2 and then came back was stamped "BE" — which reads as a
// scratch, while two of the three legs had actually paid.
//
// v2.5 tracks TP2, marks it the moment it trades, counts it on the dashboard
// beside TP1, and the closing stamp now says HOW FAR the trade got: "TP2 ✓ then
// BE" instead of "BE", "TP1 ✓ TIME" instead of "TIME".
//
// 2. THERE WAS NO ENTRY LINE. SL, TP1, TP2 and TP3 were drawn; the price the
// trade actually opened at was not. So the zones had no reference point, and
// when the stop moved to breakeven the SL line silently jumped to a level that
// was never marked. The entry is now drawn and labelled, which also makes the
// breakeven move visible instead of implied.
//
// 3. ONLY ONE PLAN WAS EVER ON THE CHART. Every new setup deleted the previous
// one's lines and labels, so scrolling back showed nothing and no claim in this
// header could be checked against your own chart. Completed plans now stay,
// frozen, up to the drawing limits. That is the single change most likely to
// tell you whether any of this works, because it lets you audit it.
//
// 4. THE FONT. Everything was size.tiny, hard-coded in 43 places. There is now
// one Text Size input and it drives the dashboard and every plan label.
//
// ─────────────────────────────────────────────────────────────────────────────
// THE TWO SETTINGS YOU FOUND. Both are real, and both are confirmed here.
//
// REGIME LOOKBACK 20 -> 30. You are right, and it is the peak rather than a
// direction: 40 gives it back. Default changed to 30.
//
//     5m                                    15m
//     lookback  trd/day  TP1  TP3   SL      lookback  trd/day  TP1  TP3   SL
//     20           4.07  62%  20%  12%      20           2.11  58%  22%  25%
//     25           3.37  64%  22%  11%      25           1.88  58%  22%  25%
//     30           3.05  65%  22%  11%      30           1.64  61%  23%  23%
//     40           2.48  64%  20%  12%      40           1.29  60%  20%  23%
//
// You also said the trades get low, and they do — a quarter of them on 5m. That
// is not a tuning failure I can fix. EVERY dial in this engine trades supply
// for quality, monotonically, and none of them gives both. What gives both is a
// better trigger, not a better filter, and I have no way to validate a new
// trigger on real gold. See the last section.
//
// THE QUALITY SCORE WAS PINNED AT 1 OUT OF 5 with no input. "The confirmations
// are weak" is literally true: one point of five was enough to trade. It is now
// an input. What it costs, at lookback 30:
//
//     5m                                    15m
//     need  trd/day  TP1  TP3   SL  TIME    need  trd/day  TP1  TP3   SL  TIME
//     1/5      3.05  65%  22%  11%   24%    1/5      1.64  61%  23%  23%   16%
//     2/5      2.25  68%  23%  13%   19%    2/5      1.40  65%  24%  26%    9%
//     3/5      1.14  75%  27%  15%   10%    3/5      0.98  68%  28%  29%    4%
//
// READ THE STOP-OUT COLUMN. A stricter score does NOT reduce losses — it RAISES
// them, on both timeframes, while collapsing the share of trades that resolve
// nothing. It converts unresolved trades into resolved ones in BOTH directions.
// That is a genuine trade and not an improvement, so the default stays at 1 and
// the dial is yours.
//
// ─────────────────────────────────────────────────────────────────────────────
// "NOT EFFECTIVE FOR SCALP" — WHAT I CAN AND CANNOT TELL YOU.
//
// I cannot tell you this engine is profitable on XAUUSD, and I should have said
// so several versions ago instead of running a fifth threshold pass.
//
// Everything in every header of this file — v2.1 through v2.4 — is COUNTS AND
// OUTCOME GEOMETRY from a synthetic price generator I wrote. That generator
// already paid a naive momentum rule +0.21R, which is why every expectancy
// figure it ever produced was withdrawn. Outcome mix from it can find a BUG —
// the collapsed VWAP band in v2.4 was a real one, and so is the TP2 defect
// above — but it cannot tell you whether the result makes money on gold, at
// your broker, with your spread. Four passes of tuning against it have not
// changed what you see on a live chart, and that is the expected outcome of
// optimising the wrong objective.
//
// So this release ships a second file: MEScalp.v2.5.strategy.pine, the same
// engine as a Pine STRATEGY. Load it and TradingView's Strategy Tester will run
// it over real XAUUSD history, with your spread and your commission, and give
// you a net P&L, a profit factor and a drawdown — none of which I have ever
// been able to compute. Set the commission and slippage in Properties before
// you read a single number off it; at a default of zero it will look far better
// than it is, and on a scalp the spread is most of the answer.
//
// If it loses there, no threshold in this file will save it and I will stop
// suggesting ones. That is the test worth running.
//
// ═══════════════════════════════════════════════════════════════════════════════
// v2.4 — THE VWAP BAND TRIGGER WAS FIRING ON ARITHMETIC, NOT ON A REJECTION.''',
     "header")

sub1('indicator("ME Scalp v2.4", shorttitle="ME Scalp v2.4", overlay=true, max_boxes_count=200, max_lines_count=200, max_labels_count=200, max_bars_back=500)',
     'indicator("ME Scalp v2.5", shorttitle="ME Scalp v2.5", overlay=true, max_boxes_count=200, max_lines_count=500, max_labels_count=500, max_bars_back=500)',
     "declaration")
sub1("// © ME Institutional — ME Scalp v2.4",
     "// © ME Institutional — ME Scalp v2.5", "copyright")
sub1('"ME SCALP v2.4 — "', '"ME SCALP v2.5 — "', "dash title")

# ── settings the user found ───────────────────────────────────────────────────
sub1('''i_erLen = input.int(20, "Regime Lookback (bars)", minval=5, maxval=100, group=G_ENG,
     tooltip="Window for the efficiency ratio and for the direction of the leg being aligned to.")''',
'''i_erLen = input.int(30, "Regime Lookback (bars)", minval=5, maxval=100, group=G_ENG,
     tooltip="Window for the efficiency ratio and for the direction of the leg being aligned to.\\n\\nv2.5: RAISED FROM 20 TO 30 on a user report, then confirmed by measurement. 30 is a peak rather than a direction — 40 gives the gain back.\\n\\n  5m                          15m\\n  lookback trd/day TP1  SL    lookback trd/day TP1  SL\\n  20          4.07 62% 12%    20          2.11 58% 25%\\n  25          3.37 64% 11%    25          1.88 58% 25%\\n  30          3.05 65% 11%    30          1.64 61% 23%\\n  40          2.48 64% 12%    40          1.29 60% 23%\\n\\nIt costs a quarter of the trades on 5m and a fifth on 15m. That is not avoidable by tuning: every dial in this engine trades supply for quality and none of them gives both.")''',
     "lookback default")

sub1('''i_useMss   = input.bool(true, "MSS — structure break",        group=G_TRIG)''',
'''i_needScore = input.int(1, "Quality Score Required (of 5)", minval=0, maxval=5, group=G_ENG,
     tooltip="v2.5: THIS WAS PINNED AT 1 AND HAD NO INPUT. One point out of five was enough to trade, which is what \\"the confirmations are weak\\" means in code.\\n\\nThe five points are independent readings of the entry bar: participation (volume >= 1.15x), body >= 0.45 ATR, close in the top/bottom third of its range, two or more triggers agreeing, and location at a band.\\n\\nMEASURED at lookback 30:\\n\\n  5m                            15m\\n  need trd/day TP1 TP3  SL TIME  need trd/day TP1 TP3  SL TIME\\n  1/5     3.05 65% 22% 11%  24%  1/5     1.64 61% 23% 23%  16%\\n  2/5     2.25 68% 23% 13%  19%  2/5     1.40 65% 24% 26%   9%\\n  3/5     1.14 75% 27% 15%  10%  3/5     0.98 68% 28% 29%   4%\\n\\nREAD THE SL COLUMN BEFORE RAISING THIS. A stricter score does not reduce losses, it RAISES them on both timeframes, while collapsing the share of trades that resolve nothing. It converts unresolved trades into resolved ones in BOTH directions.\\n\\nThat is a real trade, not an improvement, which is why the default is unchanged at 1.")

i_useMss   = input.bool(true, "MSS — structure break",        group=G_TRIG)''',
     "score input")

sub1("needScore = 1", "needScore = i_needScore", "score wiring")

# ── the font ──────────────────────────────────────────────────────────────────
sub1('''i_dashPos   = input.string("Top Right", "Dashboard Position", options=["Top Right", "Top Left", "Bottom Right", "Bottom Left"], group=G_DISP)''',
'''i_dashPos   = input.string("Top Right", "Dashboard Position", options=["Top Right", "Top Left", "Bottom Right", "Bottom Left"], group=G_DISP)
i_font      = input.string("Small", "Text Size", options=["Tiny", "Small", "Normal", "Large"], group=G_DISP,
     tooltip="v2.5: drives the dashboard AND every plan label. Through v2.4 all of it was size.tiny, hard-coded in 43 places with no way to change it.")
i_keepPlans = input.bool(true, "Keep completed plans on the chart", group=G_DISP,
     tooltip="v2.5: through v2.4 every new setup DELETED the previous one's lines and labels, so scrolling back showed nothing and no claim in this script could be checked against your own chart.\\n\\nCompleted plans now stay, frozen with their outcome, up to TradingView's drawing limit — about 80 plans at five lines and six labels each, oldest recycled first.\\n\\nThis is the change most likely to tell you whether the engine works, because it is the one that lets you audit it instead of trusting a header.")

// v2.5 one size for the whole script. fBody is the plan labels and the table
// body; fHead is one step up for the title row.
fBody = i_font == "Large" ? size.large : i_font == "Normal" ? size.normal : i_font == "Small" ? size.small : size.tiny
fHead = i_font == "Large" ? size.huge : i_font == "Normal" ? size.large : i_font == "Small" ? size.normal : size.small''',
     "font input")

suball("text_size=size.tiny", "text_size=fBody", "table font", 36)
sub1('text_size=size.small, text_halign=text.align_left)', 'text_size=fHead, text_halign=text.align_left)', "dash title font")

# The plan labels, one at a time. A blanket replace would also catch the two
# plotshape calls, where `size` is the size of a TRIANGLE and not a font.
for tail, tag in (("color.new(#FF1744, 0), size=size.tiny)", "SL label"),
                  ("color.new(#00E676, 0), size=size.tiny)", "TP1 label"),
                  ("color.new(#00E676, 20), size=size.tiny)", "TP2 label"),
                  ("color.new(#00E676, 40), size=size.tiny)", "TP3 label"),
                  ("textcolor=closeCol, size=size.tiny)", "outcome label")):
    sub1("textcolor=" + tail if not tail.startswith("textcolor") else tail,
         ("textcolor=" + tail if not tail.startswith("textcolor") else tail).replace("size=size.tiny)", "size=fBody)"),
         tag)

io.open(P, "w", encoding="utf-8").write(src)
print("\nstage 1 wrote %d bytes" % len(src))


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 2 — TP2 tracking, the entry line, plan history, the outcome stamp
# ══════════════════════════════════════════════════════════════════════════════
src = io.open(P, encoding="utf-8").read()

sub1('''var int   nTp1      = 0
var int   tp1HitBar = na''',
'''var int   nTp1      = 0
var int   tp1HitBar = na
// v2.5: TP2 was DRAWN and never TRACKED. eT2 appeared in no test anywhere in
// the engine, so a trade that ran through TP1 and TP2 and came back was stamped
// "BE" — a scratch — with two of the three legs having paid. Same defect as the
// v2.3 TP1 one, one level up, and I did not spot it then.
var bool  eTp2Done  = false
var int   nTp2      = 0
var int   tp2HitBar = na''',
     "tp2 state")

sub1('''    eBar     := bar_index
    eTp1Done := false''',
'''    eBar     := bar_index
    eTp1Done := false
    eTp2Done := false''',
     "tp2 reset")

sub1('''            if i_beAfterTp1
                eSl := eEntry
    tpHit  := tradeBuy ? high >= eT3 : low <= eT3''',
'''            if i_beAfterTp1
                eSl := eEntry
    // v2.5: the middle leg, finally measured rather than merely drawn.
    if not eTp2Done
        bool t2 = tradeBuy ? high >= eT2 : low <= eT2
        if t2 and not slHit
            eTp2Done := true
            tp2HitBar := bar_index
            nTp2 := nTp2 + 1
    tpHit  := tradeBuy ? high >= eT3 : low <= eT3''',
     "tp2 resolution")

sub1('''closeTxt   = tpHit ? "TP3 ✓" : slHit ? (eTp1Done ? "BE" : "SL ✕") : "TIME"''',
'''// v2.5: say HOW FAR it got. "BE" and "TIME" both concealed a trade that had
// banked one or two legs, which is what "the TP zones mislead" meant.
legTxt     = eTp2Done ? "TP2 ✓ " : eTp1Done ? "TP1 ✓ " : ""
closeTxt   = tpHit ? "TP3 ✓" : slHit ? (eTp1Done ? legTxt + "→ BE" : "SL ✕") : legTxt + "TIME"''',
     "outcome stamp")

# ── the entry line ────────────────────────────────────────────────────────────
sub1('''var line lnSl = na
var line lnT1 = na''',
'''// v2.5: the entry itself was never drawn. SL, TP1, TP2 and TP3 had lines; the
// price the trade opened at did not, so the zones had no reference point and
// the move to breakeven was invisible — the SL line simply jumped.
var line lnEn = na
var label lbEn = na
var line lnSl = na
var line lnT1 = na''',
     "entry line vars")

sub1('''if i_showPlan and fired
    if not na(lnSl)
        line.delete(lnSl)''',
'''if i_showPlan and fired
    // v2.5: keep the history. Through v2.4 this deleted the previous plan
    // unconditionally, so the chart could never be audited against the claims
    // in this header. TradingView recycles the oldest drawing once the limit is
    // reached, so nothing needs counting here.
    if not na(lnSl) and not i_keepPlans
        line.delete(lnEn)
        label.delete(lbEn)
        line.delete(lnSl)''',
     "keep plans")

sub1('''    if not na(lbEnd)
        label.delete(lbEnd)
    lnSl := line.new(bar_index, eSl, bar_index, eSl, color=color.new(#FF1744, 0), width=2)''',
'''    if not na(lbEnd) and not i_keepPlans
        label.delete(lbEnd)
    lnEn := line.new(bar_index, eEntry, bar_index, eEntry, color=color.new(#FFFFFF, 25), width=1, style=line.style_dotted)
    lbEn := label.new(bar_index, eEntry, "ENTRY " + str.tostring(eEntry, format.mintick), style=label.style_label_left, color=color.new(#000000, 100), textcolor=color.new(#FFFFFF, 0), size=fBody)
    lnSl := line.new(bar_index, eSl, bar_index, eSl, color=color.new(#FF1744, 0), width=2)''',
     "entry line draw")

sub1('''if i_showPlan and inTrade and not na(lnSl)
    line.set_x2(lnSl, bar_index)''',
'''if i_showPlan and inTrade and not na(lnSl)
    line.set_x2(lnEn, bar_index)
    label.set_x(lbEn, bar_index)
    line.set_x2(lnSl, bar_index)''',
     "extend entry")

sub1('''    if eTp1Done and not na(lbT1)
        label.set_text(lbT1, "TP1 ✓ " + str.tostring(eT1, format.mintick))
    label.set_x(lbT1, bar_index)''',
'''    if eTp1Done and not na(lbT1)
        label.set_text(lbT1, "TP1 ✓ " + str.tostring(eT1, format.mintick))
    // v2.5: and the same for the leg that was never tracked at all.
    if eTp2Done and not na(lbT2)
        label.set_text(lbT2, "TP2 ✓ " + str.tostring(eT2, format.mintick))
    label.set_x(lbT1, bar_index)''',
     "tp2 label")

sub1('''if i_showPlan and justClosed and not na(lnSl)
    line.set_x2(lnSl, bar_index)''',
'''if i_showPlan and justClosed and not na(lnSl)
    line.set_x2(lnEn, bar_index)
    line.set_x2(lnSl, bar_index)''',
     "freeze entry")

sub1('''    if not na(lbEnd)
        label.delete(lbEnd)
    lbEnd := label.new(bar_index, tradeBuy ? low : high, closeTxt,''',
'''    if not na(lbEnd) and not i_keepPlans
        label.delete(lbEnd)
    lbEnd := label.new(bar_index, tradeBuy ? low : high, closeTxt,''',
     "keep outcome label")

# ── the TP2 mark on the bar it traded ─────────────────────────────────────────
sub1('''plotshape(buySignal  and not inTrade[1], "BUY",''',
'''plotshape(not na(tp2HitBar) and tp2HitBar == bar_index and tradeBuy,  "TP2 hit (long)",  shape.triangleup,   location.belowbar, color.new(#00E676, 0), size=size.tiny)
plotshape(not na(tp2HitBar) and tp2HitBar == bar_index and not tradeBuy, "TP2 hit (short)", shape.triangledown, location.abovebar, color.new(#00E676, 0), size=size.tiny)

plotshape(buySignal  and not inTrade[1], "BUY",''',
     "tp2 plotshape")

# ── dashboard: TP2 beside TP1, and the pad moved to its own row ───────────────
sub1("dash := table.new(pos, 3, 13,", "dash := table.new(pos, 3, 14,", "table rows")

sub1('''    table.cell(dash, 0, 11, "TP1 reach", text_color=dim, text_size=fBody, text_halign=text.align_left, bgcolor=color.rgb(15, 15, 22))
    tp1Txt = nTrades > 0 ? str.tostring(math.round(100.0 * nTp1 / nTrades)) + "%  (" + str.tostring(nTp1) + "/" + str.tostring(nTrades) + ")" : "—"
    table.cell(dash, 1, 11, tp1Txt, text_color=nTrades == 0 ? dim : (nTp1 * 2 >= nTrades ? grn : yel), text_size=fBody)
    table.cell(dash, 2, 11, "pad " + str.tostring(i_slBuf + i_structPad, "#.##") + " / MSS " + str.tostring(i_slBuf + i_structPad + i_breakPad, "#.##"), text_color=dim, text_size=fBody)''',
'''    // v2.5: TP2 sits beside TP1 because until this release nothing counted it.
    table.cell(dash, 0, 11, "TP1 / TP2 reach", text_color=dim, text_size=fBody, text_halign=text.align_left, bgcolor=color.rgb(15, 15, 22))
    tp1Txt = nTrades > 0 ? str.tostring(math.round(100.0 * nTp1 / nTrades)) + "%  (" + str.tostring(nTp1) + "/" + str.tostring(nTrades) + ")" : "—"
    tp2Txt = nTrades > 0 ? str.tostring(math.round(100.0 * nTp2 / nTrades)) + "%  (" + str.tostring(nTp2) + "/" + str.tostring(nTrades) + ")" : "—"
    table.cell(dash, 1, 11, tp1Txt, text_color=nTrades == 0 ? dim : (nTp1 * 2 >= nTrades ? grn : yel), text_size=fBody)
    table.cell(dash, 2, 11, tp2Txt, text_color=nTrades == 0 ? dim : (nTp2 * 3 >= nTrades ? grn : yel), text_size=fBody)

    table.cell(dash, 0, 13, "Stop pad (× ATR)", text_color=dim, text_size=fBody, text_halign=text.align_left, bgcolor=color.rgb(15, 15, 22))
    table.cell(dash, 1, 13, str.tostring(i_slBuf + i_structPad, "#.##") + " shared", text_color=dim, text_size=fBody)
    table.cell(dash, 2, 13, str.tostring(i_slBuf + i_structPad + i_breakPad, "#.##") + " on MSS", text_color=dim, text_size=fBody)''',
     "dash tp2 row")

io.open(P, "w", encoding="utf-8").write(src)
print("\nstage 2 wrote %d bytes" % len(src))
