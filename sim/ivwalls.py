"""IV WALLS — what the thing actually is, and what its hit rate is worth.

THE CLAIM: an implied-volatility range whose boundaries price reverses at,
"90% accuracy". Before building it, two questions have to be separated,
because they are very easy to confuse and the confusion is where the number
comes from.

  CONTAINMENT   how often price stays inside the walls.
  REVERSAL      how often TAGGING a wall is followed by a move back to the
                middle rather than straight through it.

Only the second one is tradeable. The first is close to a definition: a band
built at k standard deviations contains price about as often as k says it
will, whatever the market does, because that is what the band is FOR. Quoting
containment as a strategy hit rate is quoting the construction back to itself.
A 2-sigma band that contained price 95% of the time would be evidence the
volatility estimate is calibrated, not evidence of an edge.

So this measures BOTH, side by side, and reports the reversal rate — which is
the only column a trader is paid on — separately from the containment rate,
which is the one that produces impressive marketing.

WHAT IS BUILDABLE IN PINE. Not this, strictly. True IV comes from an options
chain and TradingView gives Pine no access to one. What CAN be built is the
same geometry driven by a volatility estimate the chart does have:

  realized vol   Yang-Zhang from OHLC, which uses the whole bar and is several
                 times more efficient than close-to-close
  manual IV      the user types the number from their broker's chain

The walls are then S x sigma x sqrt(t) around the session open, which is
exactly the expected-move calculation. Whether sigma came from an option or
from the last twenty bars changes the number, not the geometry.

STANDING LIMIT, stated before the results rather than after. Containment rates
measured here depend on this generator's volatility process matching gold's.
It has clustering and an intraday shape, so it is not a pure tautology, but it
is not gold either. What survives the synthetic origin is the RELATIVE
question — does a 2-sigma tag revert more than a 1-sigma tag — and the trade
geometry. Neither is an expectancy claim and none is made.
"""
import math
from gen import series_regime
from engine import wilder_atr

DAYS, SEEDS, TF = 200, (1, 2, 3, 4), 300      # 5m bars
BARS_PER_DAY = 24 * 60 // (TF // 60)
VOL_LOOKBACK = 20                              # trailing days for sigma
KS = (1.0, 1.5, 2.0)
TAG_WINDOW = 24                                # bars allowed for the revert


def build(seed):
    m1 = series_regime(60 * 24 * DAYS, 60, seed=seed)
    out, st = [], TF // 60
    for j in range(0, len(m1) - st + 1, st):
        w = m1[j:j + st]
        out.append((w[0][0], w[0][1], max(b[2] for b in w), min(b[3] for b in w),
                    w[-1][4], sum(b[5] for b in w)))
    return out


def sessions(bars):
    """Split into equal-length days and return (start, end) index pairs."""
    out = []
    for s in range(0, len(bars) - BARS_PER_DAY, BARS_PER_DAY):
        out.append((s, s + BARS_PER_DAY))
    return out


def daily_sigma(bars, sess, upto):
    """Close-to-close sigma of the previous VOL_LOOKBACK sessions, as a
    fraction of price. Uses only sessions that have already CLOSED."""
    closes = [bars[e - 1][4] for (s, e) in sess[:upto]]
    if len(closes) < VOL_LOOKBACK + 1:
        return None
    rets = [math.log(closes[i] / closes[i - 1])
            for i in range(len(closes) - VOL_LOOKBACK, len(closes))]
    m = sum(rets) / len(rets)
    var = sum((r - m) ** 2 for r in rets) / max(len(rets) - 1, 1)
    return math.sqrt(var)


