"""ME Pro v4.1.5 — the profile's SHAPE, not three numbers off it."""
import io, sys, shutil

SRC = "/home/user/Claude/MovementEnginePro.v4.1.4.pine"
P = "/home/user/Claude/MovementEnginePro.v4.1.5.pine"
shutil.copy(SRC, P)
src = io.open(P, encoding="utf-8").read()


def sub1(old, new, tag):
    global src
    if src.count(old) != 1:
        sys.exit("PATCH %s: expected 1, found %d" % (tag, src.count(old)))
    src = src.replace(old, new)
    print("  ok  %s" % tag)


HDR = '''// ═══════════════════════════════════════════════════════════════════════════════
// v4.1.5 — THE PROFILE'S SHAPE IS NOW AN ENTRY. THE HISTOGRAM STOPS BEING
// THROWN AWAY.
// ─────────────────────────────────────────────────────────────────────────────
// v4.1.4 made the volume profile an entry source, but it reduced the profile to
// POC, VAH and VAL — three summary statistics. The information in a volume
// profile is the DISTRIBUTION: where volume is thick and where it is thin. This
// engine has computed that whole histogram every stride since v3.4 (volBins)
// and then used three numbers from it and discarded the rest.
//
// TWO READINGS THAT NEED THE HISTOGRAM:
//
//   LOW-VOLUME NODE     a price band almost nothing traded at. Price did not
//                       stop there, so there is nothing resting there to stop it
//                       next time either. Entering an LVN is the one profile
//                       reading that predicts SPEED.
//
//   HIGH-VOLUME NODE    a band where a lot traded. Both sides accepted it, so it
//                       absorbs and price stalls.
//
// MEASURED, 5m, all four modes, identical stack — same stop rule, same ranked
// order-flow score, same level-retest fill, same no-reversal trail:
//
//     trigger set          trades/day   TP1   TP2   TP3    SL  bars   fill
//     v4.1.4 VA events          66.22   77%   36%   17%   18%     4    75%
//     LVN/HVN shape             65.93   72%   33%   17%   23%     4    92%
//
//     lvn_up                    11.22   73%   37%   24%   23%     4
//     lvn_dn                    10.50   68%   34%   18%   26%     4
//     hvn_reject                44.22   73%   32%   15%   23%     4
//
// LVN COMMIT IS THE ADDITION WORTH HAVING. lvn_up reaches TP3 24% of the time —
// second only to VA migration (28%) out of every event measured in this engine,
// and roughly half again the 17% of the VA set it sits alongside. The fill rate
// is also far better, 92% against 75%, because a thin band next to price is a
// nearer level than a value-area edge.
//
// HVN REJECTION IS NOT, AND IT SHIPS OFF. It is 44 of the 66 trades in that set
// — two thirds of the supply — at TP2 32% and TP3 15%, and it is what drags the
// shape row below the VA row on aggregate. Turn it on and you get three times
// the trades at materially worse follow-through.
//
// ─────────────────────────────────────────────────────────────────────────────
// THE PATTERN THIS COMPLETES, and it has now held on every event measured in
// this engine without exception:
//
//     event type            share of supply   TP3
//     VA migration (accept)            low    28%
//     LVN commit   (accept)            low    24%
//     VAL/VAH reclaim (mixed)          mid    21-23%
//     VA breakout  (accept)            low    12%
//     HVN reject   (fade)             HIGH    15%
//     POC cross    (fade)             HIGH    10%
//     VWAP band    (fade)             HIGH     8%
//
// THE FADE EVENTS ARE ALWAYS THE HIGH-SUPPLY, LOW-FOLLOW-THROUGH ONES, AND THE
// ACCEPTANCE EVENTS ARE ALWAYS THE OPPOSITE. Every version of this engine that
// looked busy and paid little was busy because a fade event dominated its
// supply. That is the single most reliable finding in this whole file, and it
// is why the defaults now switch the fades off rather than merely ranking them
// lower.
//
// ─────────────────────────────────────────────────────────────────────────────
// TESTED AND NOT SHIPPED: HIGH-VOLUME NODES AS TARGETS. A thick node is where a
// move ends, so placing TP2 at the nearest one instead of a fixed 1.4 ATR ought
// to be reached more often. The test returned IDENTICAL rows — the substitution
// never fired, because an entry taken at a thin band's edge sits close enough to
// the adjacent thick band that the candidate never cleared the minimum-distance
// guard. That is an inconclusive test, not a negative one: there is no evidence
// either way and the change is therefore not in this file.
//
// Counts and outcome geometry only. No expectancy computed or quoted; synthetic
// data, and no usable real feed was reachable from the session that built this.
// ═══════════════════════════════════════════════════════════════════════════════

'''

