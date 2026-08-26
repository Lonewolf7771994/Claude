"""TRADE PACE ON ALL MODES — and what each relaxation costs in outcome mix.

fullstack.py established the problem: at v4.9 defaults the REAL twenty-one-gate
conjunction produces 0.14-0.19 signals/day on every mode. One trade a week, and
the mode selector changes almost nothing (0.14 vs 0.19) because the gates that
bind are the ones every mode shares.

The four largest blockers the v4.9 preset never touched:

    reward       71.2%    TP1 must clear 1.0R, but TP1 SNAPS to the nearest
                          structure level, which is frequently nearer than 1R.
                          The gate rejects the trade for a property of the
                          target, not of the setup.
    momentum     60.6%    EMA 8 > EMA 21
    cvd          58.2%    CVD fast EMA > slow EMA
    struct bias  53.8%    HTF-locked MSS direction

The last three, plus GATE: trail at 56.9%, are FOUR CORRELATED READINGS OF ONE
THING — is the market going my way. Stacking four of them is not four times the
safety; it is one filter applied four times, and it costs most of the trades.

The no-reversal guarantee comes from the trail alone: a long requires the trail
in its up state, so a long against the trend cannot pass regardless of what the
other three say. That is why they are the ones this file relaxes and the trail
is the one it never touches — every configuration below keeps it.

DIR DEPTH is how many of the three redundant direction filters are enforced on
top of the trail: 0 = trail only, 1 = + momentum, 2 = + cvd, 3 = + struct bias
(the v4.9 behaviour).

REPORTED: signals/day per mode, and the outcome mix, so a relaxation that buys
trades by taking worse ones shows up as a rising SL column. Outcome mix is
geometry. NO EXPECTANCY IS COMPUTED OR QUOTED — no price feed is reachable.
"""
import math
from gen import series_regime
from fullstack import build, prep, MODES, TF, DAYS, SEEDS
from ladder_diag import ladder, med, pct
from nonrev_mix import walk2

RMUL = (0.8, 1.4, 2.2)
SPREAD_PCT = 11.5   # 5m XAUUSD, share of a ~1.5 ATR stop (v3.5.40)

# name          body  vol   of%  delta  cool minR  minRR  dirDepth
GRID = [
    ("v4.9 now  ", 0.40, 1.00, 58.0, 0.15,  6, 0.7, 1.00, 3),
    ("dir 3->1  ", 0.40, 1.00, 58.0, 0.15,  6, 0.7, 1.00, 1),
    ("rr 1.0->0.6", 0.40, 1.00, 58.0, 0.15, 6, 0.7, 0.60, 3),
    ("both      ", 0.40, 1.00, 58.0, 0.15,  6, 0.7, 0.60, 1),
    ("STEADY    ", 0.40, 1.00, 58.0, 0.15,  6, 0.7, 0.60, 2),
    ("ACTIVE    ", 0.30, 0.80, 56.0, 0.12,  3, 0.5, 0.60, 1),
    ("RAPID     ", 0.25, 0.70, 54.0, 0.10,  2, 0.4, 0.50, 0),
]


