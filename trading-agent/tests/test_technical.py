from sentra.tools.technical import compute_macd, compute_rsi, summarize_technicals


def test_compute_rsi_prefers_uptrend() -> None:
    closes = [float(value) for value in range(100, 130)]
    rsi = compute_rsi(closes)
    assert rsi is not None
    assert rsi > 50


def test_compute_macd_returns_bias() -> None:
    closes = [100 + (index * 0.8) for index in range(60)]
    macd = compute_macd(closes)
    assert macd["signal_bias"] in {"bullish", "bearish", "neutral"}


def test_summarize_technicals_from_price_points() -> None:
    price_points = [[index * 86_400_000, 100 + index] for index in range(60)]
    technicals = summarize_technicals(price_points)
    assert technicals["price_points"] == 60
    assert technicals["rsi_14"] is not None
    assert technicals["macd_bias"] in {"bullish", "bearish", "neutral"}
