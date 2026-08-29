import pytest

from iphone_watch.config import Criteria
from iphone_watch.filters import evaluate, split
from iphone_watch.models import Listing


def make(title, price=1199.0, **kwargs):
    return Listing(source="s", listing_id=title, title=title, price=price, **kwargs).enriched()


DEFAULTS = Criteria()


def test_accepts_new_large_screen_256gb():
    assert evaluate(make("Apple iPhone 17 Pro Max 256GB - New"), DEFAULTS) is None


def test_rejects_small_screen():
    reason = evaluate(make("Apple iPhone 17 Pro 256GB - New"), DEFAULTS)
    assert "screen" in reason


def test_rejects_low_storage():
    reason = evaluate(make("Apple iPhone 17 Pro Max 128GB - New"), DEFAULTS)
    assert "128GB" in reason


def test_rejects_refurbished():
    reason = evaluate(make("Apple iPhone 17 Pro Max 256GB - Certified Refurbished"), DEFAULTS)
    assert "condition" in reason


def test_rejects_unknown_model_by_default():
    assert "not recognised" in evaluate(make("Galaxy S25 Ultra 512GB New"), DEFAULTS)


def test_allows_unknown_models_when_configured():
    criteria = Criteria(allow_unknown_models=True)
    listing = make('Pixel 10 Pro XL 6.8-inch 256GB New')
    assert evaluate(listing, criteria) is None


def test_respects_price_ceiling_and_currency():
    criteria = Criteria(max_price=1000.0)
    assert "price ceiling" in evaluate(make("iPhone 17 Pro Max 256GB New", price=1199.0), criteria)
    assert "currency" in evaluate(make("iPhone 17 Pro Max 256GB New", currency="EUR"), DEFAULTS)


def test_model_allow_and_exclude_lists():
    only_max = Criteria(models=("Pro Max",))
    assert evaluate(make("iPhone 17 Pro Max 256GB New"), only_max) is None
    assert "not in the watch list" in evaluate(make("iPhone 16 Plus 256GB New"), only_max)
    no_plus = Criteria(exclude_models=("Plus",))
    assert "excluded" in evaluate(make("iPhone 16 Plus 256GB New"), no_plus)


def test_out_of_stock_and_bad_price():
    assert "out of stock" in evaluate(make("iPhone 17 Pro Max 256GB New", in_stock=False), DEFAULTS)
    assert "no usable price" in evaluate(make("iPhone 17 Pro Max 256GB New", price=0), DEFAULTS)


def test_split_partitions_listings():
    kept, rejected = split(
        [
            Listing(source="s", listing_id="a", title="iPhone 17 Pro Max 256GB New", price=1199.0),
            Listing(source="s", listing_id="b", title="iPhone 17 Pro 256GB New", price=1099.0),
        ],
        DEFAULTS,
    )
    assert [listing.listing_id for listing in kept] == ["a"]
    assert [rejection.listing.listing_id for rejection in rejected] == ["b"]


def test_accepts_unlocked_and_tmobile_listings():
    assert evaluate(make("Apple iPhone 17 Pro Max 256GB (Unlocked) - New"), DEFAULTS) is None
    # An existing T-Mobile line means a T-Mobile listing is still usable.
    assert evaluate(make("Apple iPhone 17 Pro Max 256GB - T-Mobile - New"), DEFAULTS) is None


def test_rejects_other_carriers():
    assert "locked to AT&T" in evaluate(make("Apple iPhone 17 Pro Max 256GB - AT&T - New"), DEFAULTS)
    assert "locked to Verizon" in evaluate(make("Apple iPhone 17 Pro Max 256GB Verizon New"), DEFAULTS)
    # Metro is a T-Mobile brand but its phones are still carrier locked.
    assert "Metro" in evaluate(make("Metro by T-Mobile Apple iPhone 16 Plus 256GB New"), DEFAULTS)


def test_rejects_prices_that_need_a_new_line_or_trade_in():
    reason = evaluate(make("Apple iPhone 17 Pro Max 256GB New - $500 off with new line activation"), DEFAULTS)
    assert "new line" in reason
    assert "trade-in" in evaluate(make("Apple iPhone 17 Pro Max 256GB New with trade-in"), DEFAULTS)


def test_silent_listings_are_watched_by_default_but_can_be_required_to_state_it():
    quiet = make("Apple iPhone 17 Pro Max 256GB Deep Blue - New")
    assert evaluate(quiet, DEFAULTS) is None
    strict = Criteria(allow_unknown_carrier=False)
    assert "not stated" in evaluate(quiet, strict)


def test_carrier_checks_can_be_turned_off_or_widened():
    assert evaluate(make("Apple iPhone 17 Pro Max 256GB - AT&T - New"), Criteria(require_unlocked=False)) is None
    widened = Criteria(allowed_carriers=("unlocked", "t-mobile", "at&t"))
    assert evaluate(make("Apple iPhone 17 Pro Max 256GB - AT&T - New"), widened) is None
    lenient = Criteria(exclude_new_line_offers=False)
    assert evaluate(make("Apple iPhone 17 Pro Max 256GB New - $500 off with new line"), lenient) is None


@pytest.mark.parametrize(
    "title",
    [
        "Apple iPhone Air 256GB Sky Blue - Unlocked - New",
        "Apple iPhone Air 256GB Sky Blue - T-Mobile - New",
        "Apple iPhone Air 512GB - Unlocked - New",
        "Apple iPhone 16 Plus 256GB Teal (Unlocked) - New",
        "Apple iPhone 16 Plus 256GB Teal - T-Mobile - New",
        "Apple iPhone 17 Pro Max 256GB (Unlocked) - New",
        "Apple iPhone 16 Pro Max 256GB - Unlocked - New",
    ],
)
def test_the_whole_accepted_lineup_is_watched(title):
    # The iPhone Air sits exactly on the 6.5" threshold, so the comparison has
    # to stay inclusive; this pins every family the defaults should catch.
    assert evaluate(make(title), DEFAULTS) is None


def test_iphone_air_needs_256gb_like_everything_else():
    assert "128GB below" in evaluate(make("Apple iPhone Air 128GB - Unlocked - New"), DEFAULTS)


def test_raising_the_screen_threshold_would_drop_the_air():
    # Documented consequence of min_screen_inches > 6.5, guarded so it is a
    # deliberate choice rather than a surprise.
    strict = Criteria(min_screen_inches=6.7)
    assert "screen below" in evaluate(make("Apple iPhone Air 256GB - Unlocked - New"), strict)
    assert evaluate(make("Apple iPhone 16 Plus 256GB - Unlocked - New"), strict) is None
