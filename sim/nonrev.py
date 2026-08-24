"""No reversal trades. What does that cost, and can volume profile pay for it?

THE REQUEST: signals should read the volume profile and order flow, use the
zones, and TAKE NO REVERSAL TRADES.

THE CONFLICT, stated before anything is built. Two of v4.1's four triggers are
REVERSAL SETUPS BY CONSTRUCTION, and they are the two that supply most of the
trades:

  BAND   price trades THROUGH a VWAP deviation band and closes back inside.
         v4.0's own header calls it "a REVERSION setup" and hands it the mean
         as its first target for that reason. It supplies 20.9 triggers/day on
         15m against 14.9 for MSS, FVG and sweep combined, and on 1H/4H it is
         74% of entries.
  SWEEP  a low is speared and reclaimed — buying after a decline. v3.5.1
         EXEMPTED sweeps from the CVD and momentum gates precisely because
         "the trend reads bearish at exactly the moment the setup forms".

So a naive reading of "no reversal" deletes the engine's trade supply, which is
the disease every version from v3.5.38 through v4.1 was written to cure.

THE DISTINCTION THAT ACTUALLY MATTERS. A sweep is not inherently a reversal. A
bull sweep taken while the leg is DOWN is a reversal. The same sweep taken while
the leg is UP is a pullback that resumed — textbook continuation. What made
these triggers reversal trades was not their shape, it was the EXEMPTION that
let them fire against the prevailing direction.

So "non-reversal" is measured here as DIRECTIONAL AGREEMENT, not as a trigger
ban: the trade must run with the leg in progress, where the leg is price now
against price LEG bars ago — the same definition ME Scalp v2.2 uses.

MEASURED BELOW
  1  what share of each trigger's signals are reversal by that definition
  2  what a non-reversal gate costs in trades per day
  3  whether volume-profile triggers the engine already has the data for can
     pay that cost back:
       POC RECLAIM     price crosses and holds the highest-volume price, which
                       is the profile's own centre of gravity and currently
                       drives NOTHING — it is computed and only displayed
       VA MIGRATION    the value area itself moving up or down, a directional
                       read straight out of the profile
  4  an ORDER FLOW reading the engine does not have at all: ABSORPTION, high
     volume producing little range, i.e. effort without result
"""
import math
from gen import series_regime
from engine import wilder_atr, sma_prior, frvp
from flow import vwap_bands, zones
from v4 import triggers_v4

DAYS = 150
SEEDS = (1, 2, 3, 4, 5, 6)
TF = 900
LEG = 20


def build(seed):
    m1 = series_regime(60 * 24 * DAYS, 60, seed=seed)
    bars = []
    step = TF // 60
    for j in range(0, len(m1) - step + 1, step):
        w = m1[j:j + step]
        bars.append((w[0][0], w[0][1], max(b[2] for b in w), min(b[3] for b in w),
                     w[-1][4], sum(b[5] for b in w)))
    return bars


def pct(n, d):
    return 100.0 * n / d if d else 0.0


# ── pass 1: how reversal is each trigger, and what does the gate cost? ──────
by_trig = {}
vp_supply = {"poc": 0, "vamig": 0, "absorb": 0}
vp_nonrev = {"poc": 0, "vamig": 0, "absorb": 0}
days_total = DAYS * len(SEEDS)

