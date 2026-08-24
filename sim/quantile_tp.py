"""Targets at the MEASURED quantiles of movement, not at guessed ATR multiples.

Every target this engine has ever placed came from a number somebody chose:
1.5/2.5/4.0 R in v4.1, 0.8/1.4/2.2 ATR in v4.4. Both are guesses wearing
decimal points. Nothing ever asked the instrument how far it actually travels.

WHAT THIS TESTS. For every bar at least H bars in the past, the MAXIMUM
FAVOURABLE EXCURSION over the following H bars is measured and divided by the
ATR at that bar. That is a distribution of how far this market really moves, in
its own volatility units, over the horizon the engine actually holds for. Then:

    TP1 = the q1-th percentile of that distribution
    TP2 = the q2-th
    TP3 = the q3-th

A target at the 50th percentile is, by construction, reached by about half of
all H-bar windows. That is a claim the ATR guesses cannot make at all.

NON-REPAINTING BY CONSTRUCTION. The window ends H bars BEFORE the current bar,
so every excursion used is fully resolved history. Nothing in the distribution
can change after the fact.

Compared here against v4.4's fixed 0.8/1.4/2.2 ATR ladder on identical entries,
identical stops and the identical no-reversal gate.
"""
import math
from gen import series_regime
from engine import wilder_atr, ema
from v4 import triggers_v4
from ladder_diag import med, pct
from nonrev_mix import walk2

DAYS = 150
SEEDS = (1, 2, 3, 4, 5, 6)
TF = 900
LEG = 20
ER_MIN = 0.32
H = 16                      # horizon: the engine's own time stop
WIN = 500                   # how much history the distribution is built from
FIXED = (0.8, 1.4, 2.2)
QS = (0.50, 0.70, 0.85)
MINRISK, MAXRISK = 1.0, 3.0


def quantile(sorted_xs, q):
    if not sorted_xs:
        return None
    k = min(len(sorted_xs) - 1, max(0, int(round(q * (len(sorted_xs) - 1)))))
    return sorted_xs[k]


rows = {"fixed ATR 0.8/1.4/2.2": [], "quantile 50/70/85": []}
qsnap = []

for seed in SEEDS:
    m1 = series_regime(60 * 24 * DAYS, 60, seed=seed)
    bars = []
    step = TF // 60
    for j in range(0, len(m1) - step + 1, step):
        w = m1[j:j + step]
        bars.append((w[0][0], w[0][1], max(b[2] for b in w), min(b[3] for b in w),
                     w[-1][4], sum(b[5] for b in w)))
    n = len(bars)
    c = [b[4] for b in bars]; hi = [b[2] for b in bars]; lo = [b[3] for b in bars]
    T, _b, atr, _f = triggers_v4(bars, TF)
    e50 = ema(c, 50)

    # per-bar resolved excursions, in ATR — long and short side separately
    mfeL = [None] * n
    mfeS = [None] * n
    for i in range(n - H):
        A = atr[i]
        if A is None or math.isnan(A) or A <= 0:
            continue
        top = max(hi[i + 1:i + 1 + H])
        bot = min(lo[i + 1:i + 1 + H])
        mfeL[i] = (top - c[i]) / A
        mfeS[i] = (c[i] - bot) / A

    ER = [None] * n
    path = 0.0
    for i in range(1, n):
        path += abs(c[i] - c[i - 1])
        if i > LEG:
            path -= abs(c[i - LEG] - c[i - LEG - 1])
            ER[i] = abs(c[i] - c[i - LEG]) / max(path, 1e-9)

    for i in range(WIN + H + 5, n - 50):
        A = atr[i]
        if A is None or math.isnan(A):
            continue
        if ER[i] is None or ER[i] < ER_MIN:
            continue
        legUp = c[i] > c[i - LEG]
        htfUp = not math.isnan(e50[i]) and c[i] > e50[i]

        for side, is_buy in (("buy", True), ("sell", False)):
            ev = T[i][side]
            if not ev:
                continue
            # the v4.4 default gate: leg + trend + HTF
            if is_buy != legUp or is_buy != htfUp:
                continue
            name, ref, inval = ev[0]
            if is_buy:
                sl = min(inval - A * 0.5, c[i] - A * MINRISK); risk = c[i] - sl
            else:
                sl = max(inval + A * 0.5, c[i] + A * MINRISK); risk = sl - c[i]
            if risk > A * MAXRISK or risk <= 0:
                continue

            # the distribution, built ONLY from windows that fully resolved
            # before this bar: i-WIN-H .. i-H-1
            src = mfeL if is_buy else mfeS
            sample = sorted(x for x in src[i - WIN - H:i - H] if x is not None)
            if len(sample) < 100:
                continue
            qmul = [quantile(sample, q) for q in QS]
            if any(x is None or x <= 0 for x in qmul):
                continue
            if is_buy:
                qsnap.append(tuple(qmul))

            d = 1.0 if is_buy else -1.0
            for label, mults in (("fixed ATR 0.8/1.4/2.2", FIXED),
                                 ("quantile 50/70/85", qmul)):
                tps = sorted([c[i] + d * A * m for m in mults], reverse=not is_buy)
                dur, got, how = walk2(bars, i, is_buy, c[i], sl, tps)
                rows[label].append(dict(dur=dur, got=got, how=how,
                                        t3=abs(tps[2] - c[i]) / A))

print("TARGETS AT THE MEASURED QUANTILES OF MOVEMENT")
print("15m, %d days x %d seeds. v4.4 default gate (leg+trend+HTF), same stop." % (DAYS, len(SEEDS)))
print("Distribution: max favourable excursion over %d bars, %d-bar window,\n"
      "fully resolved before the entry bar.\n" % (H, WIN))
print("  %-26s%9s%8s%8s%8s%8s%8s%9s" %
      ("ladder", "trades", "TP1", "TP2", "TP3", "SL", "BE", "TP3 ATR"))
for label in ("fixed ATR 0.8/1.4/2.2", "quantile 50/70/85"):
    d = rows[label]
    n_ = len(d)
    if n_ == 0:
        print("  %-26s no trades" % label)
        continue
    print("  %-26s%9d%7.0f%%%7.0f%%%7.0f%%%7.0f%%%7.0f%%%9.2f" % (
        label, n_,
        pct(sum(1 for x in d if x["got"][0]), n_),
        pct(sum(1 for x in d if x["got"][1]), n_),
        pct(sum(1 for x in d if x["got"][2]), n_),
        pct(sum(1 for x in d if x["how"] == "sl"), n_),
        pct(sum(1 for x in d if x["how"] == "be"), n_),
        med([x["t3"] for x in d])))

if qsnap:
    print("\n  What the market actually said, median over %d long setups:" % len(qsnap))
    print("    q50 %.2f ATR    q70 %.2f ATR    q85 %.2f ATR" % (
        med([q[0] for q in qsnap]), med([q[1] for q in qsnap]), med([q[2] for q in qsnap])))
    print("    against the guessed 0.80 / 1.40 / 2.20")
print("\n  A quantile target states its own reach rate before the trade is taken.")
print("  Fill rates and hold times are geometry. NO EXPECTANCY IS REPORTED — this")
print("  generator cannot price a directional method and no real feed was reachable.")
