"""ME Pro v4.1 — "slow trades, fragmented, mistaken". Measure all three.

The report is three complaints and they have three different causes. Two of
them are provable by reading the code; the first needs measuring.

SLOW. Every target is a multiple of the STOP DISTANCE:

    tp = entry + dir * risk * rmul          rmul = 1.5 / 2.5 / 4.0

and the stop is structural, capped at i_maxRisk = 3.0 ATR. So TP1 sits at
1.5 x risk, which is up to 4.5 ATR from entry, and TP3 up to 12 ATR. The
wider the stop the further EVERY target runs — the plan is slowest exactly
when the structure is widest, which is backwards. What is measured here is
the distance to TP1 in ATR and how many bars the plan takes to resolve,
against the same plan with targets measured in ATR instead of in R.

FRAGMENTED. Three defects, all read off the source, none needing a harness:

  1  TP2 IS NEVER TRACKED. The engine keeps activeTp1Px and activeTp3Px and
     no activeTp2Px. TP2 is drawn on the chart, sent in the alert, and the
     engine has no idea whether it traded. A three-leg scale-out is tracked
     as two legs.
  2  THE MANUAL TP2 OVERRIDE IS DEAD. i_mTP2 moves the drawn line and the
     label and nothing else, because there is no tracked value to write to.
  3  The ladder mixes structure levels and R-multiples and then NUDGES the
     R-multiples off the structure by minGap, so the three targets can come
     from three different logics with the spacing decided by a collision
     loop rather than by the plan.

MISTAKEN. The four places that decide what a trade IS disagree about which
trigger fired. Priority order, read straight from v4.1:

    buyType      (line 3351)   MSS  > FVG  > SWEEP > BAND
    buySlAnchor  (line 2953)   SWEEP > BAND > FVG  > MSS
    buyChaseRef  (line 2913)   SWEEP > BAND > FVG  > MSS
    tpMeanBuy    (line 3022)   BAND, whenever band is live at all

So when MSS and sweep fire on the same bar the label says MSS, the stop is
anchored to the sweep's wick, the chase cap is measured from the swept
level, and if a band is also live the VWAP mean is injected as a target.
Four different setups wearing one signal number.

And this is not a rare corner: v4.1's own confluence score AWARDS A POINT
for two triggers stacking (buyTrigCount >= 2), so the engine is scoring
highest on exactly the bars where its four descriptions disagree most.
That is measured below as the STACK RATE.
"""
import math
from gen import series_regime
from engine import wilder_atr, sma_prior, frvp
from flow import vwap_bands, zones
from v4 import triggers_v4


def ladder(entry, risk, atr, struct, rmul, unit_mode, tp1_cap):
    """v4.1's ladder, with `unit_mode` selecting what the multiples measure.

    'risk'  what v4.1 does — every target is a multiple of the stop distance
    'atr'   the same numbers measured in ATR, so a wide stop no longer pushes
            the targets out with it
    """
    d = 1.0 if entry is not None else 1.0
    unit = risk if unit_mode == "risk" else atr
    raw = sorted([x for x in struct if x > entry], key=lambda v: abs(v - entry))
    gap = max(atr * 0.5, risk * 0.25)
    cands = []
    for x in raw:
        if not cands or abs(x - cands[-1]) >= gap:
            cands.append(x)
    cap = risk * tp1_cap if tp1_cap > 0 else 1e12
    if cands and abs(cands[0] - entry) > cap:
        cands = [entry + unit * rmul[0]] + cands
    fV = []
    for s in range(3):
        if s < len(cands):
            fV.append(cands[s])
        else:
            rv = entry + unit * rmul[s]
            for _ in range(4):
                for j in list(fV):
                    if abs(rv - j) < gap:
                        rv = j + gap
            fV.append(rv)
    fV.sort()
    return fV


def walk(bars, i, entry, sl, tps, max_look=400):
    """Bars until the plan resolves, and which legs were reached."""
    got = [False] * 3
    stop = sl
    for k in range(i + 1, min(i + 1 + max_look, len(bars))):
        h, l = bars[k][2], bars[k][3]
        hit_sl = l <= stop
        for t in range(3):
            if got[t]:
                continue
            if h >= tps[t] and not (hit_sl and t == 0 and not got[0]):
                got[t] = True
                if t == 0:
                    stop = entry
        if hit_sl:
            return k - i, got, ("be" if stop == entry else "sl")
        if all(got):
            return k - i, got, "tp3"
    return max_look, got, "time"


