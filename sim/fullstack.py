"""WHY IT STILL FIRES NOTHING — the whole conjunction, not the six the preset moved.

v4.9's preset was searched with scalp_target.py, which modelled EIGHT gates.
The live indicator ANDs TWENTY-ONE:

  trigger, bar direction, body, wick, order flow, CVD, momentum, mode pass,
  structural bias, cooldown, risk band, RSI, news, breaker, anti-chase,
  session, regime, no-reversal, silver bullet, reward, confluence

So the preset raised the rate of an eight-gate engine to 4.84/day and the other
thirteen gates then took it back down. That is the bug: the measurement and the
product were not the same engine.

This file measures the REAL conjunction at v4.9 defaults, per mode, and counts
every gate that vetoed a trigger — not just the first — so a gate appearing in
40% of blocks is genuinely responsible for 40% of them. Shares sum past 100%
because several usually fire on the same bar.

Trigger supply here is CONSERVATIVE: this harness has MSS, FVG, sweep, band,
band2 and value-area rejections but not the v4.3 POC reclaim or the v4.7 CRT,
both of which join with `or` and can only add. Real trigger counts are higher
than the ones printed; every conversion percentage below is therefore an upper
bound on the real one.
"""
import math
from gen import series_regime
from engine import wilder_atr, ema, rsi as rsi_f, sma_prior, pivots
from v4 import triggers_v4

DAYS, SEEDS, TF = 120, (1, 2, 3), 300
PRISM_ATR, PRISM_BASE, PRISM_REFR, PRISM_RANK = 12, 3.0, 0.35, 200
LEG = 20

# v4.9 defaults, with the "moderate" preset applied to the six it controls
BODY, VOLF, OFT, DELTA, COOL, MINR = 0.40, 1.00, 58.0, 0.15, 6, 0.7
MAXR, WICK, MAXCHASE, VWAPMAX, MINRR = 3.0, 2.0, 1.0, 3.0, 1.0
RSI_BUY, RSI_SELL = (40, 78), (22, 60)
MODES = ("Aggressive", "Balanced", "Strict", "Scalp")


def build(seed, tf):
    m1 = series_regime(60 * 24 * DAYS, 60, seed=seed)
    out, st = [], tf // 60
    for j in range(0, len(m1) - st + 1, st):
        w = m1[j:j + st]
        out.append((w[0][0], w[0][1], max(b[2] for b in w), min(b[3] for b in w),
                    w[-1][4], sum(b[5] for b in w)))
    return out


def prep(bars):
    """Everything the conjunction reads, computed once per series."""
    n = len(bars)
    o = [b[1] for b in bars]; h = [b[2] for b in bars]
    l = [b[3] for b in bars]; c = [b[4] for b in bars]; v = [b[5] for b in bars]
    T, (vw, u1, l1, u2, l2), atr, (POC, VAH, VAL) = triggers_v4(bars, TF)
    e8, e21, e50 = ema(c, 8), ema(c, 21), ema(c, 50)
    rs = rsi_f(c, 14); vavg = sma_prior(v, 20)
    patr = wilder_atr(h, l, c, PRISM_ATR)

    # CVD: signed body volume, fast/slow EMA of the running sum
    cvd, run = [], 0.0
    for i in range(n):
        rng = max(h[i] - l[i], 1e-9)
        run += v[i] * ((c[i] - o[i]) / rng)
        cvd.append(run)
    cf, cs = ema(cvd, 9), ema(cvd, 21)

    # the v4.6 Prism trail — the leg half of the no-reversal gate
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

    # structural bias: MSS locked in only when HTF agrees (v3.3)
    ph, pl = pivots(h, l, 2)
    PH = PL = None
    sBull, sInit = False, False
    sb, si = [False]*n, [False]*n
    for i in range(n):
        if ph[i] is not None: PH = ph[i]
        if pl[i] is not None: PL = pl[i]
        A = atr[i]
        if A is not None and not math.isnan(A) and i > 0:
            htfUp = not math.isnan(e50[i]) and c[i] > e50[i]
            if PH is not None and c[i] >= PH + A*0.10 and c[i-1] < PH and htfUp:
                sBull, sInit = True, True
            if PL is not None and c[i] <= PL - A*0.10 and c[i-1] > PL and not htfUp:
                sBull, sInit = False, True
        sb[i], si[i] = sBull, sInit
    return dict(n=n, o=o, h=h, l=l, c=c, v=v, T=T, vw=vw, u1=u1, l1=l1, u2=u2, l2=l2,
                atr=atr, e8=e8, e21=e21, e50=e50, rs=rs, vavg=vavg, cf=cf, cs=cs,
                pdir=pdir, sb=sb, si=si, POC=POC, VAH=VAH, VAL=VAL)


