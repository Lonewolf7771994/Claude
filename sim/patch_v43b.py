"""v4.3 logic — leg, POC reclaim trigger, VA migration, absorption, gate."""
import io, sys

P = "/home/user/Claude/MovementEnginePro.v4.3.pine"
src = io.open(P, encoding="utf-8").read()


def sub1(old, new, tag):
    global src
    if src.count(old) != 1:
        sys.exit("PATCH %s: expected 1, found %d" % (tag, src.count(old)))
    src = src.replace(old, new)
    print("  ok  %s" % tag)


# ── LEG + ABSORPTION, defined with the other bar readings ──────────────────
sub1(
"""bodySize  = math.abs(close - open)
upperWick = high - math.max(close, open)""",
"""// ═══════════════════════════════════════════════════════════════════════════════
// v4.3 THE LEG IN PROGRESS
// ─────────────────────────────────────────────────────────────────────────────
// The engine had no direct read of the move it is trading inside. It had an HTF
// EMA bias, an 8/21 momentum stack and a CVD cross — three smoothed proxies, all
// of which lag and none of which answers the plain question "is price higher
// than it was". The no-reversal gate needs that plain answer, so it is measured
// plainly. Closed history only, so it cannot repaint.
// ═══════════════════════════════════════════════════════════════════════════════
legUp   = close > close[i_legLen]
legDown = close < close[i_legLen]

// v4.3 ABSORPTION — the one order-flow reading that measures effort against
// result. Every other order-flow test in this engine reads the SHAPE of a single
// bar (close position, body conviction), and shape cannot tell a quiet bar from
// one where a large participant is being filled into. Heavy volume producing
// almost no range is size trading while price refuses to move.
absorbing = volDataSeen and i_absorb and relVol >= i_absorbVol and (high - low) <= atr14 * i_absorbRng

bodySize  = math.abs(close - open)
upperWick = high - math.max(close, open)""",
"leg and absorption")

# ── VA MIGRATION replaces the broken position test ─────────────────────────
sub1(
"""frvpBullOk = na(vahPrice) or close >= valPrice
frvpBearOk = na(valPrice) or close <= vahPrice""",
"""// ═══════════════════════════════════════════════════════════════════════════════
// v4.3 — THE VALUE-AREA CONFLUENCE LEG WAS TRUE FOR BOTH SIDES AT ONCE
// ─────────────────────────────────────────────────────────────────────────────
// frvpBullOk was `close >= valPrice` and frvpBearOk was `close <= vahPrice`, so
// while price sat anywhere INSIDE the value area — most of the time — both were
// true and the leg scored a point for the bull side and the bear side
// simultaneously. That is not a directional reading.
//
// It was not harmless. This leg feeds buyAligned/sellAligned, which feed the
// confluence gate AND the invalidation exit, and v3.5.23's own comment recorded
// the symptom without naming the cause: "a fully flipped market commonly reads
// 3/3 against and 1/3 for". The 1/3 was this leg, scoring for the losing side.
//
// v4.3 asks a question with one answer: is the value area itself MOVING? Both
// edges higher than five bars ago means value is migrating up. That is the
// profile expressing DIRECTION rather than position — the volume-profile input
// this engine was asked for and never had.
// ═══════════════════════════════════════════════════════════════════════════════
vaUp   = not na(vahPrice) and not na(vahPrice[5]) and not na(valPrice[5]) and vahPrice > vahPrice[5] and valPrice > valPrice[5]
vaDown = not na(vahPrice) and not na(vahPrice[5]) and not na(valPrice[5]) and vahPrice < vahPrice[5] and valPrice < valPrice[5]
frvpBullOk = i_vaMigrate ? vaUp   : (na(vahPrice) or close >= valPrice)
frvpBearOk = i_vaMigrate ? vaDown : (na(valPrice) or close <= vahPrice)

// ═══════════════════════════════════════════════════════════════════════════════
// v4.3 POC RECLAIM TRIGGER — the profile finally starts a trade
// ─────────────────────────────────────────────────────────────────────────────
// The POC is the single highest-volume price in the profile: the price the most
// business was done at, and the level most participants agree on. Through v4.2
// this engine computed it every bar and never let it do anything — drawn,
// published in the alert, offered as a target candidate, never once an entry.
// Closing through it, from the other side, is the profile's centre of gravity
// changing hands.
// Measured on 15m over 150 days x 6 seeds: 7.81 events/day, of which 6.31 run
// with the leg — roughly a fifth of what the no-reversal gate removes, returned.
// The invalidation is the POC itself, so the stop is structural like the rest.
// ═══════════════════════════════════════════════════════════════════════════════
pocBullEvent = i_pocTrig and barstate.isconfirmed and not na(pocPrice) and close > pocPrice and close[1] <= nz(pocPrice[1], pocPrice) and closePos >= 0.55
pocBearEvent = i_pocTrig and barstate.isconfirmed and not na(pocPrice) and close < pocPrice and close[1] >= nz(pocPrice[1], pocPrice) and closePos <= 0.45

var int pocBullAge = 999
var int pocBearAge = 999
pocBullAge := pocBullEvent ? 0 : math.min(pocBullAge + 1, 999)
pocBearAge := pocBearEvent ? 0 : math.min(pocBearAge + 1, 999)
if pocBullEvent
    pocBearAge := 999
if pocBearEvent
    pocBullAge := 999
pocBull = pocBullAge <= effTriggerAge
pocBear = pocBearAge <= effTriggerAge

var float pocBullLvl = na
var float pocBearLvl = na
if pocBullEvent
    pocBullLvl := pocPrice
if pocBearEvent
    pocBearLvl := pocPrice""",
"va migration and poc trigger")

