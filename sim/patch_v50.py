"""ME Pro v5.0 — the preset now governs the whole conjunction, not eight of it.

v4.9's preset was searched against an eight-gate model. The indicator ANDs
twenty-one. fullstack.py measured the real thing: 0.14-0.19 signals/day on
EVERY mode. This fixes the two structural causes.
"""
import io, sys, shutil

SRC = "/home/user/Claude/MovementEnginePro.v4.9.pine"
P = "/home/user/Claude/MovementEnginePro.v5.0.pine"
shutil.copy(SRC, P)
src = io.open(P, encoding="utf-8").read()


def sub1(old, new, tag):
    global src
    if src.count(old) != 1:
        sys.exit("PATCH %s: expected 1, found %d" % (tag, src.count(old)))
    src = src.replace(old, new)
    print("  ok  %s" % tag)


PACE_TIP = (
    "v5.0 REPLACES the v4.9 preset, which was measured against the wrong "
    "engine.\\n\\nWHAT WENT WRONG. v4.9's preset was searched on a model with "
    "EIGHT gates and reported 4.84 signals/day. The indicator ANDs TWENTY-ONE. "
    "Re-measured against the real conjunction, 5m, 120 days x 3 seeds, both "
    "sides:\\n\\n"
    "  mode          signals/day\\n"
    "  Aggressive           0.19\\n"
    "  Balanced             0.15\\n"
    "  Strict               0.14\\n"
    "  Scalp                0.19\\n\\n"
    "One trade a week, and the mode selector moved it from 0.14 to 0.19 — "
    "essentially nothing, because the gates that bind are the ones every mode "
    "shares.\\n\\nTHE TWO CAUSES, by share of all blocked triggers:\\n\\n"
    "  reward       71.2%   TP1 must clear 1.0R. But TP1 is the ATR ladder's "
    "first rung at 0.8 x ATR, and the structural stop is usually wider than "
    "that, so TP1 CANNOT clear 1.0R on most setups. The gate was rejecting "
    "trades for a property of the target, not of the setup. It is the single "
    "largest blocker in the engine and no previous version touched it.\\n"
    "  momentum     60.6%   EMA 8 > EMA 21\\n"
    "  cvd          58.2%   CVD fast EMA > slow EMA\\n"
    "  GATE: trail  56.9%   the no-reversal trail\\n"
    "  struct bias  53.8%   HTF-locked MSS direction\\n\\n"
    "Those last four are FOUR CORRELATED READINGS OF ONE QUESTION — is the "
    "market going my way. Stacking four is not four times the safety; it is "
    "one filter applied four times, and it costs most of the trades.\\n\\n"
    "WHAT THIS CONTROL DOES. It sets the six filters v4.9 already moved, PLUS "
    "the reward floor, PLUS how many of the three redundant direction filters "
    "sit on top of the trail (Dir Stack, 0-3).\\n\\nMEASURED, real conjunction, "
    "120 days x 3 seeds, both sides, trail ON in every row:\\n\\n"
    "  tf   pace      dir   Aggr   Balan  Strict  Scalp     SL   TP3\\n"
    "  3m   Steady     1    0.61    0.44   0.36    0.60    51%   13%\\n"
    "  3m   Active     0    3.08    1.25   1.01    3.06    44%   12%\\n"
    "  3m   Rapid      0    5.35    2.27   1.78    5.30    43%   11%\\n"
    "  5m   Steady     1    0.38    0.31   0.26    0.38    50%   18%\\n"
    "  5m   Active     0    2.10    1.00   0.83    2.09    46%   12%\\n"
    "  5m   RAPID      0    3.64    1.88   1.47    3.60    44%   12%\\n"
    "  15m  Steady     1    0.42    0.38   0.36    0.41    57%   21%\\n"
    "  15m  Active     0    0.99    0.76   0.71    0.97    56%   15%\\n"
    "  15m  Rapid      0    1.49    1.10   0.99    1.45    55%   14%\\n\\n"
    "READ THE SL AND TP3 COLUMNS. The pace is bought, not found. Going from "
    "the v4.9 stack to Rapid takes the stop-out rate from 42% to 44% and cuts "
    "the share of trades reaching TP3 from 46% to 12% — the trades added by "
    "loosening are shorter and resolve nearer the entry. That is the honest "
    "price and it is not a rounding error.\\n\\nBALANCED AND STRICT CANNOT REACH "
    "4/DAY AT ANY SETTING. They require HTF agreement AND the correct side of "
    "VWAP, which block 52.4% and 56.2% of triggers on their own. That is what "
    "those modes MEAN, so no filter setting reaches past it. If you want four "
    "or more trades a day, run Aggressive or Scalp on 3m at Rapid (5.35 and "
    "5.30) — and pay 14.9% of your stop to the spread instead of 11.5%.\\n\\n"
    "THE NO-REVERSAL GUARANTEE IS UNCHANGED AT EVERY SETTING. Dir Stack 0 "
    "still requires the trail to be in its up state for a long. A long against "
    "the trend cannot pass at any pace. What Dir Stack removes is the three "
    "filters that re-ask the same question, not the guarantee.\\n\\n"
    "SIGNAL COUNT AND OUTCOME MIX ARE ALL THAT IS CLAIMED. Both are counts and "
    "geometry. No expectancy was computed and none is quoted — no price feed "
    "was reachable from any session that built this file, and the XAUUSD "
    "spread (14.9% of a ~1.5 ATR stop on 3m, 11.5% on 5m, 6.7% on 15m) is a "
    "real cost the outcome mix does not include.")

