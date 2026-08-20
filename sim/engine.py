"""Faithful Python port of the ME Pro signal path.

Exists because 37 versions were shipped without the logic ever being executed.
Every threshold, clamp and gate below mirrors MovementEnginePro.pine; where the
port deviates it is marked APPROX and stated in the report.
"""
import math
from dataclasses import dataclass, field

# Set to 0.0 to reproduce the exact-cap comparison bug (risk == cap fails `<=`
# by one ULP). Kept switchable so the bug's cost can be measured, not asserted.
RISK_TOL = 1e-9

# ── indicators ──────────────────────────────────────────────────────────────
def wilder_atr(h, l, c, n):
    out=[float('nan')]*len(c); tr=[]
    for i in range(len(c)):
        if i==0: tr.append(h[i]-l[i])
        else: tr.append(max(h[i]-l[i], abs(h[i]-c[i-1]), abs(l[i]-c[i-1])))
        if i==n-1: out[i]=sum(tr[:n])/n
        elif i>=n: out[i]=(out[i-1]*(n-1)+tr[i])/n
    return out

def ema(src, n):
    out=[float('nan')]*len(src); k=2/(n+1); acc=None
    for i,v in enumerate(src):
        acc = v if acc is None else v*k+acc*(1-k)
        if i>=n-1: out[i]=acc
    return out

def rsi(c, n=14):
    out=[float('nan')]*len(c); g=l=0.0
    for i in range(1,len(c)):
        d=c[i]-c[i-1]; up=max(d,0); dn=max(-d,0)
        if i<=n: g+=up; l+=dn
        if i==n:
            g/=n; l/=n; out[i]=100-100/(1+g/max(l,1e-9))
        elif i>n:
            g=(g*(n-1)+up)/n; l=(l*(n-1)+dn)/n
            out[i]=100-100/(1+g/max(l,1e-9))
    return out

def sma_prior(src, n):
    """average of the PRIOR n bars (v3.5.4 fix)"""
    out=[float('nan')]*len(src)
    for i in range(len(src)):
        if i>=n: out[i]=sum(src[i-n:i])/n
    return out

def pivots(h, l, n):
    """ta.pivothigh/low(n,n) — confirmed n bars AFTER the pivot bar"""
    ph=[None]*len(h); pl=[None]*len(l)
    for i in range(n, len(h)-n):
        if h[i]==max(h[i-n:i+n+1]) and all(h[i]>h[j] for j in range(i-n,i) ):
            ph[i+n]=h[i]                      # known only at i+n
        if l[i]==min(l[i-n:i+n+1]) and all(l[i]<l[j] for j in range(i-n,i)):
            pl[i+n]=l[i]
    return ph, pl

