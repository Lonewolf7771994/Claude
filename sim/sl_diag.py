"""Is the ME Scalp stop actually too tight? Measure it rather than argue about it.

THE SUSPICION. The stop is built from the setup's own invalidation level and then
CLAMPED into a 1.0 ATR window:

    raw = min(inval, close - A*min_risk) - A*sl_buf
    sl  = max(raw, close - A*max_risk)          <- the clamp

When the clamp binds, the stop no longer sits BEYOND the level that would prove
the idea wrong. It sits INSIDE it. Price returning to the structure — which is
ordinary behaviour, not invalidation — then takes the trade out.

The v2.1 header already half-noticed this: "widening the stop buffer did nothing
at all (SL 45% -> 44%) since the 1.0 ATR clamp already governs the distance."
That is the buffer being inert because the clamp dominates every stop.

WHAT IS MEASURED HERE, and why these are trustworthy despite the generator
retraction: all four are GEOMETRIC properties of where the stop is placed
relative to structure and to the subsequent price path. None depends on the
generator's drift.

  1  clamp rate        how often the structural stop is outside the cap
  2  intrusion         when clamped, how far INSIDE the invalidation the stop
                       lands, in ATR
  3  SL rate           stop-outs as a share of trades
  4  PREMATURE STOPS   the one that matters: stop hit while the structural
                       invalidation was NEVER breached. That is a trade closed
                       for a loss while its own thesis was still intact.

MEAN R IS NOT REPORTED. The generator that produced the v2.1 header's expectancy
figures paid a naive momentum rule +0.214R, so no expectancy number from this
harness is worth reporting. Outcome MIX is reported because it is geometry.
"""
import math
import sys
from gen import series_regime
from engine import wilder_atr, sma_prior, frvp
from flow import vwap_bands, zones
from scalp import triggers, resolve


def run_diag(bars, freq="Standard", stop_mode="clamp",
             max_risk=1.0, min_risk=0.40, sl_buf=0.20,
             tp_r=(0.8, 1.4, 2.0), tstop=12,
             er_min=0.32, er_len=20, align=True, need=1, cooldown=3,
             struct_pad=0.0):
    """stop_mode:
         clamp      current v2.1 behaviour — squeeze the stop to the cap
         reject     decline the setup when structure needs more than the cap
         structure  honour the structural stop, cap only as a far backstop
    struct_pad: extra ATR beyond the invalidation, used by 'structure' mode.
    """
    h = [b[2] for b in bars]; l = [b[3] for b in bars]
    c = [b[4] for b in bars]; o = [b[1] for b in bars]; v = [b[5] for b in bars]
    atr = wilder_atr(h, l, c, 14)
    vw, u1, l1, u2, l2 = vwap_bands(bars, 1.0, 2.0)
    Z = zones(bars, atr, 0.30, 30)
    POC, VAH, VAL = frvp(bars)
    T = triggers(bars, atr, vw, u1, l1, u2, l2, Z, VAH, VAL)
    vavg = sma_prior(v, 20)

    ER = [None] * len(bars)
    path = 0.0
    for i in range(1, len(bars)):
        path += abs(c[i] - c[i - 1])
        if i > er_len:
            path -= abs(c[i - er_len] - c[i - er_len - 1])
            ER[i] = abs(c[i] - c[i - er_len]) / max(path, 1e-9)

    last = -10 ** 9
    trades = []
    rejected_wide = 0

    for i in range(60, len(bars)):
        A = atr[i]
        if math.isnan(A) or math.isnan(vavg[i]):
            continue
        ev = T[i]
        if not ev["buy"] and not ev["sell"]:
            continue
        rng = max(h[i] - l[i], 1e-9); cp = (c[i] - l[i]) / rng
        body = abs(c[i] - o[i]); relv = v[i] / max(vavg[i], 1e-9)

        for is_buy in (True, False):
            cand = ev["buy"] if is_buy else ev["sell"]
            if not cand:
                continue
            name, ref, inval = cand[0]

            if er_min > 0.0:
                e = ER[i]
                if e is None or e < er_min:
                    continue
                if align and (c[i] > c[i - er_len]) != is_buy:
                    continue
            if (c[i] > o[i]) != is_buy:
                continue
            if i - last < cooldown:
                continue

            score = 0
            if relv >= 1.15: score += 1
            if body >= A * 0.45: score += 1
            if (cp >= 0.65) if is_buy else (cp <= 0.35): score += 1
            if len(cand) >= 2: score += 1
            if name not in ("band", "band2"):
                if (c[i] <= l1[i] * 1.002) if is_buy else (c[i] >= u1[i] * 0.998):
                    score += 1
            else:
                score += 1 if name == "band2" else 0
            if score < need:
                continue

            # ── the stop, three ways ─────────────────────────────────────────
            raw = (min(inval, c[i] - A * min_risk) - A * sl_buf) if is_buy else \
                  (max(inval, c[i] + A * min_risk) + A * sl_buf)
            raw_dist = (c[i] - raw) if is_buy else (raw - c[i])
            clamped = raw_dist > A * max_risk

            if stop_mode == "clamp":
                sl = max(raw, c[i] - A * max_risk) if is_buy else min(raw, c[i] + A * max_risk)
            elif stop_mode == "reject":
                if clamped:
                    rejected_wide += 1
                    continue
                sl = raw
            elif stop_mode in ("structure", "hybrid"):
                pad = A * struct_pad
                sl = (raw - pad) if is_buy else (raw + pad)
            else:
                raise ValueError(stop_mode)

            risk = (c[i] - sl) if is_buy else (sl - c[i])
            if risk < A * min_risk * 0.5:
                continue

            # how far INSIDE the invalidation does this stop sit?
            # positive = the stop is on the wrong side of the level
            intrusion = ((sl - inval) if is_buy else (inval - sl)) / A

            d = 1.0 if is_buy else -1.0
            tps = []
            # HYBRID: the stop is placed by STRUCTURE but the targets are placed
            # by VOLATILITY, at the same ATR distances the clamped build produced
            # (0.8 / 1.4 / 2.0 ATR). That keeps the targets where they were in
            # PRICE, so the trade resolves as fast as before, while the stop
            # finally sits beyond the level. The cost is R:R — the same target is
            # a smaller multiple of a larger stop.
            unit = (A if stop_mode == "hybrid" else risk)
            for s_, rmul in enumerate(tp_r):
                t = c[i] + d * unit * rmul
                if s_ == 0:
                    near = [x for x in (u1[i] if is_buy else l1[i], vw[i],
                                        POC[i] if POC[i] else None)
                            if x is not None and (x > c[i]) == is_buy
                            and abs(x - c[i]) < abs(t - c[i]) and abs(x - c[i]) >= risk * 0.6]
                    if near:
                        t = min(near, key=lambda x: abs(x - c[i]))
                tps.append(t)

            pnl, got, dur, how = resolve(bars, i, is_buy, c[i], sl, tps, tstop)

            # ── PREMATURE STOP TEST. Walk the same window the trade was open
            # for and ask: was the structural invalidation ever breached on a
            # CLOSE before the stop was touched? If not, the trade was closed
            # while its own thesis was still intact.
            premature = False
            if how == "sl":
                breached = False
                for k in range(i + 1, min(i + 1 + dur, len(bars))):
                    if (c[k] < inval) if is_buy else (c[k] > inval):
                        breached = True
                        break
                premature = not breached

            trades.append(dict(i=i, side="B" if is_buy else "S", how=how, dur=dur,
                               r=risk / A, clamped=clamped, intrusion=intrusion,
                               raw_r=raw_dist / A, premature=premature, trig=name))
            last = i
            break
    return dict(trades=trades, rejected_wide=rejected_wide)


