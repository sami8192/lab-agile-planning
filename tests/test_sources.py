import json

import pytest

from iphone_watch.http import HttpError, dig
from iphone_watch.sources import SOURCE_TYPES, SourceError, build_source
from iphone_watch.sources import bestbuy as bestbuy_module
from iphone_watch.sources import custom_html as html_module
from iphone_watch.sources import custom_json as json_module


def test_registry_exposes_every_type():
    assert set(SOURCE_TYPES) == {"sample", "custom_json", "custom_html", "bestbuy", "ebay"}
    with pytest.raises(SourceError):
        build_source({"type": "nope"})


def test_dig_walks_dicts_and_lists():
    data = {"a": {"b": [{"c": 7}]}}
    assert dig(data, "a.b.0.c") == 7
    assert dig(data, "a.b.9.c", default="x") == "x"
    assert dig(data, "", default=None) == data


def test_sample_source_reads_the_bundled_fixture():
    listings = list(build_source({"type": "sample", "name": "demo"}).fetch())
    assert len(listings) == 7
    assert any(listing.title.startswith("Apple iPhone 17 Pro Max 256GB") for listing in listings)


def test_sample_source_applies_price_delta():
    base = {listing.listing_id: listing.price for listing in build_source({"type": "sample"}).fetch()}
    shifted = {
        listing.listing_id: listing.price
        for listing in build_source({"type": "sample", "price_delta": -100}).fetch()
    }
    assert shifted["demo-17-pro-max-256"] == base["demo-17-pro-max-256"] - 100


def test_sample_source_reports_a_missing_fixture(tmp_path):
    with pytest.raises(SourceError):
        list(build_source({"type": "sample", "path": str(tmp_path / "nope.json")}).fetch())


def test_custom_json_source_maps_fields(monkeypatch):
    payload = {
        "data": {
            "products": [
                {
                    "sku": "A1",
                    "name": "Apple iPhone 17 Pro Max 256GB - New",
                    "price": {"amount": "$1,199.00", "currency": "USD"},
                    "links": {"web": "https://shop.example/a1"},
                    "condition": "New",
                    "availability": {"online": True},
                },
                {"sku": "A2", "name": "broken", "price": {}},
            ]
        }
    }
    monkeypatch.setattr(json_module, "get_json", lambda url, **kwargs: payload)
    listings = list(
        build_source(
            {
                "type": "custom_json",
                "name": "shop",
                "url": "https://api.example/search",
                "items_path": "data.products",
                "fields": {
                    "id": "sku",
                    "title": "name",
                    "price": "price.amount",
                    "currency": "price.currency",
                    "url": "links.web",
                    "in_stock": "availability.online",
                },
            }
        ).fetch()
    )
    assert len(listings) == 1  # the item without a price is skipped
    listing = listings[0].enriched()
    assert (listing.key, listing.price, listing.currency) == ("shop:A1", 1199.0, "USD")
    assert listing.model == "iPhone 17 Pro Max" and listing.storage_gb == 256


def test_custom_json_source_requires_a_url():
    with pytest.raises(SourceError):
        list(build_source({"type": "custom_json", "name": "shop"}).fetch())


def test_custom_json_source_wraps_http_errors(monkeypatch):
    def boom(url, **kwargs):
        raise HttpError("HTTP 503", 503)

    monkeypatch.setattr(json_module, "get_json", boom)
    with pytest.raises(SourceError) as excinfo:
        list(build_source({"type": "custom_json", "name": "shop", "url": "https://x"}).fetch())
    assert "503" in str(excinfo.value)


PAGE = """
<html><head><title>Apple iPhone 17 Pro Max 256GB</title>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Product","name":"iPhone 17 Pro Max",
 "offers":{"@type":"Offer","price":"1149.00","priceCurrency":"USD",
 "availability":"https://schema.org/InStock","itemCondition":"https://schema.org/NewCondition"}}
</script></head><body>Price: $1,149.00</body></html>
"""


def test_custom_html_source_reads_json_ld(monkeypatch):
    monkeypatch.setattr(html_module, "request", lambda url, **kwargs: PAGE)
    listing = list(
        build_source({"type": "custom_html", "name": "store", "url": "https://shop.example/p"}).fetch()
    )[0].enriched()
    assert listing.price == 1149.0
    assert listing.currency == "USD"
    assert listing.condition == "new"
    assert listing.in_stock is True
    assert listing.model == "iPhone 17 Pro Max"
    assert listing.storage_gb == 256


