"""ME SCALP v2.4 — the three levers the user named: STOP, ENTRY ZONE, CONFIRMATION.

WHAT THIS IS FOR. The report is "3 won and 2 lost, unstable win rate on 5m to
15m". Five trades cannot measure a win rate — 3W/2L is what a 59% process looks
like most of the time it is sampled five times. So this file does not chase the
five. It measures the three things that were actually asked for, on the SAME
engine the Pine ships, and only changes what the measurement supports.

THE ENGINE MODELLED HERE IS v2.3 EXACTLY:

    slRaw = min(inval, close - atr*minRisk) - atr*slBuf - atr*structPad
    reject when risk > atr*structMax
    targets at fixed ATR distances (0.8 / 1.4 / 2.0), TP1 pulled in to structure
    breakeven after TP1, time stop 12 bars, ER regime gate, score >= 1

LEVERS SWEPT, one at a time and then together:

  INVALIDATION  v2.3 builds a fade's stop from the TRIGGER BAR'S OWN WICK. That
                is one bar of information. "swing" uses the extreme of the last
                `look` bars instead, so the stop sits beyond the local structure
                rather than beyond one candle.

  ENTRY ZONE    "close" = market at the trigger close (v2.3).
                "retest" = arm at the trigger's OWN level and fill only if price
                comes back to it. Measured at 88% fill on the ME Pro stack; it
                buys a better price and a shorter distance to the stop.

  CONFIRMATION  "confirm" = wait one bar and require it to CLOSE beyond the
                trigger bar's extreme before entering. Costs a bar of price and
                some trades; the question is whether the outcome mix pays.

THE FILL BAR IS CHECKED FOR THE STOP. On a retest the bar that fills can also
take the trade out, and not checking it flatters the retest by about 3 points of
stop-out rate. That correction is in.

COUNTS AND OUTCOME GEOMETRY ONLY. NO EXPECTANCY IS COMPUTED OR QUOTED — the
generator that produced this repo's old expectancy figures paid a naive momentum
rule +0.21R, so no mean-R from it is worth printing.
"""
import math
from gen import series_regime
from engine import wilder_atr, sma_prior, frvp
from flow import vwap_bands, zones
from scalp import triggers

DAYS, SEEDS = 120, (1, 2, 3)
FADE = ("band", "band2", "value", "sweep")   # stop built from a single wick in v2.3


def bars_at(seed, tf_min):
    m1 = series_regime(60 * 24 * DAYS, 60, seed=seed)
    out = []
    for j in range(0, len(m1) - tf_min + 1, tf_min):
        w = m1[j:j + tf_min]
        out.append((w[0][0], w[0][1], max(b[2] for b in w), min(b[3] for b in w),
                    w[-1][4], sum(b[5] for b in w)))
    return out


_CACHE = {}


def prep(seed, tf_min, band_w=0.0):
    key = (seed, tf_min, band_w)
    if key in _CACHE:
        return _CACHE[key]
    bars = bars_at(seed, tf_min)
    h = [b[2] for b in bars]; l = [b[3] for b in bars]
    c = [b[4] for b in bars]; o = [b[1] for b in bars]; v = [b[5] for b in bars]
    atr = wilder_atr(h, l, c, 14)
    vw, u1, l1, u2, l2 = vwap_bands(bars, 1.0, 2.0)
    Z = zones(bars, atr, 0.30, 30)
    POC, VAH, VAL = frvp(bars)
    T = triggers(bars, atr, vw, u1, l1, u2, l2, Z, VAH, VAL, band_min_w=band_w)
    vavg = sma_prior(v, 20)
    D = dict(bars=bars, o=o, h=h, l=l, c=c, v=v, atr=atr, vw=vw, u1=u1, l1=l1,
             u2=u2, l2=l2, POC=POC, VAH=VAH, VAL=VAL, T=T, vavg=vavg, n=len(bars))
    _CACHE[key] = D
    return D


def eff_ratio(c, i, ln):
    if i <= ln:
        return None
    path = sum(abs(c[k] - c[k - 1]) for k in range(i - ln + 1, i + 1))
    return abs(c[i] - c[i - ln]) / max(path, 1e-9)


def walk(D, is_buy, entry, sl, tps, start, tstop):
    """Path resolution from bar `start`. Breakeven after TP1, hard time stop.
    Returns (how, got, dur)."""
    h, l, n = D["h"], D["l"], D["n"]
    stop, got, at_be = sl, [False] * 3, False
    for k in range(start, min(start + tstop, n)):
        hit_sl = (l[k] <= stop) if is_buy else (h[k] >= stop)
        for t in range(3):
            if got[t]:
                continue
            reach = (h[k] >= tps[t]) if is_buy else (l[k] <= tps[t])
            # a bar that touches both the stop and TP1 is scored as the stop
            if reach and not (hit_sl and t == 0 and not got[0]):
                got[t] = True
                if t == 0:
                    stop, at_be = entry, True
        if hit_sl:
            return ("be" if at_be else "sl"), got, k - start + 1
        if all(got):
            return "tp3", got, k - start + 1
    return "time", got, tstop


