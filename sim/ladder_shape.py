"""The scale-out does not scale out. What SHAPE of ladder actually completes?

ladder_diag.py measured v4.1's 1.5 / 2.5 / 4.0 ladder on 15m and found:

    TP1 reached 50%   TP2 reached 14%   TP3 reached 6%

The plan says the position leaves in thirds. In practice the second third
fills once in seven trades and the last third once in sixteen. The scale-out
is a three-leg plan of which two legs are decorative.

THIS IS NOT COSMETIC, because the reward gate PRICES all three legs:

    blend = (0.33*(tp1-e) + 0.33*(tp2-e) + 0.34*(tp3-e)) / risk

i_minBlendRR (1.3 by default) admits a setup on that number, and 0.34 of it
is a target that fills 6% of the time. The gate is not measuring the plan,
it is measuring a plan that would exist if every leg filled. A setup whose
TP1 is poor and whose TP3 is enormous passes on the strength of the leg
least likely to be reached — and v3.5.26 introduced the blended path
SPECIFICALLY to admit more of those.

Measured here: the reward the gate ASSUMES against the reward actually
realised, and then a sweep of ladder shapes to find one whose legs fill.
"""
import math
from gen import series_regime
from engine import wilder_atr, frvp
from v4 import triggers_v4
from ladder_diag import ladder, walk, med, pct

DAYS = 150
SEEDS = (1, 2, 3, 4, 5, 6)
TF = 900
MAXRISK = 3.0
MINRISK = 1.0
W = (0.33, 0.33, 0.34)

SHAPES = (
    ((1.5, 2.5, 4.0), "risk", "v4.1  1.5/2.5/4.0 R"),
    ((1.5, 2.5, 4.0), "atr",  "      1.5/2.5/4.0 ATR"),
    ((1.0, 1.8, 3.0), "atr",  "      1.0/1.8/3.0 ATR"),
    ((0.8, 1.4, 2.2), "atr",  "      0.8/1.4/2.2 ATR"),
    ((0.6, 1.1, 1.8), "atr",  "      0.6/1.1/1.8 ATR"),
)

rows = {k[2]: [] for k in SHAPES}

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

    for i in range(80, len(bars) - 50):
        A = atr[i]
        if A is None or math.isnan(A):
            continue
        ev = T[i]["buy"]
        if not ev:
            continue
        inval = ev[0][2]
        sl = min(inval - A * 0.5, c[i] - A * 0.5, c[i] - A * MINRISK)
        risk = c[i] - sl
        if risk > A * MAXRISK:
            continue
        struct = [x for x in (VAH[i], POC[i]) if x is not None]

        for rmul, unit, label in SHAPES:
            tps = ladder(c[i], risk, A, struct, rmul, unit, 2.0)
            dur, got, how = walk(bars, i, c[i], sl, tps)
            assumed = sum(w * (t - c[i]) for w, t in zip(W, tps)) / risk
            realised = 0.0
            stopped = (how == "sl")
            for t in range(3):
                if got[t]:
                    realised += W[t] * (tps[t] - c[i]) / risk
            rem = sum(W[t] for t in range(3) if not got[t])
            if how == "sl":
                realised += rem * -1.0
            elif how == "be":
                realised += 0.0
            rows[label].append(dict(dur=dur, got=got, how=how,
                                    assumed=assumed, realised=realised))

print("ME PRO v4.1 — THE SCALE-OUT DOES NOT SCALE OUT")
print("15m, %d days x %d seeds, %d bullish plans per shape." % (DAYS, len(SEEDS), len(rows[SHAPES[0][2]])))
print("Same entries and the same stop in every row — only the ladder changes.\n")
print("  %-26s%7s%7s%7s%7s%8s%11s%11s" %
      ("ladder", "TP1%", "TP2%", "TP3%", "bars", "SL%", "gate says", "realised"))
for _r, _u, label in SHAPES:
    d = rows[label]
    n = len(d)
    print("  %-26s%6.0f%%%6.0f%%%6.0f%%%7d%7.0f%%%11.2f%11.2f" % (
        label,
        pct(sum(1 for x in d if x["got"][0]), n),
        pct(sum(1 for x in d if x["got"][1]), n),
        pct(sum(1 for x in d if x["got"][2]), n),
        med([x["dur"] for x in d]),
        pct(sum(1 for x in d if x["how"] == "sl"), n),
        med([x["assumed"] for x in d]),
        sum(x["realised"] for x in d) / n))

print("\n  'gate says'  median blended reward i_minBlendRR is compared against")
print("  'realised'   mean R actually booked by walking the same plan forward")
print("\n  The gap between those two columns is the blended reward gate")
print("  measuring a plan whose last two legs mostly never fill.")
print("\n  CAVEAT, and it is the same one every table in this project carries:")
print("  synthetic driftless data, so the LEVEL of the realised column is not")
print("  a forecast of anything. Fill RATES and the gap between assumed and")
print("  realised are geometry and do not depend on drift.")
