from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_TIMEOUT_SECONDS = 10.0


class ToolError(Exception):
    """Base error for external tool failures."""


class ToolConfigError(ToolError):
    """Raised when a tool is not configured for use."""


class ToolRequestError(ToolError):
    """Raised when a remote HTTP call fails."""


class ToolDataError(ToolError):
    """Raised when remote data is malformed or missing."""


@dataclass(frozen=True)
class JsonResponse:
    payload: Any
    status: int


def get_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> JsonResponse:
    query = f"?{urlencode(params)}" if params else ""
    request = Request(
        f"{url}{query}",
        headers={
            "Accept": "application/json",
            "User-Agent": "sentra/0.1",
            **(headers or {}),
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return JsonResponse(payload=json.loads(body), status=response.status)
    except HTTPError as exc:
        raise ToolRequestError(f"{url} returned HTTP {exc.code}") from exc
    except URLError as exc:
        raise ToolRequestError(f"{url} request failed: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise ToolDataError(f"{url} returned invalid JSON") from exc
