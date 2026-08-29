"""Minimal HTTP helper built on the standard library (no third-party deps)."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

USER_AGENT = "iphone-price-watch/1.0 (+https://github.com/sami8192/lab-agile-planning)"


class HttpError(RuntimeError):
    """Any non-recoverable HTTP failure, with the status code when known."""

    def __init__(self, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.status = status


def request(
    url: str,
    *,
    method: str = "GET",
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    data: Any = None,
    json_body: Any = None,
    timeout: float = 20.0,
    retries: int = 2,
    backoff: float = 1.5,
) -> str:
    """Perform an HTTP request and return the body as text.

    Retries on 429/5xx and transport errors with exponential backoff, which is
    what most retailer APIs need to survive an unattended schedule.
    """
    if params:
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        url = f"{url}{'&' if '?' in url else '?'}{query}"

    body: Optional[bytes]
    request_headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}
    if json_body is not None:
        body = json.dumps(json_body).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    elif isinstance(data, dict):
        body = urllib.parse.urlencode(data).encode("utf-8")
        request_headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif isinstance(data, str):
        body = data.encode("utf-8")
    else:
        body = data
    request_headers.update(headers or {})

    last_error: Optional[Exception] = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=body, headers=request_headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(charset, errors="replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:400]
            if exc.code in (408, 429) or exc.code >= 500:
                last_error = HttpError(f"HTTP {exc.code} from {url}: {detail}", exc.code)
            else:
                raise HttpError(f"HTTP {exc.code} from {url}: {detail}", exc.code) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = HttpError(f"network error for {url}: {exc}")
        if attempt < retries:
            time.sleep(backoff * (2 ** attempt))
    raise last_error or HttpError(f"request to {url} failed")


def get_json(url: str, **kwargs) -> Any:
    """GET a URL and parse the response as JSON."""
    text = request(url, **kwargs)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise HttpError(f"expected JSON from {url}, got: {text[:200]!r}") from exc


def dig(data: Any, path: str, default: Any = None) -> Any:
    """Look up a dotted path such as ``results.0.price.value`` in nested data."""
    if not path:
        return data
    current = data
    for part in path.split("."):
        if isinstance(current, list):
            try:
                current = current[int(part)]
                continue
            except (ValueError, IndexError):
                return default
        if isinstance(current, dict) and part in current:
            current = current[part]
            continue
        return default
    return current
