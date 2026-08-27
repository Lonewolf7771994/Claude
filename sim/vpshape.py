"""THE PROFILE AS THE ENTRY SOURCE — using its SHAPE, not three numbers off it.

v4.1.4 made the profile an entry source, but it reduced the profile to POC, VAH
and VAL. Those are three summary statistics. The information in a volume profile
is the DISTRIBUTION — where volume is thick and where it is thin — and this
engine computes the whole histogram every stride and then discards it.

The two readings that need the histogram, and what they mean:

  LOW-VOLUME NODE (LVN)   a price band almost nothing traded at. Price did not
                          stop there, which means there is nothing resting there
                          to stop it next time either. Entering an LVN is the
                          one profile reading that predicts SPEED.

  HIGH-VOLUME NODE (HVN)  a price band where a lot traded. Both sides accepted
                          it, so it absorbs and price stalls. It is where a move
                          ends, which makes it a target and a place to fade.

That gives a complete trade from the profile alone: enter as price commits into
a thin band, target the thick band on the far side, stop behind the thick band
it just left. Nothing in that sentence needs a pivot, a gap or a moving average.

MEASURED against the v4.1.4 profile events (VA migration, edge reclaim,
breakout) on the identical stack — same stop rule, same level-retest fill, same
no-reversal trail, same ranked order-flow score. Only the trigger differs.

Counts and outcome geometry only. No expectancy computed or quoted.
"""
import math
import fullstack
from fullstack import build, prep, MODES
from giveback import pct

SEEDS, TF, MAXHOLD = (1, 2), 300, 80
LEN, BINS, STRIDE, VA = 100, 32, 5, 0.70
LVN_PCT, HVN_PCT = 0.30, 0.70          # percentile of bin volume within profile
PAD, MINR, CAP = 1.2, 0.4, 3.0
PENDBARS, OFNEED = 8, 3


def profile(bars):
    """Per-bar profile INCLUDING the histogram. Returns lists of dicts:
    {lo, bs, acc[], poc, vah, val} or None before the window fills."""
    n = len(bars)
    out = [None] * n
    cur = None
    for i in range(n):
        if i >= LEN and i % STRIDE == 0:
            w = bars[i - LEN + 1:i + 1]
            hi = max(b[2] for b in w); lo = min(b[3] for b in w)
            bs = max(hi - lo, 1e-9) / BINS
            acc = [0.0] * BINS
            for _, o, h, l, c, v in w:
                rng = h - l
                if rng <= 0:
                    k = min(BINS - 1, max(0, int((h - lo) / bs)))
                    acc[k] += v
                    continue
                a = min(BINS - 1, max(0, int((l - lo) / bs)))
                b_ = min(BINS - 1, max(0, int((h - lo) / bs)))
                for k in range(a, b_ + 1):
                    bb = lo + k * bs
                    ov = min(bb + bs, h) - max(bb, l)
                    if ov > 0:
                        acc[k] += v * (ov / rng)
            tot = sum(acc)
            if tot > 0:
                pb = max(range(BINS), key=lambda k: acc[k])
                c_, up, dn, tgt, it = acc[pb], pb, pb, tot * VA, 0
                while c_ < tgt and it < BINS * 2:
                    uv = sum(acc[up + 1:up + 3]); us = min(2, BINS - 1 - up)
                    dv = sum(acc[max(0, dn - 2):dn]); ds = min(2, dn)
                    if us == 0 and ds == 0:
                        break
                    if us > 0 and (ds == 0 or uv >= dv):
                        up += us; c_ += uv
                    else:
                        dn -= ds; c_ += dv
                    it += 1
                cur = dict(lo=lo, bs=bs, acc=acc,
                           poc=lo + (pb + .5) * bs,
                           vah=lo + (up + 1) * bs, val=lo + dn * bs)
        out[i] = cur
    return out