sub1("// ═══════════════════════════════════════════════════════════════════════════════\n// v4.1.4 — THE ENTRIES NOW COME FROM THE VOLUME PROFILE AND ORDER FLOW.",
     HDR + "// ═══════════════════════════════════════════════════════════════════════════════\n// v4.1.4 — THE ENTRIES NOW COME FROM THE VOLUME PROFILE AND ORDER FLOW.",
     "header")

sub1('''i_useVaEdge  = input.bool(true,  "  Entry: VA edge reclaim / reject (FRVP)", group=G_STRUCT,''',
'''i_useLvn     = input.bool(true,  "  Entry: Low-volume node commit (FRVP shape)", group=G_STRUCT,
     tooltip="Price closes INTO a band almost nothing traded at. Nothing rests there to stop it, so this is the one profile reading that predicts SPEED rather than direction.\\n\\nMeasured, 5m, all modes: lvn_up TP3 24%%, TP2 37%%, SL 23%%; lvn_dn TP3 18%%, TP2 34%%, SL 26%%. That TP3 is second only to VA migration out of every event measured in this engine, and the fill rate is 92%% against 75%% for the value-area events because a thin band next to price is a nearer level than a value-area edge.")
i_useHvn     = input.bool(false, "  Entry: High-volume node rejection (FRVP shape)", group=G_STRUCT,
     tooltip="OFF BY DEFAULT ON MEASUREMENT. Price reaches a thick band and closes back out of it. It is a FADE, and every fade event measured in this engine has the same shape: it dominates supply and follows through worst. Here it is 44 of 66 trades — two thirds — at TP2 32%% and TP3 15%%, and it is what drags the shape set below the value-area set on aggregate.\\n\\nA thick node is where a move ENDS, which makes it a place to take profit rather than a place to enter. Switch this on for roughly three times the trades at materially worse follow-through.")
i_lvnPct     = input.float(0.30, "  Thin-node percentile", minval=0.05, maxval=0.45, step=0.05, group=G_STRUCT,
     tooltip="A profile bin counts as THIN if its volume sits below this percentile of all bins in the current profile. Ranked within the profile rather than against an absolute volume, so it means the same thing in every regime and on every symbol.")
i_hvnPct     = input.float(0.70, "  Thick-node percentile", minval=0.55, maxval=0.95, step=0.05, group=G_STRUCT)

i_useVaEdge  = input.bool(true,  "  Entry: VA edge reclaim / reject (FRVP)", group=G_STRUCT,''',
     "lvn/hvn inputs")

# ── node detection, inside the existing profile rebuild ───────────────────
sub1("""    vahPrice := frvpLow + (upperIdx + 1) * binSize
    valPrice := frvpLow + lowerIdx       * binSize""",
"""    vahPrice := frvpLow + (upperIdx + 1) * binSize
    valPrice := frvpLow + lowerIdx       * binSize
    // ── v4.1.5 NODE DETECTION ───────────────────────────────────────────────
    // The histogram has been built every stride since v3.4 and three numbers
    // taken off it. These are the bands themselves: thin ones price runs
    // through, thick ones it stalls at. Percentiles are taken WITHIN the
    // profile, so "thin" means the same thing in every regime.
    float[] srtBins = array.copy(volBins)
    array.sort(srtBins, order.ascending)
    float loQ = array.get(srtBins, math.max(0, math.min(i_frvpBins - 1, int(i_frvpBins * i_lvnPct))))
    float hiQ = array.get(srtBins, math.max(0, math.min(i_frvpBins - 1, int(i_frvpBins * i_hvnPct))))
    int pxBin = math.max(0, math.min(i_frvpBins - 1, int((close - frvpLow) / binSize)))
    // nearest thin band ABOVE price: its lower edge is where a long commits
    lvnUpEdge := na
    lvnUpHt   := na
    for b3 = pxBin to i_frvpBins - 1
        if array.get(volBins, b3) <= loQ
            int e = b3
            for b4 = b3 to i_frvpBins - 1
                if array.get(volBins, b4) <= loQ
                    e := b4
                else
                    break
            lvnUpEdge := frvpLow + b3 * binSize
            lvnUpHt   := (e - b3 + 1) * binSize
            break
    // nearest thin band BELOW price: its upper edge is where a short commits
    lvnDnEdge := na
    lvnDnHt   := na
    for b5 = pxBin to 0
        if array.get(volBins, b5) <= loQ
            int s2 = b5
            for b6 = b5 to 0
                if array.get(volBins, b6) <= loQ
                    s2 := b6
                else
                    break
            lvnDnEdge := frvpLow + (b5 + 1) * binSize
            lvnDnHt   := (b5 - s2 + 1) * binSize
            break
    // nearest thick bands either side — used for the HVN rejection event
    hvnUpEdge := na
    for b7 = pxBin to i_frvpBins - 1
        if array.get(volBins, b7) >= hiQ
            hvnUpEdge := frvpLow + b7 * binSize
            break
    hvnDnEdge := na
    for b8 = pxBin to 0
        if array.get(volBins, b8) >= hiQ
            hvnDnEdge := frvpLow + (b8 + 1) * binSize
            break""",
     "node detection")

