"""ENTRIES BUILT FROM THE VOLUME PROFILE AND ORDER FLOW, not from pivots.

v4.1's four triggers are all PRICE-STRUCTURE events: a pivot broke, a gap was
retested, a wick speared a level, price left a standard-deviation band. The
volume profile has been computed since v3.4 and used only as a filter and a
target source. Order flow has been computed since v3.3 and used only as a gate.
Neither has ever STARTED a trade.

This builds the trigger set the other way round.

THE FRVP EVENTS. Each is a dated, single-bar event with its own invalidation,
which is what the stop needs:

  VAL RECLAIM    price trades below the value area and closes back inside.
                 Invalidation: the excursion low. Long.
  VAH REJECT     mirror. Short.
  POC RECLAIM    price crosses the point of control and closes through it,
                 having been the other side on the previous bar. The POC is
                 where the most volume traded — the fairest price in the window
                 — so crossing it is a change in what the market accepts.
  VA BREAKOUT    close beyond VAH (or VAL) with participation. Acceptance
                 OUTSIDE value, which is the continuation case rather than the
                 reversion one.
  VA MIGRATION   both edges of the value area have moved the same way over the
                 last stride. Value itself is relocating.

THE ORDER-FLOW SCORE, and the reason it is percentile-ranked rather than fixed.
Every order-flow threshold in v4.1 is an absolute number — 60% close position,
0.20 delta, 1.2x relative volume. An absolute threshold means something
different in every volatility regime and on every symbol, so it is really a
hidden regime filter. Ranking each reading against its own recent history makes
it self-calibrating: "this bar's conviction is in the top quartile of the last
200" means the same thing everywhere.

  delta rank      |close-open|/range, ranked
  volume rank     relative volume, ranked
  location        close in the top/bottom quartile of its own bar
  CVD agreement   cumulative delta sloping the trade's way

REPORTED against v4.1's own trigger set on the identical stack, stop rule and
ladder, so the only thing that differs is what starts the trade.

Counts and outcome geometry only. No expectancy computed or quoted.
"""
import math
import fullstack
from fullstack import build, prep, MODES
from giveback import pct
from ladder_diag import ladder

SEEDS, TF, MAXHOLD = (1, 2), 300, 80
RANKLEN = 200
STRIDE = 10
PAD, MINR, CAP = 1.2, 0.4, 3.0
RMUL = (0.8, 1.4, 2.2)
PENDBARS = 8


def rank(series, i, n=RANKLEN):
    """Percentile of series[i] within the trailing window. Self-calibrating."""
    lo = max(0, i - n + 1)
    win = [x for x in series[lo:i + 1] if x is not None and not math.isnan(x)]
    if len(win) < 20:
        return None
    v = series[i]
    if v is None or math.isnan(v):
        return None
    return sum(1 for x in win if x <= v) / len(win)


def frvp_triggers(D, bars):
    """Every entry event derived from the profile. Returns per-bar buy/sell
    lists of (name, level, invalidation) — the same shape v4.1's triggers use,
    so the stop is built the same way."""
    n = D["n"]
    o, h, l, c = D["o"], D["h"], D["l"], D["c"]
    POC, VAH, VAL = D["POC"], D["VAH"], D["VAL"]
    out = [{"buy": [], "sell": []} for _ in range(n)]
    for i in range(1, n):
        poc, vah, val = POC[i], VAH[i], VAL[i]
        if poc is None or vah is None or val is None:
            continue
        rng = max(h[i] - l[i], 1e-9)
        cp = (c[i] - l[i]) / rng

        # 1 value-area edge reclaim / rejection
        if l[i] <= val and c[i] > val and cp >= 0.55:
            out[i]["buy"].append(("val_reclaim", val, l[i]))
        if h[i] >= vah and c[i] < vah and cp <= 0.45:
            out[i]["sell"].append(("vah_reject", vah, h[i]))

        # 2 POC cross with follow-through — the fair price has moved
        if c[i - 1] < poc and c[i] > poc and cp >= 0.55:
            out[i]["buy"].append(("poc_reclaim", poc, min(l[i], l[i - 1])))
        if c[i - 1] > poc and c[i] < poc and cp <= 0.45:
            out[i]["sell"].append(("poc_reject", poc, max(h[i], h[i - 1])))

        # 3 acceptance OUTSIDE value — the continuation case
        if c[i - 1] <= vah and c[i] > vah and cp >= 0.6:
            out[i]["buy"].append(("va_break", vah, val if val < c[i] else l[i]))
        if c[i - 1] >= val and c[i] < val and cp <= 0.4:
            out[i]["sell"].append(("va_break", val, vah if vah > c[i] else h[i]))

        # 4 value itself relocating
        j = i - STRIDE
        if j >= 0 and VAH[j] is not None and VAL[j] is not None:
            if vah > VAH[j] and val > VAL[j] and c[i] > poc and cp >= 0.55:
                out[i]["buy"].append(("va_migrate", poc, val))
            if vah < VAH[j] and val < VAL[j] and c[i] < poc and cp <= 0.45:
                out[i]["sell"].append(("va_migrate", poc, vah))
    return out


def of_score(D, i, is_buy, dser, vser):
    """0-4, every component percentile-ranked against its own recent history."""
    dr = rank(dser, i)
    vr = rank(vser, i)
    if dr is None or vr is None:
        return None
    rng = max(D["h"][i] - D["l"][i], 1e-9)
    cp = (D["c"][i] - D["l"][i]) / rng
    loc = cp if is_buy else 1.0 - cp
    delta = (D["c"][i] - D["o"][i]) / rng
    cvdOk = (D["cf"][i] > D["cs"][i]) == is_buy
    return ((1 if dr >= 0.5 else 0)
            + (1 if vr >= 0.5 else 0)
            + (1 if loc >= 0.70 else 0)
            + (1 if cvdOk else 0)
            + (1 if (delta > 0) == is_buy else 0))


