"""v4.7 part 2 — CRT (candle range theory) trigger and Silver Bullet windows."""
import io, sys

P = "/home/user/Claude/MovementEnginePro.v4.7.pine"
src = io.open(P, encoding="utf-8").read()


def sub1(old, new, tag):
    global src
    if src.count(old) != 1:
        sys.exit("PATCH %s: expected 1, found %d" % (tag, src.count(old)))
    src = src.replace(old, new)
    print("  ok  %s" % tag)


# ── INPUTS ─────────────────────────────────────────────────────────────────
sub1('var string G_PRISM  = "══ Trend Trail ══"',
     'var string G_ICT    = "══ CRT + Silver Bullet ══"\nvar string G_PRISM  = "══ Trend Trail ══"',
     "ict group")

sub1('i_prismOn    = input.bool(true, "Show Trend Trail",',
"""i_crtOn      = input.bool(true, "CRT — Candle Range Theory Trigger",
     tooltip="v4.7: the previous HIGHER-TIMEFRAME candle's range is the playing field. The setup is the classic three-candle sequence, expressed as an event on the chart timeframe:\\n\\n  1  the prior HTF candle sets a range — its high and its low\\n  2  price runs one side of that range and CLOSES BACK INSIDE it\\n  3  the expansion is toward the opposite side\\n\\nStep 2 is the trigger. It is the same SHAPE as this engine's liquidity sweep, with one difference that matters: a sweep hunts a pivot, which is structure the chart drew for itself, while CRT hunts the boundary of a completed higher-timeframe candle — a level a far larger set of participants is looking at.\\n\\nIts invalidation is the extreme of the bar that ran the range, exactly as a sweep's is, so the stop is built the same structural way. It is admitted into the trigger selection ABOVE the ordinary sweep, because an HTF candle boundary is a more precisely defined level than a chart-timeframe pivot.\\n\\nNOT MEASURED. No harness figure is quoted for CRT because no price feed was reachable — it is implemented to the model's definition, not validated against it.",
     group=G_ICT)
i_crtTf      = input.timeframe("240", "  CRT Range Timeframe",
     tooltip="v4.7: which candle's range defines the field. It must be genuinely ABOVE the chart timeframe or the range is the chart's own last bar and the trigger is meaningless — the same defect v3.5.28 found in the HTF filter. The dashboard warns when it is not higher and the trigger self-disables.",
     group=G_ICT)
i_crtMid     = input.bool(false, "  Require Reclaim Past The 50% Level",
     tooltip="v4.7: a stricter reading of step 2. Instead of merely closing back inside the range, the close must recover past its midpoint — the argument being that a shallow reclaim has not proved the range is being defended.\\n\\nStricter and rarer. Off by default because it is a judgement, not a measurement, and this file does not ship judgements as defaults without saying so.",
     group=G_ICT)
i_crtShow    = input.bool(true, "  Draw The CRT Range", group=G_ICT)

i_sbMode     = input.string("Off", "Silver Bullet Window",
     options=["Off", "Highlight only", "Restrict signals to windows"],
     tooltip="v4.7: the three one-hour windows the model trades, in New York time:\\n\\n  03:00-04:00   London\\n  10:00-11:00   New York AM\\n  14:00-15:00   New York PM\\n\\nHIGHLIGHT ONLY tints the windows and changes nothing about signal generation — use this first to see whether your setups actually cluster there before you let it gate anything.\\n\\nRESTRICT SIGNALS blocks every signal outside the windows, and additionally requires the entry to come from an FVG, which is the model's actual entry: a gap forms inside the window in the direction of the draw, and the trade is the retrace into it. Reported as 'sb' in the Last Block row.\\n\\nThis is a HARD time filter and it is expensive — three hours out of twenty-four. Expect trade count to fall by roughly the share of the day it removes, and more, since the FVG requirement also binds. That cost is arithmetic; whether the windows are worth it on your data is not something this file can tell you.",
     group=G_ICT)
i_sbTz       = input.string("America/New_York", "  Silver Bullet Timezone", group=G_ICT)
i_sbFvgOnly  = input.bool(true, "  Require FVG Entry Inside The Window",
     tooltip="v4.7: the model's entry is the retrace into a fair value gap formed inside the window, not simply any setup that happens to occur during the hour. With this off the windows become a pure time filter and any trigger may fire inside them.",
     group=G_ICT)
i_prismOn    = input.bool(true, "Show Trend Trail",""",
"ict inputs")