def run(tf_min, inval_mode="bar", entry_mode="close", look=5, pend=4,
        sl_buf=0.20, struct_pad=0.25, fade_pad=None, min_risk=0.40,
        struct_max=4.0, tp_r=(0.8, 1.4, 2.0), tstop=12, cooldown=3,
        er_min=0.32, er_len=20, need=1, only=None, drop=(), band_w=0.0,
        confirm_only=None, pad_by=None, score_bar="trigger"):
    """One pass over every seed at one timeframe.

    fade_pad     when set, replaces struct_pad for the fade family only
    pad_by       {trigger name: struct_pad} overriding struct_pad per family
    drop         trigger names removed from the engine entirely
    band_w       minimum VWAP band WIDTH in ATR for a band event to count
    confirm_only when set, the confirmation bar is required ONLY for these
                 trigger names; everything else still enters at the close
    """
    out = []
    armed = filled = 0
    for seed in SEEDS:
        D = prep(seed, tf_min, band_w)
        o, h, l, c, n = D["o"], D["h"], D["l"], D["c"], D["n"]
        atr, vavg = D["atr"], D["vavg"]
        last = -10 ** 9
        for i in range(60, n - tstop - pend - 3):
            A = atr[i]
            if math.isnan(A) or math.isnan(vavg[i]):
                continue
            ev = D["T"][i]
            if not ev["buy"] and not ev["sell"]:
                continue
            rng = max(h[i] - l[i], 1e-9)
            cp = (c[i] - l[i]) / rng
            body = abs(c[i] - o[i]); relv = D["v"][i] / max(vavg[i], 1e-9)
            er = eff_ratio(c, i, er_len)
            if er is None or er < er_min:
                continue
            for is_buy in (True, False):
                cand = ev["buy"] if is_buy else ev["sell"]
                if drop:
                    cand = [x for x in cand if x[0] not in drop]
                if not cand:
                    continue
                if (c[i] > c[i - er_len]) != is_buy:      # i_align
                    continue
                if (c[i] > o[i]) != is_buy:               # bar agrees
                    continue
                if i - last < cooldown:
                    continue
                name, ref, inval = cand[0]
                if only and name not in only:
                    continue

                needs_conf = (confirm_only is not None and name in confirm_only) \
                    or (confirm_only is None and entry_mode in ("confirm", "retest_confirm"))
                si = i + 1 if (score_bar == "confirm" and needs_conf and i + 1 < n) else i
                srng = max(h[si] - l[si], 1e-9)
                scp = (c[si] - l[si]) / srng
                sbody = abs(c[si] - o[si]); srelv = D["v"][si] / max(vavg[si], 1e-9)
                score = 0
                if srelv >= 1.15: score += 1
                if sbody >= A * 0.45: score += 1
                if (scp >= 0.65) if is_buy else (scp <= 0.35): score += 1
                if len(cand) >= 2: score += 1
                if name == "band2": score += 1
                elif name != "band":
                    if (c[si] <= D["l1"][si] * 1.002) if is_buy else (c[si] >= D["u1"][si] * 0.998):
                        score += 1
                if score < need:
                    continue

                # ── INVALIDATION ────────────────────────────────────────────
                iv = inval
                if inval_mode == "swing" and name in FADE:
                    lo = max(0, i - look + 1)
                    iv = min(l[lo:i + 1]) if is_buy else max(h[lo:i + 1])
                    iv = min(iv, inval) if is_buy else max(iv, inval)

                pad = struct_pad if (fade_pad is None or name not in FADE) else fade_pad
                if pad_by and name in pad_by:
                    pad = pad_by[name]

                # ── ENTRY ───────────────────────────────────────────────────
                em = entry_mode
                if confirm_only is not None:
                    em = "confirm" if name in confirm_only else "close"
                if em == "close":
                    ent, start = c[i], i + 1
                elif em == "confirm":
                    j = i + 1
                    if j >= n:
                        continue
                    if (c[j] <= h[i]) if is_buy else (c[j] >= l[i]):
                        last = i
                        break
                    ent, start = c[j], j + 1
                elif em in ("retest", "retest_confirm"):
                    j0 = i + 1
                    if em == "retest_confirm":
                        j = i + 1
                        if j >= n or ((c[j] <= h[i]) if is_buy else (c[j] >= l[i])):
                            last = i
                            break
                        j0 = j + 1
                    armed += 1
                    fill = None
                    for j in range(j0, min(j0 + pend, n)):
                        if (l[j] <= ref) if is_buy else (h[j] >= ref):
                            fill = j
                            break
                    if fill is None:
                        last = i
                        break
                    filled += 1
                    ent, start = ref, fill + 1
                else:
                    raise ValueError(em)

                # ── STOP, from the entry actually used ──────────────────────
                if is_buy:
                    sl = min(iv, ent - A * min_risk) - A * sl_buf - A * pad
                    risk = ent - sl
                else:
                    sl = max(iv, ent + A * min_risk) + A * sl_buf + A * pad
                    risk = sl - ent
                if risk < A * min_risk * 0.5 or risk > A * struct_max:
                    last = i
                    break

                # THE FILL BAR CAN ALSO TAKE THE TRADE OUT. Not checking it
                # flatters every delayed entry.
                if em in ("retest", "retest_confirm"):
                    fb = start - 1
                    if (l[fb] <= sl) if is_buy else (h[fb] >= sl):
                        out.append(dict(name=name, how="sl", got=[False] * 3,
                                        dur=0, r=risk / A))
                        last = i
                        break

                d = 1.0 if is_buy else -1.0
                tps = []
                for s_, rmul in enumerate(tp_r):
                    t = ent + d * A * rmul
                    if s_ == 0:
                        near = [x for x in ((D["u1"][i] if is_buy else D["l1"][i]),
                                            D["vw"][i], D["POC"][i])
                                if x is not None and (x > ent) == is_buy
                                and abs(x - ent) < abs(t - ent) and abs(x - ent) >= A * 0.6]
                        if near:
                            t = min(near, key=lambda x: abs(x - ent))
                    tps.append(t)

                how, got, dur = walk(D, is_buy, ent, sl, tps, start, tstop)
                out.append(dict(name=name, how=how, got=got, dur=dur, r=risk / A))
                last = i
                break
    return out, armed, filled


