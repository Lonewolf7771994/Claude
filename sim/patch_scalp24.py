"""ME Scalp v2.4 — band width, confirmation, per-family stop pad."""
import io, sys, shutil

SRC = "/home/user/Claude/MEScalp.v2.3.pine"
P = "/home/user/Claude/MEScalp.v2.4.pine"
shutil.copy(SRC, P)
src = io.open(P, encoding="utf-8").read()


def sub1(old, new, tag):
    global src
    if src.count(old) != 1:
        sys.exit("PATCH %s: expected 1, found %d" % (tag, src.count(old)))
    src = src.replace(old, new)
    print("  ok  %s" % tag)


# ── header ────────────────────────────────────────────────────────────────────
sub1('''// ═══════════════════════════════════════════════════════════════════════════════
// v2.3 — TP1 WAS BEING REACHED AND THE CHART NEVER SAID SO.''',
'''// ═══════════════════════════════════════════════════════════════════════════════
// v2.4 — THE VWAP BAND TRIGGER WAS FIRING ON ARITHMETIC, NOT ON A REJECTION.
// ─────────────────────────────────────────────────────────────────────────────
// Reported: "3 won and 2 lost, unstable win rate on 5m to 15m."
//
// FIRST, THE PART THAT IS NOT A BUG. Five trades cannot measure a win rate.
// A process that reaches TP1 about 57% of the time produces 3W/2L more often
// than any other five-trade result — it is the single most likely outcome, not
// evidence of instability. Nothing below was changed because of those five
// trades. It was changed because looking for the cause turned up a real defect.
//
// ─────────────────────────────────────────────────────────────────────────────
// THE DEFECT. The band trigger is:
//
//     bandBull = low <= l1 and close > l1 and closePos >= 0.55
//
// l1 is the lower VWAP deviation band. The deviation is accumulated from the
// session anchor, so on the first bars after the anchor it is computed from ONE
// SAMPLE and collapses: u1 == l1 == vwap. "low <= l1 and close > l1" is then
// true of any bar that closes above its own low. The engine reads that as a
// band rejection. It is not a rejection of anything.
//
// The v2.2 header called this trigger "the highest-supply event in the engine —
// 20.9 events/day on 15m against 14.9 for MSS, FVG and sweep combined". That
// was true, and the reason was arithmetic, not opportunity.
//
// WHAT THOSE TRADES DO, per family, 5m and 15m, 360 simulated days each:
//
//     5m                                    15m
//     family   trd/d  TP1  TP3   SL  TIME   trd/d  TP1  TP3   SL  TIME  hold
//     mss       2.85  61%  20%  11%   28%    1.18  49%  19%  36%   15%    2b
//     fvg       1.13  64%  23%  19%   17%    0.68  66%  25%   9%   25%    3b
//     sweep     0.10  84%  14%  16%    0%    0.21  64%  27%  36%    0%    1b
//     band      0.74  30%   7%  15%   55%    1.03  25%   4%  23%   52%   12b
//     band2     0.04  40%   7%   0%   60%    0.02  33%  17%   0%   67%   12b
//     value     0.05  56%  11%  22%   22%    0.02  17%   0%  17%   67%   12b
//
// On 15m the band family is a THIRD of all trades, reaches TP1 25% of the time
// against 66% for FVG, and its median hold sits exactly on the 12-bar time stop
// — i.e. the typical band trade resolves nothing and is closed by the clock.
//
// v2.4 requires a band to HAVE WIDTH before it counts as a level: the u1-l1
// distance must be at least i_bandMinW × ATR (default 0.30). That is a one-line
// test and it removes the collapsed-band events without touching the real ones.
//
// ─────────────────────────────────────────────────────────────────────────────
// CONFIRMATION. A confirmed family does not fire on its own bar: the event is
// read off the previous bar and THIS bar must CLOSE beyond that bar's extreme.
// Measured, applied to everything at once on 5m: stop-outs 14% -> 7%, TP1
// unchanged at 57%, and the trade rate falls from 4.92/day to 1.24. That is a
// 75% cut in supply for a halving of stop-outs, which is a real choice and is
// offered as "All triggers".
//
// The default is "Fades only" — band, band2 and value area, the three families
// that enter AGAINST the move in progress. After the width gate those families
// are small, so the default costs very little and is worth about a point.
//
// ─────────────────────────────────────────────────────────────────────────────
// THE STOP. MSS is the only family whose invalidation is a PIVOT rather than a
// bar extreme, and on 15m that pivot is often only a few ticks from the entry:
// MSS stops out at 36% there, against 9% for FVG. It now takes its own extra
// clearance, i_breakPad, on top of the shared pad.
//
//     MSS pad     15m MSS SL   15m all SL   15m TP1   15m trd/day
//     0.45 total       36%          28%        56%         2.15
//     0.65 total       32%          25%        58%         2.11   <- default
//     0.85 total       29%          23%        59%         2.06
//
// On 5m the same change is neutral (MSS SL 11% -> 9%, TP1 unchanged at 62%), so
// the default is set where 15m improves and 5m does not suffer.
//
// ─────────────────────────────────────────────────────────────────────────────
// WHAT THE THREE CHANGES DO TOGETHER — and this is the answer to "unstable
// from 5 to 15", because the two timeframes stop disagreeing:
//
//     5m                                    15m
//              trd/d  TP1   BE  TP3   SL  TIME      trd/d  TP1   BE  TP3   SL  TIME
//     v2.3      4.92  57%  39%  18%  14%   29%       3.13  45%  30%  16%  26%   29%
//     v2.4      4.07  62%  41%  20%  12%   26%       2.11  58%  35%  22%  25%   17%
//
// The TP1 gap between the two timeframes goes from 12 points to 4. The
// time-stop share on 15m — trades that resolved nothing — is cut from 29% to
// 17%. The cost is about 17% of the trades on 5m and 33% on 15m.
//
// The stop-out gap does NOT close: 12% on 5m against 25% on 15m. That is the
// one number this release does not fix, and it is not a defect in the logic —
// a 15m stop is a bigger price distance and takes longer to reach, so more of
// the path is exposed to it.
//
// ─────────────────────────────────────────────────────────────────────────────
// THREE THINGS I TESTED AND DID NOT SHIP, because the measurement said not to.
//
//  1 SWING INVALIDATION for the fades. The band/value stop is built from the
//    TRIGGER BAR'S OWN WICK — one candle. Replacing that with the extreme of
//    the last 3, 5 or 8 bars moved the 5m stop-out rate from 14% to 13% and the
//    15m rate from 26% to 25%. The shared pad already dominates the placement.
//    I expected this to matter and it does not.
//
//  2 LEVEL-RETEST ENTRY — arm at the trigger's own level and fill only if price
//    returns to it. This is the change that helped ME Pro (88% fill, fewer stop
//    -outs). Here it HURTS, badly: 5m stop-outs 14% -> 22%, 15m 26% -> 41%.
//    The reason is structural and it took the measurement to see it. ME Pro's
//    triggers are acceptance events, so a pullback to the level is a discount.
//    ME Scalp's are rejections — price coming BACK to the level it just
//    rejected is the setup failing, not a better price. The same mechanic
//    reverses sign between the two engines. It is not ported.
//
//  3 A LONGER TIME STOP. On 5m, 12 -> 18 bars moves TP1 reach 62% -> 66% and
//    the time-stop share 25% -> 19%. It looks like a clear gain and it is not
//    decidable here: the 6 points come out as +2 TP3, +2 breakeven and +2 full
//    stop-outs, and what a time exit is actually worth — it closes at market,
//    anywhere — is precisely what an outcome-mix harness cannot price. The
//    width gate was shipped on the opposite pattern: it moved trades out of the
//    time stop into BOTH resolved outcomes with TP3 rising more than SL. This
//    one is a coin toss dressed as an improvement, so the default stays at 12.
//
// EVERYTHING ABOVE IS COUNTS AND OUTCOME GEOMETRY on a synthetic generator.
// NO EXPECTANCY IS COMPUTED OR QUOTED anywhere in this file. Position size
// divides by stop distance, so a wider stop pays less per win — that trade-off
// is real, is not visible in any table here, and is why the pads were moved as
// little as the measurements allowed.
//
// ═══════════════════════════════════════════════════════════════════════════════
// v2.3 — TP1 WAS BEING REACHED AND THE CHART NEVER SAID SO.''',
     "header")