# ── mode presets, mirroring the eff* block ──────────────────────────────────
@dataclass
class Cfg:
    mode: str = "Scalp"          # Scalp | Aggressive | Balanced | Strict
    freq: str = "Selective"      # Selective | Standard | High
    swing: int = 3
    sweep_pivot: int = 5
    trigger_age: int = 3
    mss_follow: float = 0.10
    fvg_min: float = 0.35
    fvg_max_age: int = 30
    sweep_wick: float = 0.40
    of_thresh: float = 60.0
    delta_floor: float = 0.20
    vol_floor: float = 1.20
    body_atr: float = 0.50
    wick_max: float = 2.0
    min_risk: float = 1.00
    max_risk: float = 3.00
    sl_atr: float = 0.50
    scalp_sl_cap: float = 0.30
    cooldown: int = 12
    min_rr: float = 1.00
    min_blend_rr: float = 1.30
    min_tp1_floor: float = 0.50
    max_tp1_r: float = 2.00      # v3.5.35
    scalp_max_risk: float = 2.00 # Scalp cap, isolated so it can be swept alone
    tp1r: float = 1.5
    tp2r: float = 2.5
    tp3r: float = 4.0
    min_conf: int = 0
    max_chase: float = 1.00
    vwap_max: float = 3.00
    rsi_buy: tuple = (40, 78)
    rsi_sell: tuple = (22, 60)
    v21: bool = False            # reproduce v3.5.21 exactly: no v3.5.29 risk floor
    # ── Scalp-only loosening levers (all no-ops unless loose=True and mode=Scalp)
    loose: bool = False
    loose_vol: float = 0.75      # Scalp volume floor  (v3.5.21 clamps to 1.00)
    loose_body: float = 0.20     # Scalp body/ATR floor (v3.5.21 clamps to 0.30)
    loose_rr: tuple = (0.8, 0.7, 0.6)   # Selective / Standard / High
    loose_max_risk: float = 2.50 # Scalp max risk in ATR (v3.5.21 caps at 2.00)
    loose_clamp_risk: bool = True  # stop beyond the cap -> clamp, do not block
    loose_vwap_max: float = 4.0  # Scalp overextension guard (v3.5.21 uses 3.0)
    loose_min_conf: bool = True  # drop the unturnoffable conf>=1 floor on Sel/Std
    loose_cd: tuple = (3, 2, 1)  # Scalp cooldown bars: Selective / Standard / High
    loose_max_chase: float = 1.6 # Scalp entry extension past trigger, in ATR

    def eff(self):
        s = self.mode == "Scalp"
        hi = s and self.freq == "High"
        st = s and self.freq == "Standard"
        e = dict(
            swing        = 2 if s else self.swing,
            vol_floor    = min(self.vol_floor, 1.0) if s else self.vol_floor,
            delta_floor  = min(self.delta_floor, .15) if s else self.delta_floor,
            of_thresh    = min(self.of_thresh, 57.) if s else self.of_thresh,
            body_atr     = min(self.body_atr, .3) if s else self.body_atr,
            cooldown     = min(self.cooldown, 2 if hi else 4 if st else 5) if s else self.cooldown,
            min_risk     = min(self.min_risk, .5) if s else self.min_risk,
            tp1r         = min(self.tp1r, 1.0) if s else self.tp1r,
            tp2r         = min(self.tp2r, 1.5) if s else self.tp2r,
            tp3r         = min(self.tp3r, 2.0) if s else self.tp3r,
            rsi_buy      = (min(self.rsi_buy[0],35),  max(self.rsi_buy[1],80))  if s else self.rsi_buy,
            rsi_sell     = (min(self.rsi_sell[0],20), max(self.rsi_sell[1],65)) if s else self.rsi_sell,
            min_conf     = (self.min_conf if hi else max(self.min_conf,1)) if s else self.min_conf,
            min_rr       = min(self.min_rr, .7 if hi else .9 if st else 99.) if s else self.min_rr,
        )
        if s and self.loose:
            e["vol_floor"] = min(self.vol_floor, self.loose_vol)
            e["body_atr"]  = min(self.body_atr,  self.loose_body)
            e["min_rr"]    = min(self.min_rr, self.loose_rr[2] if hi else
                                              self.loose_rr[1] if st else self.loose_rr[0])
            e["cooldown"]  = min(self.cooldown, self.loose_cd[2] if hi else
                                                self.loose_cd[1] if st else self.loose_cd[0])
            if self.loose_min_conf:
                e["min_conf"] = self.min_conf
        buf_worst = min(self.sl_atr, self.scalp_sl_cap) * 1.3          # v3.5.29
        if s and self.loose:
            e["max_risk"] = min(self.max_risk, self.loose_max_risk)
            return e
        if self.v21:
            e["max_risk"] = min(self.max_risk, self.scalp_max_risk) if s else self.max_risk
        else:
            e["max_risk"] = max(min(self.max_risk, self.scalp_max_risk), buf_worst + .75) if s else self.max_risk
        return e

