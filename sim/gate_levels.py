"""No reversal, made airtight. Four strictness levels, priced in supply and speed.

WHY THIS EXISTS. v4.3's gate was `close > close[20]` for a long. That guarantees
zero reversals AGAINST THAT DEFINITION, and the definition is weak: price can be
higher than it was 20 bars ago while the last 8 bars have been a hard sell-off,
and buying into that is a reversal by any trader's reading of the chart.

A gate is only as airtight as the definition it enforces, so this prices four
definitions rather than asserting one. Every level is a condition known AT ENTRY
— none of them peeks forward.

  L1 LEG        close > close[N]                       (v4.3)
  L2 +TREND     and the market is actually trending, efficiency ratio >= 0.32.
                In chop there is no trend to continue, so a "continuation" entry
                there is a coin flip that will often be the top of a swing.
  L3 +HTF       and the higher-timeframe EMA bias agrees. Cross-timeframe
                agreement, which the engine already computes and never applied
                to this question.
  L4 +NO COUNTER-SWING
                and price is not currently in a sharp move AGAINST the trade over
                the last 5 bars. This is the one that catches "higher than 20
                bars ago, but falling hard right now".

REPORTED: surviving supply, and SPEED — median bars to resolve — because the
request was that the operation be fast as well as directional.

WHAT THIS CANNOT TELL YOU. Whether any of it makes money. The data is synthetic
and its trend_k is calibrated so momentum earns nothing, so expectancy is not
reported at any level and would be worthless if it were. Supply and speed are
counts and geometry; they are what this harness can honestly produce.
"""
import math
from gen import series_regime
from engine import wilder_atr, ema, frvp
from v4 import triggers_v4
from ladder_diag import ladder, med, pct
from nonrev_mix import walk2

DAYS = 150
SEEDS = (1, 2, 3, 4, 5, 6)
TF = 900
LEG = 20
ER_MIN = 0.32
RMUL = (0.8, 1.4, 2.2)
MINRISK, MAXRISK = 1.0, 3.0
LEVELS = ("none", "L1 leg", "L2 +trend", "L3 +htf", "L4 +no-counter")

rows = {k: [] for k in LEVELS}
leak = {k: 0 for k in LEVELS}

for seed in SEEDS:
    m1 = series_regime(60 * 24 * DAYS, 60, seed=seed)
    bars = []
    step = TF // 60
    for j in range(0, len(m1) - step + 1, step):
        w = m1[j:j + step]
        bars.append((w[0][0], w[0][1], max(b[2] for b in w), min(b[3] for b in w),
                     w[-1][4], sum(b[5] for b in w)))
    c = [b[4] for b in bars]
    T, _b, atr, (POC, VAH, VAL) = triggers_v4(bars, TF)
    e50 = ema(c, 50)

    # efficiency ratio, closed history only
    ER = [None] * len(bars)
    path = 0.0
    for i in range(1, len(bars)):
        path += abs(c[i] - c[i - 1])
        if i > LEG:
            path -= abs(c[i - LEG] - c[i - LEG - 1])
            ER[i] = abs(c[i] - c[i - LEG]) / max(path, 1e-9)

    for i in range(80, len(bars) - 50):
        A = atr[i]
        if A is None or math.isnan(A):
            continue
        legUp = c[i] > c[i - LEG]
        trending = ER[i] is not None and ER[i] >= ER_MIN
        htfUp = not math.isnan(e50[i]) and c[i] > e50[i]
        # sharp counter-move over the last 5 bars, measured in ATR
        sw = (c[i] - c[i - 5]) / max(A, 1e-9)

        for side, is_buy in (("buy", True), ("sell", False)):
            ev = T[i][side]
            if not ev:
                continue
            name, ref, inval = ev[0]
            if is_buy:
                sl = min(inval - A * 0.5, c[i] - A * MINRISK)
                risk = c[i] - sl
            else:
                sl = max(inval + A * 0.5, c[i] + A * MINRISK)
                risk = sl - c[i]
            if risk > A * MAXRISK or risk <= 0:
                continue

            ok = {}
            ok["none"] = True
            ok["L1 leg"] = (is_buy == legUp)
            ok["L2 +trend"] = ok["L1 leg"] and trending
            ok["L3 +htf"] = ok["L2 +trend"] and (is_buy == htfUp)
            counter = (sw < -0.5) if is_buy else (sw > 0.5)
            ok["L4 +no-counter"] = ok["L3 +htf"] and not counter

            struct = [x for x in (VAH[i] if is_buy else VAL[i], POC[i]) if x is not None]
            struct = [x for x in struct if (x > c[i]) == is_buy]
            if is_buy:
                tps = ladder(c[i], risk, A, struct, RMUL, "atr", 2.0)
            else:
                mir = [c[i] + (c[i] - x) for x in struct]
                tps = [c[i] - (t - c[i]) for t in ladder(c[i], risk, A, mir, RMUL, "atr", 2.0)]
            dur, got, how = walk2(bars, i, is_buy, c[i], sl, tps)

            for lv in LEVELS:
                if ok[lv]:
                    rows[lv].append(dict(dur=dur, got=got, how=how))
                    # leakage audit: did a trade AGAINST the leg survive this gate?
                    if is_buy != legUp:
                        leak[lv] += 1

days_total = DAYS * len(SEEDS)
base = len(rows["none"])

print("NO REVERSAL, MADE AIRTIGHT — four definitions priced")
print("15m, %d days x %d seeds. Same triggers, same stop, same ATR ladder.\n" % (DAYS, len(SEEDS)))
print("  %-16s%10s%9s%10s%8s%8s%8s%8s%13s" %
      ("gate", "trades/d", "kept", "bars", "TP1", "TP2", "SL", "BE", "against-leg"))
for lv in LEVELS:
    d = rows[lv]
    n = len(d)
    if n == 0:
        print("  %-16s no trades" % lv)
        continue
    print("  %-16s%10.2f%8.0f%%%10d%7.0f%%%7.0f%%%7.0f%%%7.0f%%%12d" % (
        lv, n / days_total, pct(n, base), med([x["dur"] for x in d]),
        pct(sum(1 for x in d if x["got"][0]), n),
        pct(sum(1 for x in d if x["got"][1]), n),
        pct(sum(1 for x in d if x["how"] == "sl"), n),
        pct(sum(1 for x in d if x["how"] == "be"), n),
        leak[lv]))

print("\n  'against-leg' is the LEAKAGE AUDIT: how many surviving trades ran")
print("  counter to the leg. Every level from L1 down must read exactly 0, and")
print("  that is the claim 'no reversal trades' has to be able to make.")
print("\n  'bars' is the speed column. SL and BE are geometry. EXPECTANCY IS NOT")
print("  REPORTED AND WAS NOT COMPUTED — this generator's trend_k is calibrated")
print("  so momentum earns nothing, so it cannot price a directional filter.")
print("  Only your Strategy Tester on real gold can settle that.")