sub1('indicator("ME Scalp v2.3", shorttitle="ME Scalp v2.3"',
     'indicator("ME Scalp v2.4", shorttitle="ME Scalp v2.4"', "title")
sub1("// © ME Institutional — ME Scalp v2.3",
     "// © ME Institutional — ME Scalp v2.4", "copyright")
sub1('"ME SCALP v2.3 — "', '"ME SCALP v2.4 — "', "dash title")

# ── new inputs ────────────────────────────────────────────────────────────────
sub1('''i_useValue = input.bool(true, "Value-area rejection (VAH/VAL)", group=G_TRIG)''',
'''i_useValue = input.bool(true, "Value-area rejection (VAH/VAL)", group=G_TRIG)

// v2.4 — the two inputs that this release exists for.
i_bandMinW = input.float(0.30, "Band must be this wide to count (× ATR)", minval=0.0, maxval=2.0, step=0.05, group=G_TRIG,
     tooltip="A VWAP band only counts as a level if u1 - l1 is at least this many ATR wide.\\n\\nWHY THIS EXISTS. The deviation is accumulated from the session anchor, so on the first bars after it the deviation comes from ONE SAMPLE and the bands collapse onto VWAP: u1 == l1 == vwap. The rejection test is then \\"low <= l1 and close > l1\\", which is true of any bar that closes above its own low. The engine was reading arithmetic as a rejection.\\n\\nMEASURED, per family, 360 simulated days:\\n\\n  family   5m TP1  5m TIME   15m TP1  15m TIME\\n  mss         61%      28%       49%       15%\\n  fvg         64%      17%       66%       25%\\n  band        30%      55%       25%       52%\\n\\nOn 15m the band family was a third of all trades, reached TP1 a quarter of the time, and its median hold sat exactly on the 12-bar time stop — the typical band trade resolved nothing and was closed by the clock.\\n\\nWith the gate at 0.30 the 15m mix goes TP1 45% -> 55%, time stop 29% -> 16%, at a cost of 0.73 trades/day. 0.15, 0.30 and 0.50 all measured within a point of each other; 0.00 restores v2.3 exactly.")
i_confirm  = input.string("Fades only", "Confirmation Bar", options=["Off", "Fades only", "All triggers"], group=G_TRIG,
     tooltip="A CONFIRMED family does not fire on its own bar. The event is read off the previous bar and THIS bar must CLOSE beyond that bar's extreme before the setup is taken. Entry is one bar later and at a worse price; the stop is still built from the trigger bar's invalidation.\\n\\nOff\\n  v2.3 behaviour. Every trigger fires on its own close.\\n\\nFades only (default)\\n  Band, band2 and value area — the three families that enter AGAINST the move in progress. After the width gate these are small, so this costs few trades and measured about a point of TP1 and a point of stop-out on both timeframes.\\n\\nAll triggers\\n  Measured on 5m: stop-outs 14% -> 7%, TP1 unchanged at 57%, trade rate 4.92/day -> 1.24. A 75% cut in supply for a halving of stop-outs. That is a real choice, not an improvement — take it if you would rather wait.")''',
     "trigger inputs")

