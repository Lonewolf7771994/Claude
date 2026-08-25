"""FOUR non-reversal trades a day. Which timeframe and settings can deliver it?

The target is specific, so it gets searched rather than guessed at: at least
4 signals/day, both sides, every one of them running WITH the trend.

WHAT MAKES THIS HARD, from this project's own history. v3.5.40 measured the
engine converting 1-3% of triggers at every timeframe and concluded 3/day was
unreachable on 15m. v4.0 then roughly doubled trigger supply with the band
rejections, and v4.7 added POC and CRT on top, so the ceiling moved — but the
arithmetic is unchanged: signals/day = triggers/day x conversion, and the
no-reversal gate takes a large bite out of conversion by design.

There are only two ways to reach 4: more triggers (a lower timeframe) or a
higher conversion (a looser stack). Both are priced here.

REPORTED per configuration: signals/day, and the OUTCOME MIX — what fraction
reach TP1, TP2, TP3, and what fraction stop out. Mix is geometry and does not
depend on the generator's drift. Expectancy is NOT reported and was not
computed; this harness cannot price a directional method and no price feed was
reachable.

SPREAD IS PRICED SEPARATELY AND IT IS THE REAL COST OF DROPPING TIMEFRAME.
v3.5.40 measured spread against a ~1.5 ATR stop on XAUUSD:
    1m 25.8%   3m 14.9%   5m 11.5%   15m 6.7%   30m 4.7%
A trade taken on 3m gives up more than twice as much of its stop to the spread
as the same trade on 15m. That is a cost no amount of tuning removes.
"""
import math
from gen import series_regime
from engine import wilder_atr, ema, rsi as rsi_f, sma_prior
from v4 import triggers_v4
from ladder_diag import ladder, med, pct
from nonrev_mix import walk2

DAYS, SEEDS = 120, (1, 2, 3)
LEG = 20
PRISM_ATR, PRISM_BASE, PRISM_REFR, PRISM_RANK = 12, 3.0, 0.35, 200
RMUL = (0.8, 1.4, 2.2)
SPREAD_PCT = {180: 14.9, 300: 11.5, 900: 6.7}

# name, body xATR, relvol, of%, delta, cooldown, minRisk, maxRisk
CFGS = [
    ("strict   ", 0.50, 1.20, 60.0, 0.20, 12, 1.0, 3.0),
    ("moderate ", 0.40, 1.00, 58.0, 0.15,  6, 0.7, 3.0),
    ("scalp    ", 0.30, 0.80, 56.0, 0.12,  3, 0.5, 3.0),
    ("scalp+   ", 0.25, 0.70, 54.0, 0.10,  2, 0.4, 3.0),
]


def build(seed, tf):
    m1 = series_regime(60 * 24 * DAYS, 60, seed=seed)
    out, st = [], tf // 60
    for j in range(0, len(m1) - st + 1, st):
        w = m1[j:j + st]
        out.append((w[0][0], w[0][1], max(b[2] for b in w), min(b[3] for b in w),
                    w[-1][4], sum(b[5] for b in w)))
    return out


results = {}

