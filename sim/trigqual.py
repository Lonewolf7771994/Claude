"""WHICH ENTRY TYPES ARE THE FAKE ONES. Measured one at a time.

The report is that the ENTRIES are misleading. ME Pro ORs six trigger types
together:

    buyTrigger = mssUp or fvg or sweep or band or poc or CRT

and exposes no way to switch any of them off. If one of those is bad, it is
bad on every signal the engine produces and there is no setting that helps.

So each is run IN ISOLATION here — the engine with exactly one trigger type
enabled — which is precisely what a toggle would do, so the table predicts
what you would actually get rather than describing an attribution.

Reported per trigger:
    share      how much of the combined engine's supply it accounts for
    SL / BE / TP    outcome mix
    PREMATURE  stop-outs where the setup's own invalidation was never closed
               through. A trigger with a high premature rate is one whose
               invalidation level does not describe the trade — which is the
               precise technical meaning of a misleading entry.
    bars       median hold

The harness has mss, fvg, sweep, band, band2 and value. It does NOT have the
v4.3 POC reclaim or the v4.7 CRT, so those two are absent from the table and
nothing is claimed about them.

Counts and outcome geometry only. No expectancy computed or quoted.
"""
import math
import fullstack
from fullstack import build, prep, MODES
from pace import evaluate
from giveback import pct

SEEDS, TF, MAXHOLD = (1, 2, 3), 300, 80
KINDS = ("mss", "fvg", "sweep", "band", "band2", "value")
CFG = dict(body=0.25, vol=0.70, of=53.0, delta=0.08, cool=2,
           minr=0.4, minrr=0.50, dir=0, pad=0.8)      # v5.1 Rapid


def run(only):
    """only = a set of trigger kinds to keep, or None for the combined engine."""
    out = []
    fullstack.TF = TF
    for seed in SEEDS:
        bars = build(seed, TF)
        D = prep(bars)
        h = [b[2] for b in bars]; l = [b[3] for b in bars]; c = [b[4] for b in bars]
        # filter the trigger store down to the kinds under test
        if only is not None:
            T2 = []
            for ev in D["T"]:
                T2.append({"buy":  [e for e in ev["buy"] if e[0] in only],
                           "sell": [e for e in ev["sell"] if e[0] in only]})
            D = dict(D)
            D["T"] = T2
        for mode in MODES:
            last = -10 ** 9
            for i in range(80, D["n"] - 90):
                A = D["atr"][i]
                if A is None or math.isnan(A) or math.isnan(D["vavg"][i]):
                    continue
                for is_buy in (True, False):
                    ok, sl, tps = evaluate(D, i, is_buy, mode, last, CFG)
                    if not ok:
                        continue
                    inval = D["T"][i]["buy" if is_buy else "sell"][0][2]
                    stop = sl
                    got = [False] * 3
                    at_be = False
                    how, dur, breached = "time", MAXHOLD, False
                    for j in range(i + 1, min(i + 1 + MAXHOLD, len(bars))):
                        if (c[j] < inval) if is_buy else (c[j] > inval):
                            breached = True
                        if (l[j] <= stop) if is_buy else (h[j] >= stop):
                            how = "be" if at_be else "sl"
                            dur = j - i
                            break
                        for ti, tp in enumerate(tps):
                            if got[ti]:
                                continue
                            if (h[j] >= tp) if is_buy else (l[j] <= tp):
                                got[ti] = True
                        if got[0] and not at_be:
                            stop = c[i]
                            at_be = True
                        if all(got):
                            how = "tp3"
                            dur = j - i
                            break
                    out.append(dict(how=how, got=got, dur=dur,
                                    prem=(how == "sl" and not breached)))
                    last = i
                    break
    return out


def row(label, d, total):
    n = len(d)
    if not n:
        print("  %-9s  no trades" % label)
        return
    sl = [x for x in d if x["how"] == "sl"]
    print("  %-9s%8d%8.0f%%%7.0f%%%7.0f%%%7.0f%%%7.0f%%%7.0f%%%7d%10.0f%%" % (
        label, n, pct(n, total),
        pct(sum(1 for x in d if x["got"][0]), n),
        pct(sum(1 for x in d if x["got"][1]), n),
        pct(sum(1 for x in d if x["got"][2]), n),
        pct(sum(1 for x in d if x["how"] == "be"), n),
        pct(len(sl), n),
        sorted(x["dur"] for x in d)[n // 2],
        pct(sum(1 for x in sl if x["prem"]), len(sl))))


if __name__ == "__main__":
    print("ENTRY TYPE QUALITY — each trigger run ALONE, 5m, v5.1 Rapid, all modes\n")
    combined = run(None)
    tot = len(combined)
    print("  %-9s%8s%9s%7s%7s%7s%7s%7s%7s%10s" %
          ("trigger", "trades", "share", "TP1", "TP2", "TP3", "BE", "SL", "bars", "PREMATURE"))
    row("ALL (now)", combined, tot)
    print()
    singles = {}
    for k in KINDS:
        singles[k] = run({k})
        row(k, singles[k], tot)

    good = [k for k in KINDS if singles[k] and
            pct(sum(1 for x in singles[k] if x["how"] == "sl"), len(singles[k]))
            <= pct(sum(1 for x in combined if x["how"] == "sl"), len(combined))]
    print("\n  Triggers at or below the combined engine's stop-out rate: %s"
          % (", ".join(good) if good else "none"))
    if good:
        d = run(set(good))
        print()
        row("KEEP", d, tot)
    print("\n  PREMATURE = share of that trigger's full stop-outs where its own")
    print("  invalidation was never closed through. High means the level the")
    print("  stop is built from does not describe the trade.")
    print("\n  Counts and outcome geometry only. NO EXPECTANCY COMPUTED OR QUOTED.")
