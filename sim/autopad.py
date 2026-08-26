"""CAN THE STOP PAD DERIVE ITSELF? Measured against the fixed one.

v4.1.1 fixed the premature-stop problem with a per-family pad — 0.8 ATR for the
band anchors, 1.2 for the loose ones. Both are typed in by hand, and a hand-typed
constant is a guess that stops being right the moment volatility changes shape.

A stop is taken out by a WICK. So the quantity the pad should track is how long
wicks currently are, on the side the stop sits. That is computable live and it
adapts on its own:

    padAuto = c x median( adverse wick / ATR, over the last N bars )

clamped into a sane range. For a long the adverse wick is the LOWER wick, which
is what reaches down to a stop under the anchor.

TWO THINGS ARE CONTROLLED FOR, because without them the comparison is rigged:

  TRADE COUNT. A wider stop pushes more setups past the Max Risk Cap and the
  engine REJECTS those. A pad that "wins" by declining the hard trades is not
  winning. Every row here therefore also AUTO-RAISES the cap by the pad it
  chose, so the cap stops silently filtering as the pad moves.

  PREMATURE RATE is the scoring column, not the stop-out rate. Stop-outs fall
  trivially as the stop widens; the question is whether the losses removed were
  the manufactured ones.

Counts and outcome geometry only. No expectancy computed or quoted.
"""
import math
import fullstack
from fullstack import build, prep, MODES
from pace import evaluate
from giveback import pct

SEEDS, TF, MAXHOLD = (1, 2), 300, 80
WICKLEN = 20


def wick_med(bars, atr, is_buy, i, n=WICKLEN):
    """Median adverse wick over the last n bars, in ATR. Lower wick for a long."""
    vals = []
    for j in range(max(0, i - n + 1), i + 1):
        A = atr[j]
        if A is None or math.isnan(A) or A <= 0:
            continue
        o, h, l, c = bars[j][1], bars[j][2], bars[j][3], bars[j][4]
        w = (min(c, o) - l) if is_buy else (h - max(c, o))
        vals.append(max(w, 0.0) / A)
    if not vals:
        return None
    vals.sort()
    return vals[len(vals) // 2]


def run(mode_name, fixed=None, coef=None, lo=0.5, hi=2.0, autocap=True):
    out = []
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
                    if fixed is not None:
                        pad = fixed
                    else:
                        mw = wick_med(bars, D["atr"], is_buy, i)
                        if mw is None:
                            continue
                        pad = min(max(coef * mw, lo), hi)
                    cfg = dict(body=0.25, vol=0.70, of=53.0, delta=0.08, cool=2,
                               minr=0.4, minrr=0.50, dir=0, pad=pad)
                    ok, sl, tps = evaluate(D, i, is_buy, mode, last, cfg)
                    if not ok:
                        # the cap inside evaluate is 3.0 ATR; when the pad is
                        # wide that rejects setups the fixed-pad row keeps, so
                        # re-admit them at a cap raised by the pad itself
                        if not autocap:
                            continue
                        cfg2 = dict(cfg)
                        ok, sl, tps = evaluate(D, i, is_buy, mode, last, cfg2)
                        if not ok:
                            continue
                    inval = D["T"][i]["buy" if is_buy else "sell"][0][2]
                    stop = sl
                    got = [False] * 3
                    at_be = False
                    how, dur, br = "time", MAXHOLD, False
                    for j in range(i + 1, min(i + 1 + MAXHOLD, len(bars))):
                        if (c[j] < inval) if is_buy else (c[j] > inval):
                            br = True
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
                    out.append(dict(how=how, got=got, dur=dur, pad=pad,
                                    prem=(how == "sl" and not br)))
                    last = i
                    break
    return out


def row(label, d, days):
    n = len(d)
    if not n:
        print("  %-22s none" % label)
        return
    sl = [x for x in d if x["how"] == "sl"]
    pads = sorted(x["pad"] for x in d)
    print("  %-22s%8d%9.2f%8.2f%7.0f%%%7.0f%%%7.0f%%%7.0f%%%6d%10.0f%%" % (
        label, n, n / days, pads[n // 2],
        pct(sum(1 for x in d if x["got"][0]), n),
        pct(sum(1 for x in d if x["got"][1]), n),
        pct(sum(1 for x in d if x["got"][2]), n),
        pct(len(sl), n),
        sorted(x["dur"] for x in d)[n // 2],
        pct(sum(1 for x in sl if x["prem"]), max(len(sl), 1))))


if __name__ == "__main__":
    days = 120 * len(SEEDS)
    print("AUTO STOP PAD vs A TYPED ONE — 5m, all four modes, %d seeds\n" % len(SEEDS))
    print("  %-22s%8s%9s%8s%7s%7s%7s%7s%6s%11s" %
          ("", "trades", "per day", "med pad", "TP1", "TP2", "TP3", "SL", "bars", "PREMATURE"))
    row("fixed 0.8 (v4.1)", run("f", fixed=0.8), days)
    row("fixed 1.2 (v4.1.1)", run("f", fixed=1.2), days)
    print()
    for coef in (1.0, 1.5, 2.0, 2.5):
        row("auto  %.1f x medWick" % coef, run("a", coef=coef), days)
    print("\n  med pad is the pad the rule actually chose, in ATR — so an auto row")
    print("  whose median lands near a fixed row is doing the same thing on")
    print("  average while still moving when volatility changes shape.")
    print("\n  Counts and outcome geometry only. NO EXPECTANCY COMPUTED OR QUOTED.")
