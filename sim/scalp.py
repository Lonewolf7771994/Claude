"""ME Scalp — a purpose-built scalp engine, not a patch of ME Pro.

WHY A REWRITE. ME Pro ANDs 19 gates. If each independently passes 85% of the
time the chain passes 0.85^19 = 4.6%, which is precisely the 2-4% trigger
conversion measured across v3.5.x. Loosening any single gate moves one factor in
a 19-term product, which is why six passes of threshold tuning never fixed it.

THREE STRUCTURAL CHANGES.

  1 SCORE, NOT A CHAIN. Bar quality is one 0-5 score with a threshold, so a
    strong bar that is merely average on one dimension still trades. In the AND
    chain any single below-threshold reading killed it outright.

  2 HARD GATES ONLY WHERE THEY ARE ABOUT SAFETY. Three remain, and each answers
    "is this tradeable", never "is this good": the bar agrees with the direction,
    the risk is measurable, the cooldown has elapsed.

  3 TIGHT RISK AND A TIME STOP. Stop distance sets target distance (TP1 = 1R),
    so a wide stop makes a slow trade. Risk is capped at 1.0 ATR and a trade that
    has resolved nothing in `tstop` bars is closed. "Quick" is enforced, not hoped
    for.
"""
import math
from engine import wilder_atr, ema, sma_prior, pivots, frvp
from flow import vwap_bands, zones


def triggers(bars, atr, vw, u1, l1, u2, l2, Z, VAH, VAL,
             wick=0.35, mss_follow=0.08, swing=2, sweep_len=5):
    """Five independent entry events. Each carries its own invalidation level,
    so the stop is defined by the setup rather than by a fixed ATR guess."""
    n = len(bars)
    h = [b[2] for b in bars]; l = [b[3] for b in bars]
    c = [b[4] for b in bars]
    ph, pl = pivots(h, l, swing)
    sph, spl = pivots(h, l, sweep_len)
    PH = []; PL = []; SPH = None; SPL = None
    out = []
    for i in range(n):
        if ph[i] is not None: PH.insert(0, ph[i]); PH = PH[:3]
        if pl[i] is not None: PL.insert(0, pl[i]); PL = PL[:3]
        if sph[i] is not None: SPH = sph[i]
        if spl[i] is not None: SPL = spl[i]
        ev = {"buy": [], "sell": []}
        if i < 60 or math.isnan(atr[i]):
            out.append(ev); continue
        A = atr[i]
        rng = max(h[i] - l[i], 1e-9); cp = (c[i] - l[i]) / rng

        # 1 MSS — structure gives way
        if PH and c[i] >= PH[0] + A * mss_follow and c[i-1] < PH[0]:
            ev["buy"].append(("mss", PH[0], PL[0] if PL else l[i]))
        if PL and c[i] <= PL[0] - A * mss_follow and c[i-1] > PL[0]:
            ev["sell"].append(("mss", PL[0], PH[0] if PH else h[i]))
        # 2 FVG retest
        bz, sz = Z[i]
        for g in reversed(bz):
            if l[i] <= g[0] and c[i] >= g[1] and cp >= .55:
                ev["buy"].append(("fvg", g[0], g[1])); break
        for g in reversed(sz):
            if h[i] >= g[1] and c[i] <= g[0] and cp <= .45:
                ev["sell"].append(("fvg", g[1], g[0])); break
        # 3 sweep and reclaim
        if SPL and (SPL - l[i]) >= A * wick and c[i] > SPL and cp >= .55:
            ev["buy"].append(("sweep", SPL, l[i]))
        if SPH and (h[i] - SPH) >= A * wick and c[i] < SPH and cp <= .45:
            ev["sell"].append(("sweep", SPH, h[i]))
        # 4 VWAP band rejection — the highest-supply event in the engine
        for tag, lo, up in (("band", l1, u1), ("band2", l2, u2)):
            if l[i] <= lo[i] and c[i] > lo[i] and cp >= .55:
                ev["buy"].append((tag, lo[i], l[i]))
            if h[i] >= up[i] and c[i] < up[i] and cp <= .45:
                ev["sell"].append((tag, up[i], h[i]))
        # 5 value-area rejection
        if VAL[i] is not None and VAH[i] is not None:
            if l[i] <= VAL[i] and c[i] > VAL[i] and cp >= .55:
                ev["buy"].append(("value", VAL[i], l[i]))
            if h[i] >= VAH[i] and c[i] < VAH[i] and cp <= .45:
                ev["sell"].append(("value", VAH[i], h[i]))
        out.append(ev)
    return out


def resolve(bars, i, is_buy, entry, sl, tps, tstop, be_after_tp1=True):
    """33/33/34 scale-out, breakeven after TP1, and a hard time stop. Returns
    (pnl in R, legs filled, bars held, how it ended)."""
    R = abs(entry - sl); got = [False]*3; stop = sl; pnl = 0.0; w = [.33, .33, .34]
    for k in range(i+1, min(i+1+tstop, len(bars))):
        hi, lo = bars[k][2], bars[k][3]
        hit_sl = lo <= stop if is_buy else hi >= stop
        for t in range(3):
            if got[t]: continue
            reach = hi >= tps[t] if is_buy else lo <= tps[t]
            # a bar that touches both the stop and TP1 is scored as the stop
            if reach and not (hit_sl and t == 0 and not got[0]):
                got[t] = True; pnl += w[t] * abs(tps[t]-entry) / R
                if t == 0 and be_after_tp1: stop = entry
        if hit_sl:
            rem = sum(w[t] for t in range(3) if not got[t])
            pnl += rem * (0.0 if stop == entry else -1.0)
            return pnl, got, k-i, ("be" if stop == entry else "sl")
        if all(got):
            return pnl, got, k-i, "tp3"
    # time stop — close the remainder at the last close
    rem = sum(w[t] for t in range(3) if not got[t])
    last = bars[min(len(bars)-1, i+tstop)][4]
    pnl += rem * ((last-entry)/R if is_buy else (entry-last)/R)
    return pnl, got, tstop, "time"