def evaluate(D, i, is_buy, mode, last, cfg):
    """v4.9's conjunction with the direction stack and reward floor parameterised.
    Returns (ok, sl, tps) — sl/tps only meaningful when ok."""
    o, h, l, c, v = D["o"], D["h"], D["l"], D["c"], D["v"]
    A = D["atr"][i]
    ev = D["T"][i]["buy" if is_buy else "sell"]
    if not ev:
        return False, None, None
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
    dep = cfg["dir"]

    if (c[i] > o[i]) != is_buy:                       return False, None, None
    if body < A * cfg["body"]:                        return False, None, None
    if kinds & {"sweep", "fvg", "band", "band2", "value"}:
        wr = (upper if is_buy else lower) / body if body > 0 else 999.0
    else:
        wr = (upper + lower) / body if body > 0 else 999.0
    if wr > 2.0:                                      return False, None, None
    if relv < cfg["vol"]:                             return False, None, None
    if ofpct < cfg["of"]:                             return False, None, None
    if (delta < cfg["delta"]) if is_buy else (delta > -cfg["delta"]):
        return False, None, None

    # THE NO-REVERSAL GUARANTEE — present in every configuration, never relaxed
    if (D["pdir"][i] == 1) != is_buy:                 return False, None, None
    # the redundant readings, enforced to depth
    if dep >= 1 and (D["e8"][i] > D["e21"][i]) != is_buy:   return False, None, None
    if dep >= 2 and (D["cf"][i] > D["cs"][i]) != is_buy:    return False, None, None
    if dep >= 3 and not scalp and D["si"][i] and D["sb"][i] != is_buy:
        return False, None, None

    vwDist = abs(c[i] - D["vw"][i]) / A
    if vwDist > 3.0:                                  return False, None, None
    if mode in ("Balanced", "Strict"):
        if htfUp != is_buy:                           return False, None, None
        if (c[i] > D["vw"][i]) != is_buy:             return False, None, None
    if i - last < cfg["cool"]:                        return False, None, None

    lo, hi = (40, 78) if is_buy else (22, 60)
    if scalp:
        lo, hi = (35, 80) if is_buy else (20, 65)
    if not (lo <= D["rs"][i] <= hi):                  return False, None, None
    ref = ev[0][1]
    if (c[i] - ref if is_buy else ref - c[i]) > A * 1.0:
        return False, None, None

    inval = ev[0][2]
    pad = cfg.get("pad", 0.5)
    if is_buy:
        sl = min(inval - A*pad, c[i] - A*cfg["minr"]); risk = c[i] - sl
    else:
        sl = max(inval + A*pad, c[i] + A*cfg["minr"]); risk = sl - c[i]
    if risk < A*cfg["minr"] or risk > A*3.0:          return False, None, None

    struct = [x for x in (D["VAH"][i] if is_buy else D["VAL"][i], D["POC"][i])
              if x is not None and (x > c[i]) == is_buy]
    if is_buy:
        tps = ladder(c[i], risk, A, struct, RMUL, "atr", 2.0)
    else:
        mir = [c[i] + (c[i]-x) for x in struct]
        tps = [c[i] - (t-c[i]) for t in ladder(c[i], risk, A, mir, RMUL, "atr", 2.0)]
    if abs(tps[0] - c[i]) / max(risk, 1e-9) < cfg["minrr"]:
        return False, None, None

    need = 2 if mode == "Strict" else 0 if mode == "Aggressive" else 1
    band = (c[i] <= D["l1"][i]*1.002) if is_buy else (c[i] >= D["u1"][i]*0.998)
    conf = (1 if relv >= 1.20 else 0) + (1 if body >= A*0.55 else 0) + \
           (1 if (cp if is_buy else 1-cp) >= 0.70 else 0) + \
           (1 if len(ev) >= 2 else 0) + (1 if band else 0)
    if conf < need:                                   return False, None, None
    return True, sl, tps


if __name__ == "__main__":
    days = DAYS * len(SEEDS)
    res = {(g[0], m): [] for g in GRID for m in MODES}
    for seed in SEEDS:
        bars = build(seed, TF)
        D = prep(bars)
        for g in GRID:
            name, body, vol, of, delta, cool, minr, minrr, dep = g
            cfg = dict(body=body, vol=vol, of=of, delta=delta, cool=cool,
                       minr=minr, minrr=minrr, dir=dep)
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
                        res[(name, mode)].append(dict(dur=dur, got=got, how=how))
                        last = i
                        break

    print("TRADE PACE ON ALL MODES — 5m, %d days x %d seeds, both sides" % (DAYS, len(SEEDS)))
    print("Every row keeps the no-reversal trail. dir = how many redundant")
    print("direction filters sit on top of it (3 = v4.9).\n")
    hdr = "  %-12s%4s%6s" % ("preset", "dir", "rr")
    for m in MODES:
        hdr += "%12s" % m[:9]
    print(hdr + "        TP1   TP2   TP3    SL  bars")
    for g in GRID:
        name, body, vol, of, delta, cool, minr, minrr, dep = g
        row = "  %-12s%4d%6.2f" % (name, dep, minrr)
        allrows = []
        for m in MODES:
            d = res[(name, m)]
            allrows += d
            r = len(d) / days
            row += "%11.2f%s" % (r, "*" if r >= 4.0 else " ")
        N = len(allrows)
        if N:
            row += "%9.0f%%%6.0f%%%6.0f%%%6.0f%%%6d" % (
                pct(sum(1 for x in allrows if x["got"][0]), N),
                pct(sum(1 for x in allrows if x["got"][1]), N),
                pct(sum(1 for x in allrows if x["got"][2]), N),
                pct(sum(1 for x in allrows if x["how"] == "sl"), N),
                med([x["dur"] for x in allrows]))
        print(row)
    print("\n  * = clears 4 signals/day in that mode. Mix is pooled across modes.")
    print("  Spread on 5m XAUUSD eats %.1f%% of a ~1.5 ATR stop and is not in the mix." % SPREAD_PCT)
    print("  NO EXPECTANCY IS REPORTED and none was computed.")