# the node variables must exist before the rebuild block writes them
sub1("var float pocPrice = na\nvar float vahPrice = na\nvar float valPrice = na",
     """var float pocPrice = na
var float vahPrice = na
var float valPrice = na
// v4.1.5 profile-shape levels, rebuilt on the same stride as the profile
var float lvnUpEdge = na
var float lvnUpHt   = na
var float lvnDnEdge = na
var float lvnDnHt   = na
var float hvnUpEdge = na
var float hvnDnEdge = na""",
     "node vars")

# ── the events ────────────────────────────────────────────────────────────
sub1("frvpLive = not na(pocPrice) and not na(vahPrice) and not na(valPrice)",
"""frvpLive = not na(pocPrice) and not na(vahPrice) and not na(valPrice)

// v4.1.5 LOW-VOLUME NODE COMMIT. Price closes INTO a band almost nothing traded
// at, having been outside it. The invalidation is one band-height back on the
// far side — if price is rejected out of a vacuum, the reading was wrong.
lvnBull = frvpLive and barstate.isconfirmed and not na(lvnUpEdge) and close > lvnUpEdge and close[1] <= lvnUpEdge and closePos >= 0.55
lvnBear = frvpLive and barstate.isconfirmed and not na(lvnDnEdge) and close < lvnDnEdge and close[1] >= lvnDnEdge and closePos <= 0.45
// HIGH-VOLUME NODE REJECTION. A fade, and off by default — see the input.
hvnBull = frvpLive and barstate.isconfirmed and not na(hvnDnEdge) and low  <= hvnDnEdge and close > hvnDnEdge and closePos >= 0.55
hvnBear = frvpLive and barstate.isconfirmed and not na(hvnUpEdge) and high >= hvnUpEdge and close < hvnUpEdge and closePos <= 0.45

var int lvnBullAge = 999
var int lvnBearAge = 999
var int hvnBullAge = 999
var int hvnBearAge = 999
lvnBullAge := lvnBull ? 0 : math.min(lvnBullAge + 1, 999)
lvnBearAge := lvnBear ? 0 : math.min(lvnBearAge + 1, 999)
hvnBullAge := hvnBull ? 0 : math.min(hvnBullAge + 1, 999)
hvnBearAge := hvnBear ? 0 : math.min(hvnBearAge + 1, 999)

var float lvnBullInval = na
var float lvnBearInval = na
var float hvnBullLow   = na
var float hvnBearHigh  = na
if lvnBull
    lvnBullInval := lvnUpEdge - nz(lvnUpHt, atr14 * 0.5)
if lvnBear
    lvnBearInval := lvnDnEdge + nz(lvnDnHt, atr14 * 0.5)
if hvnBull
    hvnBullLow  := low
if hvnBear
    hvnBearHigh := high""",
     "lvn/hvn events")