def pct(n, d):
    return 100.0 * n / d if d else 0.0


def report(tf_min, mode, res, days, struct_pad=0.0):
    t = res["trades"]
    n = len(t)
    if n == 0:
        print(f"  {mode:<10} no trades")
        return
    sl = [x for x in t if x["how"] == "sl"]
    prem = [x for x in sl if x["premature"]]
    cl = [x for x in t if x["clamped"]]
    intr = sorted(x["intrusion"] for x in cl)
    med_int = intr[len(intr) // 2] if intr else 0.0
    med_r = sorted(x["r"] for x in t)[n // 2]
    med_d = sorted(x["dur"] for x in t)[n // 2]
    label = mode if not struct_pad else f"{mode}+{struct_pad:g}"
    print(f"  {label:<14}{n / days:>7.2f}{pct(len(cl), n):>9.0f}%{med_int:>9.2f}"
          f"{med_r:>7.2f}{med_d:>6}{pct(len(sl), n):>7.0f}%{pct(len([x for x in t if x['how'] == 'be']), n):>6.0f}%"
          f"{pct(len([x for x in t if x['how'] == 'tp3']), n):>6.0f}%"
          f"{pct(len([x for x in t if x['how'] == 'time']), n):>7.0f}%{pct(len(prem), len(sl)):>11.0f}%")


DAYS = 150
SEEDS = (1, 2, 3, 4, 5, 6)

print("ME SCALP v2.1 — IS THE STOP TOO TIGHT?")
print("One price path per seed, resampled to each timeframe. Standard freq,")
print("ER>=0.32, aligned. Mean R deliberately absent (see module docstring).\n")

for tf_min in (5, 15, 30):
    agg = {}
    for seed in SEEDS:
        m1 = series_regime(60 * 24 * DAYS, 60, seed=seed)
        bars = []
        for j in range(0, len(m1) - tf_min + 1, tf_min):
            w = m1[j:j + tf_min]
            bars.append((w[0][0], w[0][1], max(b[2] for b in w), min(b[3] for b in w),
                         w[-1][4], sum(b[5] for b in w)))
        for mode, pad in (("clamp", 0.0), ("reject", 0.0),
                          ("structure", 0.0), ("structure", 0.25),
                          ("hybrid", 0.0), ("hybrid", 0.25)):
            key = (mode, pad)
            r = run_diag(bars, stop_mode=mode, struct_pad=pad)
            agg.setdefault(key, {"trades": [], "rej": 0})
            agg[key]["trades"] += r["trades"]
            agg[key]["rej"] += r["rejected_wide"]

    print(f"{tf_min}m")
    print(f"  {'mode':<14}{'trd/day':>7}{'clamped':>10}{'intrude':>9}"
          f"{'med R':>7}{'bars':>6}{'SL':>7}{'BE':>6}{'TP3':>6}{'time':>7}{'PREMATURE':>11}")
    for (mode, pad), d in agg.items():
        report(tf_min, mode, {"trades": d["trades"]}, DAYS * len(SEEDS), pad)
    print()