DAYS = 150
SEEDS = (1, 2, 3, 4, 5, 6)
TF = 900          # 15m
RMUL = (1.5, 2.5, 4.0)
MAXRISK = 3.0     # i_maxRisk default, non-Scalp
MINRISK = 1.0     # i_minRisk default

print("ME PRO v4.1 — SLOW / FRAGMENTED / MISTAKEN")
print("15m, %d days x %d seeds. Longs only (the ladder is symmetric)." % (DAYS, len(SEEDS)))
print("Targets 1.5 / 2.5 / 4.0, risk window 1.0-3.0 ATR, TP1 cap 2.0R.\n")

agg = {"risk": [], "atr": []}
stack_bull = 0
trig_bull = 0

for seed in SEEDS:
    m1 = series_regime(60 * 24 * DAYS, 60, seed=seed)
    bars = []
    step = TF // 60
    for j in range(0, len(m1) - step + 1, step):
        w = m1[j:j + step]
        bars.append((w[0][0], w[0][1], max(b[2] for b in w), min(b[3] for b in w),
                     w[-1][4], sum(b[5] for b in w)))

    h = [b[2] for b in bars]; l = [b[3] for b in bars]; c = [b[4] for b in bars]
    T, _bands, atr, (POC, VAH, VAL) = triggers_v4(bars, TF)

    for i in range(80, len(bars) - 50):
        A = atr[i]
        if A is None or math.isnan(A):
            continue
        ev = T[i]["buy"]
        if not ev:
            continue
        trig_bull += 1
        # v4.1 scores a point for two triggers stacking — count how often the
        # four descriptions of the trade therefore disagree
        names = set(x[0] for x in ev)
        if len(names) >= 2:
            stack_bull += 1

        # v4.1's stop: structural, floored and capped into the risk window
        inval = ev[0][2]
        sl = min(inval - A * 0.5, c[i] - A * 0.5)
        sl = min(sl, c[i] - A * MINRISK)            # near clamp (default ON)
        risk = c[i] - sl
        if risk > A * MAXRISK:                       # far side REJECTS by default
            continue
        struct = [x for x in (VAH[i], POC[i]) if x is not None]

        for mode in ("risk", "atr"):
            tps = ladder(c[i], risk, A, struct, RMUL, mode, 2.0)
            dur, got, how = walk(bars, i, c[i], sl, tps)
            agg[mode].append(dict(t1_atr=(tps[0] - c[i]) / A,
                                  t3_atr=(tps[2] - c[i]) / A,
                                  risk_atr=risk / A,
                                  dur=dur, got=got, how=how))


def med(xs):
    s = sorted(xs)
    return s[len(s) // 2] if s else 0.0


def pct(n, d):
    return 100.0 * n / d if d else 0.0


print("  %-24s%9s%9s%8s%8s%8s%8s%8s" %
      ("targets measured in", "TP1 ATR", "TP3 ATR", "bars", "TP1%", "TP2%", "TP3%", "SL%"))
for mode, label in (("risk", "risk (v4.1)"), ("atr", "ATR (proposed)")):
    r = agg[mode]
    n = len(r)
    print("  %-24s%9.2f%9.2f%8d%7.0f%%%7.0f%%%7.0f%%%7.0f%%" % (
        label, med([x["t1_atr"] for x in r]), med([x["t3_atr"] for x in r]),
        med([x["dur"] for x in r]),
        pct(sum(1 for x in r if x["got"][0]), n),
        pct(sum(1 for x in r if x["got"][1]), n),
        pct(sum(1 for x in r if x["got"][2]), n),
        pct(sum(1 for x in r if x["how"] == "sl"), n)))

r = agg["risk"]
print("\n  trades %d, identical in both rows — the ladder moved, not the entries." % len(r))
print("  median structural risk %.2f ATR, p90 %.2f" % (
    med([x["risk_atr"] for x in r]),
    sorted(x["risk_atr"] for x in r)[int(len(r) * 0.9)] if r else 0.0))

print("\n  MISTAKEN — how often two different triggers fire on the same bar,")
print("  which is when v4.1's four priority orders disagree AND when its")
print("  confluence score awards its stacking point:")
print("    bullish trigger bars %d, of which %d stack  =  %.0f%%" % (
    trig_bull, stack_bull, pct(stack_bull, trig_bull)))
