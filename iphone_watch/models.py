"""Domain objects: iPhone catalog, listing records and text parsing helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

# Display size (inches) per iPhone model. Used to decide what counts as a
# "large screen" phone without having to trust a retailer's own wording.
IPHONE_SCREEN_INCHES: dict[str, float] = {
    "iPhone 13 mini": 5.4,
    "iPhone 13": 6.1,
    "iPhone 13 Pro": 6.1,
    "iPhone 13 Pro Max": 6.7,
    "iPhone 14": 6.1,
    "iPhone 14 Plus": 6.7,
    "iPhone 14 Pro": 6.1,
    "iPhone 14 Pro Max": 6.7,
    "iPhone 15": 6.1,
    "iPhone 15 Plus": 6.7,
    "iPhone 15 Pro": 6.1,
    "iPhone 15 Pro Max": 6.7,
    "iPhone 16e": 6.1,
    "iPhone 16": 6.1,
    "iPhone 16 Plus": 6.7,
    "iPhone 16 Pro": 6.3,
    "iPhone 16 Pro Max": 6.9,
    "iPhone 17": 6.3,
    "iPhone Air": 6.5,
    "iPhone 17 Pro": 6.3,
    "iPhone 17 Pro Max": 6.9,
}

# Longest names first so "iPhone 16 Pro Max" wins over "iPhone 16 Pro".
_MODELS_BY_LENGTH = sorted(IPHONE_SCREEN_INCHES, key=len, reverse=True)

_STORAGE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(TB|GB)\b", re.IGNORECASE)
_SCREEN_RE = re.compile(r"(\d\.\d)\s*(?:-|\s)?(?:inch|in\b|\")", re.IGNORECASE)
_PRICE_RE = re.compile(r"(\d[\d.,]*)")

# Words retailers use for anything that is not a brand-new, sealed unit.
_NON_NEW_MARKERS = (
    "refurb",
    "renewed",
    "pre-owned",
    "preowned",
    "used",
    "open box",
    "open-box",
    "openbox",
    "certified pre",
    "excellent condition",
    "good condition",
    "seller refurbished",
)


def normalize_model(text: str) -> Optional[str]:
    """Return the canonical iPhone model name mentioned in ``text``."""
    if not text:
        return None
    # Collapse whitespace so "iPhone  16   Pro" still matches.
    haystack = re.sub(r"\s+", " ", text)
    lowered = haystack.lower()
    for model in _MODELS_BY_LENGTH:
        idx = lowered.find(model.lower())
        if idx == -1:
            continue
        end = idx + len(model)
        # Reject partial matches such as "iPhone 16" inside "iPhone 16e".
        if end < len(haystack) and haystack[end].isalnum():
            continue
        return model
    return None


def parse_storage_gb(text: str) -> Optional[int]:
    """Extract a storage capacity in GB from free-form text."""
    if not text:
        return None
    best: Optional[int] = None
    for amount, unit in _STORAGE_RE.findall(text):
        value = float(amount)
        gigabytes = int(value * 1024) if unit.upper() == "TB" else int(value)
        # Ignore RAM-sized numbers that occasionally appear in titles.
        if gigabytes < 32:
            continue
        if best is None or gigabytes > best:
            best = gigabytes
    return best


def parse_screen_inches(text: str) -> Optional[float]:
    """Extract a display size in inches from free-form text."""
    if not text:
        return None
    match = _SCREEN_RE.search(text)
    if not match:
        return None
    inches = float(match.group(1))
    return inches if 4.0 <= inches <= 8.0 else None


def parse_price(value) -> Optional[float]:
    """Coerce a price given as a number or a string like ``"$1,199.00"``."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    match = _PRICE_RE.search(str(value))
    if not match:
        return None
    raw = match.group(1)
    # "1.199,00" (EU) vs "1,199.00" (US): the last separator is the decimal one.
    if "," in raw and "." in raw:
        raw = raw.replace(",", "") if raw.rfind(".") > raw.rfind(",") else raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        raw = raw.replace(",", ".") if len(raw.split(",")[-1]) == 2 else raw.replace(",", "")
    try:
        return round(float(raw), 2)
    except ValueError:
        return None


def normalize_condition(text: Optional[str]) -> str:
    """Map a retailer's condition wording onto ``new`` / ``refurbished`` / ``used``."""
    if not text:
        return "unknown"
    lowered = text.lower()
    for marker in _NON_NEW_MARKERS:
        if marker in lowered:
            if "refurb" in marker or "renewed" in marker or "certified pre" in marker:
                return "refurbished"
            return "used"
    if "new" in lowered:
        return "new"
    return "unknown"


@dataclass(frozen=True)
class Listing:
    """One offer for one phone, as returned by a source."""

    source: str
    listing_id: str
    title: str
    price: float
    currency: str = "USD"
    url: str = ""
    condition: str = "unknown"
    model: Optional[str] = None
    storage_gb: Optional[int] = None
    screen_inches: Optional[float] = None
    seller: Optional[str] = None
    in_stock: bool = True
    extra: dict = field(default_factory=dict)

    @property
    def key(self) -> str:
        """Stable identity used to track this offer's price across runs."""
        return f"{self.source}:{self.listing_id}"

    @property
    def label(self) -> str:
        parts = [self.model or self.title]
        if self.storage_gb:
            parts.append(f"{self.storage_gb}GB" if self.storage_gb < 1024 else f"{self.storage_gb // 1024}TB")
        return " ".join(parts)

    def enriched(self) -> "Listing":
        """Fill in model/storage/screen/condition from the title where missing."""
        model = self.model or normalize_model(self.title)
        storage = self.storage_gb or parse_storage_gb(self.title)
        screen = self.screen_inches
        if screen is None and model:
            screen = IPHONE_SCREEN_INCHES.get(model)
        if screen is None:
            screen = parse_screen_inches(self.title)
        condition = self.condition
        if condition in ("", "unknown", None):
            condition = normalize_condition(self.title)
        else:
            condition = normalize_condition(condition)
        return Listing(
            source=self.source,
            listing_id=self.listing_id,
            title=self.title,
            price=self.price,
            currency=self.currency,
            url=self.url,
            condition=condition,
            model=model,
            storage_gb=storage,
            screen_inches=screen,
            seller=self.seller,
            in_stock=self.in_stock,
            extra=dict(self.extra),
        )