sub1('''i_beAfterTp1 = input.bool(true, "Move stop to breakeven after TP1", group=G_RISK)''',
'''i_breakPad  = input.float(0.20, "Extra Pad for MSS Breaks (× ATR)", minval=0.0, maxval=1.5, step=0.05, group=G_RISK,
     tooltip="Added to the shared pad for MSS setups ONLY.\\n\\nWHY ONLY MSS. Every other family stops beyond a bar extreme or a gap edge. MSS stops beyond the PIVOT it just broke, and on 15m that pivot is frequently a few ticks from the entry. Measured, 15m: MSS stops out at 36% against 9% for FVG, while being 56% of all trades.\\n\\n  MSS pad    15m MSS SL   15m all SL   15m TP1   15m trd/day\\n  0.45 total      36%          28%        56%         2.15\\n  0.65 total      32%          25%        58%         2.11   <- default\\n  0.85 total      29%          23%        59%         2.06\\n\\nOn 5m the same change is neutral — MSS stop-outs 11% -> 9%, TP1 unchanged at 62% — so the default sits where 15m gains and 5m does not lose.\\n\\nTHE COST, which no table here shows: position size divides by stop distance, so every MSS win pays proportionally less. Set to 0 to hold every family at the same pad.\\n\\nIgnored in the v2.1 clamp mode.")
i_beAfterTp1 = input.bool(true, "Move stop to breakeven after TP1", group=G_RISK)''',
     "break pad input")