# ── TP ladder: port of f_tpLevels incl. the v3.5.21 spacing and v3.5.35 ceiling
def tp_levels(is_buy, entry, risk, atr, struct, e, cfg):
    d = 1.0 if is_buy else -1.0
    raw = sorted([x for x in struct if (x > entry) == is_buy], key=lambda v: abs(v-entry))
    gap = max(atr*0.5, risk*0.25)
    cands=[]
    for x in raw:
        if not cands or abs(x-cands[-1]) >= gap: cands.append(x)
    cap = risk*cfg.max_tp1_r if cfg.max_tp1_r > 0 else 1e12
    inj = False
    if cands and abs(cands[0]-entry) > cap:                    # v3.5.35
        cands = [entry + d*risk*e["tp1r"]] + cands; inj = True
    rmul=[e["tp1r"], e["tp2r"], e["tp3r"]]
    fV=[]
    for s in range(3):
        if s < len(cands):
            fV.append(cands[s])
        else:
            rv = entry + d*risk*rmul[s]
            for _ in range(4):                                  # v3.5.21 nudge
                for j in list(fV):
                    if abs(rv-j) < gap: rv = j + d*gap
            fV.append(rv)
    fV.sort(reverse=not is_buy)
    return fV

def resolve(bars, i, is_buy, entry, sl, tps, be_ok, max_look=400):
    """Walk forward. 33/33/34 scale-out, breakeven after TP1 when armed."""
    R = abs(entry-sl); got=[False]*3; stop=sl; pnl=0.0; w=[.33,.33,.34]
    for k in range(i+1, min(i+1+max_look, len(bars))):
        h,l = bars[k][2], bars[k][3]
        hit_sl = l <= stop if is_buy else h >= stop
        for t in range(3):
            if got[t]: continue
            reach = h >= tps[t] if is_buy else l <= tps[t]
            if reach and not (hit_sl and t == 0 and not got[0]):
                got[t]=True; pnl += w[t]*abs(tps[t]-entry)/R
                if t==0 and be_ok: stop = entry
        if hit_sl:
            rem = sum(w[t] for t in range(3) if not got[t])
            pnl += rem * (0.0 if stop==entry else -1.0)
            return pnl, got, k-i
        if all(got): return pnl, got, k-i
    rem = sum(w[t] for t in range(3) if not got[t])
    last = bars[min(len(bars)-1, i+max_look)][4]
    pnl += rem * ((last-entry)/R if is_buy else (entry-last)/R)
    return pnl, got, max_look