# ── CRT ENGINE, placed with the other triggers (after the sweep block) ─────
sub1("""// ═══════════════════════════════════════════════════════════════════════════════
// v4.0 BAND REJECTION TRIGGER""",
"""// ═══════════════════════════════════════════════════════════════════════════════
// v4.7 CRT — THE PREVIOUS HTF CANDLE'S RANGE IS THE FIELD
// ─────────────────────────────────────────────────────────────────────────────
// Candle Range Theory in three steps: a higher-timeframe candle sets a range,
// the next runs one side of it and closes back inside, and the expansion goes
// the other way. Step two is the tradeable event and it is what this implements.
//
// It is the same SHAPE as the liquidity sweep already in this engine, and one
// difference makes it worth having separately: a sweep hunts a PIVOT, which is
// structure the chart drew for itself, while CRT hunts the boundary of a
// COMPLETED higher-timeframe candle — a level a far larger set of participants
// is looking at, and one that exists before price gets there rather than being
// confirmed several bars afterwards.
//
// The range comes from the PREVIOUS HTF candle via close[1]-style offsets with
// lookahead_on — the stable idiom v3.5.17 established. That returns the last
// CLOSED HTF candle, identical live and historical, so the field cannot be
// redrawn after the fact.
//
// The invalidation is the extreme of the bar that ran the range, exactly as a
// sweep's is, so the stop is built the same structural way as every other
// trigger here.
// ═══════════════════════════════════════════════════════════════════════════════
[crtHi, crtLo] = request.security(syminfo.tickerid, i_crtTf, [high[1], low[1]], lookahead=barmerge.lookahead_on)
crtDegenerate  = timeframe.in_seconds(i_crtTf) <= timeframe.in_seconds()
crtOk          = i_crtOn and not crtDegenerate and not na(crtHi) and not na(crtLo) and crtHi > crtLo
crtMid         = (crtHi + crtLo) / 2.0

// step 2, bullish: ran the low of the range and closed back inside it
crtBullEvent = crtOk and barstate.isconfirmed and low <= crtLo and close > crtLo and closePos >= 0.55 and (not i_crtMid or close >= crtMid)
crtBearEvent = crtOk and barstate.isconfirmed and high >= crtHi and close < crtHi and closePos <= 0.45 and (not i_crtMid or close <= crtMid)

var int crtBullAge = 999
var int crtBearAge = 999
crtBullAge := crtBullEvent ? 0 : math.min(crtBullAge + 1, 999)
crtBearAge := crtBearEvent ? 0 : math.min(crtBearAge + 1, 999)
if crtBullEvent
    crtBearAge := 999
if crtBearEvent
    crtBullAge := 999
crtBull = crtBullAge <= effTriggerAge
crtBear = crtBearAge <= effTriggerAge

var float crtBullLow  = na
var float crtBullLvl  = na
var float crtBearHigh = na
var float crtBearLvl  = na
if crtBullEvent
    crtBullLow := low
    crtBullLvl := crtLo
if crtBearEvent
    crtBearHigh := high
    crtBearLvl  := crtHi

// the field itself, drawn on the last bar only
var line crtHiLine = na
var line crtLoLine = na
var line crtMidLine = na
if i_crtShow and crtOk and barstate.islast
    if not na(crtHiLine)
        line.delete(crtHiLine)
        line.delete(crtLoLine)
        line.delete(crtMidLine)
    int xA = bar_index - 60
    int xB = bar_index + 12
    crtHiLine  := line.new(xA, crtHi,  xB, crtHi,  color=color.new(#B39DDB, 20), width=1, style=line.style_solid)
    crtLoLine  := line.new(xA, crtLo,  xB, crtLo,  color=color.new(#B39DDB, 20), width=1, style=line.style_solid)
    crtMidLine := line.new(xA, crtMid, xB, crtMid, color=color.new(#B39DDB, 60), width=1, style=line.style_dotted)

// ═══════════════════════════════════════════════════════════════════════════════
// v4.7 SILVER BULLET — three one-hour windows, and the entry the model uses
// ─────────────────────────────────────────────────────────────────────────────
// 03:00-04:00, 10:00-11:00 and 14:00-15:00 New York time. The model's entry is
// the retrace into a fair value gap formed INSIDE the window, which is why the
// restrict mode also requires the FVG trigger rather than accepting whatever
// setup happens to occur during the hour.
//
// It is a HARD time filter and the cost is arithmetic: three hours out of
// twenty-four, and more once the FVG requirement binds on top. Highlight mode
// exists so the windows can be looked at before they are allowed to gate
// anything — if your setups do not visibly cluster there, restricting to them
// is throwing trades away for a reason that is not present in your data.
// ═══════════════════════════════════════════════════════════════════════════════
sbW1 = not na(time(timeframe.period, "0300-0400:23456", i_sbTz))
sbW2 = not na(time(timeframe.period, "1000-1100:23456", i_sbTz))
sbW3 = not na(time(timeframe.period, "1400-1500:23456", i_sbTz))
inSilverBullet = sbW1 or sbW2 or sbW3
sbActive  = i_sbMode != "Off"
sbRestrict = i_sbMode == "Restrict signals to windows"
bgcolor(sbActive and inSilverBullet ? color.new(#B39DDB, 92) : na, title="Silver Bullet Window")

// ═══════════════════════════════════════════════════════════════════════════════
// v4.0 BAND REJECTION TRIGGER""",
"crt engine")

