"""v4.2 part 4 — time stop default, dashboard leg readout, header, title."""
import io, sys

P = "/home/user/Claude/MovementEnginePro.v4.2.pine"
src = io.open(P, encoding="utf-8").read()


def sub1(old, new, tag):
    global src
    if src.count(old) != 1:
        sys.exit("PATCH %s: expected 1, found %d" % (tag, src.count(old)))
    src = src.replace(old, new)
    print("  ok  %s" % tag)


# ── 9. TIME STOP ON BY DEFAULT ─────────────────────────────────────────────
sub1(
"""i_maxBars    = input.int(0, "Max Bars In Trade (0 = off)", minval=0, maxval=500,""",
"""i_maxBars    = input.int(24, "Max Bars In Trade (0 = off)", minval=0, maxval=500,""",
"time stop default")

# ── TITLE ──────────────────────────────────────────────────────────────────
sub1(
'''indicator("Movement Engine Pro v4.1", shorttitle="ME Pro v4.1", overlay=true''',
'''indicator("Movement Engine Pro v4.2", shorttitle="ME Pro v4.2", overlay=true''',
"indicator title")

sub1(
'''// © ME Institutional — Movement Engine Pro v4.1 (mode rebuild)''',
'''// © ME Institutional — Movement Engine Pro v4.2 (one trigger, one ladder, one gate)''',
"copyright line")

sub1('''(isHeikin ? "⛔ HEIKIN ASHI — LEVELS INVALID" : "ME PRO v4.1")''',
     '''(isHeikin ? "⛔ HEIKIN ASHI — LEVELS INVALID" : "ME PRO v4.2")''',
     "dashboard title")

# ── DASHBOARD: which legs of the scale-out actually filled ────────────────
sub1(
"""    sigSuffix  = activeAtBe ? "  · SL@BE" : lossStreak > 0 ? "  · " + str.tostring(lossStreak) + "L streak" : \"\"""",
"""    // v4.2: the scale-out's legs, as they fill. v4.1 could not show this — it
    // never tracked TP2 at all, so the middle third of every plan was invisible
    // to the engine that drew it.
    legTxt = not na(activeSlPx) ? "  · " + (activeTp1Hit ? "1" : "-") + (activeTp2Hit ? "2" : "-") + "3" : ""
    sigSuffix  = (activeAtBe ? "  · SL@BE" : lossStreak > 0 ? "  · " + str.tostring(lossStreak) + "L streak" : "") + legTxt""",
"dashboard legs")

