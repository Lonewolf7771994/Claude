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
             wick=0.35, mss_follow=0.08, swing=2, sweep_len=5, band_min_w=0.0):
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
        # 4 VWAP band rejection — the highest-supply event in the engine.
        # A band is only a level if it has WIDTH. At session open the deviation
        # is computed from one sample, so u1==l1==vwap and "low <= l1" is
        # trivially true — the trigger fires on arithmetic, not on a rejection.
        bandOk = (u1[i] - l1[i]) >= A * band_min_w
        for tag, lo, up in ((("band", l1, u1), ("band2", l2, u2)) if bandOk else ()):
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


def resolve(bars, i, is_buy, entry, sl, tps, tstop, be_after_tp1=True, start=None,
            no_tp_first=False):
    """33/33/34 scale-out, breakeven after TP1, and a hard time stop. Returns
    (pnl in R, legs filled, bars held, how it ended)."""
    R = abs(entry - sl); got = [False]*3; stop = sl; pnl = 0.0; w = [.33, .33, .34]
    k0 = i+1 if start is None else start
    for k in range(k0, min(k0+tstop, len(bars))):
        hi, lo = bars[k][2], bars[k][3]
        hit_sl = lo <= stop if is_buy else hi >= stop
        # On a limit-fill bar the high and the low both belong to the same bar
        # and OHLC does not say which came first. Crediting a target there
        # assumes the favourable ordering on every fill; only the stop is
        # evaluated, which is the pessimistic reading.
        skip_tp = no_tp_first and k == k0
        for t in range(3):
            if got[t] or skip_tp: continue
            reach = hi >= tps[t] if is_buy else lo <= tps[t]
            # a bar that touches both the stop and TP1 is scored as the stop
            if reach and not (hit_sl and t == 0 and not got[0]):
                got[t] = True; pnl += w[t] * abs(tps[t]-entry) / R
                if t == 0 and be_after_tp1: stop = entry
        if hit_sl:
            rem = sum(w[t] for t in range(3) if not got[t])
            pnl += rem * (0.0 if stop == entry else -1.0)
            return pnl, got, k-k0+1, ("be" if stop == entry else "sl")
        if all(got):
            return pnl, got, k-k0+1, "tp3"
    # time stop — close the remainder at the last close
    rem = sum(w[t] for t in range(3) if not got[t])
    last = bars[min(len(bars)-1, k0+tstop-1)][4]
    pnl += rem * ((last-entry)/R if is_buy else (entry-last)/R)
    return pnl, got, tstop, "time"


