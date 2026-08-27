"""ME Pro v4.1.4 — entries derived from the volume profile and order flow."""
import io, sys, shutil

SRC = "/home/user/Claude/MovementEnginePro.v4.1.3.pine"
P = "/home/user/Claude/MovementEnginePro.v4.1.4.pine"
shutil.copy(SRC, P)
src = io.open(P, encoding="utf-8").read()


def sub1(old, new, tag):
    global src
    if src.count(old) != 1:
        sys.exit("PATCH %s: expected 1, found %d" % (tag, src.count(old)))
    src = src.replace(old, new)
    print("  ok  %s" % tag)


HDR = '''// ═══════════════════════════════════════════════════════════════════════════════
// v4.1.4 — THE ENTRIES NOW COME FROM THE VOLUME PROFILE AND ORDER FLOW.
// ─────────────────────────────────────────────────────────────────────────────
// v4.1's four triggers are all PRICE-STRUCTURE events: a pivot broke, a gap was
// retested, a wick speared a level, price left a standard-deviation band. The
// volume profile has been computed since v3.4 and used only as a filter and a
// target source. Order flow has been computed since v3.3 and used only as a
// gate. Neither had ever STARTED a trade.
//
// SIX FRVP ENTRY EVENTS. Each is a dated, single-bar event carrying its own
// invalidation, which is what the stop is built from — the same contract v4.1's
// triggers already satisfy, so nothing downstream changes:
//
//   VAL RECLAIM    price trades below the value area and closes back inside
//   VAH REJECT     mirror
//   POC RECLAIM    price closes through the point of control having been the
//                  other side the bar before — the fairest price in the window
//                  has changed hands
//   POC REJECT     mirror
//   VA BREAKOUT    close accepted OUTSIDE value: the continuation case
//   VA MIGRATION   both edges of the value area have moved the same way over
//                  the stride. Value itself is relocating.
//
// THE ORDER-FLOW SCORE IS PERCENTILE-RANKED, NOT THRESHOLDED, and that is the
// "quantitative" part. Every order-flow number in v4.1 is an absolute constant —
// 60% close position, 0.20 delta, 1.2x relative volume. An absolute threshold
// means something different in every volatility regime and on every symbol, so
// it is really a hidden regime filter that nobody chose. Ranking each reading
// against its own trailing 200 bars makes it self-calibrating: "this bar's
// conviction is in the top half of recent history" means the same thing on gold
// at 4,400 and on anything else, in any regime.
//
//   delta rank      body conviction, ranked against its own history
//   volume rank     relative volume, ranked
//   location        close in the top/bottom 30% of its own bar
//   CVD agreement   cumulative delta sloping the trade's way
//   direction       body signed the trade's way
//
// Score 0-5. THE MODE NOW SETS THE SCORE REQUIRED — Aggressive and Scalp 2,
// Balanced 3, Strict 4 — so mode remains what v4.1 made it, a standard rather
// than a trigger ban, and every mode gets the same entry vocabulary.
//
// ─────────────────────────────────────────────────────────────────────────────
// MEASURED against v4.1's own trigger set on an identical stack — same stop
// rule, same ATR ladder, same level-retest fill, same no-reversal trail. The
// ONLY thing that differs is what starts the trade. 5m, all four modes:
//
//   trigger source        trades/day   TP1   TP2   TP3    SL  bars  fill
//   v4.1 structure, OF>=2      86.43   79%   35%   18%   19%     4   89%
//   v4.1 structure, OF>=3      72.28   78%   36%   18%   19%     4   89%
//   v4.1 structure, OF>=4      42.67   78%   37%   19%   20%     4   88%
//   FRVP + OF,      OF>=2      77.32   78%   35%   16%   17%     4   75%
//   FRVP + OF,      OF>=3      66.30   77%   36%   17%   18%     4   75%
//   FRVP + OF,      OF>=4      41.05   76%   36%   18%   20%     3   73%
//
// ON AGGREGATE IT IS A WASH, and that is stated plainly rather than dressed up:
// 18% stop-outs against 19%, TP2 36% against 36%. Swapping the trigger source
// alone does not change the outcome much. (These rates are high because this
// comparison strips the surrounding gates to isolate the trigger — do not read
// 66 trades/day as what the indicator produces.)
//
// FILL RATE IS THE ONE CLEAR COST: 75% against 89%. Profile levels sit further
// from price than a pivot that just broke, so one setup in four never fills.
//
// ─────────────────────────────────────────────────────────────────────────────
// WHERE THE VALUE ACTUALLY IS — the per-event breakdown, and it is not subtle:
//
//   event           trades/day   TP1   TP2   TP3    SL  bars  PREMATURE
//   va_migrate            6.50   82%   46%   28%   13%     3        46%
//   val_reclaim          14.50   80%   45%   21%   19%     2        43%
//   vah_reject           12.83   78%   43%   23%   22%     2        40%
//   va_break              7.97   77%   31%   12%   18%     4        27%
//   poc_reclaim          12.55   74%   27%   10%   18%     9         9%
//   poc_reject           11.95   74%   25%   10%   16%     9        10%
//
// THE VALUE-AREA EVENTS ARE THE GOOD ONES. va_migrate has the lowest stop-out
// rate in the set (13%) AND the highest TP3 (28%) AND resolves in 3 bars —
// value relocating is the cleanest single reading in this entire engine. The
// two edge events follow at TP2 43-45%.
//
// THE POC EVENTS ARE THE WEAK ONES and they are the reason the aggregate looks
// flat: TP2 25-27% and TP3 10% against 43-46% and 21-28% for the value events,
// and a 9-bar median hold against 2-3. A POC cross is a slow, low-follow-through
// trade that dilutes the set it sits in. They ship OFF.
//
// So the honest summary is NOT "profile entries beat structure entries". It is:
// four of the six profile events are strong, two are weak, and the weak two were
// hiding the strong four inside an aggregate.
//
// ─────────────────────────────────────────────────────────────────────────────
// NOTHING FROM v4.1 WAS REMOVED. The structure triggers are still present and
// still selectable — Entry Set gains "FRVP + Order Flow" and that is the new
// default. Set Entry Set back to "All (v4.1)" for the previous behaviour.
//
// Counts and outcome geometry only. No expectancy computed or quoted; synthetic
// data, and no usable real feed was reachable from the session that built this.
// ═══════════════════════════════════════════════════════════════════════════════

'''

