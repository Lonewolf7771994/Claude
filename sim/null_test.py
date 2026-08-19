"""MANDATORY GUARD — run before believing ANY result from this harness.

If a brain-dead momentum rule is profitable on the test data, then the data
pays for trend following and every "edge" measured on it is circular. This has
already happened twice in this project:

    phi=0.82        naive rule profitable -> every engine looked profitable
    trend_k=0.55    naive rule +0.214R    -> ME Scalp "edge" of +0.29R was fake,
                                             and collapsed on real gold

A generator passes only when the naive rule's t-statistic is inside +/-2.
"""
import sys, statistics; sys.path.insert(0, '.')
from engine import wilder_atr


def naive(bars, er_len=20, hold=12, er_min=0.32):
    h = [b[2] for b in bars]; l = [b[3] for b in bars]; c = [b[4] for b in bars]
    atr = wilder_atr(h, l, c, 14); out = []; path = 0.0
    for i in range(1, len(bars)):
        path += abs(c[i]-c[i-1])
        if i <= er_len or i < 60: continue
        path -= abs(c[i-er_len]-c[i-er_len-1])
        if abs(c[i]-c[i-er_len]) / max(path, 1e-9) < er_min: continue
        A = atr[i]
        if A != A: continue
        up = c[i] > c[i-er_len]; e = c[i]
        sl = e-A if up else e+A
        tp = e+A if up else e-A
        for k in range(i+1, min(i+1+hold, len(bars))):
            if (l[k] <= sl) if up else (h[k] >= sl): out.append(-1.0); break
            if (h[k] >= tp) if up else (l[k] <= tp): out.append(+1.0); break
        else:
            j = min(len(bars)-1, i+hold)
            out.append(((c[j]-e) if up else (e-c[j])) / A)
    return out


def check(gen, label, seeds=(11, 23, 37, 51, 67, 83), days=150, **kw):
    ok = True
    for tf, s in (("5m", 300), ("15m", 900)):
        r = []
        for sd in seeds:
            r += naive(gen(int(days*24*3600/s), s, seed=sd, **kw))
        m = statistics.mean(r); se = statistics.pstdev(r)/len(r)**.5
        t = m/se
        verdict = "PASS" if abs(t) < 2 else ("FAIL - free trend edge" if t > 0
                                             else "fail - free reversion edge")
        if abs(t) >= 2: ok = False
        print("  %-22s %-5s meanR=%+.4f t=%+6.2f  %s" % (label, tf, m, t, verdict))
    return ok


if __name__ == "__main__":
    from gen import series, series_regime
    print("NULL TEST — a passing generator pays nothing for naive momentum\n")
    a = check(series, "driftless")
    b = check(series_regime, "regime (default)")
    print("\n%s" % ("ALL PASS" if (a and b) else
                    "SOME FAIL - results from failing generators are circular"))