# ── ADMIT CRT INTO THE TRIGGER SET ────────────────────────────────────────
sub1("""buyTrigPoc   = pocBull
sellTrigPoc  = pocBear""",
"""buyTrigPoc   = pocBull
sellTrigPoc  = pocBear
buyTrigCrt   = crtBull
sellTrigCrt  = crtBear""",
"admit crt")

sub1("""buyTrigger  = mssUp   or buyTrigFvg  or buyTrigSweep  or buyTrigBand  or buyTrigPoc
sellTrigger = mssDown or sellTrigFvg or sellTrigSweep or sellTrigBand or sellTrigPoc""",
"""buyTrigger  = mssUp   or buyTrigFvg  or buyTrigSweep  or buyTrigBand  or buyTrigPoc  or buyTrigCrt
sellTrigger = mssDown or sellTrigFvg or sellTrigSweep or sellTrigBand or sellTrigPoc or sellTrigCrt""",
"crt in trigger set")

# CRT sits ABOVE the ordinary sweep: an HTF candle boundary is a more precisely
# defined level than a chart-timeframe pivot.
sub1('''buySel  = buyTrigSweep  ? "SWEEP" : buyTrigBand  ? "BAND" : buyTrigFvg  ? "FVG" : buyTrigPoc  ? "POC" : mssUp   ? "MSS" : ""
sellSel = sellTrigSweep ? "SWEEP" : sellTrigBand ? "BAND" : sellTrigFvg ? "FVG" : sellTrigPoc ? "POC" : mssDown ? "MSS" : ""''',
'''// v4.7: CRT is placed FIRST. Its invalidation — the bar that ran a completed
// higher-timeframe candle's boundary — is the most precisely defined level of
// the six, which is the ordering principle v4.2 established.
buySel  = buyTrigCrt  ? "CRT" : buyTrigSweep  ? "SWEEP" : buyTrigBand  ? "BAND" : buyTrigFvg  ? "FVG" : buyTrigPoc  ? "POC" : mssUp   ? "MSS" : ""
sellSel = sellTrigCrt ? "CRT" : sellTrigSweep ? "SWEEP" : sellTrigBand ? "BAND" : sellTrigFvg ? "FVG" : sellTrigPoc ? "POC" : mssDown ? "MSS" : ""''',
"crt selection order")

