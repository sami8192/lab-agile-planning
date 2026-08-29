from datetime import timedelta

import pytest

from iphone_watch.config import AlertRules
from iphone_watch.models import Listing
from iphone_watch.monitor import PriceDrop, build_notifications, detect_drops, money
from iphone_watch.storage import StateStore, utcnow


@pytest.fixture()
def store(tmp_path):
    return StateStore(str(tmp_path / "prices.json"))


def listing(price, listing_id="a", title="Apple iPhone 17 Pro Max 256GB - New", **kwargs):
    return Listing(
        source="demo", listing_id=listing_id, title=title, price=price, url="https://example.com/x", **kwargs
    ).enriched()


RULES = AlertRules(min_drop_percent=2.0, min_drop_amount=10.0, notify_cooldown_hours=12)


def test_first_sighting_is_not_a_drop(store):
    assert detect_drops([listing(1199.0)], store, RULES) == []
    assert store.get("demo:a").best_price == 1199.0


def test_first_sighting_alerts_when_configured(store):
    rules = AlertRules(notify_on_first_seen=True)
    drops = detect_drops([listing(1199.0)], store, rules)
    assert len(drops) == 1 and drops[0].first_seen


def test_price_drop_is_detected(store):
    detect_drops([listing(1199.0)], store, RULES)
    drops = detect_drops([listing(1049.0)], store, RULES)
    assert len(drops) == 1
    drop = drops[0]
    assert drop.previous_price == 1199.0
    assert drop.drop_amount == 150.0
    assert round(drop.drop_percent, 1) == 12.5


def test_small_drops_are_ignored(store):
    detect_drops([listing(1199.0)], store, RULES)
    assert detect_drops([listing(1194.0)], store, RULES) == []      # under min_drop_amount
    assert detect_drops([listing(1180.0)], store, RULES) == []      # under min_drop_percent


def test_price_increase_is_ignored(store):
    detect_drops([listing(1199.0)], store, RULES)
    assert detect_drops([listing(1299.0)], store, RULES) == []


def test_best_baseline_ignores_a_rebound_to_an_earlier_price(store):
    detect_drops([listing(1199.0)], store, RULES)
    detect_drops([listing(999.0)], store, RULES)
    detect_drops([listing(1150.0)], store, RULES)
    # 1099 is below the previous price but above the best price ever seen.
    assert detect_drops([listing(1099.0)], store, RULES) == []
    assert detect_drops([listing(949.0)], store, RULES) != []


def test_last_baseline_alerts_on_any_fall_from_the_previous_price(store):
    rules = AlertRules(baseline="last", notify_cooldown_hours=0)
    detect_drops([listing(1199.0)], store, rules)
    detect_drops([listing(999.0)], store, rules)
    detect_drops([listing(1150.0)], store, rules)
    assert detect_drops([listing(1099.0)], store, rules) != []


def test_cooldown_suppresses_a_repeat_alert(store):
    now = utcnow()
    detect_drops([listing(1199.0)], store, RULES, now=now)
    drops = detect_drops([listing(1049.0)], store, RULES, now=now)
    assert drops
    store.upsert("demo:a").last_notified = store.get("demo:a").last_seen
    store.upsert("demo:a").last_notified_price = 1049.0

    # A tiny further dip inside the cooldown window stays quiet…
    assert detect_drops([listing(1045.0)], store, RULES, now=now + timedelta(hours=1)) == []
    # …but a real further drop still gets through.
    assert detect_drops([listing(899.0)], store, RULES, now=now + timedelta(hours=1)) != []


def test_cooldown_expires(store):
    now = utcnow()
    detect_drops([listing(1199.0)], store, RULES, now=now)
    detect_drops([listing(1049.0)], store, RULES, now=now)
    tracked = store.upsert("demo:a")
    tracked.last_notified = tracked.last_seen
    tracked.last_notified_price = 1049.0
    assert detect_drops([listing(999.0)], store, RULES, now=now + timedelta(hours=13)) != []


def test_drops_are_sorted_by_size(store):
    first = [listing(1199.0, "a"), listing(999.0, "b", title="Apple iPhone Air 256GB - New")]
    detect_drops(first, store, RULES)
    drops = detect_drops(
        [listing(1150.0, "a"), listing(799.0, "b", title="Apple iPhone Air 256GB - New")], store, RULES
    )
    assert [drop.listing.listing_id for drop in drops] == ["b", "a"]


def test_grouped_notification_summarises_every_drop():
    drops = [
        PriceDrop(listing(1049.0, "a"), 1199.0, 150.0, 12.5, 1049.0),
        PriceDrop(listing(899.0, "b", title="Apple iPhone Air 256GB - New"), 999.0, 100.0, 10.0, 899.0),
    ]
    notifications = build_notifications(drops, AlertRules(max_items_per_notification=1))
    assert len(notifications) == 1
    note = notifications[0]
    assert note.title == "2 iPhone price drops (best -12%)"
    assert "iPhone 17 Pro Max 256GB: $1,199 → $1,049 (-12.5%)" in note.message
    assert "…and 1 more" in note.message
    assert note.url == "https://example.com/x"
    assert len(note.data["drops"]) == 2


def test_ungrouped_notifications_are_one_per_drop():
    drops = [PriceDrop(listing(1049.0), 1199.0, 150.0, 12.5, 1049.0)]
    notifications = build_notifications(drops, AlertRules(group_notifications=False))
    assert len(notifications) == 1
    assert notifications[0].title == "iPhone price drop: iPhone 17 Pro Max 256GB"


def test_money_formatting():
    assert money(1199.0, "USD") == "$1,199"
    assert money(1199.5, "EUR") == "€1,199.5"
    assert money(1199.0, "SEK") == "1,199 SEK"
