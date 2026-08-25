"""What actually brings the rate back, ranked by measured effect.

why_silent.py found v4.7's defaults convert 1.44% of triggers into 0.28
signals/day on 15m, and named the blockers. This sweeps the levers that
matter, one at a time and then together, so the cost of each is separable.

The no-reversal gate is NOT abandoned in any row here: every configuration
below still requires the trade to run with the trend. What varies is HOW
HARD the surrounding stack is, because that is where the silence came from.
"""
import math
from gen import series_regime
from engine import wilder_atr, ema, rsi as rsi_f, sma_prior
from v4 import triggers_v4

DAYS, SEEDS, TF, LEG = 150, (1, 2, 3, 4), 900, 20
PRISM_ATR, PRISM_BASE, PRISM_REFR, PRISM_RANK = 12, 3.0, 0.35, 200

CFG = [
    dict(name="v4.7 defaults",        er=0.32, body=0.50, vol=1.2, delta=0.20, of=60.0, mode="bal",  cd=12),
    dict(name="ER 0.32 -> 0.20",      er=0.20, body=0.50, vol=1.2, delta=0.20, of=60.0, mode="bal",  cd=12),
    dict(name="body 0.50 -> 0.35",    er=0.32, body=0.35, vol=1.2, delta=0.20, of=60.0, mode="bal",  cd=12),
    dict(name="vol 1.2 -> 0.9",       er=0.32, body=0.50, vol=0.9, delta=0.20, of=60.0, mode="bal",  cd=12),
    dict(name="gate Leg only (no ER)",er=0.00, body=0.50, vol=1.2, delta=0.20, of=60.0, mode="bal",  cd=12),
    dict(name="mode Aggressive",      er=0.32, body=0.50, vol=1.2, delta=0.20, of=60.0, mode="aggr", cd=12),
    dict(name="ER .20 + body .35",    er=0.20, body=0.35, vol=1.2, delta=0.20, of=60.0, mode="bal",  cd=12),
    dict(name="ER .20 body .35 vol .9",er=0.20, body=0.35, vol=0.9, delta=0.15, of=57.0, mode="bal", cd=6),
    dict(name="  ^ + Aggressive",     er=0.20, body=0.35, vol=0.9, delta=0.15, of=57.0, mode="aggr", cd=6),
]

res = {c["name"]: [0, 0] for c in CFG}   # [triggers, signals]
days = DAYS * len(SEEDS)

for seed in SEEDS:
    m1 = series_regime(60 * 24 * DAYS, 60, seed=seed)
    bars = []
    st = TF // 60
    for j in range(0, len(m1) - st + 1, st):
        w = m1[j:j + st]
        bars.append((w[0][0], w[0][1], max(b[2] for b in w), min(b[3] for b in w),
                     w[-1][4], sum(b[5] for b in w)))
    n = len(bars)
    o = [b[1] for b in bars]; h = [b[2] for b in bars]
    l = [b[3] for b in bars]; c = [b[4] for b in bars]; v = [b[5] for b in bars]
    T, (vw, u1, l1, u2, l2), atr, _f = triggers_v4(bars, TF)
    e50 = ema(c, 50); rs = rsi_f(c, 14); vavg = sma_prior(v, 20)
    patr = wilder_atr(h, l, c, PRISM_ATR)

    pdir = [1] * n; pup = [None] * n; pdn = [None] * n
    for i in range(n):
        A = patr[i]
        if A is None or math.isnan(A):
            continue
        win = [x for x in patr[max(0, i - PRISM_RANK):i + 1] if x is not None and not math.isnan(x)]
        rank = (sum(1 for x in win if x <= A) / len(win)) if win else 0.5
        mult = max(0.2, PRISM_BASE - PRISM_REFR * (1.0 - rank))
        ur, dr = c[i] - A * mult, c[i] + A * mult
        pup[i] = ur if (i == 0 or pup[i-1] is None or c[i-1] <= pup[i-1]) else max(ur, pup[i-1])
        pdn[i] = dr if (i == 0 or pdn[i-1] is None or c[i-1] >= pdn[i-1]) else min(dr, pdn[i-1])
        if i > 0:
            pdir[i] = 1 if c[i] > (pdn[i-1] or dr) else (-1 if c[i] < (pup[i-1] or ur) else pdir[i-1])

    ER = [None] * n; path = 0.0
    for i in range(1, n):
        path += abs(c[i] - c[i-1])
        if i > LEG:
            path -= abs(c[i-LEG] - c[i-LEG-1])
            ER[i] = abs(c[i] - c[i-LEG]) / max(path, 1e-9)

    for cfg in CFG:
        last = -10**9
        for i in range(80, n - 5):
            A = atr[i]
            if A is None or math.isnan(A) or math.isnan(vavg[i]):
                continue
            if not T[i]["buy"]:
                continue
            if cfg is CFG[0]:
                pass
            res[cfg["name"]][0] += 1
            rng = max(h[i]-l[i], 1e-9); cp = (c[i]-l[i])/rng
            body = abs(c[i]-o[i]); relv = v[i]/max(vavg[i], 1e-9)
            delta = (c[i]-o[i])/rng
            htfUp = not math.isnan(e50[i]) and c[i] > e50[i]
            ok = (c[i] > o[i]) and body >= A*cfg["body"] and relv >= cfg["vol"] \
                 and cp*100.0 >= cfg["of"] and delta >= cfg["delta"] \
                 and 40 <= rs[i] <= 78 and (i - last) >= cfg["cd"]
            if cfg["mode"] == "bal":
                ok = ok and htfUp and c[i] > vw[i]
            # the no-reversal gate is present in EVERY row
            ok = ok and pdir[i] == 1 and htfUp
            if cfg["er"] > 0:
                ok = ok and ER[i] is not None and ER[i] >= cfg["er"]
            inval = T[i]["buy"][0][2]
            sl = min(inval - A*0.5, c[i] - A*1.0)
            ok = ok and (c[i]-sl) <= A*3.0
            if ok:
                res[cfg["name"]][1] += 1
                last = i

base = res[CFG[0]["name"]][1] / days
print("WHAT BRINGS THE RATE BACK — 15m, %d days x %d seeds, long side" % (DAYS, len(SEEDS)))
print("Every row still enforces the no-reversal gate (trail + HTF).\n")
print("  %-26s%11s%11s%9s" % ("configuration", "signals/day", "vs default", "conv %"))
for cfg in CFG:
    t, s = res[cfg["name"]]
    d = s / days
    mult = ("%.1fx" % (d / base)) if base > 0 else "n/a"
    print("  %-26s%11.2f%11s%8.2f%%" % (cfg["name"], d, mult, 100.0*s/max(t, 1)))
print("\n  Fill rates and expectancy are NOT shown and were not computed. This")
print("  table answers one question — how many trades each setting produces —")
print("  and that is a count, which this harness can produce honestly.")