# v2.3 shipped two tooltips containing a literal "%%" — a leftover from the
# patch script that wrote them, which TradingView displays verbatim as "57%%".
n = src.count("%%")
src = src.replace("%%", "%")
print("  ok  stray double-percent in %d places" % n)

io.open(P, "w", encoding="utf-8").write(src)
print("\nstage 1 wrote %d bytes" % len(src))


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 2 — the trigger block, the stop, the dashboard
# ══════════════════════════════════════════════════════════════════════════════
src = io.open(P, encoding="utf-8").read()

OLD_TRIG = '''// 1 MSS — price closes through the last short-term pivot
mssBull = conf and i_useMss and not na(lastPH) and close >= lastPH + atr * 0.08 and close[1] < lastPH
mssBear = conf and i_useMss and not na(lastPL) and close <= lastPL - atr * 0.08 and close[1] > lastPL

// 2 FVG retest — price trades into a live gap and closes back out of it
fvgBull = false
float fvgBullLvl = na
float fvgBullInv = na
if conf and i_useFvg and array.size(fvgBullBar) > 0
    for k = array.size(fvgBullBar) - 1 to 0
        if low <= array.get(fvgBullTop, k) and close >= array.get(fvgBullBot, k) and closePos >= 0.55
            fvgBull := true
            fvgBullLvl := array.get(fvgBullTop, k)
            fvgBullInv := array.get(fvgBullBot, k)
            break
fvgBear = false
float fvgBearLvl = na
float fvgBearInv = na
if conf and i_useFvg and array.size(fvgBearBar) > 0
    for k = array.size(fvgBearBar) - 1 to 0
        if high >= array.get(fvgBearBot, k) and close <= array.get(fvgBearTop, k) and closePos <= 0.45
            fvgBear := true
            fvgBearLvl := array.get(fvgBearBot, k)
            fvgBearInv := array.get(fvgBearTop, k)
            break

// 3 Liquidity sweep — a pivot is taken out by a wick and immediately reclaimed
swBull = conf and i_useSweep and not na(sweepLo) and (sweepLo - low) >= atr * 0.35 and close > sweepLo and closePos >= 0.55
swBear = conf and i_useSweep and not na(sweepHi) and (high - sweepHi) >= atr * 0.35 and close < sweepHi and closePos <= 0.45

// 4 VWAP band rejection — traded through a deviation band, closed back inside
bandBull  = conf and i_useBand and low  <= l1 and close > l1 and closePos >= 0.55
bandBear  = conf and i_useBand and high >= u1 and close < u1 and closePos <= 0.45
band2Bull = conf and i_useBand and low  <= l2 and close > l2 and closePos >= 0.55
band2Bear = conf and i_useBand and high >= u2 and close < u2 and closePos <= 0.45

// 5 Value-area rejection — traded outside the value area, closed back inside
valBull = conf and i_useValue and not na(val) and low  <= val and close > val and closePos >= 0.55
valBear = conf and i_useValue and not na(vah) and high >= vah and close < vah and closePos <= 0.45
'''

