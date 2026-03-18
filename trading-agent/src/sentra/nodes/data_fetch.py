from sentra.state import TradingState


def data_fetch_node(state: TradingState) -> TradingState:
    asset = state.get("asset", "BTC")
    market_data = {
        "asset": asset,
        "price": 68500.0 if asset == "BTC" else 3550.0,
        "change_24h_pct": 1.8,
        "change_7d_pct": 4.2,
        "change_30d_pct": 9.6,
        "volume_24h": 24_000_000_000,
    }
    news_data = [
        {
            "headline": f"{asset} sentiment remains constructive in stub scenario",
            "sentiment": "positive",
        }
    ]
    technical_data = {
        "rsi_14": 58.0,
        "macd_signal": "bullish",
    }
    return {
        "market_data": market_data,
        "news_data": news_data,
        "onchain_data": {"status": "not_used_in_phase_1"},
        "technical_data": technical_data,
        "data_quality_flags": [],
        "tool_errors": [],
    }
