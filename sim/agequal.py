"""WEAK ENTRIES: is the problem WHEN the entry is taken?

Every measurement I have run in this project entered on the TRIGGER BAR ITSELF.
The indicator does not. i_triggerAge defaults to 3, so a trigger stays valid for
three more bars and the entry can be taken on any of them — at a price that has
drifted away from the level while the stop stays anchored to it.

That means every table I have produced UNDERSTATES the real engine. This file
closes that gap.

The project already argued about this twice and never settled it:

  v3.5.30 clamped Scalp freshness 3 -> 2, on a simulation showing an entry at
          age 3 passes chase/risk/rr less often (70.9% at age 1, 55.7% at age 3).
  v3.5.31 REVERTED it, because that simulation measured the wrong thing — trade
          COUNT depends on whether a trigger converts ANYWHERE in its window,
          and each extra bar is another attempt (64.6% -> 86.6% across ages 1-3).

Both are right about their own quantity and neither measured OUTCOME. That is
what this does: it runs the full v5.2 conjunction with a real freshness window,
records the AGE at which each entry was actually taken, and reports the outcome
mix separately for each age.

If late entries are as good as same-bar ones, the window is free and the
complaint is about something else. If they are worse, the window is where the
weak entries come from and it costs nothing to shrink it.

Counts and outcome geometry only. No expectancy computed or quoted.
"""
import math
import fullstack
from fullstack import build, prep, MODES
from pace import evaluate
from giveback import pct

SEEDS, TF, MAXHOLD = (1, 2, 3), 300, 80
MAXAGE = 3
CFG = dict(body=0.25, vol=0.70, of=53.0, delta=0.08, cool=2,
           minr=0.4, minrr=0.50, dir=0, pad=0.8)


def aged(D, maxage):
    """Re-emit each trigger for `maxage` extra bars, carrying its ORIGINAL level
    and invalidation — which is exactly what the Pine freshness window does. The
    entry price is the later bar's close; the stop is still anchored to the
    level from the trigger bar."""
    n = D["n"]
    out = [{"buy": [], "sell": [], "age": {}} for _ in range(n)]
    for side in ("buy", "sell"):
        carry = None
        age = 999
        for i in range(n):
            ev = D["T"][i][side]
            if ev:
                carry, age = ev, 0
            elif carry is not None:
                age += 1
            if carry is not None and age <= maxage:
                out[i][side] = carry
                out[i]["age"][side] = age
    return out


def run(maxage):
    rows = []
    fullstack.TF = TF
    for seed in SEEDS:
        bars = build(seed, TF)
        D = prep(bars)
        h = [b[2] for b in bars]; l = [b[3] for b in bars]; c = [b[4] for b in bars]
        T2 = aged(D, maxage)
        D2 = dict(D)
        D2["T"] = T2
        for mode in MODES:
            last = -10 ** 9
            for i in range(80, D["n"] - 90):
                A = D["atr"][i]
                if A is None or math.isnan(A) or math.isnan(D["vavg"][i]):
                    continue
                for is_buy in (True, False):
                    ok, sl, tps = evaluate(D2, i, is_buy, mode, last, CFG)
                    if not ok:
                        continue
                    side = "buy" if is_buy else "sell"
                    age = T2[i]["age"].get(side, 0)
                    inval = T2[i][side][0][2]
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
                    rows.append(dict(age=age, how=how, got=got, dur=dur,
                                     prem=(how == "sl" and not breached),
                                     r=abs(c[i] - sl) / A))
                    last = i
                    break
    return rows


def row(label, d, days):
    n = len(d)
    if not n:
        print("  %-16s  none" % label)
        return
    sl = [x for x in d if x["how"] == "sl"]
    print("  %-16s%8d%9.2f%7.2f%7.0f%%%7.0f%%%7.0f%%%7.0f%%%7.0f%%%6d%9.0f%%" % (
        label, n, n / days, sorted(x["r"] for x in d)[n // 2],
        pct(sum(1 for x in d if x["got"][0]), n),
        pct(sum(1 for x in d if x["got"][1]), n),
        pct(sum(1 for x in d if x["got"][2]), n),
        pct(sum(1 for x in d if x["how"] == "be"), n),
        pct(len(sl), n),
        sorted(x["dur"] for x in d)[n // 2],
        pct(sum(1 for x in sl if x["prem"]), max(len(sl), 1))))


if __name__ == "__main__":
    days = 120 * len(SEEDS)
    print("ENTRY AGE AND ENTRY QUALITY — 5m, v5.2 Rapid, all four modes\n")
    print("Every previous table in this project entered on the trigger bar.")
    print("The indicator allows %d bars of freshness. This measures the difference.\n" % MAXAGE)
    print("  %-16s%8s%9s%7s%7s%7s%7s%7s%7s%6s%10s" %
          ("", "trades", "per day", "med R", "TP1", "TP2", "TP3", "BE", "SL", "bars", "PREMATURE"))

    full = run(MAXAGE)
    row("window 0-3 (now)", full, days)
    print()
    for a in range(MAXAGE + 1):
        row("  taken at age %d" % a, [x for x in full if x["age"] == a], days)

    print("\n  Now the same engine with the window SHRUNK — not a re-slice of the")
    print("  rows above, a separate run, because a shorter window changes which")
    print("  bar each trigger converts on.\n")
    for m in (0, 1, 2, 3):
        row("window 0-%d" % m, run(m), days)

    print("\n  PREMATURE = stop-outs where the setup's own invalidation was never")
    print("  closed through. A late entry keeps the stop anchored to a level it")
    print("  has already walked away from, so this column is where drift shows up.")
    print("\n  Counts and outcome geometry only. NO EXPECTANCY COMPUTED OR QUOTED.")