# ── main pass ───────────────────────────────────────────────────────────────
def run(bars, cfg: Cfg, tf_sec: int):
    """bars = [(t,o,h,l,c,v)]. Returns per-bar stats and the trade list."""
    e = cfg.eff()
    t=[b[0] for b in bars]; o=[b[1] for b in bars]; h=[b[2] for b in bars]
    l=[b[3] for b in bars]; c=[b[4] for b in bars]; v=[b[5] for b in bars]
    n=len(bars)
    atr14=wilder_atr(h,l,c,14); atr50=wilder_atr(h,l,c,50)
    vwp = session_vwap(bars)
    htf_sec = 14400 if tf_sec<=900 else (86400 if tf_sec<=14400 else 604800)
    hbias = htf_bias(bars, tf_sec, htf_sec)
    POC,VAH,VAL = frvp(bars)
    ef=ema(c,8); es=ema(c,21); rs=rsi(c,14)
    vavg=sma_prior(v,20)
    ph,pl = pivots(h,l,e["swing"])
    sph,spl = pivots(h,l,cfg.sweep_pivot)

    PH=[]; PL=[]; SPH=None; SPL=None
    fvgs={"bull":[], "bear":[]}
    mss_up_age=mss_dn_age=999; swp_b_age=swp_s_age=999
    swp_b_low=swp_b_lvl=swp_s_high=swp_s_lvl=None
    cvd=0.0; cvd_hist=[]
    last_sig=-10**9
    trig=0; sig=0; trades=[]
    blocks={}

    for i in range(n):
        if ph[i] is not None: PH.insert(0, ph[i]); PH[:] = PH[:3]
        if pl[i] is not None: PL.insert(0, pl[i]); PL[:] = PL[:3]
        if sph[i] is not None: SPH=sph[i]
        if spl[i] is not None: SPL=spl[i]
        cvd += v[i] if c[i]>o[i] else (-v[i] if c[i]<o[i] else 0.0)
        cvd_hist.append(cvd)
        if i<55 or math.isnan(atr14[i]) or math.isnan(atr50[i]) or math.isnan(rs[i]) or math.isnan(es[i]):
            continue
        A=atr14[i]; AB=max(atr14[i],atr50[i])
        rng=max(h[i]-l[i],1e-9); cp=(c[i]-l[i])/rng; bp=cp*100
        scalp = cfg.mode=="Scalp"; refA = A if scalp else AB
        volreg = atr14[i]/atr50[i] if atr50[i] else 1.0
        chop = volreg<=0.85; expand = volreg>=1.15

        # triggers
        lastPH = PH[0] if PH else None; lastPL = PL[0] if PL else None
        mss_up_ev = lastPH is not None and c[i]>=lastPH+A*cfg.mss_follow and c[i-1]<lastPH
        mss_dn_ev = lastPL is not None and c[i]<=lastPL-A*cfg.mss_follow and c[i-1]>lastPL
        mss_up_age = 0 if mss_up_ev else min(mss_up_age+1,999)
        mss_dn_age = 0 if mss_dn_ev else min(mss_dn_age+1,999)
        if mss_up_ev: mss_dn_age=999
        if mss_dn_ev: mss_up_age=999
        mssUp = mss_up_age<=cfg.trigger_age; mssDn = mss_dn_age<=cfg.trigger_age

        # FVG (with v3.5.33 contiguity guard)
        contig = (t[i]-t[i-2]) <= tf_sec*1000*2*3.0
        if contig and l[i]>h[i-2] and (l[i]-h[i-2])>=A*cfg.fvg_min and c[i-1]>o[i-1]:
            fvgs["bull"].append([l[i], h[i-2], i]); fvgs["bull"]=fvgs["bull"][-5:]
        if contig and l[i-2]>h[i] and (l[i-2]-h[i])>=A*cfg.fvg_min and c[i-1]<o[i-1]:
            fvgs["bear"].append([l[i-2], h[i], i]); fvgs["bear"]=fvgs["bear"][-5:]
        fvgs["bull"]=[g for g in fvgs["bull"] if i-g[2]<=cfg.fvg_max_age and c[i]>=g[1]]
        fvgs["bear"]=[g for g in fvgs["bear"] if i-g[2]<=cfg.fvg_max_age and c[i]<=g[0]]
        hitB=hitS=None
        for g in reversed(fvgs["bull"]):
            m=(g[0]+g[1])/2
            if (l[i]<=g[0] and c[i]>=g[1] and cp>=.6) or (l[i]<=m and c[i]>m and cp>=.6): hitB=g; break
        for g in reversed(fvgs["bear"]):
            m=(g[0]+g[1])/2
            if (h[i]>=g[1] and c[i]<=g[0] and cp<=.4) or (h[i]>=m and c[i]<m and cp<=.4): hitS=g; break

        # sweep
        sb = SPL is not None and (SPL-l[i])>=A*cfg.sweep_wick and c[i]>SPL and cp>=.6
        ss = SPH is not None and (h[i]-SPH)>=A*cfg.sweep_wick and c[i]<SPH and cp<=.4
        if sb: swp_b_low=l[i]; swp_b_lvl=SPL
        if ss: swp_s_high=h[i]; swp_s_lvl=SPH
        swp_b_age = 0 if sb else min(swp_b_age+1,999)
        swp_s_age = 0 if ss else min(swp_s_age+1,999)
        if sb: swp_s_age=999
        if ss: swp_b_age=999
        swB = swp_b_age<=cfg.trigger_age; swS = swp_s_age<=cfg.trigger_age

        tf_b = cfg.mode!="Strict" and hitB is not None
        tf_s = cfg.mode!="Strict" and hitS is not None
        sw_b = (cfg.mode=="Aggressive" or scalp) and swB
        sw_s = (cfg.mode=="Aggressive" or scalp) and swS
        trigB = mssUp or tf_b or sw_b
        trigS = mssDn or tf_s or sw_s
        if trigB or trigS: trig+=1
        if not (trigB or trigS): continue

        yield_state = dict(i=i, A=A, refA=refA, cp=cp, bp=bp, chop=chop, expand=expand,
                           lastPH=lastPH, lastPL=lastPL, hitB=hitB, hitS=hitS,
                           swp_b_low=swp_b_low, swp_b_lvl=swp_b_lvl,
                           swp_s_high=swp_s_high, swp_s_lvl=swp_s_lvl,
                           tf_b=tf_b, tf_s=tf_s, sw_b=sw_b, sw_s=sw_s,
                           mssUp=mssUp, mssDn=mssDn, trigB=trigB, trigS=trigS)
        yield_state.update(vwap=vwp[i], htfBull=hbias[i], vah=VAH[i], val=VAL[i])
        r = _eval(bars, yield_state, cfg, e, PH, PL, ef, es, rs, v, vavg,
                  cvd_hist, last_sig, blocks, scalp)
        if r is not None:
            sig+=1; last_sig=i; trades.append(r)
    return dict(bars=n, triggers=trig, signals=sig, trades=trades, blocks=blocks)

