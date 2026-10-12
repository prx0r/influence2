"""Momentum detection — RSI + trend classification for content performance.

RSI (Welles Wilder, 1978): momentum oscillator 0-100 from the ratio of
average gains to average losses over N periods. Classic thresholds:
  RSI > 70 = overbought (viral peak — expect pullback)
  RSI < 30 = oversold (dead — pivot or kill)
  RSI crossing 50 = trend regime change

Applied to content (not prices):
  - Input series: daily views (or likes, subs) per video or channel
  - Output: RSI value + trend label + divergence flags
  - Use: analytics_review anomaly detection, character_direct evidence,
    release timing (don't launch into a dead channel)

Also includes:
  - EMA (exponential moving average) for smoothing
  - MACD-style signal (fast EMA - slow EMA) for momentum shifts
  - Divergence: views making new highs while RSI doesn't = weakening trend

Pure stdlib. No network. No model calls.
"""
from __future__ import annotations


def rsi(series: list[float], period: int = 14) -> list[float | None]:
    """Wilder's RSI. Returns list same length as series, None where undefined."""
    n = len(series)
    out: list[float | None] = [None] * n
    if n < period + 1:
        return out
    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, n):
        d = series[i] - series[i - 1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    # Wilder's smoothing (SMMA)
    avg_g = sum(gains[:period]) / period
    avg_l = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        if i == period:
            pass  # first value uses SMA above
        else:
            avg_g = (avg_g * (period - 1) + gains[i]) / period
            avg_l = (avg_l * (period - 1) + losses[i]) / period
        if avg_l == 0:
            out[i + 1] = 100.0 if avg_g > 0 else 50.0
        else:
            rs = avg_g / avg_l
            out[i + 1] = round(100 - (100 / (1 + rs)), 2)
    return out


def ema(series: list[float], period: int) -> list[float | None]:
    """Exponential moving average."""
    n = len(series)
    out: list[float | None] = [None] * n
    if n < period or period < 1:
        return out
    k = 2 / (period + 1)
    e = sum(series[:period]) / period
    out[period - 1] = round(e, 2)
    for i in range(period, n):
        e = series[i] * k + e * (1 - k)
        out[i] = round(e, 2)
    return out


def momentum_signal(series: list[float], period: int = 14) -> dict:
    """Full momentum read on a series. Returns current RSI, trend, flags."""
    if len(series) < 3:
        return {"rsi": None, "trend": "insufficient_data", "flags": []}
    r = rsi(series, min(period, len(series) - 1))
    current = next((v for v in reversed(r) if v is not None), None)
    flags: list[str] = []
    if current is None:
        return {"rsi": None, "trend": "insufficient_data", "flags": []}
    # regime
    if current >= 70:
        trend = "overbought"
        flags.append("viral_peak: expect pullback, bank the win, prep follow-up")
    elif current <= 30:
        trend = "oversold"
        flags.append("dead: pivot format or kill, do not double down")
    elif current >= 55:
        trend = "bullish"
    elif current <= 45:
        trend = "bearish"
    else:
        trend = "neutral"
    # momentum shift: compare first-half RSI to second-half
    defined = [v for v in r if v is not None]
    if len(defined) >= 4:
        mid = len(defined) // 2
        early = sum(defined[:mid]) / max(1, mid)
        late = sum(defined[mid:]) / max(1, len(defined) - mid)
        if early < 50 <= late:
            flags.append("bullish_cross: momentum turning up")
        elif early >= 50 > late:
            flags.append("bearish_cross: momentum turning down")
    # divergence: price new high, RSI not
    if len(series) >= 5 and len(defined) >= 5:
        if series[-1] == max(series[-5:]) and defined[-1] < max(defined[-5:-1]):
            flags.append("bearish_divergence: views peaking but momentum fading")
        if series[-1] == min(series[-5:]) and defined[-1] > min(defined[-5:-1]):
            flags.append("bullish_divergence: views bottoming but momentum building")
    return {"rsi": current, "trend": trend, "flags": flags}


def channel_momentum(daily_views: list[float], daily_subs: list[float] | None = None,
                     period: int = 14) -> dict:
    """Channel-level momentum read. Views RSI + optional subs RSI."""
    out = {"views": momentum_signal(daily_views, period)}
    if daily_subs:
        out["subs"] = momentum_signal(daily_subs, period)
    # combined verdict
    vt = out["views"]["trend"]
    if vt in ("overbought",):
        out["verdict"] = "hot: ride it, schedule follow-up within 48h"
    elif vt in ("bullish", "bullish_cross"):
        out["verdict"] = "growing: keep cadence, test adjacent formats"
    elif vt in ("oversold",):
        out["verdict"] = "cold: pause and rethink, do not feed a dead channel"
    elif vt in ("bearish", "bearish_cross"):
        out["verdict"] = "cooling: experiment, one pivot test before deciding"
    else:
        out["verdict"] = "steady: hold cadence"
    return out


def velocity(current: float, previous: float) -> dict:
    """Simple period-over-period velocity for single comparisons."""
    if previous <= 0:
        return {"change_pct": None, "direction": "no_baseline"}
    pct = round((current - previous) / previous * 100, 1)
    direction = "up" if pct > 10 else "down" if pct < -10 else "flat"
    return {"change_pct": pct, "direction": direction}
