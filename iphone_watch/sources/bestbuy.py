"""Best Buy Products API source (official, key-based)."""

from __future__ import annotations

from typing import Iterable

from ..http import HttpError, get_json
from ..models import Listing, parse_price
from .base import Source, SourceError

ENDPOINT = "https://api.bestbuy.com/v1/products"
FIELDS = "sku,name,salePrice,regularPrice,onSale,url,onlineAvailability,manufacturer"


class BestBuySource(Source):
    """Searches Best Buy for new iPhones.

    Settings:
        ``api_key``   Best Buy developer key (required; use ``${BESTBUY_API_KEY}``)
        ``search``    search term, default ``iphone``
        ``page_size`` results per request (max 100)
    """

    type_name = "bestbuy"

    def fetch(self) -> Iterable[Listing]:
        api_key = self._require("api_key")
        search = self.settings.get("search", "iphone")
        # Best Buy's filter syntax: ((search=iphone)&(condition=new))
        query = f"((search={search})&(condition=new))"
        try:
            payload = get_json(
                f"{ENDPOINT}{query}",
                params={
                    "apiKey": api_key,
                    "format": "json",
                    "show": FIELDS,
                    "pageSize": int(self.settings.get("page_size", 100)),
                    "sort": "salePrice.asc",
                },
                timeout=float(self.settings.get("timeout", 25)),
            )
        except HttpError as exc:
            raise SourceError(f"source '{self.name}': {exc}") from exc

        listings = []
        for product in payload.get("products", []):
            price = parse_price(product.get("salePrice") or product.get("regularPrice"))
            if price is None:
                continue
            listings.append(
                Listing(
                    source=self.name,
                    listing_id=str(product.get("sku")),
                    title=str(product.get("name", "")),
                    price=price,
                    currency="USD",
                    url=str(product.get("url", "")),
                    condition="new",
                    seller="Best Buy",
                    in_stock=bool(product.get("onlineAvailability", True)),
                    extra={"regular_price": parse_price(product.get("regularPrice"))},
                )
            )
        return listings
