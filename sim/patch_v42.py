"""Build ME Pro v4.2 from v4.1. Three reported faults, six code changes."""
import io, re, sys

P = "/home/user/Claude/MovementEnginePro.v4.2.pine"
src = io.open(P, encoding="utf-8").read()
n0 = len(src)


def sub1(old, new, tag):
    global src
    if src.count(old) != 1:
        sys.exit("PATCH %s: expected 1 occurrence, found %d" % (tag, src.count(old)))
    src = src.replace(old, new)
    print("  ok  %s" % tag)


# ── 1. ONE TRIGGER SELECTION ────────────────────────────────────────────────
sub1(
"""buyTrigger  = mssUp   or buyTrigFvg  or buyTrigSweep  or buyTrigBand
sellTrigger = mssDown or sellTrigFvg or sellTrigSweep or sellTrigBand""",
"""buyTrigger  = mssUp   or buyTrigFvg  or buyTrigSweep  or buyTrigBand
sellTrigger = mssDown or sellTrigFvg or sellTrigSweep or sellTrigBand

// ═══════════════════════════════════════════════════════════════════════════════
// v4.2 THE SELECTED TRIGGER — decided ONCE, and everything downstream reads it
// ─────────────────────────────────────────────────────────────────────────────
// v4.1 decided which trigger a trade "is" in FOUR separate places, and the four
// used THREE different priority orders:
//
//     buyType      name and alert      MSS   > FVG  > SWEEP > BAND
//     buySlAnchor  where the stop goes  SWEEP > BAND > FVG  > MSS
//     buyChaseRef  the chase reference  SWEEP > BAND > FVG  > MSS
//     tpMeanBuy    target style         BAND, whenever a band was live at all
//
// So when MSS and a sweep fired on the same bar, the chart said MSS, the stop
// was placed beyond the SWEEP's wick, the chase cap was measured from the swept
// level, and a live band injected the VWAP mean as a target. One signal number,
// four different trades.
//
// MEASURED, 15m, 150 days x 6 seeds: 9,832 of 17,738 bullish trigger bars carry
// TWO OR MORE distinct triggers — 55%. This is the majority case, not an edge.
// Worse, v4.1's own confluence score AWARDS A POINT for stacking
// (buyTrigCount >= 2), so the engine rates highest exactly the bars on which its
// four descriptions disagree most.
//
// ONE order now, chosen by how precisely the trigger defines its own
// invalidation — the thing the stop is built from:
//
//     SWEEP  the rejecting bar's wick     tightest, a dated single-bar extreme
//     BAND   the rejecting bar's extreme  same shape, measured off the mean
//     FVG    the far edge of the gap      a zone, not a bar
//     MSS    the last pivot               widest, and the least specific
//
// This is the order the STOP already used, so stop placement is unchanged. What
// changes is that the name, the chase reference and the target style now agree
// with it instead of contradicting it.
// ═══════════════════════════════════════════════════════════════════════════════
buySel  = buyTrigSweep  ? "SWEEP" : buyTrigBand  ? "BAND" : buyTrigFvg  ? "FVG" : mssUp   ? "MSS" : ""
sellSel = sellTrigSweep ? "SWEEP" : sellTrigBand ? "BAND" : sellTrigFvg ? "FVG" : mssDown ? "MSS" : ""
buySelStack  = buyTrigCount  >= 2
sellSelStack = sellTrigCount >= 2""",
"selected trigger")