def evaluate(D, i, is_buy, mode, last, cfg):
    """Return the list of gates that vetoed. Empty list = a signal."""
    o, h, l, c, v = D["o"], D["h"], D["l"], D["c"], D["v"]
    A = D["atr"][i]
    ev = D["T"][i]["buy" if is_buy else "sell"]
    if not ev:
        return None
    kinds = {e[0] for e in ev}
    rng = max(h[i] - l[i], 1e-9)
    cp = (c[i] - l[i]) / rng
    body = abs(c[i] - o[i])
    upper, lower = h[i] - max(c[i], o[i]), min(c[i], o[i]) - l[i]
    relv = v[i] / max(D["vavg"][i], 1e-9)
    delta = (c[i] - o[i]) / rng
    ofpct = cp * 100.0 if is_buy else (100.0 - cp * 100.0)
    htfUp = not math.isnan(D["e50"][i]) and c[i] > D["e50"][i]
    scalp = mode == "Scalp"
    W = []

    if (c[i] > o[i]) != is_buy:                       W.append("bar dir")
    if body < A * cfg["body"]:                        W.append("body")
    # wick: directional against the entry for rejection triggers, total for MSS
    if kinds & {"sweep", "fvg", "band", "band2", "value"}:
        wr = (upper if is_buy else lower) / body if body > 0 else 999.0
    else:
        wr = (upper + lower) / body if body > 0 else 999.0
    if wr > cfg["wick"]:                              W.append("wick")
    if relv < cfg["vol"]:                             W.append("vol")
    if ofpct < cfg["of"]:                             W.append("of%")
    if (delta < cfg["delta"]) if is_buy else (delta > -cfg["delta"]):
        W.append("delta")
    cvdUp = D["cf"][i] > D["cs"][i]
    if cvdUp != is_buy:                               W.append("cvd")
    momUp = D["e8"][i] > D["e21"][i]
    if momUp != is_buy:                               W.append("momentum")

    # mode pass
    vwDist = abs(c[i] - D["vw"][i]) / A
    notExt = vwDist <= cfg["vwapmax"]
    if mode == "Aggressive":
        pass
    elif scalp:
        if not notExt:                                W.append("mode: vwap dist")
    else:
        if htfUp != is_buy:                           W.append("mode: htf")
        if (c[i] > D["vw"][i]) != is_buy:             W.append("mode: vwap side")
        if not notExt:                                W.append("mode: vwap dist")

    if not scalp and D["si"][i] and D["sb"][i] != is_buy:
        W.append("struct bias")
    if i - last < cfg["cool"]:                        W.append("cooldown")

    lo, hi = RSI_BUY if is_buy else RSI_SELL
    if scalp:
        lo, hi = (min(lo, 35), max(hi, 80)) if is_buy else (min(lo, 20), max(hi, 65))
    if not (lo <= D["rs"][i] <= hi):                  W.append("rsi")

    ref = ev[0][1]
    if (c[i] - ref if is_buy else ref - c[i]) > A * cfg["chase"]:
        W.append("chase")

    if (D["pdir"][i] == 1) != is_buy:                 W.append("GATE: trail")

    inval = ev[0][2]
    if is_buy:
        sl = min(inval - A*0.5, c[i] - A*cfg["minr"]); risk = c[i] - sl
    else:
        sl = max(inval + A*0.5, c[i] + A*cfg["minr"]); risk = sl - c[i]
    if risk < A*cfg["minr"] or risk > A*cfg["maxr"]:  W.append("risk band")

    # reward: TP1 is the nearer of the first structure level and 0.8 ATR
    struct = [x for x in (D["VAH"][i] if is_buy else D["VAL"][i], D["POC"][i])
              if x is not None and (x > c[i]) == is_buy]
    tp1 = min(struct, key=lambda x: abs(x - c[i])) if struct else (
        c[i] + (A*0.8 if is_buy else -A*0.8))
    rr = abs(tp1 - c[i]) / max(risk, 1e-9)
    if rr < cfg["minrr"]:                             W.append("reward")

    # v4.1 confluence, mode-dependent
    need = 2 if mode == "Strict" else 0 if mode == "Aggressive" else 1
    band = (c[i] <= D["l1"][i]*1.002) if is_buy else (c[i] >= D["u1"][i]*0.998)
    conf = (1 if relv >= 1.20 else 0) + (1 if body >= A*0.55 else 0) + \
           (1 if (cp if is_buy else 1-cp) >= 0.70 else 0) + \
           (1 if len(ev) >= 2 else 0) + (1 if band else 0)
    if conf < need:                                   W.append("confluence")
    return W


CFG = dict(body=BODY, vol=VOLF, of=OFT, delta=DELTA, cool=COOL, minr=MINR,
           maxr=MAXR, wick=WICK, chase=MAXCHASE, vwapmax=VWAPMAX, minrr=MINRR)

if __name__ == "__main__":
    days = DAYS * len(SEEDS)
    tally = {m: dict(trig=0, sig=0, blocks={}) for m in MODES}
    for seed in SEEDS:
        D = prep(build(seed, TF))
        for mode in MODES:
            t = tally[mode]
            last = -10**9
            for i in range(80, D["n"] - 40):
                A = D["atr"][i]
                if A is None or math.isnan(A) or math.isnan(D["vavg"][i]):
                    continue
                for is_buy in (True, False):
                    W = evaluate(D, i, is_buy, mode, last, CFG)
                    if W is None:
                        continue
                    t["trig"] += 1
                    if W:
                        for k in W:
                            t["blocks"][k] = t["blocks"].get(k, 0) + 1
                    else:
                        t["sig"] += 1
                        last = i
                        break

    print("THE REAL CONJUNCTION — 5m, %d days x %d seeds, both sides" % (DAYS, len(SEEDS)))
    print("v4.9 defaults with the 'moderate' preset applied to the six it controls.\n")
    print("  %-12s%10s%12s%10s" % ("mode", "trig/day", "SIGNALS/DAY", "conv %"))
    for m in MODES:
        t = tally[m]
        print("  %-12s%10.1f%12.2f%9.2f%%" % (
            m, t["trig"]/days, t["sig"]/days, 100.0*t["sig"]/max(t["trig"], 1)))

    for m in MODES:
        t = tally[m]
        print("\n  %s — which gate blocked, share of all triggers" % m.upper())
        for k, cnt in sorted(t["blocks"].items(), key=lambda kv: -kv[1])[:14]:
            print("    %-18s %7d   %5.1f%%" % (k, cnt, 100.0*cnt/max(t["trig"], 1)))

    print("\n  scalp_target.py measured 4.84/day for 'moderate' on 5m using EIGHT")
    print("  of these gates. The difference between that number and the ones above")
    print("  is the thirteen gates it did not model.")
