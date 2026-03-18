from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from sentra.tools.http import JsonResponse, ToolDataError, get_json

COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
SYMBOL_TO_ID = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
}
PROJECT_ROOT = Path(__file__).resolve().parents[3]
ASSET_CACHE_DIR = PROJECT_ROOT / ".cache"
ASSET_CACHE_PATH = ASSET_CACHE_DIR / "coingecko_asset_ids.json"


def _coingecko_headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    demo_key = os.getenv("COINGECKO_DEMO_API_KEY")
    pro_key = os.getenv("COINGECKO_PRO_API_KEY")
    if demo_key:
        headers["x-cg-demo-api-key"] = demo_key
    if pro_key:
        headers["x-cg-pro-api-key"] = pro_key
    return headers


def _get_json(path: str, *, params: dict[str, Any]) -> JsonResponse:
    return get_json(
        f"{COINGECKO_BASE_URL}{path}",
        params=params,
        headers=_coingecko_headers(),
    )


def _load_asset_cache() -> dict[str, str]:
    if not ASSET_CACHE_PATH.exists():
        return {}
    try:
        with ASSET_CACHE_PATH.open("r", encoding="utf-8") as file:
            payload = json.load(file)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return {
        key: value
        for key, value in payload.items()
        if isinstance(key, str) and isinstance(value, str)
    }


def _store_asset_cache(cache: dict[str, str]) -> None:
    try:
        ASSET_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with ASSET_CACHE_PATH.open("w", encoding="utf-8") as file:
            json.dump(cache, file, indent=2, sort_keys=True)
    except OSError:
        # Cache writes are a quota optimization, not a correctness requirement.
        return


def resolve_asset_id(asset: str) -> str:
    normalized = asset.strip().lower()
    upper = normalized.upper()
    if upper in SYMBOL_TO_ID:
        return SYMBOL_TO_ID[upper]

    cache = _load_asset_cache()
    if normalized in cache:
        return cache[normalized]

    response = _get_json("/search", params={"query": asset})
    coins = response.payload.get("coins", [])
    if not coins:
        raise ToolDataError(f"CoinGecko could not resolve asset '{asset}'")
    coin_id = coins[0]["id"]
    cache[normalized] = coin_id
    _store_asset_cache(cache)
    return coin_id


def fetch_market_snapshot(
    asset: str,
    *,
    vs_currency: str = "usd",
    coin_id: str | None = None,
) -> dict[str, Any]:
    coin_id = coin_id or resolve_asset_id(asset)
    response = _get_json(
        "/coins/markets",
        params={
            "vs_currency": vs_currency,
            "ids": coin_id,
            "price_change_percentage": "24h,7d,30d",
            "precision": "full",
        },
    )
    markets = response.payload
    if not isinstance(markets, list) or not markets:
        raise ToolDataError(f"CoinGecko returned no market data for '{asset}'")

    item = markets[0]
    return {
        "asset": asset.upper(),
        "coingecko_id": coin_id,
        "name": item.get("name", asset.upper()),
        "symbol": item.get("symbol", asset.lower()).upper(),
        "price": item.get("current_price"),
        "market_cap": item.get("market_cap"),
        "market_cap_rank": item.get("market_cap_rank"),
        "volume_24h": item.get("total_volume"),
        "high_24h": item.get("high_24h"),
        "low_24h": item.get("low_24h"),
        "change_24h_pct": item.get("price_change_percentage_24h"),
        "change_7d_pct": item.get("price_change_percentage_7d_in_currency"),
        "change_30d_pct": item.get("price_change_percentage_30d_in_currency"),
        "last_updated": item.get("last_updated"),
        "source": "coingecko",
    }


def fetch_market_chart(
    asset: str,
    *,
    vs_currency: str = "usd",
    days: int = 60,
    coin_id: str | None = None,
) -> dict[str, Any]:
    coin_id = coin_id or resolve_asset_id(asset)
    now = int(time.time())
    from_ts = now - (days * 24 * 60 * 60)
    response = _get_json(
        f"/coins/{coin_id}/market_chart/range",
        params={
            "vs_currency": vs_currency,
            "from": from_ts,
            "to": now,
            "precision": "full",
        },
    )
    payload = response.payload
    prices = payload.get("prices", [])
    if not prices:
        raise ToolDataError(f"CoinGecko returned no price history for '{asset}'")

    return {
        "asset": asset.upper(),
        "coingecko_id": coin_id,
        "prices": prices,
        "market_caps": payload.get("market_caps", []),
        "total_volumes": payload.get("total_volumes", []),
        "source": "coingecko",
    }
