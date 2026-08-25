"""THE CEILING PER MODE — how fast can each mode go, and where does it stop.

pace.py showed that even the loosest full-stack configuration tops out around
3.6 signals/day on 5m in Aggressive and Scalp, and only 1.5-1.9 in Balanced and
Strict. That gap is not a tuning failure, it is the mode definition: Balanced
and Strict require HTF agreement AND the correct side of VWAP, which blocked
52.4% and 56.2% of all triggers respectively. No filter setting reaches past a
gate that is part of what the mode means.

So this sweeps timeframe as well, which is the only lever that raises trigger
SUPPLY rather than conversion, and reports the ceiling for each mode with the
cost printed next to it.

Every row keeps the no-reversal trail. Nothing here trades against the trend.
"""
import math
from fullstack import build, prep, MODES, DAYS, SEEDS
import fullstack
from pace import evaluate, RMUL
from ladder_diag import med, pct
from nonrev_mix import walk2

SPREAD_PCT = {180: 14.9, 300: 11.5, 900: 6.7}

#  name        body  vol   of%  delta cool minR  minRR dir
GRID = [
    ("balanced ", 0.35, 0.90, 56.0, 0.12, 4, 0.6, 0.60, 1),
    ("active   ", 0.30, 0.80, 55.0, 0.10, 3, 0.5, 0.55, 0),
    ("rapid    ", 0.25, 0.70, 53.0, 0.08, 2, 0.4, 0.50, 0),
]

days = DAYS * len(SEEDS)
print("PER-MODE CEILING — %d days x %d seeds, both sides, trail always on\n" % (DAYS, len(SEEDS)))
print("  %-5s%-11s%4s" % ("tf", "preset", "dir"), end="")
for m in MODES:
    print("%11s" % m[:9], end="")
print("      TP1   TP2   TP3    SL  bars  sprd")

for tf in (180, 300, 900):
    fullstack.TF = tf
    for g in GRID:
        name, body, vol, of, delta, cool, minr, minrr, dep = g
        cfg = dict(body=body, vol=vol, of=of, delta=delta, cool=cool,
                   minr=minr, minrr=minrr, dir=dep)
        rows = {m: [] for m in MODES}
        for seed in SEEDS:
            bars = build(seed, tf)
            D = prep(bars)
            for mode in MODES:
                last = -10**9
                for i in range(80, D["n"] - 40):
                    A = D["atr"][i]
                    if A is None or math.isnan(A) or math.isnan(D["vavg"][i]):
                        continue
                    for is_buy in (True, False):
                        ok, sl, tps = evaluate(D, i, is_buy, mode, last, cfg)
                        if not ok:
                            continue
                        dur, got, how = walk2(bars, i, is_buy, D["c"][i], sl, tps)
                        rows[mode].append(dict(dur=dur, got=got, how=how))
                        last = i
                        break
        line = "  %-5s%-11s%4d" % (str(tf//60)+"m", name, dep)
        allr = []
        for m in MODES:
            r = len(rows[m]) / days
            allr += rows[m]
            line += "%10.2f%s" % (r, "*" if r >= 4.0 else " ")
        N = len(allr)
        if N:
            line += "%8.0f%%%6.0f%%%6.0f%%%6.0f%%%6d%5.1f%%" % (
                pct(sum(1 for x in allr if x["got"][0]), N),
                pct(sum(1 for x in allr if x["got"][1]), N),
                pct(sum(1 for x in allr if x["got"][2]), N),
                pct(sum(1 for x in allr if x["how"] == "sl"), N),
                med([x["dur"] for x in allr]), SPREAD_PCT[tf])
        print(line)
    print()

print("  * = clears 4 signals/day in that mode.")
print("  sprd = share of a ~1.5 ATR stop the XAUUSD spread consumes at that")
print("  timeframe. It is a real cost and is NOT included in the outcome mix.")
print("  NO EXPECTANCY IS REPORTED and none was computed.")
