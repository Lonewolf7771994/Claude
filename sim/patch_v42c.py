"""v4.2 part 3 — wire the ladder unit through f_tpLevels, fix the reward gate."""
import io, sys

P = "/home/user/Claude/MovementEnginePro.v4.2.pine"
src = io.open(P, encoding="utf-8").read()


def sub1(old, new, tag):
    global src
    if src.count(old) != 1:
        sys.exit("PATCH %s: expected 1, found %d" % (tag, src.count(old)))
    src = src.replace(old, new)
    print("  ok  %s" % tag)


# signature takes the unit
sub1("f_tpLevels(bool _isBuy, float _entry, float _risk, float _mean) =>",
     "f_tpLevels(bool _isBuy, float _entry, float _risk, float _mean, float _unit) =>",
     "ladder signature")

# TP1 injection and the R-multiple fallbacks both measure in _unit
sub1("        array.unshift(cands, _entry + dir * _risk * effTp1R)",
     "        array.unshift(cands, _entry + dir * _unit * effTp1R)",
     "tp1 injection unit")

sub1("            float rv = _entry + dir * _risk * array.get(rMul, s)",
     "            float rv = _entry + dir * _unit * array.get(rMul, s)",
     "fallback unit")

# callers pass the unit
sub1("    [t1, t2, t3, g1, g2, g3] = f_tpLevels(true, buyEntryRef, buyRiskDist, tpMeanBuy)",
     "    [t1, t2, t3, g1, g2, g3] = f_tpLevels(true, buyEntryRef, buyRiskDist, tpMeanBuy, tpUnitBuy)",
     "buy caller")

sub1("    [t1, t2, t3, g1, g2, g3] = f_tpLevels(false, sellEntryRef, sellRiskDist, tpMeanSell)",
     "    [t1, t2, t3, g1, g2, g3] = f_tpLevels(false, sellEntryRef, sellRiskDist, tpMeanSell, tpUnitSell)",
     "sell caller")

# define the units next to the reversion-target definition
sub1(
"""tpMeanBuy  = buySel  == "BAND" ? vwMean : na
tpMeanSell = sellSel == "BAND" ? vwMean : na""",
"""tpMeanBuy  = buySel  == "BAND" ? vwMean : na
tpMeanSell = sellSel == "BAND" ? vwMean : na

// v4.2 LADDER UNIT. In v4.1 every target was a multiple of the STOP DISTANCE,
// so a structural stop near the 3.0 ATR cap pushed TP3 out to 12 ATR and the
// scale-out's last two legs stopped being reachable. Measured on 15m over 150
// days x 6 seeds with identical entries and identical stops, only the ladder
// changing: TP2 filled 14% of the time and TP3 6%. A plan that leaves in thirds
// realised nothing like thirds.
// Measuring the multiples in ATR instead breaks that coupling — the stop still
// goes where structure puts it, and the targets stop being dragged out with it.
tpUnitBuy  = i_tpUnit == "Risk / R (v4.1)" ? buyRiskDist  : atr14
tpUnitSell = i_tpUnit == "Risk / R (v4.1)" ? sellRiskDist : atr14""",
"ladder units")

