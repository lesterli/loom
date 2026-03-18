from sentra.nodes import data_fetch as data_fetch_module


def test_data_fetch_collects_real_tool_shapes(monkeypatch) -> None:
    monkeypatch.setattr(data_fetch_module, "resolve_asset_id", lambda asset: "bitcoin")
    monkeypatch.setattr(
        data_fetch_module,
        "fetch_market_snapshot",
        lambda asset, coin_id=None: {
            "asset": asset,
            "coingecko_id": "bitcoin",
            "price": 70000.0,
            "source": "coingecko",
        },
    )
    monkeypatch.setattr(
        data_fetch_module,
        "fetch_market_chart",
        lambda asset, coin_id=None: {
            "coingecko_id": "bitcoin",
            "prices": [[index, 100 + index] for index in range(60)],
        },
    )

    result = data_fetch_module.data_fetch_node({"asset": "BTC"})

    assert result["market_data"]["source"] == "coingecko"
    assert result["resolved_asset_id"] == "bitcoin"
    assert result["technical_data"]["price_points"] == 60
    assert result["news_data"] == []
    assert result["tool_errors"] == []


def test_data_fetch_gracefully_degrades_on_failures(monkeypatch) -> None:
    monkeypatch.setattr(
        data_fetch_module,
        "resolve_asset_id",
        lambda asset: (_ for _ in ()).throw(data_fetch_module.ToolRequestError("search down")),
    )
    monkeypatch.setattr(
        data_fetch_module,
        "fetch_market_snapshot",
        lambda asset, coin_id=None: (_ for _ in ()).throw(data_fetch_module.ToolRequestError("market down")),
    )
    monkeypatch.setattr(
        data_fetch_module,
        "fetch_market_chart",
        lambda asset, coin_id=None: (_ for _ in ()).throw(data_fetch_module.ToolRequestError("chart down")),
    )

    result = data_fetch_module.data_fetch_node({"asset": "BTC"})

    assert result["market_data"]["source"] == "unavailable"
    assert result["technical_data"]["source"] == "unavailable"
    assert "asset_resolution_failed" in result["data_quality_flags"]
    assert "market_data_unavailable" in result["data_quality_flags"]
    assert "technical_data_unavailable" in result["data_quality_flags"]
    assert len(result["tool_errors"]) == 3
