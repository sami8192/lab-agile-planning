import json
from datetime import timedelta

import pytest

from iphone_watch.config import Config, ConfigError, Criteria, expand_env
from iphone_watch.storage import StateStore, iso, parse_iso, utcnow


def test_state_roundtrip(tmp_path):
    path = tmp_path / "nested" / "prices.json"
    store = StateStore(str(path))
    tracked = store.upsert("demo:a")
    tracked.title = "iPhone 17 Pro Max 256GB"
    now = utcnow()
    tracked.record(1199.0, now)
    tracked.record(1099.0, now + timedelta(hours=1))
    store.save()

    reloaded = StateStore(str(path))
    entry = reloaded.get("demo:a")
    assert entry.first_price == 1199.0
    assert entry.last_price == 1099.0
    assert entry.best_price == 1099.0
    assert len(entry.history) == 2


def test_repeated_identical_prices_do_not_grow_history(tmp_path):
    store = StateStore(str(tmp_path / "p.json"))
    tracked = store.upsert("demo:a")
    now = utcnow()
    for offset in range(5):
        tracked.record(1199.0, now + timedelta(hours=offset))
    assert len(tracked.history) == 1


def test_best_price_tracks_the_lowest_value(tmp_path):
    store = StateStore(str(tmp_path / "p.json"))
    tracked = store.upsert("demo:a")
    now = utcnow()
    tracked.record(1199.0, now)
    tracked.record(999.0, now + timedelta(hours=1))
    tracked.record(1299.0, now + timedelta(hours=2))
    assert tracked.best_price == 999.0
    assert tracked.last_price == 1299.0


def test_corrupt_state_file_is_ignored(tmp_path):
    path = tmp_path / "p.json"
    path.write_text("{not json", encoding="utf-8")
    store = StateStore(str(path))
    assert store.listings == {}
    store.upsert("demo:a").record(999.0, utcnow())
    store.save()
    assert json.loads(path.read_text())["listings"]["demo:a"]["last_price"] == 999.0


def test_prune_drops_stale_listings(tmp_path):
    store = StateStore(str(tmp_path / "p.json"))
    now = utcnow()
    store.upsert("demo:fresh").record(999.0, now)
    store.upsert("demo:stale").record(999.0, now - timedelta(days=90))
    assert store.prune(max_age_days=45, now=now) == 1
    assert set(store.listings) == {"demo:fresh"}


def test_parse_iso_handles_missing_and_bad_values():
    assert parse_iso(None) is None
    assert parse_iso("not-a-date") is None
    assert parse_iso(iso(utcnow())) is not None


def test_expand_env(monkeypatch):
    monkeypatch.setenv("NTFY_TOPIC", "secret-topic")
    monkeypatch.delenv("MISSING_VAR", raising=False)
    data = {"topic": "${NTFY_TOPIC}", "server": "${MISSING_VAR:-https://ntfy.sh}", "n": 3, "l": ["${NTFY_TOPIC}"]}
    assert expand_env(data) == {
        "topic": "secret-topic",
        "server": "https://ntfy.sh",
        "n": 3,
        "l": ["secret-topic"],
    }


def test_config_defaults_and_filtering_of_disabled_entries(monkeypatch):
    monkeypatch.setenv("NTFY_TOPIC", "t")
    config = Config.from_dict(
        {
            "sources": [{"type": "sample"}, {"type": "ebay", "enabled": False}],
            "notifiers": [{"type": "ntfy", "topic": "${NTFY_TOPIC}"}],
        }
    )
    assert [s["type"] for s in config.sources] == ["sample"]
    assert config.notifiers[0]["topic"] == "t"
    assert config.criteria.min_screen_inches == 6.5
    assert config.criteria.min_storage_gb == 256
    assert config.criteria.conditions == ("new",)
    assert config.alerts.baseline == "best"


@pytest.mark.parametrize(
    "data,message",
    [
        ({"sources": [], "notifiers": [{"type": "ntfy"}]}, "sources"),
        ({"sources": [{"type": "sample"}], "notifiers": []}, "notifiers"),
        ({"sources": [{"name": "x"}], "notifiers": [{"type": "ntfy"}]}, "type"),
        (
            {"sources": [{"type": "sample"}], "notifiers": [{"type": "ntfy"}], "alerts": {"baseline": "nope"}},
            "baseline",
        ),
    ],
)
def test_invalid_configs_are_rejected(data, message):
    with pytest.raises(ConfigError) as excinfo:
        Config.from_dict(data)
    assert message in str(excinfo.value)


def test_load_reports_a_missing_file(tmp_path):
    with pytest.raises(ConfigError):
        Config.load(str(tmp_path / "nope.json"))


def test_example_config_is_loadable():
    config = Config.load("config.example.json")
    assert config.criteria.min_storage_gb == 256
    assert config.criteria.min_screen_inches == 6.5
    assert any(source["type"] == "sample" for source in config.sources)


def test_criteria_from_dict_lowercases_conditions():
    criteria = Criteria.from_dict({"conditions": ["New", "REFURBISHED"]})
    assert criteria.conditions == ("new", "refurbished")