def run(source, need, level=True):
    """source: 'frvp' or 'v41'. need: order-flow score floor."""
    out = []
    armed = filled = 0
    fullstack.TF = TF
    for seed in SEEDS:
        bars = build(seed, TF)
        D = prep(bars)
        h = [b[2] for b in bars]; l = [b[3] for b in bars]; c = [b[4] for b in bars]
        n = D["n"]
        dser = [abs(D["c"][k] - D["o"][k]) / max(D["h"][k] - D["l"][k], 1e-9) for k in range(n)]
        vser = [D["v"][k] / max(D["vavg"][k], 1e-9) if not math.isnan(D["vavg"][k]) else float("nan")
                for k in range(n)]
        T = frvp_triggers(D, bars) if source == "frvp" else D["T"]
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
                    if (c[i] > D["o"][i]) != is_buy:
                        continue
                    if i - last < 2:
                        continue
                    sc = of_score(D, i, is_buy, dser, vser)
                    if sc is None or sc < need:
                        continue
                    # the no-reversal trail, unchanged
                    if (D["pdir"][i] == 1) != is_buy:
                        continue
                    name, ref, inval = ev[0]
                    if is_buy:
                        sl = min(inval - A * PAD, ref - A * MINR)
                        risk = ref - sl
                    else:
                        sl = max(inval + A * PAD, ref + A * MINR)
                        risk = sl - ref
                    if risk <= 0 or risk > A * CAP:
                        continue
                    d = 1.0 if is_buy else -1.0
                    tps = [ref + d * A * m for m in RMUL]
                    # level-retest entry, as v4.1.3 ships
                    armed += 1
                    fill = None
                    for j in range(i + 1, min(i + 1 + PENDBARS, n)):
                        if (l[j] <= ref) if is_buy else (h[j] >= ref):
                            fill = j
                            break
                    if fill is None:
                        last = i
                        break
                    filled += 1
                    if (l[fill] <= sl) if is_buy else (h[fill] >= sl):
                        out.append(dict(name=name, how="sl", got=[False]*3, dur=0,
                                        prem=not ((c[fill] < inval) if is_buy else (c[fill] > inval))))
                        last = i
                        break
                    stop = sl
                    got = [False] * 3
                    at_be = False
                    how, dur, br = "time", MAXHOLD, False
                    for j in range(fill + 1, min(fill + 1 + MAXHOLD, n)):
                        if (c[j] < inval) if is_buy else (c[j] > inval):
                            br = True
                        if (l[j] <= stop) if is_buy else (h[j] >= stop):
                            how = "be" if at_be else "sl"
                            dur = j - fill
                            break
                        for ti, tp in enumerate(tps):
                            if got[ti]:
                                continue
                            if (h[j] >= tp) if is_buy else (l[j] <= tp):
                                got[ti] = True
                        if got[0] and not at_be:
                            stop = ref
                            at_be = True
                        if all(got):
                            how = "tp3"
                            dur = j - fill
                            break
                    out.append(dict(name=name, how=how, got=got, dur=dur,
                                    prem=(how == "sl" and not br)))
                    last = i
                    break
    return out, armed, filled


def row(label, d, days, extra=""):
    n = len(d)
    if not n:
        print("  %-24s none" % label)
        return
    sl = [x for x in d if x["how"] == "sl"]
    print("  %-24s%8d%9.2f%7.0f%%%7.0f%%%7.0f%%%7.0f%%%6d%10.0f%%%s" % (
        label, n, n / days,
        pct(sum(1 for x in d if x["got"][0]), n),
        pct(sum(1 for x in d if x["got"][1]), n),
        pct(sum(1 for x in d if x["got"][2]), n),
        pct(len(sl), n),
        sorted(x["dur"] for x in d)[n // 2],
        pct(sum(1 for x in sl if x["prem"]), max(len(sl), 1)), extra))


if __name__ == "__main__":
    days = 120 * len(SEEDS)
    print("FRVP + ORDER-FLOW ENTRIES vs v4.1's STRUCTURE ENTRIES")
    print("5m, all four modes, %d seeds. Same stop rule, same ladder, same" % len(SEEDS))
    print("level-retest fill, same no-reversal trail. Only the trigger differs.\n")
    print("  %-24s%8s%9s%7s%7s%7s%7s%6s%11s" %
          ("", "trades", "per day", "TP1", "TP2", "TP3", "SL", "bars", "PREMATURE"))
    for need in (2, 3, 4):
        d, a, f = run("v41", need)
        row("v4.1 structure, OF>=%d" % need, d, days, "  fill %.0f%%" % pct(f, a))
    print()
    best = None
    for need in (2, 3, 4):
        d, a, f = run("frvp", need)
        row("FRVP+OF, OF>=%d" % need, d, days, "  fill %.0f%%" % pct(f, a))
        if need == 3:
            best = d
    if best:
        print("\n  FRVP ENTRIES BY TYPE (order-flow score >= 3)\n")
        for nm in ("val_reclaim", "vah_reject", "poc_reclaim", "poc_reject",
                   "va_break", "va_migrate"):
            row("  " + nm, [x for x in best if x["name"] == nm], days)
    print("\n  Counts and outcome geometry only. NO EXPECTANCY COMPUTED OR QUOTED.")
