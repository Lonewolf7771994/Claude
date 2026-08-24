"""Does v4.1 still HAVE a reward gate? Measure which path admits each trade.

v3.5.8 added the engine's first and only reward check: TP1 must sit at least
i_minRR (1.0) multiples of the stop away, or the setup is skipped. Its
changelog is explicit about why — a first target closer than the stop turns
trades into scratches, and TP1 also arms the breakeven move.

v3.5.26 then added an ALTERNATIVE way to pass:

    rrOk = effMinRR <= 0  or  rrStrict  or  blendOk

    blendOk = blend >= i_minBlendRR (1.3)  and  rr >= i_minTp1Floor (0.5)

ladder_shape.py measured the median blended reward at 2.68 against a 1.3
threshold. If that holds across the distribution then blendOk is satisfied
almost always, the `or` short-circuits the strict test, and the effective
reward requirement is not 1.0R on TP1 — it is the 0.5R floor.

That would mean the engine believes it has a 1.0R reward gate and actually
has a 0.5R one, with the difference hidden behind an `or`.

Measured below: of the setups admitted, how many clear the strict test, and
how many are admitted ONLY by the blended path.
"""
import math
from gen import series_regime
from engine import wilder_atr, frvp
from v4 import triggers_v4
from ladder_diag import ladder, pct, med

DAYS = 150
SEEDS = (1, 2, 3)
TF = 900
RMUL = (1.5, 2.5, 4.0)
MINRR = 1.0
MINBLEND = 1.3
TP1FLOOR = 0.5
W = (0.33, 0.33, 0.34)

strict_only = blend_only = both = neither = 0
blends = []

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
        sl = min(inval - A * 0.5, c[i] - A * 0.5, c[i] - A * 1.0)
        risk = c[i] - sl
        if risk > A * 3.0:
            continue
        struct = [x for x in (VAH[i], POC[i]) if x is not None]
        tps = ladder(c[i], risk, A, struct, RMUL, "risk", 2.0)

        rr = (tps[0] - c[i]) / risk
        blend = sum(w * (t - c[i]) for w, t in zip(W, tps)) / risk
        blends.append(blend)

        s = rr >= MINRR
        b = (blend >= MINBLEND) and (rr >= TP1FLOOR)
        if s and b:
            both += 1
        elif s:
            strict_only += 1
        elif b:
            blend_only += 1
        else:
            neither += 1

adm = both + strict_only + blend_only
tot = adm + neither

print("ME PRO v4.1 — WHICH PATH ADMITS THE TRADE?")
print("15m, %d days x %d seeds, %d setups reaching the reward gate.\n" % (DAYS, len(SEEDS), tot))
print("  admitted                       %6d   %5.0f%% of setups" % (adm, pct(adm, tot)))
print("    clears the strict 1.0R test  %6d   %5.0f%% of admitted" % (both + strict_only, pct(both + strict_only, adm)))
print("    admitted ONLY by the blend   %6d   %5.0f%% of admitted" % (blend_only, pct(blend_only, adm)))
print("  rejected                       %6d   %5.0f%% of setups" % (neither, pct(neither, tot)))
print("\n  blended reward: median %.2f against a %.1f threshold" % (med(blends), MINBLEND))
print("  share of setups whose blend clears 1.3:  %.0f%%" % pct(sum(1 for x in blends if x >= MINBLEND), len(blends)))
print("\n  If that last figure is near 100%, the blended path is not an")
print("  alternative test — it is an unconditional pass, and the strict 1.0R")
print("  gate the engine documents is never what decides a trade.")