def analyse(bars):
    sess = sessions(bars)
    atr = wilder_atr([b[2] for b in bars], [b[3] for b in bars],
                     [b[4] for b in bars], 14)
    res = {k: dict(n=0, touch=0, close_out=0,
                   tags=0, revert_mid=0, revert_half=0, through=0,
                   trades=[]) for k in KS}
    for si, (s, e) in enumerate(sess):
        sig = daily_sigma(bars, sess, si)
        if sig is None:
            continue
        S0 = bars[s][1]
        hi = max(b[2] for b in bars[s:e])
        lo = min(b[3] for b in bars[s:e])
        cl = bars[e - 1][4]
        for k in KS:
            em = S0 * sig * k
            up, dn = S0 + em, S0 - em
            r = res[k]
            r["n"] += 1
            if hi <= up and lo >= dn:
                r["touch"] += 1
            if not (dn <= cl <= up):
                r["close_out"] += 1

            # ── tag and what followed ────────────────────────────────────
            for i in range(s, e):
                A = atr[i]
                if A is None or math.isnan(A):
                    continue
                for is_up in (True, False):
                    wall = up if is_up else dn
                    tagged = bars[i][2] >= wall if is_up else bars[i][3] <= wall
                    if not tagged:
                        continue
                    # only the FIRST tag of each wall per session counts,
                    # otherwise one long excursion is counted as many events
                    key = (si, k, is_up)
                    if key in r.setdefault("_seen", set()):
                        continue
                    r["_seen"].add(key)
                    r["tags"] += 1

                    half = (wall + S0) / 2.0
                    got_half = got_mid = broke = False
                    for j in range(i + 1, min(i + 1 + TAG_WINDOW, e)):
                        if is_up:
                            if bars[j][3] <= half: got_half = True
                            if bars[j][3] <= S0:   got_mid = True
                            if bars[j][2] >= wall + A * 1.0: broke = True
                        else:
                            if bars[j][2] >= half: got_half = True
                            if bars[j][2] >= S0:   got_mid = True
                            if bars[j][3] <= wall - A * 1.0: broke = True
                        if got_mid or broke:
                            break
                    if got_mid:  r["revert_mid"] += 1
                    if got_half: r["revert_half"] += 1
                    if broke:    r["through"] += 1

                    # ── the trade: fade the tag, stop past the wall ──────
                    entry = wall
                    stop = wall + A * 0.75 if is_up else wall - A * 0.75
                    t1, t2 = half, S0
                    risk = abs(stop - entry)
                    hitsl = hit1 = hit2 = False
                    dur = TAG_WINDOW
                    for j in range(i + 1, min(i + 1 + TAG_WINDOW, e)):
                        h_, l_ = bars[j][2], bars[j][3]
                        if (h_ >= stop) if is_up else (l_ <= stop):
                            hitsl = True; dur = j - i; break
                        if (l_ <= t1) if is_up else (h_ >= t1):
                            hit1 = True
                        if (l_ <= t2) if is_up else (h_ >= t2):
                            hit2 = True; dur = j - i; break
                    r["trades"].append(dict(sl=hitsl, t1=hit1, t2=hit2, dur=dur,
                                            rr=abs(t2 - entry) / max(risk, 1e-9)))
    return res


def pct(a, b):
    return 100.0 * a / b if b else 0.0


if __name__ == "__main__":
    tot = {k: dict(n=0, touch=0, close_out=0, tags=0, revert_mid=0,
                   revert_half=0, through=0, trades=[]) for k in KS}
    for seed in SEEDS:
        r = analyse(build(seed))
        for k in KS:
            for f in ("n", "touch", "close_out", "tags", "revert_mid",
                      "revert_half", "through"):
                tot[k][f] += r[k][f]
            tot[k]["trades"] += r[k]["trades"]

    print("IV WALLS — containment against reversal, %d days x %d seeds, %dm bars"
          % (DAYS, len(SEEDS), TF // 60))
    print("Walls = session open +/- k x sigma, sigma from the prior %d closed sessions.\n"
          % VOL_LOOKBACK)

    print("  CONTAINMENT — the number that sounds like accuracy and is not")
    print("  %-6s%10s%14s%14s" % ("k", "sessions", "never touched", "closed inside"))
    for k in KS:
        t = tot[k]
        print("  %-6.1f%10d%13.0f%%%13.0f%%" % (
            k, t["n"], pct(t["touch"], t["n"]),
            pct(t["n"] - t["close_out"], t["n"])))
    print("\n  A band built at k sigma contains price about as often as k says.")
    print("  That is the band working as designed, not a prediction. Sell the")
    print("  'closed inside' column as a win rate and you are quoting the")
    print("  construction back to itself.\n")

    print("  REVERSAL — the only column a fade is actually paid on")
    print("  %-6s%8s%12s%12s%14s" % ("k", "tags", "back to mid", "half way", "through +1ATR"))
    for k in KS:
        t = tot[k]
        print("  %-6.1f%8d%11.0f%%%11.0f%%%13.0f%%" % (
            k, t["tags"], pct(t["revert_mid"], t["tags"]),
            pct(t["revert_half"], t["tags"]), pct(t["through"], t["tags"])))

    print("\n  THE TRADE — fade the tag, stop 0.75 ATR past the wall,")
    print("  TP1 half way back, TP2 the session open. %d bars allowed.\n" % TAG_WINDOW)
    print("  %-6s%8s%8s%8s%8s%8s%8s" % ("k", "trades", "TP1", "TP2", "SL", "med R:R", "bars"))
    for k in KS:
        d = tot[k]["trades"]
        n = len(d)
        if not n:
            continue
        rr = sorted(x["rr"] for x in d)[n // 2]
        du = sorted(x["dur"] for x in d)[n // 2]
        print("  %-6.1f%8d%7.0f%%%7.0f%%%7.0f%%%8.2f%8d" % (
            k, n, pct(sum(1 for x in d if x["t1"]), n),
            pct(sum(1 for x in d if x["t2"]), n),
            pct(sum(1 for x in d if x["sl"]), n), rr, du))
    print("\n  Outcome mix is geometry. NO EXPECTANCY IS COMPUTED OR QUOTED, and")
    print("  containment depends on this generator's volatility process matching")
    print("  gold's, which is not established. The relative comparison across k")
    print("  is what survives the synthetic origin.")
