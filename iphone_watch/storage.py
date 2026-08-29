"""Persistent price history, stored as a single JSON file."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

STATE_VERSION = 1
MAX_HISTORY_POINTS = 60


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds")


def parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


@dataclass
class TrackedListing:
    """Everything we remember about one offer between runs."""

    key: str
    title: str = ""
    url: str = ""
    model: Optional[str] = None
    storage_gb: Optional[int] = None
    currency: str = "USD"
    first_price: float = 0.0
    last_price: float = 0.0
    best_price: float = 0.0
    first_seen: str = ""
    last_seen: str = ""
    last_notified: Optional[str] = None
    last_notified_price: Optional[float] = None
    history: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, key: str, data: dict) -> "TrackedListing":
        known = {f for f in cls.__dataclass_fields__ if f != "key"}
        return cls(key=key, **{k: v for k, v in data.items() if k in known})

    def to_dict(self) -> dict:
        data = asdict(self)
        data.pop("key", None)
        return data

    def record(self, price: float, moment: datetime) -> None:
        stamp = iso(moment)
        if not self.first_seen:
            self.first_seen = stamp
            self.first_price = price
            self.best_price = price
        self.last_price = price
        self.best_price = min(self.best_price, price) if self.best_price else price
        self.last_seen = stamp
        if not self.history or self.history[-1][1] != price:
            self.history.append([stamp, price])
            del self.history[:-MAX_HISTORY_POINTS]


class StateStore:
    """Loads/saves the price history; writes atomically so a crash can't corrupt it."""

    def __init__(self, path: str):
        self.path = Path(path)
        self.listings: dict[str, TrackedListing] = {}
        self.updated_at: Optional[str] = None
        self.load()

    def load(self) -> None:
        if not self.path.is_file():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            # A damaged state file must not stop the watcher; start a fresh history.
            return
        self.updated_at = data.get("updated_at")
        for key, entry in (data.get("listings") or {}).items():
            self.listings[key] = TrackedListing.from_dict(key, entry)

    def get(self, key: str) -> Optional[TrackedListing]:
        return self.listings.get(key)

    def upsert(self, key: str) -> TrackedListing:
        tracked = self.listings.get(key)
        if tracked is None:
            tracked = TrackedListing(key=key)
            self.listings[key] = tracked
        return tracked

    def prune(self, max_age_days: int = 45, now: Optional[datetime] = None) -> int:
        """Forget listings that have not been seen for a while."""
        now = now or utcnow()
        stale = []
        for key, tracked in self.listings.items():
            seen = parse_iso(tracked.last_seen)
            if seen and (now - seen).days > max_age_days:
                stale.append(key)
        for key in stale:
            del self.listings[key]
        return len(stale)

    def save(self) -> None:
        payload = {
            "version": STATE_VERSION,
            "updated_at": iso(utcnow()),
            "listings": {key: tracked.to_dict() for key, tracked in sorted(self.listings.items())},
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle, tmp = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, sort_keys=False)
                fh.write("\n")
            os.replace(tmp, self.path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
