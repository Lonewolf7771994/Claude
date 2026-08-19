"""Synthetic OHLCV calibrated to REAL structure density.

v1 used iid gaussian returns. That whipsaws constantly, so pivots form on
almost every bar and MSS/FVG/sweep fired every ~2 bars — against a real 15m
XAUUSD chart that reported "MSS fresh 27b". Every signal rate measured on v1
was inflated by roughly an order of magnitude, and the calibration built on
those rates was worthless.

v2 adds the two properties that make real price form structure slowly:
  - momentum persistence (AR(1) on returns). DEFAULT 0.03, matching real
    bar-scale autocorrelation. An earlier default of 0.82 put a large
    trend-following edge INTO the data and made every engine look profitable;
  - volatility clustering (GARCH-like), so quiet stretches stay quiet.
Both are tuned so structure-shift spacing matches the observed chart.
"""
import math, random

def series(n, tf_sec, seed=1, price=4400.0, ann_vol=0.16,
           phi=0.03, vol_persist=0.94, vol_shock=0.06, wick_mult=1.6):
    random.seed(seed)
    bars=[]; t0=1_700_000_000_000
    per_year = 365*24*3600/tf_sec
    base = ann_vol/math.sqrt(per_year)
    p=price; prev=0.0; h2=1.0
    for i in range(n):
        hour = ((i*tf_sec)//3600) % 24
        def bump(cn,w,a): return a*math.exp(-((hour-cn)**2)/(2*w*w))
        vshape = .25 + bump(8,1.6,1.0) + bump(13.5,1.8,1.6) + bump(15,1.0,.7) + bump(20,1.2,.4)
        act = 0.6 + 0.9*vshape
        # volatility clustering
        z = max(-8.0, min(8.0, prev/max(base,1e-12)))   # clamp: the GARCH feedback
        h2 = (1-vol_persist-vol_shock) + vol_persist*h2 + vol_shock*z*z
        h2 = max(0.05, min(h2, 25.0))
        sig = base*math.sqrt(max(h2,.05))*act
        # momentum persistence: returns are autocorrelated, so swings extend
        shock = random.gauss(0, sig)
        ret = phi*prev + math.sqrt(max(1-phi*phi,0))*shock
        ret = max(-0.08, min(0.08, ret))            # a single bar cannot move 8%
        prev = ret
        o=p; cl=o*math.exp(ret)
        # wicks proportional to the bar's own move, not independent noise
        # Wick size drives how much consecutive bar RANGES overlap, which is
        # what decides FVG frequency. v2 used wicks ~0.55x body and produced a
        # qualifying gap every 3 bars against a realistic 15-30. wick_mult is
        # calibrated below so gap density matches a real chart.
        body=abs(cl-o)
        wick=(body+o*sig*.6)*abs(random.gauss(0,wick_mult))
        hi=max(o,cl)+wick*random.random()
        lo=min(o,cl)-wick*random.random()
        v=max(1.0, vshape*1000*random.lognormvariate(0,.45))
        bars.append((t0+i*tf_sec*1000,o,hi,lo,cl,v))
        p=cl
    return bars


def series_regime(n, tf_sec, seed=1, price=4400.0, ann_vol=0.16,
                  vol_persist=0.94, vol_shock=0.06, wick_mult=1.6,
                  mean_range=220, mean_trend=70, trend_k=0.19):
    """OHLCV with REGIMES — the property `series` lacks and real markets have.

    WHY THIS EXISTS. `series` uses phi=0.03, so it has essentially no sustained
    directional movement: over 900 simulated days it produced TWO trades in the
    top efficiency-ratio quintile. Every threshold calibrated against it was
    therefore fitted to pure chop, which is exactly how you end up with an engine
    that fires on noise and sits out real moves.

    A Markov chain alternates two states:
      range  mean-reverting toward a slow anchor, so price chops
      trend  a persistent drift of +/- trend_k sigma per bar

    trend_k DEFAULT 0.19 IS CALIBRATED, NOT CHOSEN. It is the value at which a
    BRAIN-DEAD momentum rule (buy if price is up over 20 bars and the move is
    efficient; 1 ATR bracket) earns NO MORE than it does on the driftless
    generator. Parity, not zero: the naive rule scores the stop first on a bar
    that spans both, a constant pessimism worth about -0.15R. The test is in
    null_test.py and MUST be run before believing any result from here.

    THE ORIGINAL DEFAULT OF 0.55 WAS A DISASTER. At that setting the naive rule
    scored +0.214R at t=49.6 on 5m — the data itself paid for trend following. I
    then "discovered" that a regime filter plus trend alignment was worth +0.29R
    and shipped it. It was my own generator's momentum, measured back to me. The
    strategy went negative on the user's real backtest, which is the correct
    result. This is the SECOND time this happened (an earlier version used
    phi=0.82 with the same effect), so the guard is now permanent.

    THE DIRECTION OF EACH TREND IS DRAWN AT RANDOM WHEN THE REGIME STARTS and is
    never knowable in advance, so this adds NO free edge — buy-and-hold remains
    ~0 EV. It can only be exploited by DETECTING a regime after it begins, which
    is precisely what trend following is and precisely what the current engine
    cannot do. Getting this wrong is easy: an earlier generator used phi=0.82,
    which baked a trend-following edge into the data itself and made every
    engine look profitable.
    """
    rng = random.Random(seed)
    bars=[]; t0=1_700_000_000_000
    per_year = 365*24*3600/tf_sec
    base = ann_vol/math.sqrt(per_year)
    p=price; prev=0.0; h2=1.0
    state="range"; left=int(rng.expovariate(1.0/mean_range))+1
    mu=0.0; anchor=price
    for i in range(n):
        if left <= 0:
            if state == "range":
                state="trend"
                left=int(rng.expovariate(1.0/mean_trend))+1
                mu = rng.choice([-1.0, 1.0]) * trend_k      # direction is a coin flip
            else:
                state="range"
                left=int(rng.expovariate(1.0/mean_range))+1
                mu=0.0
                anchor=p
        left -= 1
        hour = ((i*tf_sec)//3600) % 24
        def bump(cn,w,a): return a*math.exp(-((hour-cn)**2)/(2*w*w))
        vshape = .25 + bump(8,1.6,1.0) + bump(13.5,1.8,1.6) + bump(15,1.0,.7) + bump(20,1.2,.4)
        act = 0.6 + 0.9*vshape
        z = max(-8.0, min(8.0, prev/max(base,1e-12)))
        h2 = (1-vol_persist-vol_shock) + vol_persist*h2 + vol_shock*z*z
        h2 = max(0.05, min(h2, 25.0))
        sig = base*math.sqrt(max(h2,.05))*act
        drift = mu*sig if state=="trend" else -0.05*math.log(max(p,1e-9)/max(anchor,1e-9))
        ret = drift + rng.gauss(0, sig)
        ret = max(-0.08, min(0.08, ret))
        prev = ret
        o=p; cl=o*math.exp(ret)
        body=abs(cl-o)
        wick=(body+o*sig*.6)*abs(rng.gauss(0,wick_mult))
        hi=max(o,cl)+wick*rng.random()
        lo=min(o,cl)-wick*rng.random()
        v=max(1.0, vshape*1000*rng.lognormvariate(0,.45))
        bars.append((t0+i*tf_sec*1000,o,hi,lo,cl,v))
        p=cl
    return bars
