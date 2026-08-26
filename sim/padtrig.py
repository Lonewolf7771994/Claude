"""ONE STOP PAD CANNOT SERVE SIX TRIGGERS.

trigqual.py showed the premature-stop rate varies enormously BY TRIGGER at the
single global pad of 0.8 ATR:

    mss 49%   fvg 43%   sweep 42%   value 31%   band2 26%   band 24%

That spread is not noise, it is the anchor. A band rejection is stopped beyond
the REJECTING BAR'S OWN EXTREME — a dated, single-bar level, tight and precise.
An MSS is stopped beyond the LAST PIVOT, which is a looser object several bars
old and much easier for ordinary noise to violate. Padding both by the same
0.8 ATR over-pads the precise anchor and under-pads the loose one.

So the pad is swept PER TRIGGER. If the optimum differs by trigger, a single
global setting is leaving quality on the table for every trigger except the one
it happens to suit.

Counts and outcome geometry only. No expectancy computed or quoted.
"""
import math
import fullstack
from fullstack import build, prep, MODES
from pace import evaluate
from giveback import pct

SEEDS, TF, MAXHOLD = (1, 2), 300, 80
KINDS = ("mss", "fvg", "sweep", "band", "band2", "value")
PADS = (0.4, 0.8, 1.2, 1.6)
BASE = dict(body=0.25, vol=0.70, of=53.0, delta=0.08, cool=2, minr=0.4, minrr=0.50, dir=0)

def run(only, pad):
    cfg = dict(BASE); cfg["pad"] = pad
    out = []
    fullstack.TF = TF
    for seed in SEEDS:
        bars = build(seed, TF); D = prep(bars)
        h=[b[2] for b in bars]; l=[b[3] for b in bars]; c=[b[4] for b in bars]
        T2=[]
        for ev in D["T"]:
            T2.append({"buy":[e for e in ev["buy"] if e[0] in only],
                       "sell":[e for e in ev["sell"] if e[0] in only]})
        D2 = dict(D); D2["T"] = T2
        for mode in MODES:
            last=-10**9
            for i in range(80, D["n"]-90):
                A=D["atr"][i]
                if A is None or math.isnan(A) or math.isnan(D["vavg"][i]): continue
                for is_buy in (True,False):
                    ok,sl,tps = evaluate(D2,i,is_buy,mode,last,cfg)
                    if not ok: continue
                    inval = T2[i]["buy" if is_buy else "sell"][0][2]
                    stop=sl; got=[False]*3; at_be=False
                    how,dur,br="time",MAXHOLD,False
                    for j in range(i+1, min(i+1+MAXHOLD,len(bars))):
                        if (c[j]<inval) if is_buy else (c[j]>inval): br=True
                        if (l[j]<=stop) if is_buy else (h[j]>=stop):
                            how="be" if at_be else "sl"; dur=j-i; break
                        for ti,tp in enumerate(tps):
                            if got[ti]: continue
                            if (h[j]>=tp) if is_buy else (l[j]<=tp): got[ti]=True
                        if got[0] and not at_be: stop=c[i]; at_be=True
                        if all(got): how="tp3"; dur=j-i; break
                    out.append(dict(how=how,got=got,dur=dur,prem=(how=="sl" and not br)))
                    last=i; break
    return out

print("STOP PAD PER TRIGGER — 5m, v5.2 Rapid, all modes, %d seeds\n" % len(SEEDS))
print("  %-8s%6s%8s%7s%7s%7s%7s%7s%6s%10s" % ("trigger","pad","trades","TP1","TP2","TP3","BE","SL","bars","PREMATURE"))
best = {}
for k in KINDS:
    for pad in PADS:
        d = run({k}, pad); n=len(d)
        if not n: continue
        sl=[x for x in d if x["how"]=="sl"]
        prem = pct(sum(1 for x in sl if x["prem"]), max(len(sl),1))
        slr  = pct(len(sl), n)
        print("  %-8s%6.1f%8d%6.0f%%%6.0f%%%6.0f%%%6.0f%%%6.0f%%%6d%9.0f%%" % (
            k, pad, n,
            pct(sum(1 for x in d if x["got"][0]),n),
            pct(sum(1 for x in d if x["got"][1]),n),
            pct(sum(1 for x in d if x["got"][2]),n),
            pct(sum(1 for x in d if x["how"]=="be"),n),
            slr, sorted(x["dur"] for x in d)[n//2], prem))
        if k not in best or slr < best[k][1]:
            best[k] = (pad, slr, prem, n)
    print()
print("  LOWEST STOP-OUT RATE PER TRIGGER")
for k in KINDS:
    if k in best:
        print("    %-8s pad %.1f   SL %.0f%%   premature %.0f%%   n=%d" % (k, *best[k]))
print("\n  Counts and outcome geometry only. NO EXPECTANCY COMPUTED OR QUOTED.")
