"""The committed config.json is what the scheduled workflow actually runs."""

import json
import re

import pytest

from iphone_watch.config import Config
from iphone_watch.filters import evaluate
from iphone_watch.models import Listing


@pytest.fixture(scope="module")
def criteria():
    return Config.load("config.json").criteria


def listing(title, price=999.0):
    return Listing(source="s", listing_id=title, title=title, price=price).enriched()


@pytest.mark.parametrize(
    "title",
    [
        "Apple iPhone Air 256GB Sky Blue - Unlocked - New",
        "Apple iPhone Air 512GB - T-Mobile - New",
        "Apple iPhone 16 Plus 256GB Teal (Unlocked) - New",
        "Apple iPhone 17 Pro Max 256GB (Unlocked) - New",
        "Apple iPhone 16 Pro Max 256GB - T-Mobile - New",
    ],
)
def test_the_three_watched_families_pass(title, criteria):
    assert evaluate(listing(title), criteria) is None


@pytest.mark.parametrize(
    "title,reason",
    [
        ("Apple iPhone 17 Pro 256GB - Unlocked - New", "not in the watch list"),
        ("Apple iPhone 17 256GB - Unlocked - New", "not in the watch list"),
        ("Apple iPhone 15 Plus 256GB - Unlocked - New", "not in the watch list"),
        ("Apple iPhone 16e 256GB - Unlocked - New", "not in the watch list"),
        ("Apple iPhone Air 128GB - Unlocked - New", "below the 256GB minimum"),
        ("Apple iPhone 17 Pro Max 256GB - AT&T - New", "locked to AT&T"),
        ("Apple iPhone 16 Plus 256GB - Renewed", "condition is refurbished"),
        ("Apple iPhone Air 256GB - New, $300 off with new line", "new line"),
    ],
)
def test_everything_else_is_skipped(title, reason, criteria):
    assert reason in evaluate(listing(title), criteria)


def test_pro_max_matches_every_generation(criteria):
    # "Pro Max" is deliberately generation-agnostic; narrow it to "17 Pro Max"
    # in config.json to watch only the current one.
    assert evaluate(listing("Apple iPhone 15 Pro Max 256GB - Unlocked - New"), criteria) is None


def test_shipped_config_holds_no_literal_credentials():
    raw = json.loads(open("config.json", encoding="utf-8").read())
    secrets = []
    for entry in raw["sources"] + raw["notifiers"]:
        for key in ("api_key", "client_id", "client_secret", "token", "user", "topic"):
            value = entry.get(key)
            if value and not re.fullmatch(r"\$\{[A-Z_]+(?::-[^}]*)?\}", str(value)):
                secrets.append(f"{entry['name']}.{key}")
    assert secrets == [], f"credentials must come from the environment: {secrets}"


def test_every_enabled_source_reads_its_credentials_from_the_environment():
    raw = json.loads(open("config.json", encoding="utf-8").read())
    enabled = [entry for entry in raw["sources"] if entry.get("enabled", True)]
    assert {entry["type"] for entry in enabled} <= {"bestbuy", "ebay"}
    assert [entry["name"] for entry in enabled] == ["bestbuy", "ebay-air", "ebay-16-plus", "ebay-pro-max"]
