"""Source registry: maps a config ``type`` onto a Source implementation."""

from __future__ import annotations

from .base import Source, SourceError
from .bestbuy import BestBuySource
from .custom_html import CustomHtmlSource
from .custom_json import CustomJsonSource
from .ebay import EbaySource
from .sample import SampleSource

SOURCE_TYPES: dict[str, type[Source]] = {
    cls.type_name: cls
    for cls in (SampleSource, CustomJsonSource, CustomHtmlSource, BestBuySource, EbaySource)
}


def build_source(settings: dict) -> Source:
    """Instantiate the source described by a ``sources[]`` config entry."""
    type_name = str(settings.get("type", "")).lower()
    try:
        cls = SOURCE_TYPES[type_name]
    except KeyError:
        raise SourceError(
            f"unknown source type {type_name!r}; available: {', '.join(sorted(SOURCE_TYPES))}"
        ) from None
    return cls(settings)


__all__ = ["Source", "SourceError", "SOURCE_TYPES", "build_source"]
