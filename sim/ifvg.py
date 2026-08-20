"""ME iFVG — port of the inverted-FVG model, for COUNTING ONLY.

This exists to answer one question that has gone wrong on every previous build:
does it actually fire, and how often? Rate, duration and which qualifier is
doing the rejecting are properties of the logic and are trustworthy here.

EXPECTANCY IS NOT MEASURED AND MUST NOT BE READ OFF THIS. Twice in this project
a synthetic generator produced an edge that evaporated on a real backtest, so no
mean-R figure from this file is reported.
"""
import math
from engine import wilder_atr, pivots


def run(bars, atr_len=14, sweep_piv=5, sweep_wick=0.25, sweep_age=25,
        deliv_atr=1.0, fvg_min=0.30, fvg_max=3.0, min_tgt_r=1.5,
        sl_buf=0.15, max_risk=2.0, gap_age=50, inv_age=30, rej=0.5,
        cooldown=5, use_sweep=True, use_deliv=True, use_size=True, use_tgt=True):
    o = [b[1] for b in bars]; h = [b[2] for b in bars]
    l = [b[3] for b in bars]; c = [b[4] for b in bars]
    t = [b[0] for b in bars]
    n = len(bars)
    atr = wilder_atr(h, l, c, atr_len)
    pvh, pvl = pivots(h, l, sweep_piv)

    swingHi = swingLo = None
    sweepLoAge = sweepHiAge = 10**6
    gaps = []                      # dicts: top bot bar dir stat invb delv size
    last = -10**9
    sigs = []
    blocks = {}

    def rej_(k):
        blocks[k] = blocks.get(k, 0) + 1

    for i in range(n):
        if pvh[i] is not None: swingHi = pvh[i]
        if pvl[i] is not None: swingLo = pvl[i]
        if i < 60 or math.isnan(atr[i]):
            continue
        A = atr[i]

        # ── qualifier 1: liquidity sweep, tracked as an age
        sl_now = swingLo is not None and (swingLo - l[i]) >= A*sweep_wick and c[i] > swingLo
        sh_now = swingHi is not None and (h[i] - swingHi) >= A*sweep_wick and c[i] < swingHi
        sweepLoAge = 0 if sl_now else sweepLoAge + 1
        sweepHiAge = 0 if sh_now else sweepHiAge + 1

        # ── formation, with size and delivery stamped on
        contig = (t[i] - t[i-2]) <= (t[i] - t[i-1]) * 6 if i >= 2 else False
        bull = i >= 2 and contig and l[i] > h[i-2]
        bear = i >= 2 and contig and l[i-2] > h[i]
        if bull or bear:
            top = l[i] if bull else l[i-2]
            bot = h[i-2] if bull else h[i]
            sz = (top - bot) / A
            if (not use_size) or (fvg_min <= sz and (fvg_max <= 0 or sz <= fvg_max)):
                gaps.append(dict(top=top, bot=bot, bar=i, dir=1 if bull else -1,
                                 stat=0, invb=0,
                                 delv=abs(c[i] - o[i-2]) / A, size=sz))

        # ── state machine: live -> inverted -> spent/expired
        for g in list(gaps):
            if g["stat"] == 0:
                if (g["dir"] == 1 and c[i] < g["bot"]) or (g["dir"] == -1 and c[i] > g["top"]):
                    g["stat"] = 1; g["invb"] = i
                elif i - g["bar"] > gap_age:
                    gaps.remove(g)
            elif g["stat"] == 1:
                if i - g["invb"] > inv_age:
                    gaps.remove(g)
            else:
                gaps.remove(g)

        # ── the retest
        hit = None
        for g in reversed(gaps):
            if g["stat"] != 1:
                continue
            span = g["top"] - g["bot"]
            if g["dir"] == 1 and h[i] >= g["bot"] and c[i] < g["bot"] + span*rej and c[i] < o[i]:
                hit = ("short", g); break
            if g["dir"] == -1 and l[i] <= g["top"] and c[i] > g["top"] - span*rej and c[i] > o[i]:
                hit = ("long", g); break
        if hit is None:
            continue
        side, g = hit
        is_long = side == "long"

        # ── the remaining qualifiers
        if use_sweep and (sweepLoAge if is_long else sweepHiAge) > sweep_age:
            rej_("sweep"); continue
        if use_deliv and g["delv"] < deliv_atr:
            rej_("delivery"); continue
        sl = (g["bot"] - A*sl_buf) if is_long else (g["top"] + A*sl_buf)
        risk = (c[i] - sl) if is_long else (sl - c[i])
        if risk <= 0 or risk > A*max_risk:
            rej_("risk"); continue
        tgt = swingHi if is_long else swingLo
        if use_tgt:
            if tgt is None:
                rej_("no target"); continue
            room = (tgt - c[i]) if is_long else (c[i] - tgt)
            if room < risk*min_tgt_r:
                rej_("targets"); continue
        if i - last < cooldown:
            rej_("cooldown"); continue

        g["stat"] = 2
        last = i
        # duration only: bars until the stop or the liquidity target is reached
        dur = 0
        for k in range(i+1, min(i+200, n)):
            dur = k - i
            if (l[k] <= sl) if is_long else (h[k] >= sl):
                break
            if tgt is not None and ((h[k] >= tgt) if is_long else (l[k] <= tgt)):
                break
        sigs.append(dict(i=i, side=side, dur=dur, risk=risk/A, size=g["size"], delv=g["delv"]))

    return dict(signals=sigs, blocks=blocks)
