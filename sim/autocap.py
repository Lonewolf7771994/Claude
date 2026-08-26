"""AUTO-COUPLING THE RISK CAP TO THE PAD.

v4.1.1 widened the loose-anchor pad 0.8 -> 1.2 and trade count fell 6.81 -> 3.98
per day. That drop is NOT the pad being selective: it is the Max Risk Cap, a
separate hand-typed number, rejecting the setups whose stop the wider pad just
pushed past it. Two settings that have to be moved together are two chances to
get it wrong, and I told the user to move the second one by hand.

So: derive it. cap = base + pad, so widening the pad never silently filters.

Scored on PREMATURE stops (the manufactured losses) at MATCHED trade count,
because a pad that "wins" by declining hard setups is not winning.
"""
import math
import fullstack
from fullstack import build, prep, MODES
from pace import evaluate
from giveback import pct

SEEDS, TF, MAXHOLD = (1, 2), 300, 80

def run(pad, cap):
    out=[]; fullstack.TF=TF
    cfg = dict(body=0.25, vol=0.70, of=53.0, delta=0.08, cool=2,
               minr=0.4, minrr=0.50, dir=0, pad=pad, cap=cap)
    for seed in SEEDS:
        bars=build(seed,TF); D=prep(bars)
        h=[b[2] for b in bars]; l=[b[3] for b in bars]; c=[b[4] for b in bars]
        for mode in MODES:
            last=-10**9
            for i in range(80, D["n"]-90):
                A=D["atr"][i]
                if A is None or math.isnan(A) or math.isnan(D["vavg"][i]): continue
                for is_buy in (True,False):
                    ok,sl,tps = evaluate(D,i,is_buy,mode,last,cfg)
                    if not ok: continue
                    inval=D["T"][i]["buy" if is_buy else "sell"][0][2]
                    stop=sl; got=[False]*3; at_be=False
                    how,dur,br="time",MAXHOLD,False
                    for j in range(i+1,min(i+1+MAXHOLD,len(bars))):
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

days=120*len(SEEDS)
print("RISK CAP COUPLED TO THE PAD — 5m, all modes, %d seeds\n" % len(SEEDS))
print("  %-26s%8s%9s%7s%7s%7s%7s%6s%11s" % ("","trades","per day","TP1","TP2","TP3","SL","bars","PREMATURE"))
for label,pad,cap in (("pad 0.8  cap 3.0 (v4.1)",0.8,3.0),
                      ("pad 1.2  cap 3.0 (v4.1.1)",1.2,3.0),
                      ("pad 1.2  cap 3.4 (auto)",1.2,3.4),
                      ("pad 1.2  cap 3.8 (auto)",1.2,3.8),
                      ("pad 1.2  cap 4.2 (auto)",1.2,4.2)):
    d=run(pad,cap); n=len(d); sl=[x for x in d if x["how"]=="sl"]
    print("  %-26s%8d%9.2f%6.0f%%%6.0f%%%6.0f%%%6.0f%%%6d%10.0f%%" % (
        label,n,n/days,
        pct(sum(1 for x in d if x["got"][0]),n),
        pct(sum(1 for x in d if x["got"][1]),n),
        pct(sum(1 for x in d if x["got"][2]),n),
        pct(len(sl),n), sorted(x["dur"] for x in d)[n//2],
        pct(sum(1 for x in sl if x["prem"]),max(len(sl),1))))
print("\n  Counts and outcome geometry only. NO EXPECTANCY COMPUTED OR QUOTED.")