sub1('''i_rateTarget = input.string("Measured: ~5/day (5m moderate)", "Trade Rate Preset",
     options=["Off — use the individual filters", "Measured: ~2/day (5m selective)", "Measured: ~5/day (5m moderate)", "Measured: ~10/day (5m scalp)"],''',
'''i_rateTarget = input.string("Active", "Trade Pace",
     options=["Off — use the individual filters", "Steady", "Active", "Rapid"],''',
     "pace input options")

# the tooltip is the whole measured record; replace v4.9's
old_tip_start = src.index('     tooltip="v4.9: one control that sets the six filters')
old_tip_end = src.index('\n', src.index('spread column above is a real cost that outcome mix does not include."', old_tip_start))
src = src[:old_tip_start] + '     tooltip="%s",' % PACE_TIP + src[old_tip_end:]
print("  ok  pace tooltip")

# ── preset table, now eight numbers instead of six ────────────────────────
sub1('''presetOff  = i_rateTarget == "Off — use the individual filters"
presetSel  = i_rateTarget == "Measured: ~2/day (5m selective)"
presetMod  = i_rateTarget == "Measured: ~5/day (5m moderate)"
presetScl  = i_rateTarget == "Measured: ~10/day (5m scalp)"
pBody   = presetSel ? 0.50 : presetMod ? 0.40 : 0.30
pVol    = presetSel ? 1.20 : presetMod ? 1.00 : 0.80
pOf     = presetSel ? 60.0 : presetMod ? 58.0 : 56.0
pDelta  = presetSel ? 0.20 : presetMod ? 0.15 : 0.12
pCool   = presetSel ? 12   : presetMod ? 6    : 3
pMinR   = presetSel ? 1.0  : presetMod ? 0.7  : 0.5''',
'''presetOff  = i_rateTarget == "Off — use the individual filters"
presetSel  = i_rateTarget == "Steady"
presetMod  = i_rateTarget == "Active"
presetScl  = i_rateTarget == "Rapid"
pBody   = presetSel ? 0.35 : presetMod ? 0.30 : 0.25
pVol    = presetSel ? 0.90 : presetMod ? 0.80 : 0.70
pOf     = presetSel ? 56.0 : presetMod ? 55.0 : 53.0
pDelta  = presetSel ? 0.12 : presetMod ? 0.10 : 0.08
pCool   = presetSel ? 4    : presetMod ? 3    : 2
pMinR   = presetSel ? 0.6  : presetMod ? 0.5  : 0.4
// v5.0 — the two the v4.9 preset never reached, and they were the two that
// mattered most. pRR is the reward floor; at 1.0 it rejected 71.2% of all
// triggers because TP1 is the ATR ladder's first rung and the structural stop
// is usually wider than it, so TP1 could not clear 1.0R on most setups.
pRR     = presetSel ? 0.60 : presetMod ? 0.55 : 0.50
// pDir is how many of momentum / CVD / structural bias are enforced ON TOP OF
// the no-reversal trail. All three re-ask the trail's question. The trail is
// never included in this count and is never removed — the no-reversal
// guarantee holds at Dir Stack 0.
pDir    = presetSel ? 1    : presetMod ? 0    : 0''',
     "preset values")