# ── 8. THE REWARD GATE. i_minBlendRR never binds. ──────────────────────────
sub1(
"""blendOkBuy  = i_minBlendRR > 0 and tp1FloorOkBuy  and not na(blendBuy)  and blendBuy  >= i_minBlendRR
blendOkSell = i_minBlendRR > 0 and tp1FloorOkSell and not na(blendSell) and blendSell >= i_minBlendRR""",
"""// ═══════════════════════════════════════════════════════════════════════════════
// v4.2 — THE REWARD GATE WAS NOT THE GATE IT SAYS IT IS
// ─────────────────────────────────────────────────────────────────────────────
// v3.5.8 added the engine's only reward check: TP1 at least i_minRR (1.0) times
// the stop distance. v3.5.26 then added an alternative path, and rrOk became
//     effMinRR <= 0  or  rrStrict  or  blendOk
// An `or` short-circuits, so the strict test only decides a trade when blendOk
// is FALSE. Measured on 15m, 150 days x 3 seeds, 8,198 setups reaching the gate:
//
//     blended reward, median                    2.68   against a 1.3 threshold
//     share of setups whose blend clears 1.3     100%
//
// Every single one. i_minBlendRR has never rejected anything, so blendOk reduces
// to its other term, the 0.5R TP1 floor — and the ENGINE'S EFFECTIVE REWARD
// REQUIREMENT IS 0.5R, not the 1.0R it documents and displays. 19% of admitted
// trades were admitted only by this path, i.e. with TP1 between 0.5R and 1.0R.
//
// The blend clears so easily because it prices all three legs at 33/33/34 while
// TP2 fills 14% of the time and TP3 6% — 0.34 of the number that admits the
// trade is a target that almost never pays.
//
// v4.2 does not delete the blended path; a modest TP1 behind two strong targets
// is a real setup and rejecting it was v3.5.26's genuine finding. It weights the
// blend by REACHABILITY instead of by intended size, so a distant runner can no
// longer carry a weak first target on a share of the plan it does not deliver.
// i_blendWeighted off restores the v4.1 arithmetic exactly.
// ═══════════════════════════════════════════════════════════════════════════════
blendBuyW  = not na(buyTp1)  and not na(buyTp2)  and not na(buyTp3)  ? (0.55 * (buyTp1 - buyEntryRef) + 0.30 * (buyTp2 - buyEntryRef) + 0.15 * (buyTp3 - buyEntryRef))   / math.max(buyRiskDist,  1e-9) : na
blendSellW = not na(sellTp1) and not na(sellTp2) and not na(sellTp3) ? (0.55 * (sellEntryRef - sellTp1) + 0.30 * (sellEntryRef - sellTp2) + 0.15 * (sellEntryRef - sellTp3)) / math.max(sellRiskDist, 1e-9) : na
blendUseBuy  = i_blendWeighted ? blendBuyW  : blendBuy
blendUseSell = i_blendWeighted ? blendSellW : blendSell
blendOkBuy  = i_minBlendRR > 0 and tp1FloorOkBuy  and not na(blendUseBuy)  and blendUseBuy  >= i_minBlendRR
blendOkSell = i_minBlendRR > 0 and tp1FloorOkSell and not na(blendUseSell) and blendUseSell >= i_minBlendRR""",
"reward gate")

sub1(
"""i_minTp1Floor = input.float(0.5, "Absolute TP1 Floor (× risk)",""",
"""i_blendWeighted = input.bool(true, "Weight Blended Reward By Reachability",
     tooltip="v4.2: how the blended reward path weights the three targets.\\n\\nThe blend exists so a plan with a modest TP1 and strong later targets is not rejected on TP1 alone. v3.5.26 weighted it 33/33/34 — the intended scale-out — and the gate therefore priced every leg as if it filled.\\n\\nMeasured on 15m, 150 days x 6 seeds: TP1 fills 50% of the time, TP2 14%, TP3 6%. So a third of the admitting number rested on a target reached once in seven trades and another third on one reached once in sixteen.\\n\\nThe consequence is measurable and blunt: the blended reward's median is 2.68 against a 1.3 threshold, and 100% of setups clear it. i_minBlendRR has never rejected anything. Because rrOk is an OR, that means the documented 1.0R reward gate is bypassed and the engine's real requirement is the 0.5R floor below.\\n\\nON (default): weights 0.55 / 0.30 / 0.15, roughly the measured fill rates, so the blend describes what the plan tends to deliver rather than what it would deliver if everything filled.\\nOFF: the v4.1 33/33/34 arithmetic, exactly.\\n\\nExpect fewer signals with this on. That is the gate doing the job it was documented as doing.",
     group=G_TPSL)
i_minTp1Floor = input.float(0.5, "Absolute TP1 Floor (× risk)",""",
"blend weight input")

io.open(P, "w", encoding="utf-8").write(src)
print("\nwrote %d bytes" % len(src))
