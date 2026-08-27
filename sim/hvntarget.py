"""A THICK NODE IS WHERE A MOVE ENDS. Use it as the target, not the entry.

vpshape.py measured HVN REJECTION as an entry: 67% of the shape set's supply
and the weakest follow-through in it (TP2 32%, TP3 15%). That is the same shape
as every other fade event measured in this project.

But a high-volume node is not a bad reading — it is a badly USED one. Both sides
accepted that price, so it absorbs. That makes it the place a move stops, which
is a statement about where to TAKE PROFIT, not where to enter.

So: same LVN entries, same stop, and TP2 placed at the nearest thick node beyond
entry instead of at a fixed 1.4 ATR. If the node really is where moves end, the
node-placed target should be reached MORE often than the fixed one.
"""
import math
import fullstack
from fullstack import build, prep, MODES
from giveback import pct
from vpshape import profile, nodes, of_score, shape_triggers, SEEDS, TF, MAXHOLD, PAD, MINR, CAP, PENDBARS, OFNEED

def run(hvn_target):
    out=[]; fullstack.TF=TF
    for seed in SEEDS:
        bars=build(seed,TF); D=prep(bars); PR=profile(bars)
        h=[b[2] for b in bars]; l=[b[3] for b in bars]; c=[b[4] for b in bars]; n=D["n"]
        T=shape_triggers(D,PR)
        for mode in MODES:
            last=-10**9
            for i in range(80,n-90):
                A=D["atr"][i]
                if A is None or math.isnan(A) or math.isnan(D["vavg"][i]): continue
                for is_buy in (True,False):
                    ev=[e for e in T[i]["buy" if is_buy else "sell"] if e[0].startswith("lvn")]
                    if not ev: continue
                    if (c[i]>D["o"][i])!=is_buy or i-last<2: continue
                    sc=of_score(D,i,is_buy)
                    if sc is None or sc<OFNEED: continue
                    if (D["pdir"][i]==1)!=is_buy: continue
                    name,ref,inval=ev[0]
                    if is_buy: sl=min(inval-A*PAD, ref-A*MINR); risk=ref-sl
                    else:      sl=max(inval+A*PAD, ref+A*MINR); risk=sl-ref
                    if risk<=0 or risk>A*CAP: continue
                    d=1.0 if is_buy else -1.0
                    tps=[ref+d*A*m for m in (0.8,1.4,2.2)]
                    if hvn_target and PR[i]:
                        _,hvn=nodes(PR[i])
                        cands=[(lo_+hi_)/2 for lo_,hi_ in hvn if ((lo_+hi_)/2 - ref)*d > 0]
                        if cands:
                            nearest=min(cands,key=lambda x:abs(x-ref))
                            if abs(nearest-ref) >= abs(tps[0]-ref)*1.1:
                                tps[1]=nearest
                                tps[2]=max(tps[2],nearest+d*A*0.8) if is_buy else min(tps[2],nearest+d*A*0.8)
                    fill=None
                    for j in range(i+1,min(i+1+PENDBARS,n)):
                        if (l[j]<=ref) if is_buy else (h[j]>=ref): fill=j; break
                    if fill is None: last=i; break
                    if (l[fill]<=sl) if is_buy else (h[fill]>=sl):
                        out.append(dict(how="sl",got=[False]*3,dur=0)); last=i; break
                    stop,got,at_be=sl,[False]*3,False; how,dur="time",MAXHOLD
                    for j in range(fill+1,min(fill+1+MAXHOLD,n)):
                        if (l[j]<=stop) if is_buy else (h[j]>=stop):
                            how="be" if at_be else "sl"; dur=j-fill; break
                        for ti,tp in enumerate(tps):
                            if got[ti]: continue
                            if (h[j]>=tp) if is_buy else (l[j]<=tp): got[ti]=True
                        if got[0] and not at_be: stop=ref; at_be=True
                        if all(got): how="tp3"; dur=j-fill; break
                    out.append(dict(how=how,got=got,dur=dur)); last=i; break
    return out

days=120*len(SEEDS)
print("THICK NODE AS TARGET — LVN entries only, 5m, all modes\n")
print("  %-26s%8s%9s%7s%7s%7s%7s%6s" % ("","trades","per day","TP1","TP2","TP3","SL","bars"))
for lab,ht in (("TP2 fixed 1.4 ATR",False),("TP2 at nearest HVN",True)):
    d=run(ht); n=len(d)
    print("  %-26s%8d%9.2f%6.0f%%%6.0f%%%6.0f%%%6.0f%%%6d" % (
        lab,n,n/days,
        pct(sum(1 for x in d if x["got"][0]),n),
        pct(sum(1 for x in d if x["got"][1]),n),
        pct(sum(1 for x in d if x["got"][2]),n),
        pct(sum(1 for x in d if x["how"]=="sl"),n),
        sorted(x["dur"] for x in d)[n//2]))
print("\n  Counts and outcome geometry only. NO EXPECTANCY COMPUTED OR QUOTED.")