# ── the reward floor, finally under the preset ────────────────────────────
sub1("effMinRR      = isScalp ? math.min(i_minRR, scalpHigh ? 0.7 : scalpStd ? 0.9 : 99.0) : i_minRR",
     "effMinRR      = presetOff ? (isScalp ? math.min(i_minRR, scalpHigh ? 0.7 : scalpStd ? 0.9 : 99.0) : i_minRR) : pRR",
     "preset reward floor")

# ── the direction stack ───────────────────────────────────────────────────
sub1("effMinRisk    = presetOff ? (isScalp ? math.min(i_minRisk, 0.5) : i_minRisk) : pMinR",
     '''effMinRisk    = presetOff ? (isScalp ? math.min(i_minRisk, 0.5) : i_minRisk) : pMinR
// v5.0 DIR STACK. 3 reproduces every previous version. Below 3 the redundant
// direction readings drop off in order of measured block share: structural
// bias (53.8%) first, then CVD (58.2%), then EMA momentum (60.6%). The trail
// is not in this list and never comes off.
dirStack      = presetOff ? 3 : pDir''',
     "dir stack")

sub1("biasOkBuy  = isScalp or not structInit or structBull == true",
     "biasOkBuy  = dirStack < 3 or isScalp or not structInit or structBull == true",
     "bias depth")
sub1("biasOkSell = isScalp or not structInit or structBull == false",
     "biasOkSell = dirStack < 3 or isScalp or not structInit or structBull == false",
     "bias depth sell")

sub1("cvdOkBuy   = not volDataSeen or cvdBull  or (isScalp and revExempt and (buyTrigSweep  or buyTrigBand))",
     "cvdOkBuy   = dirStack < 2 or not volDataSeen or cvdBull  or (isScalp and revExempt and (buyTrigSweep  or buyTrigBand))",
     "cvd depth")
sub1("cvdOkSell  = not volDataSeen or cvdBear  or (isScalp and revExempt and (sellTrigSweep or sellTrigBand))",
     "cvdOkSell  = dirStack < 2 or not volDataSeen or cvdBear  or (isScalp and revExempt and (sellTrigSweep or sellTrigBand))",
     "cvd depth sell")

sub1("momOkBuyEff  = momOkBuy  or (isScalp and revExempt and (buyTrigSweep  or buyTrigBand))",
     "momOkBuyEff  = dirStack < 1 or momOkBuy  or (isScalp and revExempt and (buyTrigSweep  or buyTrigBand))",
     "mom depth")
sub1("momOkSellEff = momOkSell or (isScalp and revExempt and (sellTrigSweep or sellTrigBand))",
     "momOkSellEff = dirStack < 1 or momOkSell or (isScalp and revExempt and (sellTrigSweep or sellTrigBand))",
     "mom depth sell")

# ── dashboard header: pace, dir depth, and the mode's own ceiling ─────────
sub1('''    tfWarn = not presetOff and timeframe.in_seconds() != 300 ? "  ⚠ preset measured on 5m" : ""
    table.cell(dash, 0, 0, (isHeikin ? "⛔ HEIKIN ASHI — LEVELS INVALID" : "ME PRO v4.9") + " — " + (presetOff ? str.upper(i_mode) : str.upper(str.substring(i_rateTarget, 10)))''',
'''    modeCap = (i_mode == "Balanced" or i_mode == "Strict") and not presetOff ? "  ⚠ mode caps ~2/day" : ""
    table.cell(dash, 0, 0, (isHeikin ? "⛔ HEIKIN ASHI — LEVELS INVALID" : "ME PRO v5.0") + " — " + str.upper(i_mode) + (presetOff ? "" : " · " + str.upper(i_rateTarget) + " · DIR " + str.tostring(dirStack) + "/3") + modeCap''',
     "dashboard header")

src = src.replace('indicator("Movement Engine Pro v4.9", shorttitle="ME Pro v4.9"',
                  'indicator("Movement Engine Pro v5.0", shorttitle="ME Pro v5.0"')
src = src.replace('// © ME Institutional — Movement Engine Pro v4.9 (a measured trade-rate preset)',
                  '// © ME Institutional — Movement Engine Pro v5.0 (the preset now governs the whole conjunction)')

io.open(P, "w", encoding="utf-8").write(src)
print("\nwrote %d bytes" % len(src))