def nodes(P):
    """Split the histogram into thin and thick bands, as price ranges."""
    acc = P["acc"]
    srt = sorted(acc)
    loq = srt[int(len(srt) * LVN_PCT)]
    hiq = srt[int(len(srt) * HVN_PCT)]
    lvn, hvn = [], []
    k = 0
    while k < BINS:
        if acc[k] <= loq:
            j = k
            while j + 1 < BINS and acc[j + 1] <= loq:
                j += 1
            lvn.append((P["lo"] + k * P["bs"], P["lo"] + (j + 1) * P["bs"]))
            k = j + 1
        elif acc[k] >= hiq:
            j = k
            while j + 1 < BINS and acc[j + 1] >= hiq:
                j += 1
            hvn.append((P["lo"] + k * P["bs"], P["lo"] + (j + 1) * P["bs"]))
            k = j + 1
        else:
            k += 1
    return lvn, hvn


def of_score(D, i, is_buy):
    rng = max(D["h"][i] - D["l"][i], 1e-9)
    cp = (D["c"][i] - D["l"][i]) / rng
    loc = cp if is_buy else 1.0 - cp
    delta = (D["c"][i] - D["o"][i]) / rng
    cvdOk = (D["cf"][i] > D["cs"][i]) == is_buy
    dabs = abs(D["c"][i] - D["o"][i]) / rng
    lo = max(0, i - 200)
    dwin = [abs(D["c"][k] - D["o"][k]) / max(D["h"][k] - D["l"][k], 1e-9)
            for k in range(lo, i + 1)]
    vwin = [D["v"][k] / max(D["vavg"][k], 1e-9) for k in range(lo, i + 1)
            if not math.isnan(D["vavg"][k])]
    if len(dwin) < 20 or len(vwin) < 20:
        return None
    dr = sum(1 for x in dwin if x <= dabs) / len(dwin)
    vr = sum(1 for x in vwin if x <= D["v"][i] / max(D["vavg"][i], 1e-9)) / len(vwin)
    return ((1 if dr >= 0.5 else 0) + (1 if vr >= 0.5 else 0)
            + (1 if loc >= 0.70 else 0) + (1 if cvdOk else 0)
            + (1 if (delta > 0) == is_buy else 0))


def shape_triggers(D, PR):
    """LVN commit and HVN rejection, as (name, level, invalidation)."""
    n = D["n"]
    o, h, l, c = D["o"], D["h"], D["l"], D["c"]
    out = [{"buy": [], "sell": []} for _ in range(n)]
    for i in range(1, n):
        P = PR[i]
        if P is None:
            continue
        lvn, hvn = nodes(P)
        rng = max(h[i] - l[i], 1e-9)
        cp = (c[i] - l[i]) / rng
        # LVN COMMIT — closed INTO a thin band having been outside it. Nothing
        # rests here, so the expectation is speed to the far side.
        for lo_, hi_ in lvn:
            if c[i - 1] <= lo_ < c[i] <= hi_ and cp >= 0.55:
                out[i]["buy"].append(("lvn_up", lo_, lo_ - (hi_ - lo_)))
            if hi_ > c[i - 1] >= hi_ and False:
                pass
            if c[i - 1] >= hi_ > c[i] >= lo_ and cp <= 0.45:
                out[i]["sell"].append(("lvn_dn", hi_, hi_ + (hi_ - lo_)))
        # HVN REJECT — reached a thick band and closed back out of it.
        for lo_, hi_ in hvn:
            if h[i] >= lo_ and c[i] < lo_ and cp <= 0.45:
                out[i]["sell"].append(("hvn_reject", lo_, h[i]))
            if l[i] <= hi_ and c[i] > hi_ and cp >= 0.55:
                out[i]["buy"].append(("hvn_reject", hi_, l[i]))
    return out


