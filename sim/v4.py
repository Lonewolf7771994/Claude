"""ME Pro v4 — rebuilt trigger set.

Measured problem with v3.5.x: 26.7 triggers/day on 15m and 2-4% conversion, so
under one trade a day. Removing the three redundant gates (chase 92% duplicate
of risk, delta 88% of wick, of% 76% of wick) bought only +8%. The binding
constraint is TRIGGER SUPPLY, not filtering.

v4 keeps the three structural triggers and adds two that were already computed
by the engine and never used as entries:

  band   price trades through a VWAP deviation band and closes back inside
  value  price trades through VAH/VAL and closes back inside the value area

Both are real, dated events with their own invalidation level — the band or the
edge that was rejected — so the stop is defined the same way MSS/FVG/sweep
stops are. Neither is a loosening of an existing gate.
"""
import math
from engine import wilder_atr, ema, rsi, sma_prior, pivots, tp_levels, resolve, Cfg, frvp
from flow import vwap_bands, zones

def triggers_v4(bars, tf_sec, k1=1.0, k2=2.0, wick=0.4, fvg_min=0.35,
                mss_follow=0.10, swing=2, sweep_len=5, fvg_age=30):
    n=len(bars)
    h=[b[2] for b in bars]; l=[b[3] for b in bars]; c=[b[4] for b in bars]; o=[b[1] for b in bars]
    atr=wilder_atr(h,l,c,14)
    vw,u1,l1,u2,l2 = vwap_bands(bars,k1,k2)
    Z = zones(bars, atr, fvg_min, fvg_age)
    POC, VAH, VAL = frvp(bars)
    ph,pl = pivots(h,l,swing); sph,spl = pivots(h,l,sweep_len)
    PH=[];PL=[];SPH=SPL=None
    out=[]
    for i in range(n):
        if ph[i] is not None: PH.insert(0,ph[i]); PH=PH[:3]
        if pl[i] is not None: PL.insert(0,pl[i]); PL=PL[:3]
        if sph[i] is not None: SPH=sph[i]
        if spl[i] is not None: SPL=spl[i]
        ev={"buy":[], "sell":[]}
        if i<60 or math.isnan(atr[i]):
            out.append(ev); continue
        A=atr[i]; rng=max(h[i]-l[i],1e-9); cp=(c[i]-l[i])/rng
        # 1 MSS
        if PH and c[i]>=PH[0]+A*mss_follow and c[i-1]<PH[0]: ev["buy"].append(("mss",PH[0],PL[0] if PL else l[i]))
        if PL and c[i]<=PL[0]-A*mss_follow and c[i-1]>PL[0]: ev["sell"].append(("mss",PL[0],PH[0] if PH else h[i]))
        # 2 FVG retest
        bz,sz = Z[i]
        for g in reversed(bz):
            if l[i]<=g[0] and c[i]>=g[1] and cp>=.6: ev["buy"].append(("fvg",g[0],g[1])); break
        for g in reversed(sz):
            if h[i]>=g[1] and c[i]<=g[0] and cp<=.4: ev["sell"].append(("fvg",g[1],g[0])); break
        # 3 sweep
        if SPL and (SPL-l[i])>=A*wick and c[i]>SPL and cp>=.6: ev["buy"].append(("sweep",SPL,l[i]))
        if SPH and (h[i]-SPH)>=A*wick and c[i]<SPH and cp<=.4: ev["sell"].append(("sweep",SPH,h[i]))
        # 4 NEW: VWAP band rejection — traded through, closed back inside
        if l[i]<=l1[i] and c[i]>l1[i] and cp>=.55: ev["buy"].append(("band",l1[i],l[i]))
        if h[i]>=u1[i] and c[i]<u1[i] and cp<=.45: ev["sell"].append(("band",u1[i],h[i]))
        if l[i]<=l2[i] and c[i]>l2[i] and cp>=.55: ev["buy"].append(("band2",l2[i],l[i]))
        if h[i]>=u2[i] and c[i]<u2[i] and cp<=.45: ev["sell"].append(("band2",u2[i],h[i]))
        # 5 VALUE-AREA rejection: price trades OUTSIDE the value area and closes
        # back inside it. Promised in this module's docstring since v4 and never
        # actually built — FRVP was only ever a filter and a TP source.
        if VAL[i] is not None and VAH[i] is not None:
            if l[i]<=VAL[i] and c[i]>VAL[i] and cp>=.55: ev["buy"].append(("value",VAL[i],l[i]))
            if h[i]>=VAH[i] and c[i]<VAH[i] and cp<=.45: ev["sell"].append(("value",VAH[i],h[i]))
        out.append(ev)
    return out, (vw,u1,l1,u2,l2), atr, (POC,VAH,VAL)

def count(bars, tf_sec, **kw):
    T,_,_,_ = triggers_v4(bars, tf_sec, **kw)
    tot={}; any_=0
    for e in T:
        got=False
        for side in ("buy","sell"):
            for name,_,_ in e[side]:
                tot[name]=tot.get(name,0)+1; got=True
        if got: any_+=1
    return tot, any_

