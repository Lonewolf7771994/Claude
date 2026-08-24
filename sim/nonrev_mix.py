"""Non-reversal costs 45% of supply. Does it buy anything measurable?

nonrev.py established the price: filtering to trades that run WITH the leg
removes 45% of raw trigger supply, and the loss falls almost entirely on the
band / band2 / value triggers (43-55% reversal) while MSS and FVG barely
notice (7% and 13%).

Cutting trade count is only worth doing if what survives is better. This
splits the SAME trigger set into reversal and continuation and walks both
forward through the identical stop and the identical ladder, so the only
difference between the two rows is whether the trade agreed with the leg.

Outcome MIX is geometry — what fraction of trades end each way — and does not
depend on the generator's drift, which is why it is reported here when
expectancy is not.
"""
import math
from gen import series_regime
from engine import wilder_atr, frvp
from v4 import triggers_v4
from ladder_diag import ladder, med, pct

DAYS = 150
SEEDS = (1, 2, 3, 4, 5, 6)
TF = 900
LEG = 20
RMUL = (0.8, 1.4, 2.2)      # the v4.2 ATR ladder
MINRISK, MAXRISK = 1.0, 3.0


def walk2(bars, i, is_buy, entry, sl, tps, max_look=400):
    got = [False] * 3
    stop = sl
    for k in range(i + 1, min(i + 1 + max_look, len(bars))):
        h, l = bars[k][2], bars[k][3]
        hit = l <= stop if is_buy else h >= stop
        for t in range(3):
            if got[t]:
                continue
            reach = h >= tps[t] if is_buy else l <= tps[t]
            if reach and not (hit and t == 0 and not got[0]):
                got[t] = True
                if t == 0:
                    stop = entry
        if hit:
            return k - i, got, ("be" if stop == entry else "sl")
        if all(got):
            return k - i, got, "tp3"
    return max_look, got, "time"


rows = {"continuation": [], "reversal": []}
per_trig = {}

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
        legUp = c[i] > c[i - LEG]
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
            struct = [x for x in (VAH[i] if is_buy else VAL[i], POC[i]) if x is not None]
            struct = [x for x in struct if (x > c[i]) == is_buy]
            tps = ladder(c[i], risk, A, struct, RMUL, "atr", 2.0) if is_buy else \
                  [c[i] - (t - c[i]) for t in ladder(c[i], risk, A,
                   [c[i] + (c[i] - x) for x in struct], RMUL, "atr", 2.0)]
            dur, got, how = walk2(bars, i, is_buy, c[i], sl, tps)
            kind = "continuation" if (is_buy == legUp) else "reversal"
            rec = dict(dur=dur, got=got, how=how)
            rows[kind].append(rec)
            per_trig.setdefault(name, {"continuation": [], "reversal": []})[kind].append(rec)


def line(label, d):
    n = len(d)
    if n == 0:
        print("  %-16s  no trades" % label)
        return
    print("  %-16s%9d%8.0f%%%8.0f%%%8.0f%%%8.0f%%%8.0f%%%7d" % (
        label, n,
        pct(sum(1 for x in d if x["got"][0]), n),
        pct(sum(1 for x in d if x["got"][1]), n),
        pct(sum(1 for x in d if x["got"][2]), n),
        pct(sum(1 for x in d if x["how"] == "sl"), n),
        pct(sum(1 for x in d if x["how"] == "be"), n),
        med([x["dur"] for x in d])))


print("DOES NON-REVERSAL BUY ANYTHING? — outcome mix, same stop, same ladder")
print("15m, %d days x %d seeds, ATR ladder 0.8/1.4/2.2, risk 1.0-3.0 ATR.\n" % (DAYS, len(SEEDS)))
print("  %-16s%9s%8s%8s%8s%8s%8s%7s" %
      ("", "trades", "TP1", "TP2", "TP3", "SL", "BE", "bars"))
line("continuation", rows["continuation"])
line("reversal", rows["reversal"])

print("\n  BY TRIGGER — continuation row first, reversal beneath it")
for name in sorted(per_trig, key=lambda k: -(len(per_trig[k]["continuation"]) + len(per_trig[k]["reversal"]))):
    print("  %s" % name)
    line("    with leg", per_trig[name]["continuation"])
    line("    against leg", per_trig[name]["reversal"])

print("\n  SL is the column that decides whether the 45% supply cut is worth")
print("  paying. Outcome mix is geometry and survives the retraction; mean R is")
print("  deliberately absent because this generator cannot price it.")
