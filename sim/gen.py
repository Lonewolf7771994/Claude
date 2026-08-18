"""Synthetic OHLCV with a gold-like intraday shape.

Not real XAUUSD — it cannot prove profitability. What it CAN answer is whether
the engine's own gates behave sensibly across timeframes and modes, which is
what has been argued about without evidence.
"""
import math, random

def series(n, tf_sec, seed=1, price=4400.0, ann_vol=0.16, trend=0.0):
    random.seed(seed)
    bars=[]; t0=1_700_000_000_000
    per_year = 365*24*3600/tf_sec
    sig = ann_vol/math.sqrt(per_year)
    p = price
    for i in range(n):
        hour = ((i*tf_sec)//3600) % 24
        # volume profile: Asian thin, London + NY surges
        def bump(cn,w,a): return a*math.exp(-((hour-cn)**2)/(2*w*w))
        vshape = .25 + bump(8,1.6,1.0) + bump(13.5,1.8,1.6) + bump(15,1.0,.7) + bump(20,1.2,.4)
        vol_mult = 0.6 + 0.9*vshape                      # volatility tracks activity
        drift = trend*sig
        ret = random.gauss(drift, sig*vol_mult)
        o = p
        cl = o*math.exp(ret)
        span = abs(cl-o) + o*sig*vol_mult*abs(random.gauss(0,.9))
        hi = max(o,cl) + span*random.random()*.6
        lo = min(o,cl) - span*random.random()*.6
        v  = max(1.0, vshape*1000*random.lognormvariate(0,.45))
        bars.append((t0+i*tf_sec*1000, o, hi, lo, cl, v))
        p = cl
    return bars
