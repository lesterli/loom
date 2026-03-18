from sentra.state import TradingState
from sentra.tools.http import ToolDataError, ToolRequestError
from sentra.tools.market import fetch_market_chart, fetch_market_snapshot, resolve_asset_id
from sentra.tools.technical import summarize_technicals


def data_fetch_node(state: TradingState) -> TradingState:
    asset = state.get("asset", "BTC")
    tool_errors: list[str] = []
    data_quality_flags: list[str] = []

    market_data: dict[str, object] = {}
    technical_data: dict[str, object] = {}
    resolved_asset_id = ""

    try:
        resolved_asset_id = resolve_asset_id(asset)
    except (ToolDataError, ToolRequestError) as exc:
        tool_errors.append(f"asset_resolution:{exc}")
        data_quality_flags.append("asset_resolution_failed")

    if resolved_asset_id:
        try:
            market_data = fetch_market_snapshot(asset, coin_id=resolved_asset_id)
            resolved_asset_id = resolved_asset_id or str(market_data.get("coingecko_id", ""))
        except (ToolDataError, ToolRequestError) as exc:
            tool_errors.append(f"market:{exc}")
            data_quality_flags.append("market_data_unavailable")

        try:
            market_chart = fetch_market_chart(asset, coin_id=resolved_asset_id)
            resolved_asset_id = resolved_asset_id or str(market_chart.get("coingecko_id", ""))
            technical_data = summarize_technicals(market_chart["prices"])
        except (ToolDataError, ToolRequestError) as exc:
            tool_errors.append(f"technical:{exc}")
            data_quality_flags.append("technical_data_unavailable")
    else:
        tool_errors.append("market:skipped because asset resolution failed")
        tool_errors.append("technical:skipped because asset resolution failed")
        data_quality_flags.append("market_data_unavailable")
        data_quality_flags.append("technical_data_unavailable")

    if not market_data:
        market_data = {
            "asset": asset.upper(),
            "source": "unavailable",
        }
    if not technical_data:
        technical_data = {
            "source": "unavailable",
            "macd_bias": "unknown",
            "trend_bias": "unknown",
        }

    return {
        "market_data": market_data,
        "news_data": [],
        "onchain_data": {"status": "deferred_in_phase_2"},
        "technical_data": technical_data,
        "resolved_asset_id": resolved_asset_id,
        "data_quality_flags": data_quality_flags,
        "tool_errors": tool_errors,
    }
