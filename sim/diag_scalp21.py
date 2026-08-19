"""What blocks Scalp in v3.5.21, measured — not guessed.

Cfg(v21=True, max_tp1_r=0, min_blend_rr=0) reproduces v3.5.21: no v3.5.29 risk
floor, no v3.5.35 TP1 ceiling, no v3.5.26 blended-RR pass. Everything else in
the port is unchanged from .21.
"""
import sys, statistics; sys.path.insert(0,'.')
from engine import Cfg, run
from gen import series
DAYS=150; SEEDS=[11,23,37,51,67,83]
tfs={"5m":300,"15m":900,"30m":1800,"1H":3600}
D=DAYS*len(SEEDS)

def cfg21(**kw):
    return Cfg(mode="Scalp", v21=True, max_tp1_r=0.0, min_blend_rr=0.0, **kw)

for tf,s in tfs.items():
    for freq in ("Selective","Standard","High"):
        B={}; T=S=0; pnl=[]
        for sd in SEEDS:
            n=int(DAYS*24*3600/s); b=series(n,s,seed=sd)
            r=run(b, cfg21(freq=freq), s)
            T+=r["triggers"]; S+=r["signals"]; pnl+=[x["pnl"] for x in r["trades"]]
            for k,v in r["blocks"].items(): B[k]=B.get(k,0)+v
        tot=sum(B.values())
        m=statistics.mean(pnl) if pnl else 0.0
        print("\n%s Scalp/%s  trig/day=%.1f  sig/day=%.2f  n=%d  meanR=%.4f"
              %(tf,freq,T/D,S/D,len(pnl),m))
        single={}
        for k,v in B.items():
            for r_ in k.split(): single[r_]=single.get(r_,0)+v
        print("   appears in:  " + "  ".join("%s %.0f%%"%(k,100*v/max(tot,1))
              for k,v in sorted(single.items(),key=lambda x:-x[1])[:8]))
        sole={k:v for k,v in B.items() if " " not in k}
        print("   SOLE cause:  " + "  ".join("%s %d"%(k,v)
              for k,v in sorted(sole.items(),key=lambda x:-x[1])[:8]))
