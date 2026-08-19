"""One lever at a time, then all together. Baseline is v3.5.21 Scalp/Selective."""
import sys, statistics; sys.path.insert(0,'.')
from engine import Cfg, run
from gen import series
DAYS=150; SEEDS=[11,23,37,51,67,83]
tfs={"5m":300,"15m":900,"30m":1800,"1H":3600}
D=DAYS*len(SEEDS)

BASE=dict(mode="Scalp", v21=True, max_tp1_r=0.0, min_blend_rr=0.0)
OFF=dict(loose=True, loose_vol=1.0, loose_body=0.30, loose_rr=(99.,0.9,0.7),
         loose_max_risk=2.0, loose_clamp_risk=False, loose_vwap_max=3.0)

LEVERS=[
 ("baseline v3.5.21",  {}),
 ("+rr floor 0.8",     dict(loose_rr=(0.8,0.7,0.6))),
 ("+risk clamp",       dict(loose_clamp_risk=True)),
 ("+max risk 2.5",     dict(loose_max_risk=2.5)),
 ("+vol 0.75",         dict(loose_vol=0.75)),
 ("+body 0.20",        dict(loose_body=0.20)),
 ("+vwap 4.0",         dict(loose_vwap_max=4.0)),
 ("ALL",               dict(loose_rr=(0.8,0.7,0.6), loose_clamp_risk=True,
                            loose_max_risk=2.5, loose_vol=0.75,
                            loose_body=0.20, loose_vwap_max=4.0)),
]

def measure(tf, s, over, freq="Selective"):
    kw=dict(BASE); kw["freq"]=freq
    if over is not None:
        kw.update(OFF); kw.update(over)
    S=0; pnl=[]
    for sd in SEEDS:
        n=int(DAYS*24*3600/s); b=series(n,s,seed=sd)
        r=run(b, Cfg(**kw), s)
        S+=r["signals"]; pnl+=[x["pnl"] for x in r["trades"]]
    if not pnl: return S/D, 0.0, 0.0, 0
    m=statistics.mean(pnl); w=100*sum(1 for p in pnl if p>0)/len(pnl)
    return S/D, w, m, len(pnl)

print("Scalp / Selective — signals per day (win%, mean R, n)\n")
print("%-18s %-22s %-22s %-22s %-22s"%("lever","5m","15m","30m","1H"))
for name,over in LEVERS:
    o = None if name=="baseline v3.5.21" else over
    row=[]
    for tf,s in tfs.items():
        sd_,w,m,n = measure(tf,s,o)
        row.append("%.2f/d %.0f%% %+.3fR"%(sd_,w,m))
    print("%-18s %-22s %-22s %-22s %-22s"%(name,*row))

print("\nAll levers on, every frequency:\n")
print("%-12s %-22s %-22s %-22s %-22s"%("freq","5m","15m","30m","1H"))
allo=LEVERS[-1][1]
for freq in ("Selective","Standard","High"):
    row=[]
    for tf,s in tfs.items():
        sd_,w,m,n = measure(tf,s,allo,freq)
        row.append("%.2f/d %.0f%% %+.3fR"%(sd_,w,m))
    print("%-12s %-22s %-22s %-22s %-22s"%(freq,*row))
