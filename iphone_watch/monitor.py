"""Orchestration: fetch listings, apply the rules, detect drops, push alerts."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Iterable, Optional, Sequence

from .config import AlertRules, Config
from .filters import Rejection, split
from .models import Listing
from .notifiers import Notification, Notifier, NotifierError, build_notifier
from .sources import Source, SourceError, build_source
from .storage import StateStore, TrackedListing, iso, parse_iso, utcnow

log = logging.getLogger("iphone_watch")

CURRENCY_SYMBOLS = {"USD": "$", "EUR": "€", "GBP": "£", "CAD": "C$", "AUD": "A$", "JPY": "¥"}


def money(amount: float, currency: str = "USD") -> str:
    symbol = CURRENCY_SYMBOLS.get((currency or "").upper())
    formatted = f"{amount:,.2f}".rstrip("0").rstrip(".")
    return f"{symbol}{formatted}" if symbol else f"{formatted} {currency}".strip()


@dataclass
class PriceDrop:
    """A qualifying price decrease for one tracked listing."""

    listing: Listing
    previous_price: float
    drop_amount: float
    drop_percent: float
    best_price: float
    first_seen: bool = False

    @property
    def headline(self) -> str:
        if self.first_seen:
            return f"{self.listing.label} at {money(self.listing.price, self.listing.currency)}"
        return (
            f"{self.listing.label}: {money(self.previous_price, self.listing.currency)}"
            f" → {money(self.listing.price, self.listing.currency)}"
            f" (-{self.drop_percent:.1f}%)"
        )

    def detail(self) -> str:
        bits = [f"• {self.headline}"]
        if self.listing.seller:
            bits.append(f"  at {self.listing.seller}")
        if self.listing.url:
            bits.append(f"  {self.listing.url}")
        return "\n".join(bits)


@dataclass
class RunResult:
    """What one pass of the watcher did."""

    fetched: int = 0
    eligible: int = 0
    drops: list[PriceDrop] = field(default_factory=list)
    rejections: list[Rejection] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    notified: bool = False

    @property
    def ok(self) -> bool:
        return not self.errors


def collect(sources: Sequence[Source], result: RunResult) -> list[Listing]:
    """Fetch from every source, recording (but not raising) per-source failures."""
    listings: list[Listing] = []
    for source in sources:
        try:
            fetched = list(source.fetch())
        except SourceError as exc:
            result.errors.append(str(exc))
            log.warning("source %s failed: %s", source.name, exc)
            continue
        except Exception as exc:  # pragma: no cover - defensive: one bad source
            result.errors.append(f"source '{source.name}' raised {exc.__class__.__name__}: {exc}")
            log.exception("source %s crashed", source.name)
            continue
        log.info("source %s returned %d listing(s)", source.name, len(fetched))
        listings.extend(fetched)
    result.fetched = len(listings)
    return listings


def _cooldown_blocks(tracked: TrackedListing, price: float, rules: AlertRules, now: datetime) -> bool:
    """True when we already alerted recently and the price has not fallen further."""
    last = parse_iso(tracked.last_notified)
    if last is None:
        return False
    if now - last >= timedelta(hours=rules.notify_cooldown_hours):
        return False
    previous = tracked.last_notified_price
    if previous is None:
        return True
    further = previous - price
    return not (further >= rules.min_drop_amount and previous > 0 and further / previous * 100 >= rules.min_drop_percent)


def detect_drops(
    listings: Iterable[Listing],
    store: StateStore,
    rules: AlertRules,
    now: Optional[datetime] = None,
) -> list[PriceDrop]:
    """Compare each listing against its history and return the alert-worthy falls."""
    now = now or utcnow()
    drops: list[PriceDrop] = []
    for listing in listings:
        tracked = store.get(listing.key)
        known = tracked is not None and bool(tracked.last_seen)
        entry = store.upsert(listing.key)
        baseline = None
        if known:
            baseline = entry.best_price if rules.baseline == "best" else entry.last_price

        drop: Optional[PriceDrop] = None
        if not known:
            if rules.notify_on_first_seen:
                drop = PriceDrop(listing, listing.price, 0.0, 0.0, listing.price, first_seen=True)
        elif baseline and listing.price < baseline:
            amount = round(baseline - listing.price, 2)
            percent = amount / baseline * 100
            if amount >= rules.min_drop_amount and percent >= rules.min_drop_percent:
                drop = PriceDrop(listing, baseline, amount, percent, min(entry.best_price, listing.price))

        if drop is not None and _cooldown_blocks(entry, listing.price, rules, now):
            log.info("suppressing alert for %s (cooldown)", listing.key)
            drop = None

        entry.title = listing.title
        entry.url = listing.url or entry.url
        entry.model = listing.model
        entry.storage_gb = listing.storage_gb
        entry.currency = listing.currency
        entry.record(listing.price, now)

        if drop is not None:
            drops.append(drop)

    drops.sort(key=lambda d: (-d.drop_percent, d.listing.price))
    return drops


def mark_notified(store: StateStore, drops: Sequence[PriceDrop], now: Optional[datetime] = None) -> None:
    """Stamp the cooldown clock — only after a push actually went out."""
    now = now or utcnow()
    for drop in drops:
        entry = store.upsert(drop.listing.key)
        entry.last_notified = iso(now)
        entry.last_notified_price = drop.listing.price


def build_notifications(drops: Sequence[PriceDrop], rules: AlertRules) -> list[Notification]:
    """Turn drops into one grouped push, or one push per drop."""
    if not drops:
        return []
    if not rules.group_notifications:
        return [
            Notification(
                title=f"iPhone price drop: {drop.listing.label}",
                message=drop.detail(),
                url=drop.listing.url or None,
                priority="high",
                data={"drops": [_as_dict(drop)]},
            )
            for drop in drops
        ]

    shown = list(drops)[: max(1, rules.max_items_per_notification)]
    hidden = len(drops) - len(shown)
    best = drops[0]
    if len(drops) == 1:
        title = f"iPhone price drop: {best.listing.label}"
    else:
        # Floor the headline percentage so the number is never rounded up.
        title = f"{len(drops)} iPhone price drops (best -{int(best.drop_percent)}%)"
    lines = [drop.detail() for drop in shown]
    if hidden > 0:
        lines.append(f"…and {hidden} more")
    return [
        Notification(
            title=title,
            message="\n".join(lines),
            url=best.listing.url or None,
            priority="high",
            data={"drops": [_as_dict(drop) for drop in drops]},
        )
    ]


def _as_dict(drop: PriceDrop) -> dict:
    return {
        "key": drop.listing.key,
        "title": drop.listing.title,
        "model": drop.listing.model,
        "storage_gb": drop.listing.storage_gb,
        "screen_inches": drop.listing.screen_inches,
        "price": drop.listing.price,
        "previous_price": drop.previous_price,
        "drop_amount": drop.drop_amount,
        "drop_percent": round(drop.drop_percent, 2),
        "currency": drop.listing.currency,
        "url": drop.listing.url,
        "seller": drop.listing.seller,
        "source": drop.listing.source,
        "first_seen": drop.first_seen,
    }


def dispatch(notifiers: Sequence[Notifier], notifications: Sequence[Notification], result: RunResult) -> None:
    """Send every notification through every notifier, collecting failures."""
    for notification in notifications:
        for notifier in notifiers:
            try:
                notifier.send(notification)
                result.notified = True
                log.info("sent %r via %s", notification.title, notifier.name)
            except NotifierError as exc:
                result.errors.append(str(exc))
                log.error("notifier %s failed: %s", notifier.name, exc)
            except Exception as exc:  # pragma: no cover - defensive
                result.errors.append(f"notifier '{notifier.name}' raised {exc.__class__.__name__}: {exc}")
                log.exception("notifier %s crashed", notifier.name)


def run_once(
    config: Config,
    *,
    dry_run: bool = False,
    store: Optional[StateStore] = None,
    now: Optional[datetime] = None,
) -> RunResult:
    """One full pass: fetch → filter → diff → notify → persist."""
    result = RunResult()
    store = store or StateStore(config.state_file)
    sources = [build_source(entry) for entry in config.sources]

    listings = collect(sources, result)
    eligible, rejections = split(listings, config.criteria)
    result.eligible = len(eligible)
    result.rejections = rejections
    log.info("%d/%d listing(s) match the criteria", len(eligible), len(listings))

    drops = detect_drops(eligible, store, config.alerts, now=now)
    result.drops = drops

    if dry_run:
        return result

    if drops:
        notifiers = [build_notifier(entry) for entry in config.notifiers]
        dispatch(notifiers, build_notifications(drops, config.alerts), result)
        if not result.notified:
            # Every notifier failed. Leave the state file untouched so the next
            # run sees the same drop again instead of silently swallowing it.
            log.error("no notification could be delivered; state not updated so the alert is retried")
            return result
        mark_notified(store, drops, now=now)

    store.prune()
    store.save()
    return result
