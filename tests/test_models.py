import pytest

from iphone_watch.models import (
    IPHONE_SCREEN_INCHES,
    Listing,
    normalize_condition,
    normalize_model,
    parse_price,
    parse_screen_inches,
    parse_storage_gb,
)


@pytest.mark.parametrize(
    "title,expected",
    [
        ("Apple iPhone 17 Pro Max 256GB Deep Blue", "iPhone 17 Pro Max"),
        ("APPLE IPHONE 16 PRO 512GB", "iPhone 16 Pro"),
        ("iPhone 16e 128GB Black", "iPhone 16e"),
        ("Apple iPhone Air 256GB", "iPhone Air"),
        ("iPhone  16   Plus 256GB", "iPhone 16 Plus"),
        ("Samsung Galaxy S25 Ultra 512GB", None),
    ],
)
def test_normalize_model(title, expected):
    assert normalize_model(title) == expected


def test_model_match_does_not_bleed_into_longer_names():
    # "iPhone 16" must not swallow "iPhone 16e" or "iPhone 16 Pro Max".
    assert normalize_model("iPhone 16 Pro Max 256GB") == "iPhone 16 Pro Max"
    assert normalize_model("iPhone 16e") == "iPhone 16e"


@pytest.mark.parametrize(
    "text,expected",
    [("256GB", 256), ("1TB storage", 1024), ("2 TB", 2048), ("iPhone 17 128 GB", 128), ("8GB RAM", None), ("", None)],
)
def test_parse_storage_gb(text, expected):
    assert parse_storage_gb(text) == expected


@pytest.mark.parametrize(
    "value,expected",
    [(1199, 1199.0), ("$1,199.00", 1199.0), ("1.199,00 €", 1199.0), ("USD 999", 999.0), ("n/a", None), (None, None)],
)
def test_parse_price(value, expected):
    assert parse_price(value) == expected


def test_parse_screen_inches():
    assert parse_screen_inches('6.9-inch display') == 6.9
    assert parse_screen_inches('6.7" Super Retina') == 6.7
    assert parse_screen_inches("no size here") is None


@pytest.mark.parametrize(
    "text,expected",
    [
        ("New", "new"),
        ("Brand New Sealed", "new"),
        ("Certified Refurbished", "refurbished"),
        ("Renewed", "refurbished"),
        ("Open Box - Excellent", "used"),
        ("Pre-Owned", "used"),
        ("https://schema.org/NewCondition", "new"),
        (None, "unknown"),
    ],
)
def test_normalize_condition(text, expected):
    assert normalize_condition(text) == expected


def test_enriched_fills_model_storage_and_screen():
    listing = Listing(
        source="s", listing_id="1", title="Apple iPhone 17 Pro Max 256GB - New", price=1199.0
    ).enriched()
    assert listing.model == "iPhone 17 Pro Max"
    assert listing.storage_gb == 256
    assert listing.screen_inches == IPHONE_SCREEN_INCHES["iPhone 17 Pro Max"]
    assert listing.condition == "new"
    assert listing.label == "iPhone 17 Pro Max 256GB"
    assert listing.key == "s:1"


def test_label_renders_terabytes():
    listing = Listing(source="s", listing_id="2", title="iPhone 17 Pro Max 1TB", price=1599.0).enriched()
    assert listing.label == "iPhone 17 Pro Max 1TB"


@pytest.mark.parametrize(
    "title,expected",
    [
        ("Apple iPhone 17 Pro Max 256GB (Unlocked)", "unlocked"),
        ("Apple iPhone 17 Pro Max 256GB SIM-Free", "unlocked"),
        ("Apple iPhone 17 Pro Max 256GB - T-Mobile", "t-mobile"),
        ("Apple iPhone 17 Pro Max 256GB - AT&T", "at&t"),
        ("Apple iPhone 16 Plus 256GB Verizon", "verizon"),
        ("Metro by T-Mobile iPhone 16 Plus 256GB", "metro"),
        ("iPhone 16 Plus 256GB locked to Verizon", "verizon"),
        ("Unlocked — works with T-Mobile and AT&T", "unlocked"),
        ("Apple iPhone 17 Pro Max 256GB Deep Blue", None),
    ],
)
def test_normalize_carrier(title, expected):
    from iphone_watch.models import normalize_carrier

    assert normalize_carrier(title) == expected


@pytest.mark.parametrize(
    "title,expected",
    [
        ("iPhone 17 Pro Max 256GB - $500 off with new line activation", True),
        ("Save $400 when you port-in your number", True),
        ("iPhone 17 Pro Max 256GB with trade-in", True),
        ("Apple iPhone 17 Pro Max 256GB (Unlocked)", False),
    ],
)
def test_requires_new_line(title, expected):
    from iphone_watch.models import requires_new_line

    assert requires_new_line(title) is expected


def test_enriched_reads_carrier_and_activation_terms():
    listing = Listing(
        source="s",
        listing_id="1",
        title="Apple iPhone 17 Pro Max 256GB (Unlocked) - New",
        price=1199.0,
    ).enriched()
    assert listing.carrier == "unlocked"
    assert listing.needs_new_line is False
    assert listing.label == "iPhone 17 Pro Max 256GB (Unlocked)"


def test_explicit_carrier_field_is_normalised():
    listing = Listing(
        source="s", listing_id="1", title="Apple iPhone 16 Plus 256GB", price=899.0, carrier="T-Mobile"
    ).enriched()
    assert listing.carrier == "t-mobile"
    assert listing.label.endswith("(T-Mobile)")


def test_carrier_label_falls_back_to_a_readable_string():
    from iphone_watch.models import carrier_label

    assert carrier_label(None) == "carrier not stated"
    assert carrier_label("at&t") == "AT&T"