def run(bars, tf_sec, freq="Standard",
        max_risk=1.0, min_risk=0.40, sl_buf=0.20,
        tp_r=(1.0, 1.5, 2.0), tstop=12, cooldown=2, need=None,
        er_min=0.0, er_len=20, align=False, runner=0.0, confirm=0,
        entry_mode="close", pend_bars=3, hold=0, band_min_w=0.0):
    h = [b[2] for b in bars]; l = [b[3] for b in bars]
    c = [b[4] for b in bars]; o = [b[1] for b in bars]; v = [b[5] for b in bars]
    atr = wilder_atr(h, l, c, 14)
    vw, u1, l1, u2, l2 = vwap_bands(bars, 1.0, 2.0)
    Z = zones(bars, atr, 0.30, 30)
    POC, VAH, VAL = frvp(bars)
    T = triggers(bars, atr, vw, u1, l1, u2, l2, Z, VAH, VAL, band_min_w=band_min_w)
    vavg = sma_prior(v, 20)

    # Kaufman efficiency ratio: net movement divided by path travelled.
    # ~0 = the bar is inside chop, ~1 = a clean directional leg.
    ER = [None]*len(bars)
    path = 0.0
    for i in range(1, len(bars)):
        path += abs(c[i]-c[i-1])
        if i > er_len:
            path -= abs(c[i-er_len]-c[i-er_len-1])
            ER[i] = abs(c[i]-c[i-er_len]) / max(path, 1e-9)

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

            # ── REGIME. Measured on regime-bearing data, the engine earns
            # +0.31 to +0.68R in the top two ER quintiles and roughly nothing in
            # the bottom three — which held 97% of its trades. Trading the chop
            # is what made the output look chaotic AND what kept it absent from
            # the moves; both complaints, one cause.
            if er_min > 0.0:
                e = ER[i]
                if e is None or e < er_min:
                    blocks["chop"] = blocks.get("chop", 0)+1; continue
                if align:
                    up = c[i] > c[i-er_len]
                    if up != is_buy:
                        blocks["against"] = blocks.get("against", 0)+1; continue

            # ── CONFIRMATION variants, measured rather than assumed:
            #   1 the signal bar closes beyond the PRIOR bar's extreme
            #   2 the signal bar closes beyond the prior TWO bars' extreme
            if confirm > 0:
                if is_buy:
                    ref_ = max(h[i-1], h[i-2]) if confirm > 1 else h[i-1]
                    if c[i] <= ref_:
                        blocks["confirm"] = blocks.get("confirm", 0)+1; continue
                else:
                    ref_ = min(l[i-1], l[i-2]) if confirm > 1 else l[i-1]
                    if c[i] >= ref_:
                        blocks["confirm"] = blocks.get("confirm", 0)+1; continue

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
            eff_tp = (tp_r[0], tp_r[1], max(tp_r[2], runner)) if runner > 0 else tp_r
            for s_, rmul in enumerate(eff_tp):
                t = c[i] + d*risk*rmul
                if s_ == 0:
                    near = [x for x in (u1[i] if is_buy else l1[i], vw[i],
                                        POC[i] if POC[i] else None)
                            if x is not None and (x > c[i]) == is_buy
                            and abs(x-c[i]) < abs(t-c[i]) and abs(x-c[i]) >= risk*0.6]
                    if near: t = min(near, key=lambda x: abs(x-c[i]))
                tps.append(t)
            # ── ENTRY MODE ─────────────────────────────────────────────────
            # "close"  take the signal bar's close (chase)
            # "retest" rest a limit AT the trigger's own level and wait for
            #          price to come back to it. The retest holding IS the
            #          confirmation, and the entry is closer to the
            #          invalidation, so the same stop costs less risk.
            ei = i
            entry = c[i]
            if entry_mode == "retest":
                if ref is None or (ref > c[i]) == is_buy:
                    blocks["noref"] = blocks.get("noref", 0)+1; continue
                filled = False
                for k in range(i+1, min(i+1+pend_bars, len(bars))):
                    if (l[k] <= ref) if is_buy else (h[k] >= ref):
                        ei = k
                        entry = ref
                        filled = True
                        break
                    # level breaks the wrong way first -> setup is dead
                    if (c[k] < inval) if is_buy else (c[k] > inval):
                        break
                if not filled:
                    blocks["nofill"] = blocks.get("nofill", 0)+1; continue
                # The stop must stay a REAL distance from the actual fill.
                # Allowing it to collapse toward the level makes every
                # R-multiple target trivially reachable and manufactures wins:
                # measured +0.49R on driftless data, where no edge can exist.
                sl = min(sl, entry - A*min_risk) if is_buy else max(sl, entry + A*min_risk)
                risk = (entry - sl) if is_buy else (sl - entry)
                if risk < A*min_risk:
                    blocks["thin"] = blocks.get("thin", 0)+1; continue
                d2 = 1.0 if is_buy else -1.0
                tps = [entry + d2*risk*r_ for r_ in eff_tp]

            # ── HOLD: wait one bar and require it to close beyond the entry
            # reference, THEN enter at that bar's close. v1 of this test read
            # the next bar's close to accept the trade but still entered at the
            # OLD price — buying only trades already known to be winning. It
            # scored 91.7% win and +1.04R, which is what a lookahead bug looks
            # like. Entering at the confirming bar's own close is the honest
            # version and it costs the entry level, as it should.
            if hold > 0:
                if ei+1 >= len(bars):
                    blocks["hold"] = blocks.get("hold", 0)+1; continue
                nxt = bars[ei+1]
                if (nxt[4] < entry) if is_buy else (nxt[4] > entry):
                    blocks["hold"] = blocks.get("hold", 0)+1; continue
                ei = ei + 1
                entry = nxt[4]
                # floor AND cap, both from the actual entry. Flooring only lets
                # risk grow by however far the confirming bar ran, which makes
                # the target ladder unreachable while the stop stays in range.
                if is_buy:
                    sl = min(sl, entry - A*min_risk)
                    sl = max(sl, entry - A*max_risk)
                else:
                    sl = max(sl, entry + A*min_risk)
                    sl = min(sl, entry + A*max_risk)
                risk = (entry - sl) if is_buy else (sl - entry)
                if risk < A*min_risk*0.999:
                    blocks["thin"] = blocks.get("thin", 0)+1; continue
                d3 = 1.0 if is_buy else -1.0
                tps = [entry + d3*risk*r_ for r_ in eff_tp]

            # a limit fill is charged for the REST of its own fill bar
            lim = entry_mode == "retest" and hold == 0
            st = ei if lim else None
            pnl, got, dur, how = resolve(bars, ei, is_buy, entry, sl, tps, tstop,
                                         start=st, no_tp_first=lim)
            trades.append(dict(i=ei, side="B" if is_buy else "S", pnl=pnl, got=got,
                               dur=dur, how=how, trig=name, score=score, r=risk/A))
            last = ei
            break
    return dict(triggers=ntrig, signals=len(trades), trades=trades, blocks=blocks)
