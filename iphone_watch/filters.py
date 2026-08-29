"""Eligibility rules: new, large screen, and enough storage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from .config import Criteria
from .models import Listing, carrier_label


@dataclass(frozen=True)
class Rejection:
    """Why a listing was dropped — surfaced by ``check --explain``."""

    listing: Listing
    reason: str


def _matches_any(model: Optional[str], names: Iterable[str]) -> bool:
    if not model:
        return False
    lowered = model.lower()
    return any(name.lower() in lowered for name in names)


def evaluate(listing: Listing, criteria: Criteria) -> Optional[str]:
    """Return ``None`` if the listing qualifies, else a human-readable reason."""
    if listing.price is None or listing.price <= 0:
        return "no usable price"
    if criteria.currency and listing.currency and listing.currency.upper() != criteria.currency.upper():
        return f"currency {listing.currency} != {criteria.currency}"
    if criteria.conditions and listing.condition not in criteria.conditions:
        return f"condition is {listing.condition}, want {'/'.join(criteria.conditions)}"
    if criteria.require_in_stock and not listing.in_stock:
        return "out of stock"
    if listing.model is None and not criteria.allow_unknown_models:
        return "model not recognised as an iPhone"
    if criteria.models and not _matches_any(listing.model, criteria.models):
        return f"model {listing.model} not in the watch list"
    if criteria.exclude_models and _matches_any(listing.model, criteria.exclude_models):
        return f"model {listing.model} is excluded"
    if listing.storage_gb is None:
        return "storage capacity unknown"
    if listing.storage_gb < criteria.min_storage_gb:
        return f"{listing.storage_gb}GB below the {criteria.min_storage_gb}GB minimum"
    if listing.screen_inches is None:
        if not criteria.allow_unknown_models:
            return "screen size unknown"
    elif listing.screen_inches < criteria.min_screen_inches:
        return f'{listing.screen_inches}" screen below the {criteria.min_screen_inches}" minimum'
    if criteria.require_unlocked:
        if listing.carrier is None:
            if not criteria.allow_unknown_carrier:
                return "carrier lock status not stated"
        elif listing.carrier not in criteria.allowed_carriers:
            return (
                f"locked to {carrier_label(listing.carrier)}; want "
                f"{' or '.join(carrier_label(c) for c in criteria.allowed_carriers)}"
            )
    if criteria.exclude_new_line_offers and listing.needs_new_line:
        return "price requires a new line, port-in or trade-in"
    if criteria.max_price is not None and listing.price > criteria.max_price:
        return f"{listing.price:.2f} above the {criteria.max_price:.2f} price ceiling"
    return None


def split(listings: Iterable[Listing], criteria: Criteria) -> tuple[list[Listing], list[Rejection]]:
    """Partition listings into the ones we watch and the ones we skip."""
    kept: list[Listing] = []
    rejected: list[Rejection] = []
    for raw in listings:
        listing = raw.enriched()
        reason = evaluate(listing, criteria)
        if reason is None:
            kept.append(listing)
        else:
            rejected.append(Rejection(listing, reason))
    return kept, rejected