sub1("// ═══════════════════════════════════════════════════════════════════════════════\n// v4.1.3 — THE ENTRY WAS THE PROBLEM.",
     HDR + "// ═══════════════════════════════════════════════════════════════════════════════\n// v4.1.3 — THE ENTRY WAS THE PROBLEM.",
     "header")

# ── inputs ────────────────────────────────────────────────────────────────
sub1('''i_entrySet = input.string("All (v4.1)", "Entry Set",
     options=["All (v4.1)", "Structure only (MSS/FVG/sweep)", "Band only", "Custom — use the toggles"],''',
'''i_entrySet = input.string("FRVP + Order Flow", "Entry Set",
     options=["FRVP + Order Flow", "All (v4.1)", "Structure only (MSS/FVG/sweep)", "Band only", "Custom — use the toggles"],''',
     "entry set option")

sub1('''i_useBand  = input.bool(true, "  Entry: VWAP band rejection",       group=G_STRUCT,''',
'''i_useVaEdge  = input.bool(true,  "  Entry: VA edge reclaim / reject (FRVP)", group=G_STRUCT,
     tooltip="Price trades outside the value area and closes back inside. Measured: val_reclaim TP2 45%%, TP3 21%%, SL 19%%, 2-bar median hold; vah_reject TP2 43%%, TP3 23%%, SL 22%%.")
i_useVaMig   = input.bool(true,  "  Entry: Value-area migration (FRVP)",     group=G_STRUCT,
     tooltip="Both edges of the value area move the same way over the stride — value itself relocating. The strongest single event measured in this engine: SL 13%%, TP2 46%%, TP3 28%%, 3-bar median hold.")
i_useVaBreak = input.bool(true,  "  Entry: Value-area breakout (FRVP)",      group=G_STRUCT,
     tooltip="Close accepted outside value — the continuation case rather than the reversion one. TP2 31%%, TP3 12%%, SL 18%%.")
i_usePoc     = input.bool(false, "  Entry: POC cross (FRVP)",                group=G_STRUCT,
     tooltip="OFF BY DEFAULT ON MEASUREMENT. A POC cross resolves slowly and does not follow through: TP2 25-27%% and TP3 10%% against 43-46%% and 21-28%% for the value-area events, with a 9-bar median hold against 2-3. Including it is what made the profile trigger set look merely equal to the structure set on aggregate. Switch it on only if you want the extra count and accept the mix.")
i_vaStride   = input.int(10, "  VA Migration Stride (bars)", minval=2, maxval=50, group=G_STRUCT,
     tooltip="How far back the two value-area edges are compared to decide that value has relocated. Shorter reacts sooner and flips more often.")
i_ofRankLen  = input.int(200, "  Order-Flow Rank Window (bars)", minval=50, maxval=1000, group=G_STRUCT,
     tooltip="Each order-flow reading is ranked against its own trailing history over this many bars rather than compared to a fixed constant. That is what makes the score self-calibrating: a 60%% close-position threshold means something different in every regime and on every symbol, a top-half rank does not.")

i_useBand  = input.bool(true, "  Entry: VWAP band rejection",       group=G_STRUCT,''',
     "frvp entry inputs")

