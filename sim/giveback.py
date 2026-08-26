"""STOPPED OUT ON A TRADE THAT SHOULD HAVE PAID — which of the two causes is it?

The report is three live losses that "were supposed to be profitable". Three
trades is not a sample and nothing here treats it as one. But "the stop was hit
and then the move happened" is a MECHANISM, and a mechanism can be measured
even when the anecdote cannot.

There are exactly two ways it happens and they need opposite fixes:

  GIVE-BACK   the trade went in your favour, did not reach TP1, came back and
              took the full stop. ME Pro arms breakeven ONLY after TP1 trades
              (v3.5.5), so everything short of TP1 is still a whole loss no
              matter how far it ran. Fix: arm breakeven on excursion, not on
              TP1.

  PREMATURE   the stop was hit on noise, and the original target traded
              afterwards. Fix: a wider stop — which costs hold time, as
              measured in ME Scalp v2.2.

They are distinguishable. For every stopped-out trade this records the maximum
favourable excursion BEFORE the stop, and then keeps walking AFTER the stop to
see whether the original TP1 and TP2 traded anyway.

Then it prices three candidate fixes against the current build.

Outcome mix and counts only. No expectancy computed or quoted.
"""
import math
from fullstack import build, prep, MODES
import fullstack
from pace import evaluate

SEEDS = (1, 2, 3)
TF = 300
AFTER = 40          # bars to keep watching once the stop is taken
MAXHOLD = 80
CFG = dict(body=0.25, vol=0.70, of=53.0, delta=0.08, cool=2,
           minr=0.4, minrr=0.50, dir=0)          # v5.0 Rapid


def walk(bars, ent, is_buy, entry, sl, tps, be_mode, be_at):
    """be_mode: 'tp1' (current build) or 'mfe' (arm at be_at x risk).
    Returns dict with the outcome and the diagnostic fields."""
    h = [b[2] for b in bars]; l = [b[3] for b in bars]
    R = abs(entry - sl)
    stop = sl
    got = [False] * 3
    mfe = 0.0
    at_be = False
    how, dur = "open", MAXHOLD
    end = min(ent + 1 + MAXHOLD, len(bars))
    for j in range(ent + 1, end):
        fav = (h[j] - entry) if is_buy else (entry - l[j])
        mfe = max(mfe, fav / max(R, 1e-9))
        # stop first: a bar that spans both is never scored a win
        if (l[j] <= stop) if is_buy else (h[j] >= stop):
            how = "be" if at_be else "sl"
            dur = j - ent
            break
        for ti, tp in enumerate(tps):
            if got[ti]:
                continue
            if (h[j] >= tp) if is_buy else (l[j] <= tp):
                got[ti] = True
        if got[0] and not at_be:
            if be_mode == "tp1":
                stop = entry; at_be = True
        if be_mode == "mfe" and not at_be and mfe >= be_at:
            stop = entry; at_be = True
        if all(got):
            how = "tp3"
            dur = j - ent
            break
    else:
        how = "time"
    # keep watching past the exit: did the original targets trade anyway?
    late1 = late2 = False
    if how in ("sl", "be"):
        for j in range(ent + 1 + dur, min(ent + 1 + dur + AFTER, len(bars))):
            if (h[j] >= tps[0]) if is_buy else (l[j] <= tps[0]):
                late1 = True
            if (h[j] >= tps[1]) if is_buy else (l[j] <= tps[1]):
                late2 = True
    return dict(how=how, got=got, dur=dur, mfe=mfe, late1=late1, late2=late2)


def collect(be_mode, be_at):
    rows = []
    fullstack.TF = TF
    for seed in SEEDS:
        bars = build(seed, TF)
        D = prep(bars)
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
                    rows.append(walk(bars, i, is_buy, D["c"][i], sl, tps,
                                     be_mode, be_at))
                    last = i
                    break
    return rows


def pct(a, b):
    return 100.0 * a / b if b else 0.0


if __name__ == "__main__":
    base = collect("tp1", 99.0)
    n = len(base)
    sl = [x for x in base if x["how"] == "sl"]

    print("WHY THE STOPPED-OUT TRADES STOP OUT — 5m, v5.0 Rapid, all four modes")
    print("%d trades, %d of them full stop-outs (%.0f%%)\n" % (n, len(sl), pct(len(sl), n)))

    print("  HOW FAR DID A FULL LOSS RUN IN YOUR FAVOUR FIRST?")
    print("  (maximum favourable excursion before the stop, in R)\n")
    for lo, hi in ((0.0, 0.25), (0.25, 0.5), (0.5, 0.75), (0.75, 1.0), (1.0, 99.0)):
        c = [x for x in sl if lo <= x["mfe"] < hi]
        band = "%.2f - %.2f R" % (lo, hi) if hi < 99 else "1.00 R and up"
        print("    %-16s %6d   %5.1f%% of stop-outs" % (band, len(c), pct(len(c), len(sl))))
    gb = [x for x in sl if x["mfe"] >= 0.5]
    print("\n    GIVE-BACK: %.0f%% of full stop-outs had already run 0.5R or more" % pct(len(gb), len(sl)))
    print("    in your favour. Breakeven never armed because TP1 never traded.")

    print("\n  DID THE TARGET TRADE ANYWAY, AFTER THE STOP? (%d bars watched)\n" % AFTER)
    print("    TP1 reached after the stop   %6d   %5.1f%%" % (
        sum(1 for x in sl if x["late1"]), pct(sum(1 for x in sl if x["late1"]), len(sl))))
    print("    TP2 reached after the stop   %6d   %5.1f%%" % (
        sum(1 for x in sl if x["late2"]), pct(sum(1 for x in sl if x["late2"]), len(sl))))
    print("\n    That is the PREMATURE share — stopped out of a trade whose")
    print("    target the market then went and paid.")

    print("\n\n  THREE FIXES, PRICED\n")
    print("  %-28s%8s%8s%8s%8s%8s%7s" % ("build", "TP1", "TP2", "TP3", "BE", "SL", "bars"))
    trials = [("current (BE after TP1)", "tp1", 99.0),
              ("BE at 0.50R excursion", "mfe", 0.50),
              ("BE at 0.70R excursion", "mfe", 0.70),
              ("BE at 0.85R excursion", "mfe", 0.85)]
    for name, mode, at in trials:
        d = base if mode == "tp1" else collect(mode, at)
        m = len(d)
        du = sorted(x["dur"] for x in d)[m // 2]
        print("  %-28s%7.0f%%%7.0f%%%7.0f%%%7.0f%%%7.0f%%%7d" % (
            name,
            pct(sum(1 for x in d if x["got"][0]), m),
            pct(sum(1 for x in d if x["got"][1]), m),
            pct(sum(1 for x in d if x["got"][2]), m),
            pct(sum(1 for x in d if x["how"] == "be"), m),
            pct(sum(1 for x in d if x["how"] == "sl"), m), du))
    print("\n  BE = the trade came back and closed at entry instead of at the")
    print("  stop. Those are the losses the fix converts into scratches. Watch")
    print("  the TP columns for what it costs: an early breakeven also stops")
    print("  trades that would have resolved higher.")
    print("\n  Outcome mix only. NO EXPECTANCY COMPUTED OR QUOTED.")