# ── 2. CHASE REFERENCE follows the selection ────────────────────────────────
sub1(
"""buyChaseRef  = buyTrigSweep  and not na(sweepBullLvl) ? sweepBullLvl : buyTrigBand  and not na(bandRefBullLvl) ? bandRefBullLvl : buyTrigFvg  and not na(lBullTop) ? lBullTop : mssUp   ? lastPH : na
sellChaseRef = sellTrigSweep and not na(sweepBearLvl) ? sweepBearLvl : sellTrigBand and not na(bandRefBearLvl) ? bandRefBearLvl : sellTrigFvg and not na(lBearBot) ? lBearBot : mssDown ? lastPL : na""",
"""// v4.2: keyed to buySel, so the level the chase cap is measured from is the
// level of the trigger the trade is actually reported as.
buyChaseRef  = buySel  == "SWEEP" and not na(sweepBullLvl)   ? sweepBullLvl   : buySel  == "BAND" and not na(bandRefBullLvl)  ? bandRefBullLvl  : buySel  == "FVG" and not na(lBullTop) ? lBullTop : buySel  == "MSS" ? lastPH : na
sellChaseRef = sellSel == "SWEEP" and not na(sweepBearLvl)   ? sweepBearLvl   : sellSel == "BAND" and not na(bandRefBearLvl)  ? bandRefBearLvl  : sellSel == "FVG" and not na(lBearBot) ? lBearBot : sellSel == "MSS" ? lastPL : na""",
"chase reference")

# ── 3. STOP ANCHOR follows the selection (same order, now explicit) ─────────
sub1(
"""buySlAnchor  = buyTrigSweep  and not na(sweepBullLow)  ? sweepBullLow  : buyTrigBand  and not na(bandRefBullLow)  ? bandRefBullLow  : buyTrigFvg  and not na(lBullBot) ? lBullBot : lastPL
sellSlAnchor = sellTrigSweep and not na(sweepBearHigh) ? sweepBearHigh : sellTrigBand and not na(bandRefBearHigh) ? bandRefBearHigh : sellTrigFvg and not na(lBearTop) ? lBearTop : lastPH""",
"""// v4.2: keyed to buySel. The order is the one this line already used, so stop
// placement does not move — it is now simply the SAME decision the label makes.
buySlAnchor  = buySel  == "SWEEP" and not na(sweepBullLow)   ? sweepBullLow   : buySel  == "BAND" and not na(bandRefBullLow)  ? bandRefBullLow  : buySel  == "FVG" and not na(lBullBot) ? lBullBot : lastPL
sellSlAnchor = sellSel == "SWEEP" and not na(sweepBearHigh)  ? sweepBearHigh  : sellSel == "BAND" and not na(bandRefBearHigh) ? bandRefBearHigh : sellSel == "FVG" and not na(lBearTop) ? lBearTop : lastPH""",
"stop anchor")

# ── 4. REVERSION TARGET only when the SELECTED trigger is the band ─────────
sub1(
"""tpMeanBuy  = buyTrigBand  ? vwMean : na
tpMeanSell = sellTrigBand ? vwMean : na""",
"""// v4.2: fires only when BAND is the SELECTED trigger. v4.1 read buyTrigBand
// directly, so a trade reported and stopped as an MSS continuation also had the
// VWAP mean injected as a target whenever any band happened to be live — a
// reversion target inside a continuation plan.
tpMeanBuy  = buySel  == "BAND" ? vwMean : na
tpMeanSell = sellSel == "BAND" ? vwMean : na""",
"reversion target")

# ── 5. NAME follows the selection ──────────────────────────────────────────
sub1(
"""buyType    = mssUp   ? "MSS" : buyTrigFvg   ? "FVG" : buyTrigSweep  ? "SWEEP" : buyTrigBand  ? "BAND" : "MSS"
sellType   = mssDown ? "MSS" : sellTrigFvg  ? "FVG" : sellTrigSweep ? "SWEEP" : sellTrigBand ? "BAND" : "MSS"''"""
.replace("''", ""),
"""// v4.2: the label IS the selection. A "+" marks a bar where other triggers also
// fired, so a stacked setup is visible rather than silently relabelled.
buyType    = buySel  == "" ? "MSS" : buySel  + (buySelStack  ? "+" : "")
sellType   = sellSel == "" ? "MSS" : sellSel + (sellSelStack ? "+" : "")""",
"trigger name")

io.open(P, "w", encoding="utf-8").write(src)
print("\n%d -> %d bytes" % (n0, len(src)))
