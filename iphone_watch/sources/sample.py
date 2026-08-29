"""Offline source backed by a JSON fixture — used for demos and tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from ..models import Listing, parse_price
from .base import Source, SourceError

DEFAULT_FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "sample_listings.json"


class SampleSource(Source):
    """Reads listings from a local JSON file instead of the network.

    Settings:
        ``path``            fixture to read (defaults to the bundled sample)
        ``price_delta``     amount added to every price, for trying out alerts
    """

    type_name = "sample"

    def fetch(self) -> Iterable[Listing]:
        path = Path(self.settings.get("path") or DEFAULT_FIXTURE)
        if not path.is_file():
            raise SourceError(f"sample fixture not found: {path}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SourceError(f"sample fixture {path} is not valid JSON: {exc}") from exc
        items = raw.get("listings", raw) if isinstance(raw, dict) else raw
        delta = float(self.settings.get("price_delta", 0) or 0)
        listings = []
        for index, item in enumerate(items):
            price = parse_price(item.get("price"))
            if price is None:
                continue
            listings.append(
                Listing(
                    source=self.name,
                    listing_id=str(item.get("id", index)),
                    title=item.get("title", ""),
                    price=round(max(price + delta, 0.0), 2),
                    currency=item.get("currency", "USD"),
                    url=item.get("url", ""),
                    condition=item.get("condition", ""),
                    model=item.get("model"),
                    storage_gb=item.get("storage_gb"),
                    seller=item.get("seller"),
                    in_stock=bool(item.get("in_stock", True)),
                )
            )
        return listings