NEW_TRIG = '''// ── v2.4 CONFIRMATION SWITCHES ────────────────────────────────────────────────
// A CONFIRMED family does not fire on its own bar. Its event is read off the
// PREVIOUS bar and the current bar must CLOSE beyond that bar's extreme before
// the setup is taken. Entry is therefore one bar later and at a worse price,
// while the stop is still built from the trigger bar's own invalidation — which
// is why the invalidation block further down reads [1] for a confirmed family.
cfOn   = i_confirm != "Off"
cfAll  = i_confirm == "All triggers"
cfCore = cfAll              // MSS, FVG, liquidity sweep
cfFade = cfOn               // VWAP band, band2, value area — the three fades
cfUp   = close > high[1]
cfDn   = close < low[1]

// 1 MSS — price closes through the last short-term pivot
mssBullR = conf and i_useMss and not na(lastPH) and close >= lastPH + atr * 0.08 and close[1] < lastPH
mssBearR = conf and i_useMss and not na(lastPL) and close <= lastPL - atr * 0.08 and close[1] > lastPL
mssBull  = cfCore ? (conf and mssBullR[1] and cfUp) : mssBullR
mssBear  = cfCore ? (conf and mssBearR[1] and cfDn) : mssBearR

// 2 FVG retest — price trades into a live gap and closes back out of it
fvgBullR = false
float fvgBullLvlR = na
float fvgBullInvR = na
if conf and i_useFvg and array.size(fvgBullBar) > 0
    for k = array.size(fvgBullBar) - 1 to 0
        if low <= array.get(fvgBullTop, k) and close >= array.get(fvgBullBot, k) and closePos >= 0.55
            fvgBullR := true
            fvgBullLvlR := array.get(fvgBullTop, k)
            fvgBullInvR := array.get(fvgBullBot, k)
            break
fvgBearR = false
float fvgBearLvlR = na
float fvgBearInvR = na
if conf and i_useFvg and array.size(fvgBearBar) > 0
    for k = array.size(fvgBearBar) - 1 to 0
        if high >= array.get(fvgBearBot, k) and close <= array.get(fvgBearTop, k) and closePos <= 0.45
            fvgBearR := true
            fvgBearLvlR := array.get(fvgBearBot, k)
            fvgBearInvR := array.get(fvgBearTop, k)
            break
fvgBull = cfCore ? (conf and fvgBullR[1] and cfUp) : fvgBullR
fvgBear = cfCore ? (conf and fvgBearR[1] and cfDn) : fvgBearR
fvgBullLvl = cfCore ? fvgBullLvlR[1] : fvgBullLvlR
fvgBearLvl = cfCore ? fvgBearLvlR[1] : fvgBearLvlR
fvgBullInv = cfCore ? fvgBullInvR[1] : fvgBullInvR
fvgBearInv = cfCore ? fvgBearInvR[1] : fvgBearInvR

// 3 Liquidity sweep — a pivot is taken out by a wick and immediately reclaimed
swBullR = conf and i_useSweep and not na(sweepLo) and (sweepLo - low) >= atr * 0.35 and close > sweepLo and closePos >= 0.55
swBearR = conf and i_useSweep and not na(sweepHi) and (high - sweepHi) >= atr * 0.35 and close < sweepHi and closePos <= 0.45
swBull  = cfCore ? (conf and swBullR[1] and cfUp) : swBullR
swBear  = cfCore ? (conf and swBearR[1] and cfDn) : swBearR

// 4 VWAP band rejection — traded through a deviation band, closed back inside.
// v2.4 THE BAND MUST HAVE WIDTH. The deviation is accumulated from the session
// anchor, so on the first bars after it the deviation comes from ONE SAMPLE and
// the bands collapse onto VWAP: u1 == l1 == vwap. "low <= l1 and close > l1" is
// then true of any bar closing above its own low, and the engine was reading
// that arithmetic as a rejection. Those events were a third of all 15m trades
// and reached TP1 a quarter of the time. See the i_bandMinW tooltip.
bandW  = u1 - l1
bandOk = bandW >= atr * i_bandMinW
bandBullR  = conf and i_useBand and bandOk and low  <= l1 and close > l1 and closePos >= 0.55
bandBearR  = conf and i_useBand and bandOk and high >= u1 and close < u1 and closePos <= 0.45
band2BullR = conf and i_useBand and bandOk and low  <= l2 and close > l2 and closePos >= 0.55
band2BearR = conf and i_useBand and bandOk and high >= u2 and close < u2 and closePos <= 0.45
bandBull   = cfFade ? (conf and bandBullR[1]  and cfUp) : bandBullR
bandBear   = cfFade ? (conf and bandBearR[1]  and cfDn) : bandBearR
band2Bull  = cfFade ? (conf and band2BullR[1] and cfUp) : band2BullR
band2Bear  = cfFade ? (conf and band2BearR[1] and cfDn) : band2BearR

// 5 Value-area rejection — traded outside the value area, closed back inside
valBullR = conf and i_useValue and not na(val) and low  <= val and close > val and closePos >= 0.55
valBearR = conf and i_useValue and not na(vah) and high >= vah and close < vah and closePos <= 0.45
valBull  = cfFade ? (conf and valBullR[1] and cfUp) : valBullR
valBear  = cfFade ? (conf and valBearR[1] and cfDn) : valBearR
'''
sub1(OLD_TRIG, NEW_TRIG, "trigger block")

