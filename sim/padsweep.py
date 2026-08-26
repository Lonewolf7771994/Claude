"""THE FIX FOR 'STOPPED OUT AND THEN IT WENT': widen the structural pad.

giveback.py found 83% of ME Pro's full stop-outs had their own TP1 trade
within 40 bars AFTER the stop. Breakeven-on-excursion did not fix it — at
0.50R it cut stop-outs 43%->32% but collapsed TP1 from 55% to 40%, because
arming that early also scratches the trades that were going to work.

That leaves stop WIDTH, which is the lever ME Scalp v2.2 found and which was
never applied to ME Pro. ME Pro's stop is already structural (it does not
clamp on the far side), but the pad beyond the invalidation is 0.5 ATR and
nothing ever tested whether that is enough.

PREMATURE is measured strictly here, not loosely: the stop was hit AND the
setup's own invalidation level was never CLOSED through beforehand. That is a
trade closed while its thesis was still intact, rather than merely a trade the
market later drifted back across.
"""
import math
from fullstack import build, prep, MODES
import fullstack
from pace import evaluate
from giveback import pct

SEEDS, TF, MAXHOLD, AFTER = (1, 2, 3), 300, 80, 40
PADS = (0.5, 0.8, 1.2, 1.6, 2.0)
BASE = dict(body=0.25, vol=0.70, of=53.0, delta=0.08, cool=2, minr=0.4, minrr=0.50, dir=0)

def run(pad):
    cfg = dict(BASE); cfg["pad"] = pad
    out = []
    fullstack.TF = TF
    for seed in SEEDS:
        bars = build(seed, TF); D = prep(bars)
        h=[b[2] for b in bars]; l=[b[3] for b in bars]; c=[b[4] for b in bars]
        for mode in MODES:
            last = -10**9
            for i in range(80, D["n"]-90):
                A = D["atr"][i]
                if A is None or math.isnan(A) or math.isnan(D["vavg"][i]): continue
                for is_buy in (True, False):
                    ok, sl, tps = evaluate(D, i, is_buy, mode, last, cfg)
                    if not ok: continue
                    inval = D["T"][i]["buy" if is_buy else "sell"][0][2]
                    R = abs(c[i]-sl); stop=sl; got=[False]*3
                    at_be=False; how="time"; dur=MAXHOLD; breached=False
                    for j in range(i+1, min(i+1+MAXHOLD, len(bars))):
                        if (c[j] < inval) if is_buy else (c[j] > inval): breached=True
                        if (l[j] <= stop) if is_buy else (h[j] >= stop):
                            how = "be" if at_be else "sl"; dur=j-i; break
                        for ti,tp in enumerate(tps):
                            if got[ti]: continue
                            if (h[j] >= tp) if is_buy else (l[j] <= tp): got[ti]=True
                        if got[0] and not at_be: stop=c[i]; at_be=True
                        if all(got): how="tp3"; dur=j-i; break
                    prem = (how=="sl") and not breached
                    out.append(dict(how=how, got=got, dur=dur, prem=prem, r=R/A))
                    last=i; break
    return out

print("STOP PAD ON ME PRO — 5m, v5.0 Rapid, all four modes, %d seeds\n" % len(SEEDS))
print("  %-6s%8s%7s%7s%7s%7s%7s%7s%8s%11s" %
      ("pad","trades","med R","TP1","TP2","TP3","BE","SL","bars","PREMATURE"))
for pad in PADS:
    d = run(pad); n=len(d)
    sl=[x for x in d if x["how"]=="sl"]
    print("  %-6.1f%8d%7.2f%6.0f%%%6.0f%%%6.0f%%%6.0f%%%6.0f%%%8d%10.0f%%" % (
        pad, n, sorted(x["r"] for x in d)[n//2],
        pct(sum(1 for x in d if x["got"][0]),n),
        pct(sum(1 for x in d if x["got"][1]),n),
        pct(sum(1 for x in d if x["got"][2]),n),
        pct(sum(1 for x in d if x["how"]=="be"),n),
        pct(len(sl),n), sorted(x["dur"] for x in d)[n//2],
        pct(sum(1 for x in sl if x["prem"]), len(sl))))
print("\n  PREMATURE = share of full stop-outs where the setup's own")
print("  invalidation was never closed through. Those losses are placement,")
print("  not the market. Outcome mix only — NO EXPECTANCY COMPUTED OR QUOTED.")