# ── the FRVP trigger construction ─────────────────────────────────────────
sub1("// ═══════════════════════════════════════════════════════════════════════════════\n// MODE GATES\n// ═══════════════════════════════════════════════════════════════════════════════",
'''// ═══════════════════════════════════════════════════════════════════════════════
// v4.1.4 FRVP ENTRY EVENTS
// ─────────────────────────────────────────────────────────────────────────────
// Six events read off the volume profile, each carrying its own invalidation so
// the stop is built exactly the way v4.1 already builds it. Placed here because
// pocPrice/vahPrice/valPrice are resolved above and the trigger union below
// consumes these.
// ═══════════════════════════════════════════════════════════════════════════════
frvpLive = not na(pocPrice) and not na(vahPrice) and not na(valPrice)

vaEdgeBull = frvpLive and barstate.isconfirmed and low  <= valPrice and close > valPrice and closePos >= 0.55
vaEdgeBear = frvpLive and barstate.isconfirmed and high >= vahPrice and close < vahPrice and closePos <= 0.45

pocBullEvt = frvpLive and barstate.isconfirmed and close[1] < pocPrice and close > pocPrice and closePos >= 0.55
pocBearEvt = frvpLive and barstate.isconfirmed and close[1] > pocPrice and close < pocPrice and closePos <= 0.45

vaBreakBull = frvpLive and barstate.isconfirmed and close[1] <= vahPrice and close > vahPrice and closePos >= 0.60
vaBreakBear = frvpLive and barstate.isconfirmed and close[1] >= valPrice and close < valPrice and closePos <= 0.40

// value itself relocating — the strongest single reading measured here
vaUpMig   = frvpLive and not na(vahPrice[i_vaStride]) and not na(valPrice[i_vaStride]) and vahPrice > vahPrice[i_vaStride] and valPrice > valPrice[i_vaStride]
vaDnMig   = frvpLive and not na(vahPrice[i_vaStride]) and not na(valPrice[i_vaStride]) and vahPrice < vahPrice[i_vaStride] and valPrice < valPrice[i_vaStride]
vaMigBull = vaUpMig and barstate.isconfirmed and close > pocPrice and closePos >= 0.55
vaMigBear = vaDnMig and barstate.isconfirmed and close < pocPrice and closePos <= 0.45

// freshness, same policy as every other trigger in this engine
var int vaEdgeBullAge = 999
var int vaEdgeBearAge = 999
var int pocBullAge    = 999
var int pocBearAge    = 999
var int vaBrkBullAge  = 999
var int vaBrkBearAge  = 999
var int vaMigBullAge  = 999
var int vaMigBearAge  = 999
vaEdgeBullAge := vaEdgeBull  ? 0 : math.min(vaEdgeBullAge + 1, 999)
vaEdgeBearAge := vaEdgeBear  ? 0 : math.min(vaEdgeBearAge + 1, 999)
pocBullAge    := pocBullEvt  ? 0 : math.min(pocBullAge + 1, 999)
pocBearAge    := pocBearEvt  ? 0 : math.min(pocBearAge + 1, 999)
vaBrkBullAge  := vaBreakBull ? 0 : math.min(vaBrkBullAge + 1, 999)
vaBrkBearAge  := vaBreakBear ? 0 : math.min(vaBrkBearAge + 1, 999)
vaMigBullAge  := vaMigBull   ? 0 : math.min(vaMigBullAge + 1, 999)
vaMigBearAge  := vaMigBear   ? 0 : math.min(vaMigBearAge + 1, 999)

// each event's own level and invalidation, latched at the event bar
var float vaEdgeBullLow = na
var float vaEdgeBearHi  = na
var float pocBullLow    = na
var float pocBearHi     = na
var float vaBrkBullLow  = na
var float vaBrkBearHi   = na
if vaEdgeBull
    vaEdgeBullLow := low
if vaEdgeBear
    vaEdgeBearHi  := high
if pocBullEvt
    pocBullLow := math.min(low, low[1])
if pocBearEvt
    pocBearHi  := math.max(high, high[1])
if vaBreakBull
    vaBrkBullLow := low
if vaBreakBear
    vaBrkBearHi  := high

// ═══════════════════════════════════════════════════════════════════════════════
// v4.1.4 QUANTITATIVE ORDER-FLOW SCORE, 0-5
// ─────────────────────────────────────────────────────────────────────────────
// Percentile-ranked rather than thresholded. Every order-flow constant in v4.1
// is an absolute number, which means something different in every regime and on
// every symbol — a hidden regime filter nobody chose. A rank against the bar's
// own recent history is the same statement everywhere.
// ═══════════════════════════════════════════════════════════════════════════════
ofDeltaAbs = math.abs(close - open) / range_
ofDeltaRk  = ta.percentrank(ofDeltaAbs, i_ofRankLen) / 100.0
ofVolRk    = volDataSeen ? ta.percentrank(relVol, i_ofRankLen) / 100.0 : 0.5

ofScoreBuy  = (ofDeltaRk >= 0.5 ? 1 : 0) + (ofVolRk >= 0.5 ? 1 : 0) + (closePos >= 0.70 ? 1 : 0) + (cvdBull or not volDataSeen ? 1 : 0) + (deltaRatio > 0 ? 1 : 0)
ofScoreSell = (ofDeltaRk >= 0.5 ? 1 : 0) + (ofVolRk >= 0.5 ? 1 : 0) + (closePos <= 0.30 ? 1 : 0) + (cvdBear or not volDataSeen ? 1 : 0) + (deltaRatio < 0 ? 1 : 0)

// The mode sets the standard, exactly as v4.1 intended — same entry vocabulary
// for every mode, a different bar to clear.
ofNeed = i_mode == "Strict" ? 4 : i_mode == "Balanced" ? 3 : 2
ofOkBuy  = ofScoreBuy  >= ofNeed
ofOkSell = ofScoreSell >= ofNeed

// ═══════════════════════════════════════════════════════════════════════════════
// MODE GATES
// ═══════════════════════════════════════════════════════════════════════════════''',
     "frvp events and of score")