sub1('''bullInval = mssBull ? (na(lastPL) ? low : lastPL) : fvgBull ? fvgBullInv : low
bearInval = mssBear ? (na(lastPH) ? high : lastPH) : fvgBear ? fvgBearInv : high''',
'''// v2.4: the invalidation must be read on the bar the EVENT was on, which for a
// confirmed family is the PREVIOUS bar. Reading it on the confirmation bar
// would build the stop from a bar the setup had already been proved on, which
// is both wrong and, for a long, systematically too tight.
mssBullIv  = cfCore ? (na(lastPL[1]) ? low[1]  : lastPL[1]) : (na(lastPL) ? low  : lastPL)
mssBearIv  = cfCore ? (na(lastPH[1]) ? high[1] : lastPH[1]) : (na(lastPH) ? high : lastPH)
swBullIv   = cfCore ? low[1]  : low
swBearIv   = cfCore ? high[1] : high
fadeBullIv = cfFade ? low[1]  : low
fadeBearIv = cfFade ? high[1] : high

bullInval = bullName == "MSS" ? mssBullIv : bullName == "FVG" ? fvgBullInv : bullName == "SWEEP" ? swBullIv : fadeBullIv
bearInval = bearName == "MSS" ? mssBearIv : bearName == "FVG" ? fvgBearInv : bearName == "SWEEP" ? swBearIv : fadeBearIv''',
     "invalidation")

# ── the per-family pad ────────────────────────────────────────────────────────
sub1('''slRawBull = math.min(bullInval, close - atr * i_minRisk) - atr * i_slBuf - structPad
slRawBear = math.max(bearInval, close + atr * i_minRisk) + atr * i_slBuf + structPad''',
'''// v2.4 PER-FAMILY PAD. MSS is the only family whose invalidation is a PIVOT
// rather than a bar extreme or a gap edge, and on 15m that pivot is frequently
// a few ticks from the entry — measured, MSS stops out at 36% there against 9%
// for FVG while being 56% of all trades. It gets its own extra clearance.
breakPadB = (not legacyClamp and bullName == "MSS") ? atr * i_breakPad : 0.0
breakPadS = (not legacyClamp and bearName == "MSS") ? atr * i_breakPad : 0.0
slRawBull = math.min(bullInval, close - atr * i_minRisk) - atr * i_slBuf - structPad - breakPadB
slRawBear = math.max(bearInval, close + atr * i_minRisk) + atr * i_slBuf + structPad + breakPadS''',
     "per-family pad")

# ── dashboard ─────────────────────────────────────────────────────────────────
sub1("dash := table.new(pos, 3, 12,", "dash := table.new(pos, 3, 13,", "table rows")

