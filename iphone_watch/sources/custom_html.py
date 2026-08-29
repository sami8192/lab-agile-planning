"""Product-page source: reads schema.org data, then falls back to a regex."""

from __future__ import annotations

import html
import json
import re
from typing import Any, Iterable, Optional

from ..http import HttpError, request
from ..models import Listing, parse_price
from .base import Source, SourceError

_JSONLD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
_META_RE = re.compile(
    r'<meta[^>]+(?:property|name)=["\']([^"\']+)["\'][^>]+content=["\']([^"\']*)["\']',
    re.IGNORECASE,
)
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def _walk(node: Any) -> Iterable[dict]:
    """Yield every dict inside an arbitrarily nested JSON-LD blob."""
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value)


def _first_offer(document: str) -> Optional[dict]:
    """Find the first schema.org Offer with a price in a product page."""
    for block in _JSONLD_RE.findall(document):
        try:
            data = json.loads(html.unescape(block.strip()))
        except json.JSONDecodeError:
            continue
        for node in _walk(data):
            types = node.get("@type")
            types = [types] if isinstance(types, str) else (types or [])
            if any(str(t).lower() in ("offer", "aggregateoffer") for t in types) and (
                node.get("price") is not None or node.get("lowPrice") is not None
            ):
                return node
    return None


class CustomHtmlSource(Source):
    """Watches a single product page.

    Prefers the page's own schema.org/JSON-LD offer data (stable and intended
    for machines); falls back to ``price_regex`` when a site does not publish it.

    Settings:
        ``url``           product page (required)
        ``title``         override the product title (recommended: it drives the
                          model / storage / screen-size checks)
        ``price_regex``   regex whose first group is the price
        ``carrier``       ``unlocked``/``t-mobile``/… when the page does not say
        ``currency``      currency code when the page does not state one
        ``headers``       extra request headers
    """

    type_name = "custom_html"

    def fetch(self) -> Iterable[Listing]:
        url = self._require("url")
        try:
            document = request(
                url,
                headers={"Accept": "text/html,application/xhtml+xml", **(self.settings.get("headers") or {})},
                timeout=float(self.settings.get("timeout", 25)),
            )
        except HttpError as exc:
            raise SourceError(f"source '{self.name}': {exc}") from exc

        metas = {key.lower(): value for key, value in _META_RE.findall(document)}
        offer = _first_offer(document) or {}

        price = parse_price(offer.get("price") if offer.get("price") is not None else offer.get("lowPrice"))
        if price is None:
            price = parse_price(metas.get("product:price:amount") or metas.get("og:price:amount"))
        if price is None and self.settings.get("price_regex"):
            match = re.search(self.settings["price_regex"], document, re.IGNORECASE | re.DOTALL)
            if match:
                price = parse_price(match.group(1) if match.groups() else match.group(0))
        if price is None:
            raise SourceError(
                f"source '{self.name}': no price found on {url} — "
                "set 'price_regex' for this page"
            )

        title = self.settings.get("title")
        if not title:
            title_match = _TITLE_RE.search(document)
            title = html.unescape(title_match.group(1)).strip() if title_match else url
            title = re.sub(r"\s+", " ", metas.get("og:title", title))

        availability = str(offer.get("availability", "")).lower()
        in_stock = self.settings.get("in_stock")
        if in_stock is None:
            in_stock = "outofstock" not in availability.replace("_", "")

        currency = (
            offer.get("priceCurrency")
            or metas.get("product:price:currency")
            or self.settings.get("currency", "USD")
        )
        return [
            Listing(
                source=self.name,
                listing_id=str(self.settings.get("id") or url),
                title=title,
                price=price,
                currency=str(currency),
                url=url,
                condition=str(self.settings.get("condition") or offer.get("itemCondition") or title),
                storage_gb=self.settings.get("storage_gb"),
                model=self.settings.get("model"),
                seller=self.settings.get("seller"),
                carrier=self.settings.get("carrier"),
                in_stock=bool(in_stock),
            )
        ]