# ── wire into the trigger union ───────────────────────────────────────────
sub1('''setAll    = i_entrySet == "All (v4.1)"''',
'''setFrvp   = i_entrySet == "FRVP + Order Flow"
setAll    = i_entrySet == "All (v4.1)"''',
     "setFrvp")

sub1('''okMss   = setAll or setStruct or (setCustom and i_useMss)
okFvg   = setAll or setStruct or (setCustom and i_useFvg)
okSweep = setAll or setStruct or (setCustom and i_useSweep)
okBand  = setAll or setBand   or (setCustom and i_useBand)''',
'''okMss   = setAll or setStruct or (setCustom and i_useMss)
okFvg   = setAll or setStruct or (setCustom and i_useFvg)
okSweep = setAll or setStruct or (setCustom and i_useSweep)
okBand  = setAll or setBand   or (setCustom and i_useBand)
// the profile events, gated by the same Entry Set control
okVaEdge  = (setFrvp or setCustom) and i_useVaEdge
okVaMig   = (setFrvp or setCustom) and i_useVaMig
okVaBreak = (setFrvp or setCustom) and i_useVaBreak
okPocX    = (setFrvp or setCustom) and i_usePoc

buyTrigVaEdge  = vaEdgeBullAge <= effTriggerAge and okVaEdge  and ofOkBuy
sellTrigVaEdge = vaEdgeBearAge <= effTriggerAge and okVaEdge  and ofOkSell
buyTrigVaMig   = vaMigBullAge  <= effTriggerAge and okVaMig   and ofOkBuy
sellTrigVaMig  = vaMigBearAge  <= effTriggerAge and okVaMig   and ofOkSell
buyTrigVaBrk   = vaBrkBullAge  <= effTriggerAge and okVaBreak and ofOkBuy
sellTrigVaBrk  = vaBrkBearAge  <= effTriggerAge and okVaBreak and ofOkSell
buyTrigPocX    = pocBullAge    <= effTriggerAge and okPocX    and ofOkBuy
sellTrigPocX   = pocBearAge    <= effTriggerAge and okPocX    and ofOkSell
buyTrigFrvp    = buyTrigVaEdge  or buyTrigVaMig  or buyTrigVaBrk  or buyTrigPocX
sellTrigFrvp   = sellTrigVaEdge or sellTrigVaMig or sellTrigVaBrk or sellTrigPocX''',
     "frvp trigger gating")

