import sys, statistics; sys.path.insert(0,'.')
from v4 import run_v4
from gen import series
DAYS=150; SEEDS=[11,23,37,51,67,83]
tfs={"5m":300,"15m":900,"30m":1800,"1H":3600,"4H":14400}
D=DAYS*len(SEEDS)
print("%-5s %-10s %-9s %-8s %-9s %-8s %-7s"%("tf","mode","sig/day","win%","mean R","n","t"))
for tf,s in tfs.items():
    for mode in ("Scalp","Balanced","Strict"):
        S=0; pnl=[]; trig={}
        for sd in SEEDS:
            n=int(DAYS*24*3600/s); b=series(n,s,seed=sd)
            r=run_v4(b,s,mode=mode)
            S+=r["signals"]; pnl+=[x["pnl"] for x in r["trades"]]
            for t in r["trades"]: trig[t["trig"]]=trig.get(t["trig"],0)+1
        if not pnl:
            print("%-5s %-10s %-9.2f %-8s %-9s %-8s"%(tf,mode,0,"-","-",0)); continue
        m=statistics.mean(pnl); se=statistics.pstdev(pnl)/len(pnl)**.5
        w=100*sum(1 for p in pnl if p>0)/len(pnl)
        mix=" ".join("%s=%d%%"%(k,100*v//len(pnl)) for k,v in sorted(trig.items(),key=lambda x:-x[1]))
        print("%-5s %-10s %-9.2f %-8.1f %-9.4f %-8d %-7.2f  %s"%(tf,mode,S/D,w,m,len(pnl),m/se if se else 0,mix))
    print()
