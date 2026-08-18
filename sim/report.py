import sys, statistics; sys.path.insert(0,'.')
from engine import Cfg, run
from gen import series
DAYS=90; SEEDS=[11,23,37,51,67,83,97,113]
tfs={"5m":300,"15m":900,"30m":1800,"1H":3600,"4H":14400}
print("ME Pro harness — %d days x %d seeds, synthetic gold-like OHLCV\n"%(DAYS,len(SEEDS)))
print("%-5s %-11s %-10s %-10s %-9s %-9s %-9s"%("tf","preset","trig/day","sig/day","win%","mean R","t-stat"))
for tf,s in tfs.items():
    for f in ("Selective","Standard","High"):
        T=S=0; pnl=[]
        for sd in SEEDS:
            n=int(DAYS*24*3600/s); b=series(n,s,seed=sd)
            r=run(b, Cfg(mode="Scalp", freq=f), s)
            T+=r["triggers"]; S+=r["signals"]; pnl+=[x["pnl"] for x in r["trades"]]
        d=DAYS*len(SEEDS)
        if not pnl:
            print("%-5s %-11s %-10.1f %-10.2f %-9s %-9s %-9s"%(tf,f,T/d,S/d,"-","-","-")); continue
        m=statistics.mean(pnl); se=statistics.pstdev(pnl)/len(pnl)**.5
        w=100*sum(1 for p in pnl if p>0)/len(pnl)
        print("%-5s %-11s %-10.1f %-10.2f %-9.1f %-9.4f %-9.2f"%(tf,f,T/d,S/d,w,m,m/se if se else 0))
