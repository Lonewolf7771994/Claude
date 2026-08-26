"""Does the v2.2 lesson transfer? The fade's stop sits just past the excursion
extreme — the tightest possible placement — and stops out 65-80% of the time.
ME Scalp v2.2 found exactly this shape and fixed it by widening the stop to
structure while decoupling targets to ATR so the trade did not get slower.
Same sweep here, on the best row (decayed walls)."""
import math
from gen import series_regime
from engine import wilder_atr
from ivwalls import build, sessions, daily_sigma, BARS_PER_DAY, pct

DAYS, SEEDS, KS = 200, (1, 2, 3), (1.0, 1.5, 2.0)
MAXHOLD, CONFIRM = 60, 4
PADS = (0.20, 0.60, 1.00, 1.50)
TPA = (0.8, 1.4, 2.2)          # targets in ATR, decoupled from risk

def run(bars, pad):
    sess = sessions(bars)
    h=[b[2] for b in bars]; l=[b[3] for b in bars]; c=[b[4] for b in bars]
    atr = wilder_atr(h,l,c,14)
    out = {k: [] for k in KS}
    for si,(s,e) in enumerate(sess):
        sig = daily_sigma(bars, sess, si)
        if sig is None: continue
        S0 = bars[s][1]
        for k in KS:
            fired={True:False, False:False}
            for i in range(s,e):
                A = atr[i]
                if A is None or math.isnan(A): continue
                left = max((e-i)/BARS_PER_DAY, 1e-6)
                em = S0*sig*k*math.sqrt(left)
                for is_up in (True, False):
                    if fired[is_up]: continue
                    wall = S0+em if is_up else S0-em
                    if not (h[i] >= wall if is_up else l[i] <= wall): continue
                    ent=None
                    for j in range(i, min(i+CONFIRM+1, len(bars))):
                        if (c[j] < wall) if is_up else (c[j] > wall): ent=j; break
                    if ent is None: continue
                    fired[is_up]=True
                    ex = max(h[i:ent+1]) if is_up else min(l[i:ent+1])
                    entry=c[ent]
                    stop = ex + A*pad if is_up else ex - A*pad
                    risk = abs(stop-entry)
                    if risk<=0 or risk > A*5.0: continue
                    d = -1.0 if is_up else 1.0
                    tps=[entry + d*A*m for m in TPA]
                    got=[False]*3; hitsl=False; dur=MAXHOLD
                    for j in range(ent+1, min(ent+1+MAXHOLD, len(bars))):
                        if (h[j]>=stop) if is_up else (l[j]<=stop):
                            hitsl=True; dur=j-ent; break
                        for ti,tp in enumerate(tps):
                            if got[ti]: continue
                            if (l[j]<=tp) if is_up else (h[j]>=tp): got[ti]=True
                        if all(got): dur=j-ent; break
                    out[k].append(dict(sl=hitsl, got=got, dur=dur, r=risk/A))
    return out

days = DAYS*len(SEEDS)
print("STOP WIDTH ON THE WALL FADE — decayed walls, targets fixed at %s ATR\n" % (TPA,))
print("  %-5s%-6s%9s%9s%8s%8s%8s%8s%7s" % ("pad","k","trades","per day","TP1","TP2","TP3","SL","bars"))
for pad in PADS:
    tot={k:[] for k in KS}
    for seed in SEEDS:
        r=run(build(seed), pad)
        for k in KS: tot[k]+=r[k]
    for k in KS:
        d=tot[k]; n=len(d)
        if not n: continue
        du=sorted(x["dur"] for x in d)[n//2]
        print("  %-5.2f%-6.1f%9d%9.2f%7.0f%%%7.0f%%%7.0f%%%7.0f%%%7d" % (
            pad,k,n,n/days,
            pct(sum(1 for x in d if x["got"][0]),n),
            pct(sum(1 for x in d if x["got"][1]),n),
            pct(sum(1 for x in d if x["got"][2]),n),
            pct(sum(1 for x in d if x["sl"]),n), du))
    print()
print("  Outcome mix only. NO EXPECTANCY COMPUTED OR QUOTED.")
