"""SLOW ENTRIES: how far past the level does the entry actually land, and does
entering AT the level instead fix it?

Three rounds of fixes and the same three complaints. So this measures the one I
have never measured, and tests the one lever v4.1 already contains and ships
switched off.

WHAT "SLOW" MEANS ECONOMICALLY. Not wall-clock lag — distance. Every trigger
fires at a LEVEL (the broken pivot, the swept low, the gap edge, the rejected
band) and then the engine buys the CLOSE of a confirming bar, which is somewhere
else by then. The anti-chase cap allows that gap to be up to 1.0 ATR. An entry
1 ATR past its own level is a worse price with the same stop, so it is late in
the only sense that costs money.

  Reported: the distribution of entry-minus-level in ATR, and what happens to
  the outcome mix when the cap is tightened.

THE LEVER: LEVEL-RETEST MODE (i_entryMode). Instead of buying the close, arm an
order AT the trigger's own level and fill only if price comes back. v4.1's
header rejects it on this reasoning:

    market entry   median TP1 reward 1.62R
    level  entry   median TP1 reward 2.10R   (+30% per filled trade)
    at an ASSUMED 62% fill rate:  market 1.617  level 1.301  -> negative

That assumed fill rate was never measured. It is the whole argument, and it is
a guess. Measured here, along with what the filled trades actually do.

Counts and outcome geometry only. No expectancy computed or quoted.
"""
import math
import fullstack
from fullstack import build, prep, MODES
from pace import evaluate
from giveback import pct

SEEDS, TF, MAXHOLD = (1, 2), 300, 80
PENDBARS = 8
CFG = dict(body=0.25, vol=0.70, of=53.0, delta=0.08, cool=2,
           minr=0.4, minrr=0.50, dir=0, pad=1.2, cap=3.0)


def walk(bars, start, is_buy, entry, sl, tps, inval):
    h = [b[2] for b in bars]; l = [b[3] for b in bars]; c = [b[4] for b in bars]
    stop = sl
    got = [False] * 3
    at_be = False
    how, dur, br = "time", MAXHOLD, False
    for j in range(start + 1, min(start + 1 + MAXHOLD, len(bars))):
        if (c[j] < inval) if is_buy else (c[j] > inval):
            br = True
        if (l[j] <= stop) if is_buy else (h[j] >= stop):
            how = "be" if at_be else "sl"
            dur = j - start
            break
        for ti, tp in enumerate(tps):
            if got[ti]:
                continue
            if (h[j] >= tp) if is_buy else (l[j] <= tp):
                got[ti] = True
        if got[0] and not at_be:
            stop = entry
            at_be = True
        if all(got):
            how = "tp3"
            dur = j - start
            break
    return dict(how=how, got=got, dur=dur, prem=(how == "sl" and not br))