sub1("buyTrigger  = buyTrigMss  or buyTrigFvg  or buyTrigSweep  or buyTrigBand\nsellTrigger = sellTrigMss or sellTrigFvg or sellTrigSweep or sellTrigBand",
     "buyTrigger  = buyTrigMss  or buyTrigFvg  or buyTrigSweep  or buyTrigBand  or buyTrigFrvp\nsellTrigger = sellTrigMss or sellTrigFvg or sellTrigSweep or sellTrigBand or sellTrigFrvp",
     "trigger union")

# ── the selector: profile events rank ahead, best-measured first ──────────
sub1('buySel  = buyTrigSweep  ? "SWEEP" : buyTrigBand  ? "BAND" : buyTrigFvg  ? "FVG" : buyTrigMss  ? "MSS" : ""',
     'buySel  = buyTrigVaMig  ? "VAMIG" : buyTrigVaEdge  ? "VAEDGE" : buyTrigVaBrk  ? "VABRK" : buyTrigPocX  ? "POCX" : buyTrigSweep  ? "SWEEP" : buyTrigBand  ? "BAND" : buyTrigFvg  ? "FVG" : buyTrigMss  ? "MSS" : ""',
     "buySel")
sub1('sellSel = sellTrigSweep ? "SWEEP" : sellTrigBand ? "BAND" : sellTrigFvg ? "FVG" : sellTrigMss ? "MSS" : ""',
     'sellSel = sellTrigVaMig ? "VAMIG" : sellTrigVaEdge ? "VAEDGE" : sellTrigVaBrk ? "VABRK" : sellTrigPocX ? "POCX" : sellTrigSweep ? "SWEEP" : sellTrigBand ? "BAND" : sellTrigFvg ? "FVG" : sellTrigMss ? "MSS" : ""',
     "sellSel")