sub1("""buyTrigCount  = (mssUp   ? 1 : 0) + (buyTrigFvg  ? 1 : 0) + (buyTrigSweep  ? 1 : 0) + (buyTrigBand  ? 1 : 0) + (buyTrigPoc  ? 1 : 0)
sellTrigCount = (mssDown ? 1 : 0) + (sellTrigFvg ? 1 : 0) + (sellTrigSweep ? 1 : 0) + (sellTrigBand ? 1 : 0) + (sellTrigPoc ? 1 : 0)""",
"""buyTrigCount  = (mssUp   ? 1 : 0) + (buyTrigFvg  ? 1 : 0) + (buyTrigSweep  ? 1 : 0) + (buyTrigBand  ? 1 : 0) + (buyTrigPoc  ? 1 : 0) + (buyTrigCrt  ? 1 : 0)
sellTrigCount = (mssDown ? 1 : 0) + (sellTrigFvg ? 1 : 0) + (sellTrigSweep ? 1 : 0) + (sellTrigBand ? 1 : 0) + (sellTrigPoc ? 1 : 0) + (sellTrigCrt ? 1 : 0)""",
"crt trigger count")

# chase reference and stop anchor
sub1(''' : buySel  == "POC" and not na(pocBullLvl) ? pocBullLvl : buySel  == "MSS" ? lastPH : na''',
     ''' : buySel  == "POC" and not na(pocBullLvl) ? pocBullLvl : buySel  == "CRT" and not na(crtBullLvl) ? crtBullLvl : buySel  == "MSS" ? lastPH : na''',
     "crt chase buy")
sub1(''' : sellSel == "POC" and not na(pocBearLvl) ? pocBearLvl : sellSel == "MSS" ? lastPL : na''',
     ''' : sellSel == "POC" and not na(pocBearLvl) ? pocBearLvl : sellSel == "CRT" and not na(crtBearLvl) ? crtBearLvl : sellSel == "MSS" ? lastPL : na''',
     "crt chase sell")
sub1(''' : buySel  == "POC" and not na(pocBullLvl) ? pocBullLvl : lastPL''',
     ''' : buySel  == "POC" and not na(pocBullLvl) ? pocBullLvl : buySel  == "CRT" and not na(crtBullLow) ? crtBullLow : lastPL''',
     "crt anchor buy")
sub1(''' : sellSel == "POC" and not na(pocBearLvl) ? pocBearLvl : lastPH''',
     ''' : sellSel == "POC" and not na(pocBearLvl) ? pocBearLvl : sellSel == "CRT" and not na(crtBearHigh) ? crtBearHigh : lastPH''',
     "crt anchor sell")

# ── SILVER BULLET GATE ────────────────────────────────────────────────────
sub1("""nonRevOkBuy  = gateOff or (gateLegBuy  and revTrendOk and revHtfOkBuy  and revCntrOkBuy)""",
"""// v4.7: the Silver Bullet gate. In restrict mode a signal must fall inside one
// of the three windows AND (by default) come from an FVG — the model's entry is
// the retrace into a gap formed in the window, not any setup that happens to
// occur during the hour.
sbOkBuy  = not sbRestrict or (inSilverBullet and (not i_sbFvgOnly or buyTrigFvg))
sbOkSell = not sbRestrict or (inSilverBullet and (not i_sbFvgOnly or sellTrigFvg))

nonRevOkBuy  = gateOff or (gateLegBuy  and revTrendOk and revHtfOkBuy  and revCntrOkBuy)""",
"silver bullet gate")

sub1("""and inSession and regimeOk and nonRevOkBuy
rawSellPre""",
     """and inSession and regimeOk and nonRevOkBuy and sbOkBuy
rawSellPre""", "sb gate buy")
sub1("""and inSession and regimeOk and nonRevOkSell""",
     """and inSession and regimeOk and nonRevOkSell and sbOkSell""", "sb gate sell")

sub1("""    r += nonRevOkBuy ? "" : "reversal \"""",
     """    r += nonRevOkBuy ? "" : "reversal "
    r += sbOkBuy ? "" : "sb \"""", "sb block buy")
sub1("""    r += nonRevOkSell ? "" : "reversal \"""",
     """    r += nonRevOkSell ? "" : "reversal "
    r += sbOkSell ? "" : "sb \"""", "sb block sell")

# trigger memory
sub1("or pocBullEvent or pocBearEvent",
     "or pocBullEvent or pocBearEvent or crtBullEvent or crtBearEvent",
     "crt in trigger memory")

io.open(P, "w", encoding="utf-8").write(src)
print("\nwrote %d bytes" % len(src))
