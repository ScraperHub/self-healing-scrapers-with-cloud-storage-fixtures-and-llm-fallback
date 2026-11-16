from __future__ import annotations

from selfheal.schema import (
    ProductSchema,
    as_float,
    as_int,
    currency_from_price,
    field_nulls,
    fill_rate,
    price_text,
)


def test_fill_rate_counts_only_present_fields() -> None:
    bare = ProductSchema(title="Tree Runner")
    assert fill_rate(bare) == 1 / 8
    full = ProductSchema(
        title="Tree Runner",
        price="$98",
        currency="USD",
        availability="In stock",
        rating=4.8,
        review_count=10,
        brand="Allbirds",
        sku="TR",
    )
    assert fill_rate(full) == 1.0


def test_blank_strings_count_as_null() -> None:
    product = ProductSchema(title="Tree Runner", price="  ", brand="")
    assert field_nulls(product)["price"] is True
    assert field_nulls(None)["title"] is True


def test_number_parsers() -> None:
    assert as_float("4.8 out of 5") == 4.8
    assert as_float(None) is None
    assert as_float(True) is None
    assert as_int("1,248 reviews") == 1248
    assert as_int(4.0) == 4
    assert as_int("none") is None
    assert price_text("Sale $98.00 today") == "$98.00"
    assert price_text("nope") is None
    assert currency_from_price("$9", None) == "USD"
    assert currency_from_price("10", "eur") == "EUR"
    assert currency_from_price("10", None) is None
    assert currency_from_price("£4", None) == "GBP"
    assert currency_from_price("€4", None) == "EUR"