def run_v4(bars, tf_sec, mode="Scalp", freq="Selective",
           body_min=0.30, wick_max=2.0, vol_floor=0.9,
           min_risk=0.5, max_risk=3.0, sl_buf=0.30,
           min_rr=1.0, min_blend=1.3, tp1_floor=0.5, max_tp1=2.0,
           cooldown=4, tp_r=(1.0,1.5,2.0), max_tp_r=None):
    T,(vw,u1,l1,u2,l2),atr,(POC,VAH,VAL) = triggers_v4(bars, tf_sec)
    h=[b[2] for b in bars]; l=[b[3] for b in bars]; c=[b[4] for b in bars]
    o=[b[1] for b in bars]; v=[b[5] for b in bars]
    vavg=sma_prior(v,20); htf=ema(c,50)
    ph,pl = pivots(h,l,2)
    PH=[];PL=[]; last=-10**9; trades=[]; blocks={}; nt=0
    for i in range(60,len(bars)):
        if ph[i] is not None: PH.insert(0,ph[i]); PH=PH[:3]
        if pl[i] is not None: PL.insert(0,pl[i]); PL=PL[:3]
        A=atr[i]
        if math.isnan(A) or math.isnan(vavg[i]) or math.isnan(htf[i]): continue
        ev=T[i]
        if not ev["buy"] and not ev["sell"]: continue
        nt+=1
        rng=max(h[i]-l[i],1e-9); cp=(c[i]-l[i])/rng; body=abs(c[i]-o[i])
        uw=h[i]-max(c[i],o[i]); lw=min(c[i],o[i])-l[i]
        relv=v[i]/max(vavg[i],1e-9)
        for is_buy in (True,False):
            cand = ev["buy"] if is_buy else ev["sell"]
            if not cand: continue
            name, ref, inval = cand[0]
            if (c[i]>o[i]) != is_buy: continue
            why=[]
            # 1 bar quality  (absorbs the old body / wick / delta / of% cluster)
            if body < A*body_min: why.append("body")
            wr = (uw/body if body>0 else 999) if is_buy else (lw/body if body>0 else 999)
            if wr > wick_max: why.append("wick")
            # 2 participation
            if relv < vol_floor: why.append("vol")
            # 3 context, by mode — a CONFLUENCE SCORE, not a location veto.
            #
            # v4.0 gated Strict on location ("must be at the outer band"). Measured
            # 0.38/day on 15m, 0.07/day on 1H: `loc` was the sole cause of 1066 of
            # 30m Strict's blocks and appeared in 69-74% of all of them. It vetoed
            # the `band` trigger, which is the bulk of v4's supply. Starved by
            # construction.
            #
            # Strict now means "more independent things agree", which every mode can
            # reach on any bar rather than only at a rare price location.
            score = 0
            if relv >= 1.20: score += 1                      # participation
            if body >= A*0.55: score += 1                    # conviction
            if (cp >= 0.70) if is_buy else (cp <= 0.30): score += 1   # close location in bar
            if len(cand) >= 2: score += 1                    # two triggers stacked
            # Location only counts as confluence for a trigger that is not itself a
            # band rejection — a band trigger sits at a band by construction, so
            # awarding it the point is double-counting. That is what made Strict and
            # Balanced identical on 1H/4H, where band supplies 74% of entries.
            if name not in ("band","band2"):
                if (c[i] <= l1[i]*1.002) if is_buy else (c[i] >= u1[i]*0.998): score += 1
            need = {"Scalp": 0, "Balanced": 1, "Strict": 2}[mode]
            if score < need: why.append("conf")
            if mode in ("Balanced","Strict"):
                if is_buy and c[i] < htf[i]: why.append("trend")
                if (not is_buy) and c[i] > htf[i]: why.append("trend")
            # 4 risk
            sl = (min(inval, c[i]-A*min_risk) - A*sl_buf) if is_buy else (max(inval, c[i]+A*min_risk) + A*sl_buf)
            risk = max((c[i]-sl) if is_buy else (sl-c[i]), A*0.1)
            if not (A*min_risk <= risk <= A*max_risk): why.append("risk")
            # 5 reward
            # A band rejection is a REVERSION trade: price left the band and is
            # coming back toward the mean. Giving it the same continuation ladder
            # as an MSS breakout measured -0.075R against MSS's -0.007R. Its
            # first target is the mean itself.
            if name == "value":
                struct=[x for x in (POC[i], vw[i]) if x is not None and (x>c[i])==is_buy]
            elif name in ("band","band2"):
                struct=[vw[i]]
                for band in ((u1[i],) if is_buy else (l1[i],)):
                    struct.append(band)
                struct=[x for x in struct if (x>c[i])==is_buy]
            else:
                struct=[x for x in (PH if is_buy else PL) if x is not None]
                for band in ((u1[i],u2[i]) if is_buy else (l1[i],l2[i])):
                    struct.append(band)
            cfg=Cfg(); cfg.max_tp1_r=max_tp1
            e={"tp1r":tp_r[0],"tp2r":tp_r[1],"tp3r":tp_r[2]}
            tps=tp_levels(is_buy,c[i],risk,A,struct,e,cfg)
            rr=(tps[0]-c[i])/risk if is_buy else (c[i]-tps[0])/risk
            blend=sum(w*((t-c[i]) if is_buy else (c[i]-t)) for w,t in zip((.33,.33,.34),tps))/risk
            if not (rr>=min_rr or (blend>=min_blend and rr>=tp1_floor)): why.append("rr")
            # 6 cooldown
            if i-last < cooldown: why.append("cd")
            if why:
                k=" ".join(sorted(set(why))); blocks[k]=blocks.get(k,0)+1
                continue
            pnl,got,dur = resolve(bars,i,is_buy,c[i],sl,tps,rr>=min_rr)
            trades.append(dict(i=i,side="B" if is_buy else "S",pnl=pnl,rr=rr,got=got,trig=name))
            last=i; break
    return dict(triggers=nt, signals=len(trades), trades=trades, blocks=blocks)