# ── HEADER ────────────────────────────────────────────────────────────────
sub1(
"""// ═══════════════════════════════════════════════════════════════════════════════
// v4.1 — EVERY MODE TRADES. MODE IS A STANDARD, NOT A TRIGGER BAN.""",
"""// ═══════════════════════════════════════════════════════════════════════════════
// v4.2 — SLOW, FRAGMENTED, MISTAKEN. THREE COMPLAINTS, THREE DIFFERENT CAUSES.
// ─────────────────────────────────────────────────────────────────────────────
// All three were reported together and none of them share a cause. Everything
// below was either read off v4.1's own source or measured on the sim/ harness,
// 15m, 150 days x 6 seeds, with identical entries and identical stops in every
// row — only the thing under test moves.
//
// ─────────────────────────────────────────────────────────────────────────────
// MISTAKEN — v4.1 could not agree with itself about what trade it was in.
//
// Four places decide what a signal IS, and they used THREE different priority
// orders:
//
//     buyType      name and alert       MSS   > FVG  > SWEEP > BAND
//     buySlAnchor  where the stop goes  SWEEP > BAND > FVG   > MSS
//     buyChaseRef  the chase reference  SWEEP > BAND > FVG   > MSS
//     tpMeanBuy    target style         BAND, whenever a band was live at all
//
// When MSS and a sweep fire on the same bar the chart says MSS, the stop is
// placed beyond the SWEEP's wick, the chase cap is measured from the swept
// level, and a live band injects the VWAP mean — a reversion target — into what
// is labelled a continuation trade. One signal number, four different trades.
//
// This is the MAJORITY case, not an edge: 9,832 of 17,738 bullish trigger bars
// carry two or more distinct triggers, 55%. And v4.1's confluence score AWARDS
// A POINT for stacking (buyTrigCount >= 2), so the engine rated highest exactly
// the bars where its four descriptions disagreed most.
//
// FIXED: the trigger is selected ONCE (buySel / sellSel), ordered by how
// precisely each defines its own invalidation — SWEEP > BAND > FVG > MSS, which
// is the order the STOP already used, so stop placement does not move. The name,
// the chase reference and the target style now agree with it. A stacked bar is
// labelled with a trailing "+" instead of being silently relabelled.
//
// ─────────────────────────────────────────────────────────────────────────────
// MISTAKEN, SECOND — the reward gate was never the gate it documents.
//
// v3.5.8 added the engine's only reward check: TP1 at least i_minRR = 1.0 times
// the stop. v3.5.26 added an alternative, and the test became
//     rrOk = effMinRR <= 0  or  rrStrict  or  blendOk
// An `or` short-circuits, so the strict test only decides anything when blendOk
// is false. Measured over 8,198 setups reaching the gate:
//
//     blended reward, median                    2.68   against a 1.3 threshold
//     share of setups whose blend clears 1.3     100%
//
// Every one. i_minBlendRR has never rejected a single setup, so blendOk collapses
// to its other term — the 0.5R floor. THE ENGINE'S REAL REWARD REQUIREMENT WAS
// 0.5R while it documented, displayed and defended 1.0R. 19% of admitted trades
// entered on that gap.
//
// The blend clears so easily because it prices all three legs at 33/33/34 when
// the last two almost never fill (below). FIXED: the blend is weighted by
// measured reachability, 0.55 / 0.30 / 0.15. i_blendWeighted off restores the
// v4.1 arithmetic exactly.
//
// ─────────────────────────────────────────────────────────────────────────────
// FRAGMENTED — the scale-out does not scale out, and could not be watched.
//
// v4.1 kept activeTp1Px and activeTp3Px and NO activeTp2Px. TP2 was drawn on the
// chart, published in the alert payload, and the engine never knew whether it
// traded. A three-leg plan was tracked as two legs. The v3.5.41 manual TP2
// override moved the drawn line and wrote to nothing, because there was no
// tracked value to write to — dead input, dead since it shipped.
//
// Then the fills, which is the substantive half:
//
//     ladder                TP1   TP2   TP3   bars    SL
//     1.5/2.5/4.0 R (v4.1)  50%   14%    6%      6   50%
//
// The second third of the position fills once in seven trades and the last third
// once in sixteen. A plan that leaves in thirds realises nothing like thirds.
//
// FIXED: activeTp2Px exists, is tracked, is honoured by the manual override, and
// the dashboard prints the legs as they fill ("1-3", "12-3").
//
// ─────────────────────────────────────────────────────────────────────────────
// SLOW — every target was a multiple of the STOP.
//
//     tp = entry + dir * risk * rmul          rmul = 1.5 / 2.5 / 4.0
//
// The stop is structural and capped at 3.0 ATR, so TP3 at 4.0R can sit 12 ATR
// out. The plan was slowest and least reachable exactly when the structure was
// widest — backwards: a wide invalidation says the setup needs room, not that
// the market owes you a bigger move. Median TP3 measured 6.18 ATR.
//
// FIXED: i_tpUnit measures the multiples in ATR. Same entries, same stops:
//
//     ladder                TP1   TP2   TP3   bars    SL
//     1.5/2.5/4.0 R (v4.1)  50%   14%    6%      6   50%
//     1.5/2.5/4.0 ATR       52%   16%    8%      6   48%
//     1.0/1.8/3.0 ATR       58%   19%    8%      5   42%
//     0.8/1.4/2.2 ATR       62%   24%   11%      4   38%
//
// Every fill rate rises, the stop-out rate falls 50% -> 38%, the median hold goes
// 6 bars -> 4. The time stop also ships ON at 24 bars; shipping it disabled is
// what let v3.5.23's hanging trades happen and there was no reason to repeat it.
//
// THE HONEST COST: a nearer target is a smaller win. This buys reachability, a
// working de-risk and a scale-out whose legs actually fill. It does not buy edge.
//
// ─────────────────────────────────────────────────────────────────────────────
// WHAT IS STILL NOT PROVEN, and it is the same caveat every table in this file
// carries. The data is synthetic and driftless, where expectancy is ~0 by
// construction. FILL RATES, hold times, the stop's position relative to
// structure, and the gap between what the gate assumes and what the plan
// delivers are all GEOMETRY and do not depend on drift — those are the numbers
// reported above. Profitability is not measured here and nothing above should be
// read as if it were. Run the strategy build over one range before and after.
// ═══════════════════════════════════════════════════════════════════════════════

// ═══════════════════════════════════════════════════════════════════════════════
// v4.1 — EVERY MODE TRADES. MODE IS A STANDARD, NOT A TRIGGER BAN.""",
"header")

io.open(P, "w", encoding="utf-8").write(src)
print("\nwrote %d bytes" % len(src))