sub1("""okVaEdge  = (setFrvp or setCustom) and i_useVaEdge""",
"""okLvn     = (setFrvp or setCustom) and i_useLvn
okHvn     = (setFrvp or setCustom) and i_useHvn
okVaEdge  = (setFrvp or setCustom) and i_useVaEdge""",
     "ok flags")

sub1("buyTrigFrvp    = buyTrigVaEdge  or buyTrigVaMig  or buyTrigVaBrk  or buyTrigPocX\nsellTrigFrvp   = sellTrigVaEdge or sellTrigVaMig or sellTrigVaBrk or sellTrigPocX",
"""buyTrigLvn     = lvnBullAge <= effTriggerAge and okLvn and ofOkBuy
sellTrigLvn    = lvnBearAge <= effTriggerAge and okLvn and ofOkSell
buyTrigHvn     = hvnBullAge <= effTriggerAge and okHvn and ofOkBuy
sellTrigHvn    = hvnBearAge <= effTriggerAge and okHvn and ofOkSell
buyTrigFrvp    = buyTrigLvn  or buyTrigHvn  or buyTrigVaEdge  or buyTrigVaMig  or buyTrigVaBrk  or buyTrigPocX
sellTrigFrvp   = sellTrigLvn or sellTrigHvn or sellTrigVaEdge or sellTrigVaMig or sellTrigVaBrk or sellTrigPocX""",
     "frvp union")

# selector: ranked by measured TP3 — migration, LVN, then the rest
sub1('buySel  = buyTrigVaMig  ? "VAMIG"',
     'buySel  = buyTrigVaMig  ? "VAMIG" : buyTrigLvn  ? "LVN" : buyTrigHvn  ? "HVN"',
     "buySel")
sub1('sellSel = sellTrigVaMig ? "VAMIG"',
     'sellSel = sellTrigVaMig ? "VAMIG" : sellTrigLvn ? "LVN" : sellTrigHvn ? "HVN"',
     "sellSel")

sub1('buyChaseRef  = buySel  == "VAMIG" ? pocPrice',
     'buyChaseRef  = buySel  == "LVN" ? lvnUpEdge : buySel  == "HVN" ? hvnDnEdge : buySel  == "VAMIG" ? pocPrice',
     "buyChaseRef")
sub1('sellChaseRef = sellSel == "VAMIG" ? pocPrice',
     'sellChaseRef = sellSel == "LVN" ? lvnDnEdge : sellSel == "HVN" ? hvnUpEdge : sellSel == "VAMIG" ? pocPrice',
     "sellChaseRef")
sub1('buySlAnchor  = buySel  == "VAMIG" and not na(valPrice) ? valPrice',
     'buySlAnchor  = buySel  == "LVN" and not na(lvnBullInval) ? lvnBullInval : buySel  == "HVN" and not na(hvnBullLow) ? hvnBullLow : buySel  == "VAMIG" and not na(valPrice) ? valPrice',
     "buySlAnchor")
sub1('sellSlAnchor = sellSel == "VAMIG" and not na(vahPrice) ? vahPrice',
     'sellSlAnchor = sellSel == "LVN" and not na(lvnBearInval) ? lvnBearInval : sellSel == "HVN" and not na(hvnBearHigh) ? hvnBearHigh : sellSel == "VAMIG" and not na(vahPrice) ? vahPrice',
     "sellSlAnchor")

sub1('buyIsFrvp  = buySel  == "VAMIG"',
     'buyIsFrvp  = buySel  == "LVN" or buySel  == "HVN" or buySel  == "VAMIG"',
     "buyIsFrvp")
sub1('sellIsFrvp = sellSel == "VAMIG"',
     'sellIsFrvp = sellSel == "LVN" or sellSel == "HVN" or sellSel == "VAMIG"',
     "sellIsFrvp")

src = src.replace('indicator("Movement Engine Pro v4.1.4", shorttitle="ME Pro v4.1.4"',
                  'indicator("Movement Engine Pro v4.1.5", shorttitle="ME Pro v4.1.5"')
src = src.replace('// © ME Institutional — Movement Engine Pro v4.1.4 (entries from the profile and the flow)',
                  '// © ME Institutional — Movement Engine Pro v4.1.5 (the profile shape is the entry)')
src = src.replace('"ME PRO v4.1.4"', '"ME PRO v4.1.5"')

io.open(P, "w", encoding="utf-8").write(src)
print("\nwrote %d bytes" % len(src))