for tf in (180, 300, 900):
    for cname, BODY, VOLF, OFT, DELTA, CD, MINR, MAXR in CFGS:
        key = (tf, cname)
        results[key] = {"n": 0, "trig": 0, "rows": []}

    for seed in SEEDS:
        bars = build(seed, tf)
        n = len(bars)
        o = [b[1] for b in bars]; h = [b[2] for b in bars]
        l = [b[3] for b in bars]; c = [b[4] for b in bars]; v = [b[5] for b in bars]
        T, (vw, u1, l1, u2, l2), atr, (POC, VAH, VAL) = triggers_v4(bars, tf)
        e50 = ema(c, 50); rs = rsi_f(c, 14); vavg = sma_prior(v, 20)
        patr = wilder_atr(h, l, c, PRISM_ATR)

        # the v4.6 trail — the LEG half of the no-reversal gate
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

        for cname, BODY, VOLF, OFT, DELTA, CD, MINR, MAXR in CFGS:
            key = (tf, cname)
            last = -10**9
            for i in range(80, n - 40):
                A = atr[i]
                if A is None or math.isnan(A) or math.isnan(vavg[i]):
                    continue
                rng = max(h[i]-l[i], 1e-9); cp = (c[i]-l[i])/rng
                body = abs(c[i]-o[i]); relv = v[i]/max(vavg[i], 1e-9)
                delta = (c[i]-o[i])/rng
                if T[i]["buy"] or T[i]["sell"]:
                    results[key]["trig"] += 1
                if i - last < CD:
                    continue

                for side, is_buy in (("buy", True), ("sell", False)):
                    ev = T[i][side]
                    if not ev:
                        continue
                    # NO-REVERSAL, always on: trade must run with the trail
                    if is_buy != (pdir[i] == 1):
                        continue
                    if (c[i] > o[i]) != is_buy:
                        continue
                    if body < A * BODY or relv < VOLF:
                        continue
                    ofpct = cp * 100.0 if is_buy else (100.0 - cp * 100.0)
                    if ofpct < OFT:
                        continue
                    if (delta < DELTA) if is_buy else (delta > -DELTA):
                        continue
                    if not (35 <= rs[i] <= 80):
                        continue
                    inval = ev[0][2]
                    if is_buy:
                        sl = min(inval - A*0.5, c[i] - A*MINR); risk = c[i]-sl
                    else:
                        sl = max(inval + A*0.5, c[i] + A*MINR); risk = sl-c[i]
                    if risk <= 0 or risk > A*MAXR:
                        continue
                    struct = [x for x in (VAH[i] if is_buy else VAL[i], POC[i]) if x is not None]
                    struct = [x for x in struct if (x > c[i]) == is_buy]
                    if is_buy:
                        tps = ladder(c[i], risk, A, struct, RMUL, "atr", 2.0)
                    else:
                        mir = [c[i] + (c[i]-x) for x in struct]
                        tps = [c[i] - (t-c[i]) for t in ladder(c[i], risk, A, mir, RMUL, "atr", 2.0)]
                    dur, got, how = walk2(bars, i, is_buy, c[i], sl, tps)
                    results[key]["n"] += 1
                    results[key]["rows"].append(dict(dur=dur, got=got, how=how))
                    last = i
                    break

days = DAYS * len(SEEDS)
print("FOUR NON-REVERSAL TRADES A DAY — what it takes, and what it costs")
print("%d days x %d seeds. No-reversal gate ON in every row (trade with the trail)." % (DAYS, len(SEEDS)))
print("ATR ladder 0.8/1.4/2.2, structural stop.\n")
print("  %-4s %-10s%8s%9s%7s%7s%7s%7s%6s%10s" %
      ("tf", "preset", "trig/d", "SIG/DAY", "TP1", "TP2", "TP3", "SL", "bars", "spread%"))
for tf in (180, 300, 900):
    for cname, *_ in CFGS:
        r = results[(tf, cname)]
        d = r["rows"]; N = len(d)
        if N == 0:
            print("  %-4s %-10s%8.1f%9.2f      no trades" % (str(tf//60)+"m", cname, r["trig"]/days, 0))
            continue
        rate = N / days
        flag = " ***" if rate >= 4.0 else ""
        print("  %-4s %-10s%8.1f%9.2f%6.0f%%%6.0f%%%6.0f%%%6.0f%%%6d%9.1f%%%s" % (
            str(tf//60)+"m", cname, r["trig"]/days, rate,
            pct(sum(1 for x in d if x["got"][0]), N),
            pct(sum(1 for x in d if x["got"][1]), N),
            pct(sum(1 for x in d if x["got"][2]), N),
            pct(sum(1 for x in d if x["how"] == "sl"), N),
            med([x["dur"] for x in d]), SPREAD_PCT[tf], flag))
    print()

print("  *** = clears the 4/day target.")
print("\n  spread%% is the share of a ~1.5 ATR stop the XAUUSD spread consumes at")
print("  that timeframe (measured in v3.5.40). It is the price of dropping down")
print("  and no setting removes it — a 3m trade gives up more than twice as much")
print("  of its stop as the same trade on 15m.")
print("\n  Outcome mix is geometry. NO EXPECTANCY IS REPORTED and none was")
print("  computed — this generator cannot price a directional method.")
