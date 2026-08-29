"""Generic adapter for any JSON price API, driven entirely by config."""

from __future__ import annotations

from typing import Iterable

from ..http import HttpError, dig, get_json
from ..models import Listing, parse_price
from .base import Source, SourceError

DEFAULT_FIELDS = {
    "id": "id",
    "title": "title",
    "price": "price",
    "currency": "currency",
    "url": "url",
    "condition": "condition",
    "storage_gb": "storage_gb",
    "seller": "seller",
    "in_stock": "in_stock",
}


class CustomJsonSource(Source):
    """Reads listings from an arbitrary JSON endpoint.

    Settings:
        ``url``          endpoint to call (required)
        ``params``       query-string parameters
        ``headers``      extra request headers (API keys go here)
        ``items_path``   dotted path to the list of items, e.g. ``data.products``
        ``fields``       dotted path per :class:`Listing` field, merged over the
                         defaults, e.g. ``{"price": "price.value"}``
        ``static``       fixed values merged into every listing (e.g. currency)
    """

    type_name = "custom_json"

    def fetch(self) -> Iterable[Listing]:
        url = self._require("url")
        fields = {**DEFAULT_FIELDS, **(self.settings.get("fields") or {})}
        static = self.settings.get("static") or {}
        try:
            payload = get_json(
                url,
                params=self.settings.get("params"),
                headers=self.settings.get("headers"),
                timeout=float(self.settings.get("timeout", 20)),
            )
        except HttpError as exc:
            raise SourceError(f"source '{self.name}': {exc}") from exc

        items = dig(payload, self.settings.get("items_path", ""), default=payload)
        if isinstance(items, dict):
            items = [items]
        if not isinstance(items, list):
            raise SourceError(
                f"source '{self.name}': items_path "
                f"{self.settings.get('items_path')!r} did not resolve to a list"
            )

        listings = []
        for index, item in enumerate(items):
            price = parse_price(dig(item, fields["price"]))
            if price is None:
                continue
            title = str(dig(item, fields["title"], default="") or "")
            in_stock = dig(item, fields["in_stock"], default=static.get("in_stock", True))
            listings.append(
                Listing(
                    source=self.name,
                    listing_id=str(dig(item, fields["id"], default=index)),
                    title=title,
                    price=price,
                    currency=str(dig(item, fields["currency"], default=static.get("currency", "USD"))),
                    url=str(dig(item, fields["url"], default=static.get("url", "")) or ""),
                    condition=str(dig(item, fields["condition"], default=static.get("condition", "")) or ""),
                    storage_gb=dig(item, fields["storage_gb"]),
                    seller=dig(item, fields["seller"], default=static.get("seller")),
                    in_stock=bool(in_stock),
                )
            )
        return listings