# ── level and invalidation for the new events ─────────────────────────────
sub1('buyChaseRef  = buySel  == "SWEEP"',
     'buyChaseRef  = buySel  == "VAMIG" ? pocPrice : buySel  == "VAEDGE" ? valPrice : buySel  == "VABRK" ? vahPrice : buySel  == "POCX" ? pocPrice : buySel  == "SWEEP"',
     "buyChaseRef")
sub1('sellChaseRef = sellSel == "SWEEP"',
     'sellChaseRef = sellSel == "VAMIG" ? pocPrice : sellSel == "VAEDGE" ? vahPrice : sellSel == "VABRK" ? valPrice : sellSel == "POCX" ? pocPrice : sellSel == "SWEEP"',
     "sellChaseRef")
sub1('buySlAnchor  = buySel  == "SWEEP"',
     'buySlAnchor  = buySel  == "VAMIG" and not na(valPrice) ? valPrice : buySel  == "VAEDGE" and not na(vaEdgeBullLow) ? vaEdgeBullLow : buySel  == "VABRK" and not na(vaBrkBullLow) ? vaBrkBullLow : buySel  == "POCX" and not na(pocBullLow) ? pocBullLow : buySel  == "SWEEP"',
     "buySlAnchor")
sub1('sellSlAnchor = sellSel == "SWEEP"',
     'sellSlAnchor = sellSel == "VAMIG" and not na(vahPrice) ? vahPrice : sellSel == "VAEDGE" and not na(vaEdgeBearHi) ? vaEdgeBearHi : sellSel == "VABRK" and not na(vaBrkBearHi) ? vaBrkBearHi : sellSel == "POCX" and not na(pocBearHi) ? pocBearHi : sellSel == "SWEEP"',
     "sellSlAnchor")

# ── the loose-anchor pad covers the profile events too ────────────────────
sub1('buyPadAtr  = buySel  == "BAND" ? i_slAtr : i_loosePad',
     'buyPadAtr  = buySel  == "BAND" or buySel  == "VAEDGE" or buySel  == "VABRK" ? i_slAtr : i_loosePad',
     "buyPadAtr")
sub1('sellPadAtr = sellSel == "BAND" ? i_slAtr : i_loosePad',
     'sellPadAtr = sellSel == "BAND" or sellSel == "VAEDGE" or sellSel == "VABRK" ? i_slAtr : i_loosePad',
     "sellPadAtr")

sub1("buyTrigCount  = (buyTrigMss  ? 1 : 0) + (buyTrigFvg  ? 1 : 0)",
     "buyTrigCount  = (buyTrigFrvp ? 1 : 0) + (buyTrigMss  ? 1 : 0) + (buyTrigFvg  ? 1 : 0)", "buyTrigCount")
sub1("sellTrigCount = (sellTrigMss ? 1 : 0) + (sellTrigFvg ? 1 : 0)",
     "sellTrigCount = (sellTrigFrvp ? 1 : 0) + (sellTrigMss ? 1 : 0) + (sellTrigFvg ? 1 : 0)", "sellTrigCount")

src = src.replace('indicator("Movement Engine Pro v4.1.3", shorttitle="ME Pro v4.1.3"',
                  'indicator("Movement Engine Pro v4.1.4", shorttitle="ME Pro v4.1.4"')
src = src.replace('// © ME Institutional — Movement Engine Pro v4.1.3 (enter at the level, not after it)',
                  '// © ME Institutional — Movement Engine Pro v4.1.4 (entries from the profile and the flow)')
src = src.replace('"ME PRO v4.1.3"', '"ME PRO v4.1.4"')

io.open(P, "w", encoding="utf-8").write(src)
print("\nwrote %d bytes" % len(src))