sub1('''    table.cell(dash, 2, 11, "pad " + str.tostring(i_slBuf + i_structPad, "#.##") + " ATR", text_color=dim, text_size=size.tiny)''',
'''    table.cell(dash, 2, 11, "pad " + str.tostring(i_slBuf + i_structPad, "#.##") + " / MSS " + str.tostring(i_slBuf + i_structPad + i_breakPad, "#.##"), text_color=dim, text_size=size.tiny)

    // v2.4 THE ROW THIS VERSION EXISTS FOR. If "band" reads ✕ the deviation
    // bands are too narrow to be levels right now — which is the state that was
    // producing a third of the 15m trades before this release gated it.
    table.cell(dash, 0, 12, "Confirm / band", text_color=dim, text_size=size.tiny, text_halign=text.align_left, bgcolor=color.rgb(15, 15, 22))
    table.cell(dash, 1, 12, i_confirm, text_color=cfOn ? grn : yel, text_size=size.tiny)
    table.cell(dash, 2, 12, "band " + str.tostring(math.round(bandW / math.max(atr, 1e-9), 2)) + (bandOk ? " ATR ✓" : " ATR ✕"), text_color=bandOk ? dim : yel, text_size=size.tiny)''',
     "dash rows")

io.open(P, "w", encoding="utf-8").write(src)
print("\nstage 2 wrote %d bytes" % len(src))


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 3 — remove the FVG level tracking. Nothing has ever read it: v2.3
# declared fvgBullLvl / fvgBearLvl, assigned them inside the search loop, and
# then never referenced them again. Pine warns on that, and wrapping them for
# confirmation in stage 2 would have doubled the dead names rather than the
# useful ones. The stop is built from the INVALIDATION, which is kept.
# ══════════════════════════════════════════════════════════════════════════════
src = io.open(P, encoding="utf-8").read()
for a, b, tag in (
    ("float fvgBullLvlR = na\n", "", "decl bull lvl"),
    ("float fvgBearLvlR = na\n", "", "decl bear lvl"),
    ("            fvgBullLvlR := array.get(fvgBullTop, k)\n", "", "assign bull lvl"),
    ("            fvgBearLvlR := array.get(fvgBearBot, k)\n", "", "assign bear lvl"),
    ("fvgBullLvl = cfCore ? fvgBullLvlR[1] : fvgBullLvlR\n", "", "wrap bull lvl"),
    ("fvgBearLvl = cfCore ? fvgBearLvlR[1] : fvgBearLvlR\n", "", "wrap bear lvl"),
):
    sub1(a, b, tag)

io.open(P, "w", encoding="utf-8").write(src)
print("\nstage 3 wrote %d bytes" % len(src))


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 4 — the implementation note. Where the shipped code and the harness
# differ by one bar, say so rather than implying they are the same engine.
# ══════════════════════════════════════════════════════════════════════════════
src = io.open(P, encoding="utf-8").read()
sub1('''// EVERYTHING ABOVE IS COUNTS AND OUTCOME GEOMETRY on a synthetic generator.''',
'''// WHERE THIS FILE AND THE HARNESS DIFFER, stated because they are not the same
// program. For a CONFIRMED family the harness reads the regime filter, the
// cooldown, the quality score and the ATR on the TRIGGER bar; this file reads
// them on the CONFIRMATION bar, one later, because that is the bar Pine is
// executing. Only the level and the invalidation are deliberately taken from
// the trigger bar in both. I measured the score half of that divergence
// directly — scoring the confirmation bar instead of the trigger bar moved
// nothing on either timeframe, 1514 trades against 1513 on 5m — and did not
// measure the other three. They are one bar of drift, not a different rule,
// but they are a reason to expect the chart and the tables to disagree
// slightly rather than exactly.
//
// EVERYTHING ABOVE IS COUNTS AND OUTCOME GEOMETRY on a synthetic generator.''',
     "implementation note")
io.open(P, "w", encoding="utf-8").write(src)
print("\nstage 4 wrote %d bytes" % len(src))
