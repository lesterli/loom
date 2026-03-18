from sentra.tools import market as market_module


def test_resolve_asset_id_uses_persistent_cache(tmp_path, monkeypatch) -> None:
    cache_dir = tmp_path / ".cache"
    cache_file = cache_dir / "coingecko_asset_ids.json"
    calls: list[str] = []

    monkeypatch.setattr(market_module, "ASSET_CACHE_DIR", cache_dir)
    monkeypatch.setattr(market_module, "ASSET_CACHE_PATH", cache_file)

    def fake_get_json(path: str, *, params: dict[str, str]):
        calls.append(params["query"])
        return market_module.JsonResponse(
            payload={"coins": [{"id": "chainlink"}]},
            status=200,
        )

    monkeypatch.setattr(market_module, "_get_json", fake_get_json)

    first = market_module.resolve_asset_id("LINK")
    second = market_module.resolve_asset_id("link")

    assert first == "chainlink"
    assert second == "chainlink"
    assert calls == ["LINK"]
