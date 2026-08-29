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