def run(source):
    out = []
    armed = filled = 0
    fullstack.TF = TF
    for seed in SEEDS:
        bars = build(seed, TF)
        D = prep(bars)
        PR = profile(bars)
        h = [b[2] for b in bars]; l = [b[3] for b in bars]; c = [b[4] for b in bars]
        n = D["n"]
        if source == "shape":
            T = shape_triggers(D, PR)
        else:
            from frvpof import frvp_triggers
            T = frvp_triggers(D, bars)
        for mode in MODES:
            last = -10 ** 9
            for i in range(80, n - 90):
                A = D["atr"][i]
                if A is None or math.isnan(A) or math.isnan(D["vavg"][i]):
                    continue
                for is_buy in (True, False):
                    ev = T[i]["buy" if is_buy else "sell"]
                    if not ev:
                        continue
                    if (c[i] > D["o"][i]) != is_buy or i - last < 2:
                        continue
                    sc = of_score(D, i, is_buy)
                    if sc is None or sc < OFNEED:
                        continue
                    if (D["pdir"][i] == 1) != is_buy:
                        continue
                    name, ref, inval = ev[0]
                    if is_buy:
                        sl = min(inval - A * PAD, ref - A * MINR); risk = ref - sl
                    else:
                        sl = max(inval + A * PAD, ref + A * MINR); risk = sl - ref
                    if risk <= 0 or risk > A * CAP:
                        continue
                    d = 1.0 if is_buy else -1.0
                    tps = [ref + d * A * m for m in (0.8, 1.4, 2.2)]
                    armed += 1
                    fill = None
                    for j in range(i + 1, min(i + 1 + PENDBARS, n)):
                        if (l[j] <= ref) if is_buy else (h[j] >= ref):
                            fill = j; break
                    if fill is None:
                        last = i; break
                    filled += 1
                    if (l[fill] <= sl) if is_buy else (h[fill] >= sl):
                        out.append(dict(name=name, how="sl", got=[False]*3, dur=0))
                        last = i; break
                    stop, got, at_be = sl, [False]*3, False
                    how, dur = "time", MAXHOLD
                    for j in range(fill + 1, min(fill + 1 + MAXHOLD, n)):
                        if (l[j] <= stop) if is_buy else (h[j] >= stop):
                            how = "be" if at_be else "sl"; dur = j - fill; break
                        for ti, tp in enumerate(tps):
                            if got[ti]:
                                continue
                            if (h[j] >= tp) if is_buy else (l[j] <= tp):
                                got[ti] = True
                        if got[0] and not at_be:
                            stop = ref; at_be = True
                        if all(got):
                            how = "tp3"; dur = j - fill; break
                    out.append(dict(name=name, how=how, got=got, dur=dur))
                    last = i; break
    return out, armed, filled


def row(label, d, days, extra=""):
    n = len(d)
    if not n:
        print("  %-22s none" % label); return
    print("  %-22s%8d%9.2f%7.0f%%%7.0f%%%7.0f%%%7.0f%%%6d%s" % (
        label, n, n / days,
        pct(sum(1 for x in d if x["got"][0]), n),
        pct(sum(1 for x in d if x["got"][1]), n),
        pct(sum(1 for x in d if x["got"][2]), n),
        pct(sum(1 for x in d if x["how"] == "sl"), n),
        sorted(x["dur"] for x in d)[n // 2], extra))


if __name__ == "__main__":
    days = 120 * len(SEEDS)
    print("PROFILE SHAPE AS THE ENTRY SOURCE — 5m, all modes, %d seeds\n" % len(SEEDS))
    print("  %-22s%8s%9s%7s%7s%7s%7s%6s" %
          ("", "trades", "per day", "TP1", "TP2", "TP3", "SL", "bars"))
    a, ar, fi = run("edges")
    row("v4.1.4 VA events", a, days, "  fill %.0f%%" % pct(fi, ar))
    b, ar2, fi2 = run("shape")
    row("LVN/HVN shape", b, days, "  fill %.0f%%" % pct(fi2, ar2))
    print()
    for nm in ("lvn_up", "lvn_dn", "hvn_reject"):
        row("  " + nm, [x for x in b if x["name"] == nm], days)
    print("\n  Counts and outcome geometry only. NO EXPECTANCY COMPUTED OR QUOTED.")
