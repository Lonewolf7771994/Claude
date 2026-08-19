import sys; sys.path.insert(0,'.')
from v4 import run_v4
from gen import series
DAYS=150; SEEDS=[11,23,37,51,67,83]
tfs={"15m":900,"30m":1800,"1H":3600}
for tf,s in tfs.items():
    for mode in ("Balanced","Strict"):
        B={}; nt=0; ns=0
        for sd in SEEDS:
            n=int(DAYS*24*3600/s); b=series(n,s,seed=sd)
            r=run_v4(b,s,mode=mode)
            nt+=r["triggers"]; ns+=r["signals"]
            for k,v in r["blocks"].items(): B[k]=B.get(k,0)+v
        tot=sum(B.values())
        print("\n%s %s  trig=%d sig=%d (%.2f/day)"%(tf,mode,nt,ns,ns/(DAYS*len(SEEDS))))
        # single-cause attribution: how often does each reason appear at all
        single={}
        for k,v in B.items():
            for r_ in k.split(): single[r_]=single.get(r_,0)+v
        for r_,v in sorted(single.items(),key=lambda x:-x[1]):
            print("   %-8s %6d  %5.1f%% of blocks"%(r_,v,100*v/max(tot,1)))
        # sole cause
        sole={k:v for k,v in B.items() if " " not in k}
        print("   -- sole cause --")
        for k,v in sorted(sole.items(),key=lambda x:-x[1])[:6]:
            print("   %-8s %6d"%(k,v))
