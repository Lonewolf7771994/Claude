"""IV WALLS, tested the way the method is actually described.

ivwalls.py faded the wall blind, on the tag, targeting the session open, and
had to close inside the session. That is the worst version of the idea and it
lost: SL 72% at every band. Condemning a method on its worst form is not a
test, so this runs the form the description actually specifies — "trading
REVERSALS at calculated price boundaries", which means:

  ENTRY        not the tag. The tag plus a CLOSE BACK INSIDE the wall, which
               is what makes it a reversal rather than a limit order into a
               moving market.
  STOP         beyond the excursion's extreme, not a fixed distance past the
               wall — the extreme is what has to break to prove the reversal
               wrong.
  TARGETS      reachable ones. 1R, then the next wall in, then the mid.
  WINDOW       runs past the session close, because a real trade does.

It also tests the two wall constructions separately, because they are not the
same instrument:

  STATIC       computed once at the session open from the full session, fixed
               all day. The classic expected-move level.
  DECAYED      scaled by sqrt(time remaining), so the walls contract through
               the session. Standard option-math treatment, and it puts the
               boundary much nearer price late in the day.

Same standing limit as before: synthetic data, outcome MIX only, no
expectancy computed or quoted.
"""
import math
from gen import series_regime
from engine import wilder_atr
from ivwalls import build, sessions, daily_sigma, BARS_PER_DAY, pct

DAYS, SEEDS = 200, (1, 2, 3, 4)
KS = (1.0, 1.5, 2.0)
MAXHOLD = 60          # bars, allowed to run past the session close
CONFIRM = 4           # bars after the tag in which the close-back must happen


def run(bars, decay):
    sess = sessions(bars)
    h = [b[2] for b in bars]; l = [b[3] for b in bars]; c = [b[4] for b in bars]
    atr = wilder_atr(h, l, c, 14)
    out = {k: [] for k in KS}
    for si, (s, e) in enumerate(sess):
        sig = daily_sigma(bars, sess, si)
        if sig is None:
            continue
        S0 = bars[s][1]
        for k in KS:
            fired = {True: False, False: False}
            for i in range(s, e):
                A = atr[i]
                if A is None or math.isnan(A):
                    continue
                # wall at this bar
                if decay:
                    left = max((e - i) / BARS_PER_DAY, 1e-6)
                    em = S0 * sig * k * math.sqrt(left)
                else:
                    em = S0 * sig * k
                up, dn = S0 + em, S0 - em
                for is_up in (True, False):
                    if fired[is_up]:
                        continue
                    wall = up if is_up else dn
                    tagged = h[i] >= wall if is_up else l[i] <= wall
                    if not tagged:
                        continue
                    # REVERSAL CONFIRMATION: a close back inside within CONFIRM
                    ent = None
                    for j in range(i, min(i + CONFIRM + 1, len(bars))):
                        if (c[j] < wall) if is_up else (c[j] > wall):
                            ent = j
                            break
                    if ent is None:
                        continue
                    fired[is_up] = True
                    extreme = max(h[i:ent + 1]) if is_up else min(l[i:ent + 1])
                    entry = c[ent]
                    stop = extreme + A * 0.20 if is_up else extreme - A * 0.20
                    risk = abs(stop - entry)
                    if risk <= 0 or risk > A * 4.0:
                        continue
                    d = -1.0 if is_up else 1.0
                    t1 = entry + d * risk * 1.0
                    inner = (S0 + (wall - S0) * (KS[0] / k)) if k > KS[0] else S0
                    t2 = inner
                    t3 = S0
                    if (t2 - entry) * d <= 0:
                        t2 = entry + d * risk * 2.0
                    got = [False, False, False]
                    hitsl = False
                    dur = MAXHOLD
                    for j in range(ent + 1, min(ent + 1 + MAXHOLD, len(bars))):
                        if (h[j] >= stop) if is_up else (l[j] <= stop):
                            hitsl = True; dur = j - ent; break
                        for ti, tp in enumerate((t1, t2, t3)):
                            if got[ti]:
                                continue
                            if (l[j] <= tp) if is_up else (h[j] >= tp):
                                got[ti] = True
                        if all(got):
                            dur = j - ent; break
                    out[k].append(dict(sl=hitsl, got=got, dur=dur,
                                       rr3=abs(t3 - entry) / max(risk, 1e-9)))
    return out


if __name__ == "__main__":
    for decay in (False, True):
        tot = {k: [] for k in KS}
        for seed in SEEDS:
            r = run(build(seed), decay)
            for k in KS:
                tot[k] += r[k]
        days = DAYS * len(SEEDS)
        print("\n%s WALLS — reversal entry (tag + close back inside within %d bars)"
              % ("DECAYED" if decay else "STATIC", CONFIRM))
        print("  %-6s%9s%9s%8s%8s%8s%8s%9s" %
              ("k", "trades", "per day", "1R", "wall-in", "mid", "SL", "bars"))
        for k in KS:
            d = tot[k]
            n = len(d)
            if not n:
                print("  %-6.1f  none" % k)
                continue
            du = sorted(x["dur"] for x in d)[n // 2]
            print("  %-6.1f%9d%9.2f%7.0f%%%7.0f%%%7.0f%%%7.0f%%%9d" % (
                k, n, n / days,
                pct(sum(1 for x in d if x["got"][0]), n),
                pct(sum(1 for x in d if x["got"][1]), n),
                pct(sum(1 for x in d if x["got"][2]), n),
                pct(sum(1 for x in d if x["sl"]), n), du))
    print("\n  '1R' is the first target at one times risk; 'wall-in' the next")
    print("  wall toward the middle; 'mid' the session open. Stop sits just")
    print("  beyond the excursion extreme, so risk is what the reversal itself")
    print("  defines. Outcome mix only — NO EXPECTANCY COMPUTED OR QUOTED.")