def _eval(bars, S, cfg, e, PH, PL, ef, es, rs, v, vavg, cvd_hist, last_sig, blocks, scalp):
    i=S["i"]; A=S["A"]; refA=S["refA"]; cp=S["cp"]; bp=S["bp"]
    o=bars[i][1]; h=bars[i][2]; l=bars[i][3]; c=bars[i][4]
    rng=max(h-l,1e-9); body=abs(c-o)
    uw=h-max(c,o); lw=min(c,o)-l

    relv = v[i]/max(vavg[i],1e-9) if not math.isnan(vavg[i]) else 1.0
    delta=(c-o)/rng
    thr = e["of_thresh"] + (5.0 if (not scalp and S["chop"]) else 0.0)
    cvdBull = cvd_hist[i] > (sum(cvd_hist[max(0,i-9):i+1])/min(10,i+1) if scalp
                             else sum(cvd_hist[max(0,i-19):i+1])/min(20,i+1))
    momB = ef[i]>es[i]; momS = ef[i]<es[i]

    out=None
    for is_buy in (True, False):
        if is_buy and not S["trigB"]: continue
        if (not is_buy) and not S["trigS"]: continue
        bar_ok = (c>o) if is_buy else (c<o)
        if not bar_ok: continue
        why=[]
        if body < A*e["body_atr"]: why.append("body")
        rej = (S["sw_b"] or S["tf_b"]) if is_buy else (S["sw_s"] or S["tf_s"])
        wr = (uw/body if body>0 else 999) if is_buy else (lw/body if body>0 else 999)
        wr_all = ((uw+lw)/body if body>0 else 999)
        if (wr if rej else wr_all) > cfg.wick_max: why.append("wick")
        if relv < e["vol_floor"]: why.append("vol")
        if (bp if is_buy else 100-bp) < thr: why.append("of%")
        if (delta if is_buy else -delta) < e["delta_floor"]: why.append("delta")
        sweepTrig = S["sw_b"] if is_buy else S["sw_s"]
        if not ((cvdBull if is_buy else not cvdBull) or (scalp and sweepTrig)): why.append("cvd")
        if not ((momB if is_buy else momS) or (scalp and sweepTrig)): why.append("mom")
        lo,hi = e["rsi_buy"] if is_buy else e["rsi_sell"]
        if not (lo<=rs[i]<=hi): why.append("rsi")
        if i-last_sig < e["cooldown"]: why.append("cooldown")

        # v2: the two gates the first harness omitted, and they are not minor —
        # mode IS the only mode gate Scalp has, and Selective demands conf >= 1.
        vw = S.get("vwap"); vext = abs(c-vw)/A if vw else 0.0
        vwmax = cfg.loose_vwap_max if (scalp and cfg.loose) else cfg.vwap_max
        notExtended = vext <= vwmax
        if not notExtended: why.append("mode")
        above = (c > vw) if vw else False
        hb = S.get("htfBull")
        vah = S.get("vah"); val = S.get("val")
        frvpBull = (val is None) or c >= val
        frvpBear = (vah is None) or c <= vah
        conf = ((1 if hb else 0) + (1 if above else 0) + (1 if frvpBull else 0)) if is_buy \
               else ((1 if hb is False else 0) + (0 if above else 1) + (1 if frvpBear else 0))
        if conf < e["min_conf"]: why.append("confluence")

        # stop, trigger-aware (v3.5.7)
        if is_buy:
            anchor = S["swp_b_low"] if (S["sw_b"] and S["swp_b_low"]) else (S["hitB"][1] if S["tf_b"] and S["hitB"] else S["lastPL"])
            ref    = S["swp_b_lvl"] if (S["sw_b"] and S["swp_b_lvl"]) else (S["hitB"][0] if S["tf_b"] and S["hitB"] else S["lastPH"])
        else:
            anchor = S["swp_s_high"] if (S["sw_s"] and S["swp_s_high"]) else (S["hitS"][0] if S["tf_s"] and S["hitS"] else S["lastPH"])
            ref    = S["swp_s_lvl"] if (S["sw_s"] and S["swp_s_lvl"]) else (S["hitS"][1] if S["tf_s"] and S["hitS"] else S["lastPL"])
        mult = 1.3 if S["expand"] else 1.2 if S["chop"] else 1.0
        buf  = refA*min(cfg.sl_atr, cfg.scalp_sl_cap)*mult if scalp else refA*cfg.sl_atr*mult
        if anchor is None:
            sl = c - refA*1.5 if is_buy else c + refA*1.5
        else:
            sl = min(anchor-buf, c-refA*0.5) if is_buy else max(anchor+buf, c+refA*0.5)
        near = refA*e["min_risk"]
        sl = min(sl, c-near) if is_buy else max(sl, c+near)      # near-side clamp only
        # Scalp-only: a structural stop past the cap becomes a volatility stop AT
        # the cap instead of killing the setup. `risk` is the 2nd biggest sole
        # blocker in v3.5.21 Scalp (483 of them on 15m Selective).
        if scalp and cfg.loose and cfg.loose_clamp_risk:
            far = refA*e["max_risk"]
            sl = max(sl, c-far) if is_buy else min(sl, c+far)
        risk = max((c-sl) if is_buy else (sl-c), A*0.1)
        # A clamped stop lands EXACTLY on the cap, and `<=` then fails by one
        # floating-point ULP — which was rejecting ~47% of setups here and is
        # the same latent defect the Pine carries.
        tol = RISK_TOL
        if not (refA*e["min_risk"]*(1-tol) <= risk <= refA*e["max_risk"]*(1+tol)):
            why.append("risk")
        mchase = cfg.loose_max_chase if (scalp and cfg.loose) else cfg.max_chase
        if ref is not None and ((c-ref) if is_buy else (ref-c)) > A*mchase: why.append("chase")

        struct = (PH+[None]) if is_buy else (PL+[None])
        struct = [x for x in struct if x is not None]
        tps = tp_levels(is_buy, c, risk, A, struct, e, cfg)
        rr  = (tps[0]-c)/risk if is_buy else (c-tps[0])/risk
        blend = sum(w*((tp-c) if is_buy else (c-tp)) for w,tp in zip((.33,.33,.34),tps))/risk
        strict_ok = rr >= e["min_rr"]
        blend_ok  = cfg.min_blend_rr>0 and rr>=cfg.min_tp1_floor and blend>=cfg.min_blend_rr
        if not (e["min_rr"]<=0 or strict_ok or blend_ok): why.append("rr")

        if why:
            k=" ".join(sorted(set(why)))
            blocks[k]=blocks.get(k,0)+1
            continue
        pnl,got,dur = resolve(bars,i,is_buy,c,sl,tps,strict_ok)
        out=dict(i=i, side="B" if is_buy else "S", entry=c, sl=sl, tps=tps,
                 r=risk, rr=rr, pnl=pnl, got=got, dur=dur)
        break
    return out