def test_custom_html_source_falls_back_to_a_regex(monkeypatch):
    monkeypatch.setattr(html_module, "request", lambda url, **kwargs: "<html><body>Now 1,099.00 USD</body></html>")
    listing = list(
        build_source(
            {
                "type": "custom_html",
                "name": "store",
                "url": "https://shop.example/p",
                "title": "Apple iPhone Air 256GB",
                "condition": "new",
                "price_regex": r"Now ([\d,.]+) USD",
            }
        ).fetch()
    )[0].enriched()
    assert listing.price == 1099.0
    assert listing.model == "iPhone Air"


def test_custom_html_source_reports_a_missing_price(monkeypatch):
    monkeypatch.setattr(html_module, "request", lambda url, **kwargs: "<html><body>sold out</body></html>")
    with pytest.raises(SourceError) as excinfo:
        list(build_source({"type": "custom_html", "name": "store", "url": "https://shop.example/p"}).fetch())
    assert "price_regex" in str(excinfo.value)


def test_custom_html_source_detects_out_of_stock(monkeypatch):
    page = PAGE.replace("InStock", "OutOfStock")
    monkeypatch.setattr(html_module, "request", lambda url, **kwargs: page)
    listing = list(build_source({"type": "custom_html", "name": "s", "url": "https://x"}).fetch())[0]
    assert listing.in_stock is False


def test_bestbuy_source_normalises_products(monkeypatch):
    captured = {}

    def fake_get_json(url, **kwargs):
        captured["url"] = url
        captured["params"] = kwargs.get("params")
        return {
            "products": [
                {
                    "sku": 6418599,
                    "name": "Apple - iPhone 17 Pro Max 256GB - New",
                    "salePrice": 1099.99,
                    "regularPrice": 1199.99,
                    "url": "https://bestbuy.com/x",
                    "onlineAvailability": True,
                }
            ]
        }

    monkeypatch.setattr(bestbuy_module, "get_json", fake_get_json)
    listing = list(build_source({"type": "bestbuy", "name": "bb", "api_key": "k"}).fetch())[0].enriched()
    assert "condition=new" in captured["url"]
    assert captured["params"]["apiKey"] == "k"
    assert listing.key == "bb:6418599"
    assert listing.price == 1099.99
    assert listing.condition == "new"
    assert listing.extra["regular_price"] == 1199.99


def test_bestbuy_source_requires_an_api_key():
    with pytest.raises(SourceError):
        list(build_source({"type": "bestbuy", "name": "bb"}).fetch())


def test_ebay_source_adds_shipping_and_uses_a_token(monkeypatch):
    from iphone_watch.sources import ebay as ebay_module

    monkeypatch.setattr(
        ebay_module, "request", lambda url, **kwargs: json.dumps({"access_token": "tok", "expires_in": 7200})
    )
    seen = {}

    def fake_get_json(url, **kwargs):
        seen.update(kwargs)
        return {
            "itemSummaries": [
                {
                    "itemId": "v1|123|0",
                    "title": "Apple iPhone 17 Pro Max 256GB Unlocked NEW",
                    "price": {"value": "1149.00", "currency": "USD"},
                    "shippingOptions": [{"shippingCost": {"value": "9.99"}}],
                    "itemWebUrl": "https://ebay.com/itm/123",
                    "condition": "New",
                    "seller": {"username": "topseller"},
                }
            ]
        }

    monkeypatch.setattr(ebay_module, "get_json", fake_get_json)
    listing = list(
        build_source({"type": "ebay", "name": "ebay", "client_id": "id", "client_secret": "secret"}).fetch()
    )[0].enriched()
    assert seen["headers"]["Authorization"] == "Bearer tok"
    assert "conditionIds:{1000}" in seen["params"]["filter"]
    assert listing.price == 1158.99  # item price plus shipping
    assert listing.seller == "topseller"
    assert listing.condition == "new"


def test_ebay_source_requires_credentials():
    with pytest.raises(SourceError):
        list(build_source({"type": "ebay", "name": "ebay"}).fetch())
