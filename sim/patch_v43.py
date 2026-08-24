"""Build ME Pro v4.3 from v4.2 — volume profile, order flow, no reversal."""
import io, sys, shutil

SRC = "/home/user/Claude/MovementEnginePro.v4.2.pine"
P = "/home/user/Claude/MovementEnginePro.v4.3.pine"
shutil.copy(SRC, P)
src = io.open(P, encoding="utf-8").read()


def sub1(old, new, tag):
    global src
    if src.count(old) != 1:
        sys.exit("PATCH %s: expected 1, found %d" % (tag, src.count(old)))
    src = src.replace(old, new)
    print("  ok  %s" % tag)


# ── INPUTS ─────────────────────────────────────────────────────────────────
sub1(
"""i_minConf    = input.int(0, "Min Confluence Required (0-3)", minval=0, maxval=3,""",
"""i_noReversal = input.bool(true, "No Reversal Trades — only trade WITH the leg",
     tooltip="v4.3: rejects any setup whose direction opposes the leg in progress, where the leg is price now against price i_legLen bars ago.\\n\\nWHAT IT COSTS, measured on 15m over 150 days x 6 seeds. Raw trigger supply falls 45%, from 70.65 events/day to 39.18, and the loss is not spread evenly:\\n\\n  trigger   events/day   reversal   survives\\n  band          28.38        43%      16.22\\n  band2         23.28        54%      10.80\\n  sweep          4.31        35%       2.80\\n  mss            4.23         7%       3.91\\n  fvg            1.75        13%       1.53\\n\\nMSS and FVG barely notice — they are continuation setups already. The band triggers pay almost the whole bill, which is expected: v4.0's own header calls a band rejection 'a REVERSION setup' and hands it the VWAP mean as its first target for that reason.\\n\\nWHAT IT BUYS, and this is the honest part: ON THIS HARNESS, NOTHING MEASURABLE. Splitting the same triggers with the same stop and the same ladder gave continuation SL 39% against reversal SL 38% — identical. Continuation reached the deeper targets more often (TP2 26% vs 20%, TP3 12% vs 9%) and resolved a bar sooner, and that is the whole of the difference.\\n\\nDO NOT READ THAT AS EVIDENCE AGAINST THIS FILTER. The generator's trend_k is CALIBRATED so that a naive momentum rule earns nothing above the driftless case — so a trend-alignment filter is guaranteed to measure flat on it, by construction. The harness cannot answer this question, and saying so is more useful than a number that only looks like an answer.\\n\\nThe supply cost is a COUNT and is real. Whether trading only with the leg is worth it on real gold is a judgement the tester has to settle.",
     group=G_RISK)
i_legLen     = input.int(20, "Leg Lookback (bars)", minval=5, maxval=200,
     tooltip="v4.3: the window the leg is measured over for the no-reversal gate. Price now against price this many bars ago. 20 on 15m is five hours.",
     group=G_RISK)
i_minConf    = input.int(0, "Min Confluence Required (0-3)", minval=0, maxval=3,""",
"non-reversal input")

sub1(
"""i_bandK1     = input.float(1.0, "Band 1 (× volume-weighted σ)", minval=0.5, maxval=4.0, step=0.25, group=G_VWAP)""",
"""i_pocTrig    = input.bool(true, "POC Reclaim Trigger",
     tooltip="v4.3: price closes through the POC having been on the other side of it on the previous bar.\\n\\nThe POC is the single highest-volume price in the profile — the profile's own centre of gravity, and the level most traders agree on. Through v4.2 this engine COMPUTED it and did nothing whatever with it: it was drawn on the chart, published in the alert, offered as a target candidate, and never once allowed to start a trade. The request was that the volume profile should drive signals; this is the profile's most important single level finally doing so.\\n\\nMeasured on 15m over 150 days x 6 seeds: 7.81 events/day raw, of which 6.31 run with the leg and survive the no-reversal gate. That replaces a fifth of the supply that gate removes.\\n\\nIts invalidation is the POC itself — the level whose reclaim defines the setup — so the stop is built the same structural way every other trigger's is.",
     group=G_FRVP)
i_vaMigrate  = input.bool(true, "Value-Area Migration As Direction",
     tooltip="v4.3: replaces a confluence leg that was broken.\\n\\nfrvpBullOk was 'close >= VAL' and frvpBearOk was 'close <= VAH', so BOTH WERE TRUE whenever price sat inside the value area — which is most of the time. A leg that scores for both directions at once is not a directional reading, and v3.5.23's own comment noticed the symptom ('a fully flipped market commonly reads 3/3 against and 1/3 for') without identifying it as the cause.\\n\\nThis substitutes a reading that can only point one way: has the value area itself MOVED? Both edges higher than five bars ago means value is migrating up. That is the profile expressing direction rather than merely position, and it is exactly the volume-profile input the engine was asked for.\\n\\nMeasured at 28.18 events/day on 15m, so it is a near-continuous state — which is why it is a confluence reading and NOT a trigger. Turn it off to restore the v4.2 position test.",
     group=G_FRVP)
i_bandK1     = input.float(1.0, "Band 1 (× volume-weighted σ)", minval=0.5, maxval=4.0, step=0.25, group=G_VWAP)""",
"vp inputs")

sub1(
"""i_cvdReset   = input.bool(false, "Reset CVD Each Session (daily anchor)",""",
"""i_absorb     = input.bool(true, "Absorption As An Order-Flow Reading",
     tooltip="v4.3: heavy participation that produces almost no range — effort without result.\\n\\nWhen relative volume is at least the multiple below and the bar's range is under the ceiling below, size is being traded and price is not moving. Someone is filling into it. Every other order-flow measure in this engine reads the SHAPE of one bar — close position, body conviction — and shape cannot distinguish a quiet bar from a bar where a large seller is being absorbed. This is the one order-flow reading here that measures effort against result rather than the candle's outline.\\n\\nMeasured at 4.85 events/day on 15m. It is added as a SIXTH confluence reading rather than as a trigger or a veto, so it can corroborate a setup without being able to manufacture one. Adding a sixth reading also makes each mode's threshold marginally easier to reach, which deliberately offsets a little of what the no-reversal gate removes.",
     group=G_OF)
i_absorbVol  = input.float(1.5, "  Absorption Min Rel Volume (× avg)", minval=1.0, maxval=5.0, step=0.1, group=G_OF)
i_absorbRng  = input.float(0.6, "  Absorption Max Range (× ATR)", minval=0.1, maxval=2.0, step=0.05, group=G_OF)
i_cvdReset   = input.bool(false, "Reset CVD Each Session (daily anchor)",""",
"absorption inputs")

io.open(P, "w", encoding="utf-8").write(src)
print("\nwrote %d bytes" % len(src))
