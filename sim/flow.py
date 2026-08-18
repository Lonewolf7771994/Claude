"""ME Flow — prototype of a VWAP / order-flow / FVG engine.

Different premise to ME Pro. ME Pro waits for a structure EVENT (break, sweep,
gap retest) and then filters it through fourteen gates, which converts 1-3% of
triggers and produces under one trade a day. This trades CONTINUOUS STATE:

  spine     VWAP with volume-weighted deviation bands. Price rotates around it.
  orders    unfilled FVGs are treated as resting orders — the zone where
            aggressive flow left something behind.
  entry     price trades INTO a zone and closes back out of it (rejection),
            with order flow agreeing.

A zone is available on most bars, so opportunity is not gated by how often the
market happens to break structure.
"""
import math
from engine import wilder_atr, ema, rsi, sma_prior

def vwap_bands(bars, k1=1.0, k2=2.0):
    """daily-anchored VWAP plus volume-weighted deviation bands"""
    vw=[]; b1u=[]; b1l=[]; b2u=[]; b2l=[]
    pv=vv=pv2=0.0; day=None
    for t,o,h,l,c,v in bars:
        d=t//86_400_000
        if d!=day: day=d; pv=vv=pv2=0.0
        tp=(h+l+c)/3.0
        pv+=tp*v; vv+=v; pv2+=tp*tp*v
        m=pv/max(vv,1e-9)
        var=max(pv2/max(vv,1e-9)-m*m, 0.0)
        s=math.sqrt(var)
        vw.append(m); b1u.append(m+k1*s); b1l.append(m-k1*s)
        b2u.append(m+k2*s); b2l.append(m-k2*s)
    return vw,b1u,b1l,b2u,b2l

def zones(bars, atr, min_atr=0.25, max_age=60, cap=8):
    """unfilled FVGs as resting-order zones, per side, with a closure guard"""
    bull=[]; bear=[]; out=[]
    for i,(t,o,h,l,c,v) in enumerate(bars):
        if i>=2 and not math.isnan(atr[i]):
            A=atr[i]
            contig = (t-bars[i-2][0]) <= (bars[1][0]-bars[0][0])*2*3
            if contig and l>bars[i-2][2] and (l-bars[i-2][2])>=A*min_atr and bars[i-1][4]>bars[i-1][1]:
                bull.append([l,bars[i-2][2],i]); bull=bull[-cap:]
            if contig and bars[i-2][3]>h and (bars[i-2][3]-h)>=A*min_atr and bars[i-1][4]<bars[i-1][1]:
                bear.append([bars[i-2][3],h,i]); bear=bear[-cap:]
            bull=[g for g in bull if i-g[2]<=max_age and c>=g[1]]
            bear=[g for g in bear if i-g[2]<=max_age and c<=g[0]]
        out.append((list(bull), list(bear)))
    return out

def run_flow(bars, tf_sec, mode="Scalp", of_thr=0.58, vol_floor=0.8,
             body_min=0.20, buf=0.25, min_rr=0.8, cooldown=3,
             k1=1.0, k2=2.0, zone_min=0.25, max_age=60):
    h=[b[2] for b in bars]; l=[b[3] for b in bars]; c=[b[4] for b in bars]
    o=[b[1] for b in bars]; v=[b[5] for b in bars]
    atr=wilder_atr(h,l,c,14)
    vw,u1,l1,u2,l2 = vwap_bands(bars,k1,k2)
    Z = zones(bars, atr, zone_min, max_age)
    vavg = sma_prior(v,20)
    htf = ema(c, 50)
    n=len(bars); last=-10**9
    trades=[]; opps=0; blocks={}
    for i in range(60,n):
        A=atr[i]
        if math.isnan(A) or math.isnan(vavg[i]) or math.isnan(htf[i]): continue
        rng=max(h[i]-l[i],1e-9); cp=(c[i]-l[i])/rng; body=abs(c[i]-o[i])
        relv=v[i]/max(vavg[i],1e-9); delta=(c[i]-o[i])/rng
        bullZ,bearZ = Z[i]
        for is_buy in (True,False):
            zs = bullZ if is_buy else bearZ
            # a zone counts as touched when price traded into it this bar
            hit=None
            for g in reversed(zs):
                top,bot = (g[0],g[1]) if is_buy else (g[0],g[1])
                if is_buy and l[i]<=top and c[i]>bot: hit=g; break
                if (not is_buy) and h[i]>=bot and c[i]<top: hit=g; break
            # band touch also counts as a zone — the spine is tradable on its own
            band = (l[i] <= l1[i]) if is_buy else (h[i] >= u1[i])
            if hit is None and not band: continue
            opps+=1
            why=[]
            if (cp if is_buy else 1-cp) < of_thr: why.append("of")
            if body < A*body_min: why.append("body")
            if relv < vol_floor: why.append("vol")
            if (delta if is_buy else -delta) <= 0: why.append("delta")
            if i-last < cooldown: why.append("cd")
            if mode in ("Balanced","Strict"):
                if is_buy and not (c[i] < vw[i] or c[i] > u1[i]): why.append("vwap")
                if (not is_buy) and not (c[i] > vw[i] or c[i] < l1[i]): why.append("vwap")
            if mode=="Strict":
                deep = (l[i] <= l1[i]) if is_buy else (h[i] >= u1[i])
                if not deep: why.append("band")
                if is_buy and not c[i]>htf[i]: why.append("htf")
                if (not is_buy) and not c[i]<htf[i]: why.append("htf")
            # plan
            if hit is not None:
                zlo,zhi = (min(hit[0],hit[1]), max(hit[0],hit[1]))
                sl = (zlo - A*buf) if is_buy else (zhi + A*buf)
            else:
                sl = (l[i] - A*buf) if is_buy else (h[i] + A*buf)
            risk = max((c[i]-sl) if is_buy else (sl-c[i]), A*0.15)
            t1 = vw[i]
            t2 = (u1[i] if is_buy else l1[i])
            t3 = (u2[i] if is_buy else l2[i])
            tps=[t1,t2,t3]
            tps=[x for x in tps if (x>c[i]) == is_buy]
            while len(tps)<3:
                k=len(tps)+1
                tps.append(c[i] + (1 if is_buy else -1)*risk*(1.0+0.8*k))
            tps=sorted(tps, reverse=not is_buy)
            rr=(tps[0]-c[i])/risk if is_buy else (c[i]-tps[0])/risk
            if rr < min_rr: why.append("rr")
            if why:
                k=" ".join(sorted(set(why))); blocks[k]=blocks.get(k,0)+1
                continue
            from engine import resolve
            pnl,got,dur = resolve(bars,i,is_buy,c[i],sl,tps,True)
            trades.append(dict(i=i,side="B" if is_buy else "S",pnl=pnl,rr=rr,got=got))
            last=i; break
    return dict(bars=n, opps=opps, signals=len(trades), trades=trades, blocks=blocks)