# ── ADMIT THE POC TRIGGER ──────────────────────────────────────────────────
sub1(
"""buyTrigger  = mssUp   or buyTrigFvg  or buyTrigSweep  or buyTrigBand
sellTrigger = mssDown or sellTrigFvg or sellTrigSweep or sellTrigBand""",
"""buyTrigPoc   = pocBull
sellTrigPoc  = pocBear

buyTrigger  = mssUp   or buyTrigFvg  or buyTrigSweep  or buyTrigBand  or buyTrigPoc
sellTrigger = mssDown or sellTrigFvg or sellTrigSweep or sellTrigBand or sellTrigPoc""",
"admit poc trigger")

# selection order: POC sits with the structural triggers, ahead of MSS, because
# its invalidation (the POC line) is a tighter, better-defined level than a pivot
sub1(
"""buySel  = buyTrigSweep  ? "SWEEP" : buyTrigBand  ? "BAND" : buyTrigFvg  ? "FVG" : mssUp   ? "MSS" : ""
sellSel = sellTrigSweep ? "SWEEP" : sellTrigBand ? "BAND" : sellTrigFvg ? "FVG" : mssDown ? "MSS" : \"\"""",
"""buySel  = buyTrigSweep  ? "SWEEP" : buyTrigBand  ? "BAND" : buyTrigFvg  ? "FVG" : buyTrigPoc  ? "POC" : mssUp   ? "MSS" : ""
sellSel = sellTrigSweep ? "SWEEP" : sellTrigBand ? "BAND" : sellTrigFvg ? "FVG" : sellTrigPoc ? "POC" : sellSel_mssGuard ? "MSS" : \"\"""".replace("sellSel_mssGuard", "mssDown"),
"selection order")

sub1(
"""buyTrigCount  = (mssUp   ? 1 : 0) + (buyTrigFvg  ? 1 : 0) + (buyTrigSweep  ? 1 : 0) + (buyTrigBand  ? 1 : 0)
sellTrigCount = (mssDown ? 1 : 0) + (sellTrigFvg ? 1 : 0) + (sellTrigSweep ? 1 : 0) + (sellTrigBand ? 1 : 0)""",
"""buyTrigCount  = (mssUp   ? 1 : 0) + (buyTrigFvg  ? 1 : 0) + (buyTrigSweep  ? 1 : 0) + (buyTrigBand  ? 1 : 0) + (buyTrigPoc  ? 1 : 0)
sellTrigCount = (mssDown ? 1 : 0) + (sellTrigFvg ? 1 : 0) + (sellTrigSweep ? 1 : 0) + (sellTrigBand ? 1 : 0) + (sellTrigPoc ? 1 : 0)""",
"trigger count")

# chase reference and stop anchor learn about POC
sub1(""" : buySel  == "FVG" and not na(lBullTop) ? lBullTop : buySel  == "MSS" ? lastPH : na""",
     """ : buySel  == "FVG" and not na(lBullTop) ? lBullTop : buySel  == "POC" and not na(pocBullLvl) ? pocBullLvl : buySel  == "MSS" ? lastPH : na""",
     "poc chase buy")
sub1(""" : sellSel == "FVG" and not na(lBearBot) ? lBearBot : sellSel == "MSS" ? lastPL : na""",
     """ : sellSel == "FVG" and not na(lBearBot) ? lBearBot : sellSel == "POC" and not na(pocBearLvl) ? pocBearLvl : sellSel == "MSS" ? lastPL : na""",
     "poc chase sell")
sub1(""" : buySel  == "FVG" and not na(lBullBot) ? lBullBot : lastPL""",
     """ : buySel  == "FVG" and not na(lBullBot) ? lBullBot : buySel  == "POC" and not na(pocBullLvl) ? pocBullLvl : lastPL""",
     "poc anchor buy")
sub1(""" : sellSel == "FVG" and not na(lBearTop) ? lBearTop : lastPH""",
     """ : sellSel == "FVG" and not na(lBearTop) ? lBearTop : sellSel == "POC" and not na(pocBearLvl) ? pocBearLvl : lastPH""",
     "poc anchor sell")

# ── ABSORPTION AS A SIXTH CONFLUENCE READING ──────────────────────────────
sub1(
"""confV4Buy  = (relVol >= 1.20 ? 1 : 0) + (bodySize >= atr14 * 0.55 ? 1 : 0) + (closePos >= 0.70 ? 1 : 0) + (buyTrigCount  >= 2 ? 1 : 0) + (buyAtBand  ? 1 : 0)
confV4Sell = (relVol >= 1.20 ? 1 : 0) + (bodySize >= atr14 * 0.55 ? 1 : 0) + (closePos <= 0.30 ? 1 : 0) + (sellTrigCount >= 2 ? 1 : 0) + (sellAtBand ? 1 : 0)""",
"""// v4.3: absorption is the SIXTH reading. It corroborates a setup without being
// able to create one, and a sixth reading makes each mode's threshold slightly
// easier to reach — a deliberate partial offset against the supply the
// no-reversal gate removes.
confV4Buy  = (relVol >= 1.20 ? 1 : 0) + (bodySize >= atr14 * 0.55 ? 1 : 0) + (closePos >= 0.70 ? 1 : 0) + (buyTrigCount  >= 2 ? 1 : 0) + (buyAtBand  ? 1 : 0) + (absorbing ? 1 : 0)
confV4Sell = (relVol >= 1.20 ? 1 : 0) + (bodySize >= atr14 * 0.55 ? 1 : 0) + (closePos <= 0.30 ? 1 : 0) + (sellTrigCount >= 2 ? 1 : 0) + (sellAtBand ? 1 : 0) + (absorbing ? 1 : 0)""",
"absorption confluence")

io.open(P, "w", encoding="utf-8").write(src)
print("\nwrote %d bytes" % len(src))