def pct(a, b):
    return 100.0 * a / b if b else 0.0


HDR = ("%-26s%8s%9s%8s%7s%7s%7s%7s%6s" %
       ("", "trades", "per day", "TP1", "BE", "TP3", "SL", "time", "bars"))


def row(label, t, days, extra=""):
    n = len(t)
    if not n:
        print("  %-26s%8s" % (label, "none"))
        return
    be = sum(1 for x in t if x["how"] == "be")
    tp3 = sum(1 for x in t if x["how"] == "tp3")
    sl = sum(1 for x in t if x["how"] == "sl")
    tm = sum(1 for x in t if x["how"] == "time")
    print("  %-26s%8d%9.2f%7.0f%%%6.0f%%%6.0f%%%6.0f%%%6.0f%%%6d%s" % (
        label, n, n / days, pct(be + tp3, n), pct(be, n), pct(tp3, n),
        pct(sl, n), pct(tm, n), sorted(x["dur"] for x in t)[n // 2], extra))


if __name__ == "__main__":
    days = DAYS * len(SEEDS)
    for tf in (5, 15):
        print("\n" + "=" * 96)
        print("%dm — ME Scalp v2.3 as shipped, then one lever at a time" % tf)
        print("=" * 96)
        print(HDR)
        base, _, _ = run(tf)
        row("v2.3 baseline", base, days)
        print("\n  by trigger family:")
        for nm in ("mss", "fvg", "sweep", "band", "band2", "value"):
            row("  " + nm, [x for x in base if x["name"] == nm], days)

        print("\n  LEVER 1 — invalidation for the fade family:")
        for lk in (3, 5, 8):
            t, _, _ = run(tf, inval_mode="swing", look=lk)
            row("  swing(%d) inval" % lk, t, days)

        print("\n  LEVER 2 — entry zone:")
        t, a, f = run(tf, entry_mode="retest")
        row("  retest at the level", t, days, "  fill %.0f%%" % pct(f, a))

        print("\n  LEVER 3 — confirmation (next bar closes beyond the trigger bar):")
        t, _, _ = run(tf, entry_mode="confirm")
        row("  confirm", t, days)
        t, a, f = run(tf, entry_mode="retest_confirm")
        row("  confirm then retest", t, days, "  fill %.0f%%" % pct(f, a))

        print("\n  LEVER 2b — the band family, which is where the drag is:")
        t, _, _ = run(tf, drop=("band", "band2"))
        row("  bands off entirely", t, days)
        for w in (0.15, 0.30, 0.50):
            t, _, _ = run(tf, band_w=w)
            row("  band needs %.2f ATR width" % w, t, days)

        print("\n  COMBINED — confirmation required of the FADES only:")
        t, _, _ = run(tf, confirm_only=FADE)
        row("  confirm fades", t, days)
        t, _, _ = run(tf, confirm_only=FADE, band_w=0.30)
        row("  confirm fades + band 0.30", t, days)
        t, _, _ = run(tf, confirm_only=("band", "band2", "value"), band_w=0.30)
        row("  same, sweep unconfirmed", t, days)

        print("\n  LEVER 4 — stop pad under 'confirm fades + band 0.30':")
        for buf in (0.00, 0.10, 0.20, 0.35):
            t, _, _ = run(tf, confirm_only=FADE, band_w=0.30, sl_buf=buf)
            row("  pad %.2f ATR total" % (buf + 0.25), t, days)

    print("\n  Counts and outcome geometry only. NO EXPECTANCY COMPUTED OR QUOTED.")
