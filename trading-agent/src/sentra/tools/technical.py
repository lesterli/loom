from __future__ import annotations

from math import isnan

from sentra.tools.http import ToolDataError


def compute_rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) <= period:
        return None

    gains: list[float] = []
    losses: list[float] = []
    for previous, current in zip(closes, closes[1:]):
        delta = current - previous
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for gain, loss in zip(gains[period:], losses[period:]):
        avg_gain = ((avg_gain * (period - 1)) + gain) / period
        avg_loss = ((avg_loss * (period - 1)) + loss) / period

    if avg_loss == 0:
        return 100.0

    relative_strength = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + relative_strength))


def compute_ema(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    multiplier = 2.0 / (period + 1)
    ema_values = [values[0]]
    for value in values[1:]:
        ema_values.append((value - ema_values[-1]) * multiplier + ema_values[-1])
    return ema_values


def compute_macd(
    closes: list[float],
    *,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> dict[str, float | str | None]:
    if len(closes) < slow_period:
        return {
            "macd": None,
            "signal": None,
            "histogram": None,
            "signal_bias": "insufficient_data",
        }

    fast = compute_ema(closes, fast_period)
    slow = compute_ema(closes, slow_period)
    macd_line = [fast_value - slow_value for fast_value, slow_value in zip(fast, slow)]
    signal_line = compute_ema(macd_line, signal_period)
    histogram = macd_line[-1] - signal_line[-1]

    if histogram > 0:
        bias = "bullish"
    elif histogram < 0:
        bias = "bearish"
    else:
        bias = "neutral"

    return {
        "macd": macd_line[-1],
        "signal": signal_line[-1],
        "histogram": histogram,
        "signal_bias": bias,
    }


def summarize_technicals(price_points: list[list[float]]) -> dict[str, float | str | None]:
    closes = [float(point[1]) for point in price_points if len(point) >= 2]
    if len(closes) < 30:
        raise ToolDataError("Not enough price points to compute technical indicators")

    rsi = compute_rsi(closes)
    macd = compute_macd(closes)
    latest_close = closes[-1]
    sma_20 = sum(closes[-20:]) / 20
    sma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else None

    trend = "bullish" if latest_close >= sma_20 else "bearish"
    if sma_50 is not None and latest_close >= sma_20 >= sma_50:
        trend = "bullish"
    elif sma_50 is not None and latest_close <= sma_20 <= sma_50:
        trend = "bearish"
    else:
        trend = "mixed"

    return {
        "price_points": len(closes),
        "latest_close": latest_close,
        "rsi_14": None if rsi is None or isnan(rsi) else round(rsi, 4),
        "sma_20": round(sma_20, 4),
        "sma_50": None if sma_50 is None else round(sma_50, 4),
        "macd": None if macd["macd"] is None else round(float(macd["macd"]), 6),
        "macd_signal": None if macd["signal"] is None else round(float(macd["signal"]), 6),
        "macd_histogram": None if macd["histogram"] is None else round(float(macd["histogram"]), 6),
        "macd_bias": macd["signal_bias"],
        "trend_bias": trend,
        "source": "computed_from_coingecko_market_chart",
    }