for seed in SEEDS:
    bars = build(seed)
    c = [b[4] for b in bars]; h = [b[2] for b in bars]
    l = [b[3] for b in bars]; v = [b[5] for b in bars]
    T, _b, atr, (POC, VAH, VAL) = triggers_v4(bars, TF)
    vavg = sma_prior(v, 20)

    for i in range(80, len(bars) - 50):
        A = atr[i]
        if A is None or math.isnan(A):
            continue
        legUp = c[i] > c[i - LEG]

        for side, want_up in (("buy", True), ("sell", False)):
            for name, ref, inval in T[i][side]:
                d = by_trig.setdefault(name, {"n": 0, "rev": 0})
                d["n"] += 1
                # REVERSAL = the trade fights the leg in progress
                if want_up != legUp:
                    d["rev"] += 1

        # ── candidate volume-profile supply, both directions ───────────────
        if POC[i] is not None and POC[i - 1] is not None:
            # POC RECLAIM: closed through the highest-volume price, having been
            # on the other side of it on the previous bar. The profile's centre
            # of gravity changing hands. Currently drives nothing in v4.1.
            up = c[i] > POC[i] and c[i - 1] <= POC[i - 1]
            dn = c[i] < POC[i] and c[i - 1] >= POC[i - 1]
            if up or dn:
                vp_supply["poc"] += 1
                if (up and legUp) or (dn and not legUp):
                    vp_nonrev["poc"] += 1
        if VAH[i] is not None and VAH[i - 5] is not None and VAL[i - 5] is not None:
            # VA MIGRATION: the whole value area has moved. Both edges higher
            # than five bars ago is the profile saying value itself is rising —
            # a directional read the engine has never taken.
            up = VAH[i] > VAH[i - 5] and VAL[i] > VAL[i - 5]
            dn = VAH[i] < VAH[i - 5] and VAL[i] < VAL[i - 5]
            if up or dn:
                vp_supply["vamig"] += 1
                if (up and legUp) or (dn and not legUp):
                    vp_nonrev["vamig"] += 1
        if not math.isnan(vavg[i]) and vavg[i] > 0:
            # ABSORPTION: heavy participation producing little range. Effort
            # without result — the order-flow reading v4.1 has no concept of.
            rel = v[i] / max(vavg[i], 1e-9)
            rng = (h[i] - l[i]) / max(A, 1e-9)
            if rel >= 1.5 and rng <= 0.6:
                vp_supply["absorb"] += 1
                if True:
                    vp_nonrev["absorb"] += 1

print("NO REVERSAL TRADES — WHAT IT COSTS, AND WHAT CAN PAY FOR IT")
print("15m, %d days x %d seeds. Reversal = trade direction against price over" % (DAYS, len(SEEDS)))
print("the last %d bars.\n" % LEG)

print("  %-10s%12s%12s%14s%14s" % ("trigger", "events/day", "reversal", "survives/day", "lost/day"))
tot_all = tot_keep = 0.0
for name in sorted(by_trig, key=lambda k: -by_trig[k]["n"]):
    d = by_trig[name]
    per = d["n"] / days_total
    keep = (d["n"] - d["rev"]) / days_total
    tot_all += per
    tot_keep += keep
    print("  %-10s%12.2f%11.0f%%%14.2f%14.2f" % (name, per, pct(d["rev"], d["n"]), keep, per - keep))
print("  %-10s%12.2f%11.0f%%%14.2f%14.2f" % (
    "ALL", tot_all, pct(tot_all - tot_keep, tot_all), tot_keep, tot_all - tot_keep))

print("\n  So a non-reversal gate removes %.0f%% of raw trigger supply." % pct(tot_all - tot_keep, tot_all))

print("\n  VOLUME PROFILE AND ORDER FLOW — supply the engine is not using")
print("  %-14s%14s%16s%14s" % ("source", "events/day", "non-reversal", "of which kept"))
lbl = {"poc": "POC reclaim", "vamig": "VA migration", "absorb": "absorption"}
for k in ("poc", "vamig", "absorb"):
    per = vp_supply[k] / days_total
    keep = vp_nonrev[k] / days_total
    print("  %-14s%14.2f%16.2f%13.0f%%" % (lbl[k], per, keep, pct(vp_nonrev[k], vp_supply[k])))

new = sum(vp_nonrev[k] for k in ("poc", "vamig")) / days_total
print("\n  POC reclaim + VA migration, non-reversal only:  %.2f/day" % new)
print("  Non-reversal supply lost to the gate:          %.2f/day" % (tot_all - tot_keep))
print("  Net against the loss:                          %+.2f/day" % (new - (tot_all - tot_keep)))
print("\n  These are RAW EVENTS, before every gate the engine applies — v4.1")
print("  converts 2-4% of triggers into signals. The columns are supply, which")
print("  is the quantity the non-reversal gate destroys and the quantity the")
print("  profile has to replace. They are not signals and not expectancy.")