# ── context gates that v1 of this harness omitted ───────────────────────────
def session_vwap(bars):
    """daily-anchored VWAP on hlc3, matching ta.vwap with a day anchor"""
    out=[]; pv=0.0; vv=0.0; day=None
    for t,o,h,l,c,v in bars:
        d=t//86_400_000
        if d!=day: day=d; pv=0.0; vv=0.0
        tp=(h+l+c)/3.0; pv+=tp*v; vv+=v
        out.append(pv/max(vv,1e-9))
    return out

def htf_bias(bars, tf_sec, htf_sec, ema_len=50):
    """last CLOSED higher-timeframe bar vs its EMA — the v3.5.17 stable idiom"""
    buckets={}; order=[]
    for idx,(t,o,h,l,c,v) in enumerate(bars):
        k=t//(htf_sec*1000)
        if k not in buckets: buckets[k]=[c,idx]; order.append(k)
        buckets[k][0]=c; buckets[k][1]=idx
    closes=[buckets[k][0] for k in order]
    em=ema(closes, ema_len)
    bull=[False]*len(bars); seen={}
    for j,k in enumerate(order):
        # only the PREVIOUS closed bucket is knowable during bucket j
        seen[k]= (closes[j-1] > em[j-1]) if j>=1 and em[j-1]==em[j-1] else None
    for idx,(t,*_ ) in enumerate(bars):
        k=t//(htf_sec*1000)
        bull[idx]=seen.get(k)
    return bull

