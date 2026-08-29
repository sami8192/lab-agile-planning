"""eBay Browse API source, restricted to brand-new listings."""

from __future__ import annotations

import base64
import time
from typing import Iterable, Optional

from ..http import HttpError, get_json, request
from ..models import Listing, parse_price
from .base import Source, SourceError

TOKEN_URL = "https://api.ebay.com/identity/oauth2/token"
SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
CELL_PHONES_CATEGORY = "9355"
CONDITION_NEW = "1000"


class EbaySource(Source):
    """Searches eBay for new iPhones via the Browse API.

    Needs an eBay developer application (client credentials). Settings:
        ``client_id`` / ``client_secret``   application keys (required)
        ``query``        search term, default ``Apple iPhone``
        ``marketplace``  e.g. ``EBAY_US`` (default), ``EBAY_GB``
        ``limit``        results per page (max 200)
        ``max_price``    server-side price ceiling
    """

    type_name = "ebay"

    def __init__(self, settings: dict):
        super().__init__(settings)
        self._token: Optional[str] = None
        self._token_expires_at: float = 0.0

    def _access_token(self) -> str:
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token
        client_id = self._require("client_id")
        client_secret = self._require("client_secret")
        basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        try:
            raw = request(
                TOKEN_URL,
                method="POST",
                headers={"Authorization": f"Basic {basic}"},
                data={
                    "grant_type": "client_credentials",
                    "scope": "https://api.ebay.com/oauth/api_scope",
                },
            )
        except HttpError as exc:
            raise SourceError(f"source '{self.name}': eBay token request failed: {exc}") from exc
        import json as _json

        payload = _json.loads(raw)
        self._token = payload.get("access_token")
        if not self._token:
            raise SourceError(f"source '{self.name}': eBay returned no access token")
        self._token_expires_at = time.time() + float(payload.get("expires_in", 7200))
        return self._token

    def fetch(self) -> Iterable[Listing]:
        marketplace = self.settings.get("marketplace", "EBAY_US")
        filters = [f"conditionIds:{{{CONDITION_NEW}}}", "buyingOptions:{FIXED_PRICE}"]
        if self.settings.get("max_price"):
            currency = self.settings.get("currency", "USD")
            filters.append(f"price:[..{float(self.settings['max_price'])}],priceCurrency:{currency}")
        try:
            payload = get_json(
                SEARCH_URL,
                params={
                    "q": self.settings.get("query", "Apple iPhone"),
                    "category_ids": self.settings.get("category_id", CELL_PHONES_CATEGORY),
                    "filter": ",".join(filters),
                    "limit": int(self.settings.get("limit", 100)),
                    "sort": "price",
                },
                headers={
                    "Authorization": f"Bearer {self._access_token()}",
                    "X-EBAY-C-MARKETPLACE-ID": marketplace,
                },
                timeout=float(self.settings.get("timeout", 25)),
            )
        except HttpError as exc:
            raise SourceError(f"source '{self.name}': {exc}") from exc

        listings = []
        for item in payload.get("itemSummaries", []) or []:
            price_node = item.get("price") or {}
            price = parse_price(price_node.get("value"))
            if price is None:
                continue
            shipping = 0.0
            for option in item.get("shippingOptions") or []:
                cost = parse_price((option.get("shippingCost") or {}).get("value"))
                if cost:
                    shipping = cost
                    break
            listings.append(
                Listing(
                    source=self.name,
                    listing_id=str(item.get("itemId")),
                    title=str(item.get("title", "")),
                    price=round(price + shipping, 2),
                    currency=str(price_node.get("currency", "USD")),
                    url=str(item.get("itemWebUrl", "")),
                    condition=str(item.get("condition", "")),
                    seller=str((item.get("seller") or {}).get("username", "")) or None,
                    extra={"shipping": shipping},
                )
            )
        return listings