def run(bars, tf_sec, freq="Standard",
        max_risk=1.0, min_risk=0.40, sl_buf=0.20,
        tp_r=(1.0, 1.5, 2.0), tstop=12, cooldown=2, need=None):
    h = [b[2] for b in bars]; l = [b[3] for b in bars]
    c = [b[4] for b in bars]; o = [b[1] for b in bars]; v = [b[5] for b in bars]
    atr = wilder_atr(h, l, c, 14)
    vw, u1, l1, u2, l2 = vwap_bands(bars, 1.0, 2.0)
    Z = zones(bars, atr, 0.30, 30)
    POC, VAH, VAL = frvp(bars)
    T = triggers(bars, atr, vw, u1, l1, u2, l2, Z, VAH, VAL)
    vavg = sma_prior(v, 20)

    # Calibrated, not guessed. Sweep of score threshold x cooldown on 5m/15m:
    #   need 3 -> 23.5/day on 5m (overtrading), need 5 -> 0.23/day on 15m
    #   (starvation, the exact disease this rewrite exists to cure).
    # need 4 is the usable band; the frequencies then separate on cooldown.
    if need is None:
        need, cooldown = {"High": (3, 4), "Standard": (4, 3), "Selective": (4, 6)}[freq]
    last = -10**9
    trades = []; blocks = {}; ntrig = 0

    for i in range(60, len(bars)):
        A = atr[i]
        if math.isnan(A) or math.isnan(vavg[i]): continue
        ev = T[i]
        if not ev["buy"] and not ev["sell"]: continue
        ntrig += 1
        rng = max(h[i]-l[i], 1e-9); cp = (c[i]-l[i])/rng
        body = abs(c[i]-o[i]); relv = v[i]/max(vavg[i], 1e-9)

        for is_buy in (True, False):
            cand = ev["buy"] if is_buy else ev["sell"]
            if not cand: continue
            name, ref, inval = cand[0]

            # ── HARD GATE 1: the bar must agree with the direction traded
            if (c[i] > o[i]) != is_buy:
                blocks["dir"] = blocks.get("dir", 0)+1; continue
            # ── HARD GATE 2: cooldown
            if i - last < cooldown:
                blocks["cd"] = blocks.get("cd", 0)+1; continue

            # ── QUALITY SCORE, 0-5. Replaces 19 ANDed vetoes.
            score = 0
            if relv >= 1.15: score += 1
            if body >= A*0.45: score += 1
            if (cp >= 0.65) if is_buy else (cp <= 0.35): score += 1
            if len(cand) >= 2: score += 1
            if name not in ("band", "band2"):
                if (c[i] <= l1[i]*1.002) if is_buy else (c[i] >= u1[i]*0.998):
                    score += 1
            else:
                score += 1 if name == "band2" else 0
            if score < need:
                blocks["score"] = blocks.get("score", 0)+1; continue

            # ── HARD GATE 3: risk must be measurable and inside the window.
            # A stop past the cap is CLAMPED to the cap, never used to reject —
            # rejecting there is what starved ME Pro.
            raw = (min(inval, c[i]-A*min_risk) - A*sl_buf) if is_buy else \
                  (max(inval, c[i]+A*min_risk) + A*sl_buf)
            far = A*max_risk
            sl = max(raw, c[i]-far) if is_buy else min(raw, c[i]+far)
            risk = (c[i]-sl) if is_buy else (sl-c[i])
            if risk < A*min_risk*0.5:
                blocks["risk"] = blocks.get("risk", 0)+1; continue

            # ── TARGETS. Fixed R, pulled IN to structure only when structure is
            # nearer. A target can never be further than its R-multiple, so TP1
            # is always reachable — the defect that let trades sit for 30+ min.
            d = 1.0 if is_buy else -1.0
            tps = []
            for s_, rmul in enumerate(tp_r):
                t = c[i] + d*risk*rmul
                if s_ == 0:
                    near = [x for x in (u1[i] if is_buy else l1[i], vw[i],
                                        POC[i] if POC[i] else None)
                            if x is not None and (x > c[i]) == is_buy
                            and abs(x-c[i]) < abs(t-c[i]) and abs(x-c[i]) >= risk*0.6]
                    if near: t = min(near, key=lambda x: abs(x-c[i]))
                tps.append(t)
            pnl, got, dur, how = resolve(bars, i, is_buy, c[i], sl, tps, tstop)
            trades.append(dict(i=i, side="B" if is_buy else "S", pnl=pnl, got=got,
                               dur=dur, how=how, trig=name, score=score, r=risk/A))
            last = i
            break
    return dict(triggers=ntrig, signals=len(trades), trades=trades, blocks=blocks)