def frvp(bars, length=100, bins=32, va=0.70, stride=5):
    """rolling volume profile -> (poc, vah, val) per bar, recomputed on a stride"""
    n=len(bars); P=[None]*n; VAH=[None]*n; VAL=[None]*n
    poc=vah=val=None
    for i in range(n):
        if i>=length and i%stride==0:
            w=bars[i-length+1:i+1]
            hi=max(b[2] for b in w); lo=min(b[3] for b in w)
            bs=max(hi-lo,1e-9)/bins
            acc=[0.0]*bins
            for _,o,h,l,c,v in w:
                rng=h-l
                if rng<=0:
                    k=min(bins-1,max(0,int((h-lo)/bs))); acc[k]+=v; continue
                a=min(bins-1,max(0,int((l-lo)/bs))); b_=min(bins-1,max(0,int((h-lo)/bs)))
                for k in range(a,b_+1):
                    bb=lo+k*bs; bt=bb+bs
                    ov=min(bt,h)-max(bb,l)
                    if ov>0: acc[k]+=v*(ov/rng)
            tot=sum(acc)
            if tot>0:
                pb=max(range(bins), key=lambda k: acc[k])
                cur=acc[pb]; up=dn=pb; tgt=tot*va; it=0
                while cur<tgt and it<bins*2:
                    uv=sum(acc[up+1:up+3]); us=min(2,bins-1-up)
                    dv=sum(acc[max(0,dn-2):dn]); ds=min(2,dn)
                    if us==0 and ds==0: break
                    if us>0 and (ds==0 or uv>=dv): up+=us; cur+=uv
                    else: dn-=ds; cur+=dv
                    it+=1
                poc=lo+(pb+.5)*bs; vah=lo+(up+1)*bs; val=lo+dn*bs
        P[i]=poc; VAH[i]=vah; VAL[i]=val
    return P,VAH,VAL
