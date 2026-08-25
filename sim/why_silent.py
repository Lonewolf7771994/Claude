"""Why does v4.7 fire nothing? Attribute the blocks instead of guessing.

FIRST, TWO THINGS IT IS NOT, and both are read off the source rather than
measured:

  SILVER BULLET is OFF by default. i_sbMode defaults to "Off", so sbRestrict is
  false and sbOkBuy = (not false) or ... = TRUE on every bar. It cannot block
  anything until it is deliberately switched on.

  CRT joins the trigger set with `or`:
      buyTrigger = mssUp or fvg or sweep or band or poc or CRT
  A term added to an `or` can only make it true more often. CRT can ADD signals
  and is arithmetically incapable of removing one.

So the cause is the accumulated GATE STACK, and this measures which part of it
is doing the blocking. Every gate that vetoed a trigger is counted — not just
the first one — so a gate appearing in 40% of blocks is genuinely responsible
for 40% of them, and the shares sum past 100% because several usually fire
together.
"""
import math
from gen import series_regime
from engine import wilder_atr, ema, rsi as rsi_f, sma_prior, frvp
from flow import vwap_bands
from v4 import triggers_v4

DAYS = 150
SEEDS = (1, 2, 3, 4)
TF = 900
LEG = 20

# v4.7 defaults, Balanced
ER_MIN, BODY, OF_THR, DELTA, VOLF = 0.32, 0.50, 60.0, 0.20, 1.2
COOLDOWN, MINRISK, MAXRISK = 12, 1.0, 3.0
RSI_LO, RSI_HI = 40, 78
CONF_NEED = 1          # Balanced
PRISM_ATR, PRISM_BASE, PRISM_REFR, PRISM_RANK = 12, 3.0, 0.35, 200

blocks = {}
trig_n = 0
sig_n = 0
days = DAYS * len(SEEDS)


def bump(k):
    blocks[k] = blocks.get(k, 0) + 1


for seed in SEEDS:
    m1 = series_regime(60 * 24 * DAYS, 60, seed=seed)
    bars = []
    step = TF // 60
    for j in range(0, len(m1) - step + 1, step):
        w = m1[j:j + step]
        bars.append((w[0][0], w[0][1], max(b[2] for b in w), min(b[3] for b in w),
                     w[-1][4], sum(b[5] for b in w)))
    n = len(bars)
    o = [b[1] for b in bars]; h = [b[2] for b in bars]
    l = [b[3] for b in bars]; c = [b[4] for b in bars]; v = [b[5] for b in bars]
    T, (vw, u1, l1, u2, l2), atr, (POC, VAH, VAL) = triggers_v4(bars, TF)
    e50 = ema(c, 50)
    rs = rsi_f(c, 14)
    vavg = sma_prior(v, 20)
    patr = wilder_atr(h, l, c, PRISM_ATR)

    # the Prism trail, which is the LEG half of the gate by default
    pdir = [1] * n
    pup = [None] * n
    pdn = [None] * n
    for i in range(n):
        A = patr[i]
        if A is None or math.isnan(A):
            continue
        win = [x for x in patr[max(0, i - PRISM_RANK):i + 1] if x is not None and not math.isnan(x)]
        rank = (sum(1 for x in win if x <= A) / len(win)) if win else 0.5
        mult = max(0.2, PRISM_BASE - PRISM_REFR * (1.0 - rank))
        upraw, dnraw = c[i] - A * mult, c[i] + A * mult
        pup[i] = upraw if (i == 0 or pup[i - 1] is None or c[i - 1] <= pup[i - 1]) else max(upraw, pup[i - 1])
        pdn[i] = dnraw if (i == 0 or pdn[i - 1] is None or c[i - 1] >= pdn[i - 1]) else min(dnraw, pdn[i - 1])
        if i > 0:
            pdir[i] = 1 if c[i] > (pdn[i - 1] if pdn[i - 1] else dnraw) else \
                      (-1 if c[i] < (pup[i - 1] if pup[i - 1] else upraw) else pdir[i - 1])

    ER = [None] * n
    path = 0.0
    for i in range(1, n):
        path += abs(c[i] - c[i - 1])
        if i > LEG:
            path -= abs(c[i - LEG] - c[i - LEG - 1])
            ER[i] = abs(c[i] - c[i - LEG]) / max(path, 1e-9)

    last = -10 ** 9
    for i in range(80, n - 5):
        A = atr[i]
        if A is None or math.isnan(A) or math.isnan(vavg[i]):
            continue
        ev = T[i]["buy"]
        if not ev:
            continue
        trig_n += 1
        rng = max(h[i] - l[i], 1e-9)
        cp = (c[i] - l[i]) / rng
        body = abs(c[i] - o[i])
        relv = v[i] / max(vavg[i], 1e-9)
        delta = (c[i] - o[i]) / rng
        htfUp = not math.isnan(e50[i]) and c[i] > e50[i]

        why = []
        if not (c[i] > o[i]):            why.append("bar dir")
        if body < A * BODY:              why.append("body")
        if relv < VOLF:                  why.append("vol")
        if cp * 100.0 < OF_THR:          why.append("of%")
        if delta < DELTA:                why.append("delta")
        if not htfUp:                    why.append("htf/mode")
        if c[i] <= vw[i]:                why.append("vwap side")
        if i - last < COOLDOWN:          why.append("cooldown")
        if not (RSI_LO <= rs[i] <= RSI_HI): why.append("rsi")

        # the v4.4/v4.6 no-reversal gate: trail state + efficiency ratio + HTF
        if pdir[i] != 1:                                why.append("GATE: trail")
        if ER[i] is None or ER[i] < ER_MIN:             why.append("GATE: ER")
        if not htfUp:                                   why.append("GATE: htf")

        # confluence, Balanced needs 1 of 6
        conf = (1 if relv >= 1.20 else 0) + (1 if body >= A * 0.55 else 0) + \
               (1 if cp >= 0.70 else 0) + (1 if len(ev) >= 2 else 0) + \
               (1 if c[i] <= l1[i] * 1.002 else 0)
        if conf < CONF_NEED:            why.append("confluence")

        inval = ev[0][2]
        sl = min(inval - A * 0.5, c[i] - A * MINRISK)
        risk = c[i] - sl
        if risk > A * MAXRISK:          why.append("risk")

        if why:
            for k in why:
                bump(k)
        else:
            sig_n += 1
            last = i

print("WHY v4.7 IS SILENT — block attribution, 15m, %d days x %d seeds" % (DAYS, len(SEEDS)))
print("Balanced mode, every v4.7 default. Long side.\n")
print("  bullish triggers   %6d   (%.1f/day)" % (trig_n, trig_n / days))
print("  signals            %6d   (%.2f/day)   conversion %.2f%%" % (
    sig_n, sig_n / days, 100.0 * sig_n / max(trig_n, 1)))
print("\n  WHICH GATE BLOCKED, share of all blocked triggers")
print("  (sums past 100%% — several usually fire on the same bar)\n")
for k, cnt in sorted(blocks.items(), key=lambda kv: -kv[1]):
    print("    %-16s %6d   %5.1f%%" % (k, cnt, 100.0 * cnt / max(trig_n, 1)))
print("\n  Gates prefixed GATE: are the v4.4 no-reversal stack. Everything else")
print("  predates v4.3 and was already in the engine before CRT or Silver Bullet")
print("  existed. Neither of those appears here because neither can block:")
print("  Silver Bullet defaults Off, and CRT joins the trigger set with `or`.")