def run(mode_name, chase=1.0, level=False):
    """mode_name only labels the row. chase = anti-chase cap in ATR.
    level=True arms at the trigger's own level instead of buying the close."""
    out = []
    armed = filled = 0
    fullstack.TF = TF
    for seed in SEEDS:
        bars = build(seed, TF)
        D = prep(bars)
        h = [b[2] for b in bars]; l = [b[3] for b in bars]; c = [b[4] for b in bars]
        for mode in MODES:
            last = -10 ** 9
            for i in range(80, D["n"] - 90):
                A = D["atr"][i]
                if A is None or math.isnan(A) or math.isnan(D["vavg"][i]):
                    continue
                for is_buy in (True, False):
                    ev = D["T"][i]["buy" if is_buy else "sell"]
                    if not ev:
                        continue
                    ref = ev[0][1]
                    lateness = ((c[i] - ref) if is_buy else (ref - c[i])) / A
                    if lateness > chase:
                        continue
                    ok, sl, tps = evaluate(D, i, is_buy, mode, last, CFG)
                    if not ok:
                        continue
                    inval = ev[0][2]
                    if not level:
                        out.append(dict(late=lateness,
                                        **walk(bars, i, is_buy, c[i], sl, tps, inval)))
                        last = i
                        break
                    # LEVEL RETEST: arm at ref, fill only if price returns
                    armed += 1
                    fill = None
                    for j in range(i + 1, min(i + 1 + PENDBARS, len(bars))):
                        if (l[j] <= ref) if is_buy else (h[j] >= ref):
                            fill = j
                            break
                    if fill is None:
                        last = i
                        break
                    filled += 1
                    # the plan is re-priced from the LEVEL, which is the point
                    if is_buy:
                        sl2 = min(inval - A * CFG["pad"], ref - A * CFG["minr"])
                        risk2 = ref - sl2
                    else:
                        sl2 = max(inval + A * CFG["pad"], ref + A * CFG["minr"])
                        risk2 = sl2 - ref
                    if risk2 <= 0 or risk2 > A * CFG["cap"]:
                        last = i
                        break
                    d = 1.0 if is_buy else -1.0
                    tps2 = [ref + d * A * m for m in (0.8, 1.4, 2.2)]
                    # THE FILL BAR ITSELF CAN RUN THROUGH THE STOP. Walking from
                    # fill+1 silently skips that and flatters every level entry.
                    # A bar that reaches the level and keeps going is exactly the
                    # case this mode is most exposed to, so it is scored here.
                    if (l[fill] <= sl2) if is_buy else (h[fill] >= sl2):
                        out.append(dict(late=0.0, how="sl", got=[False]*3, dur=0,
                                        prem=not ((c[fill] < inval) if is_buy else (c[fill] > inval))))
                        last = i
                        break
                    out.append(dict(late=0.0,
                                    **walk(bars, fill, is_buy, ref, sl2, tps2, inval)))
                    last = i
                    break
    return out, armed, filled


def row(label, d, days, extra=""):
    n = len(d)
    if not n:
        print("  %-26s none" % label)
        return
    sl = [x for x in d if x["how"] == "sl"]
    lates = sorted(x["late"] for x in d)
    print("  %-26s%8d%9.2f%9.2f%7.0f%%%7.0f%%%7.0f%%%7.0f%%%6d%10.0f%%%s" % (
        label, n, n / days, lates[n // 2],
        pct(sum(1 for x in d if x["got"][0]), n),
        pct(sum(1 for x in d if x["got"][1]), n),
        pct(sum(1 for x in d if x["got"][2]), n),
        pct(len(sl), n),
        sorted(x["dur"] for x in d)[n // 2],
        pct(sum(1 for x in sl if x["prem"]), max(len(sl), 1)), extra))


if __name__ == "__main__":
    days = 120 * len(SEEDS)
    print("HOW LATE IS THE ENTRY, AND DOES ENTERING AT THE LEVEL FIX IT?")
    print("5m, all four modes, %d seeds, pad 1.2\n" % len(SEEDS))
    print("  %-26s%8s%9s%9s%7s%7s%7s%7s%6s%11s" %
          ("", "trades", "per day", "med late", "TP1", "TP2", "TP3", "SL", "bars", "PREMATURE"))

    base, _, _ = run("m", chase=1.0)
    row("market, chase 1.0 (v4.1)", base, days)
    for ch in (0.75, 0.5, 0.25):
        d, _, _ = run("m", chase=ch)
        row("market, chase %.2f" % ch, d, days)

    print()
    lv, armed, filled = run("l", chase=1.0, level=True)
    row("LEVEL RETEST", lv, days, "   fill %.0f%% (%d/%d)" % (pct(filled, armed), filled, armed))

    print("\n  med late = entry price minus the trigger's own level, in ATR. The")
    print("  level-retest row is 0.00 by construction — that is what it buys.")
    print("\n  Counts and outcome geometry only. NO EXPECTANCY COMPUTED OR QUOTED.")
