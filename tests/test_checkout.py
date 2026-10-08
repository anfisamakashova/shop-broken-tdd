"""Order checkout, part 2.

How to work through this file:

1. The single red test below is done for you - it shows what RED looks like.
2. Run `./scripts/check-part2.sh` and read the failure.
3. Write one assertion per rule from `src/shop/specs/checkout.md` into the empty
   tests: a failing test first, then the code that makes it pass.
4. Never edit a finished assertion, never `skip`, never weaken a test.

Run one test at a time while you work:

    uv run pytest tests/test_checkout.py -k tier -x
"""

from shop.checkout import calculate_order_total, validate_order


def line(sku: str = "SKU-1", qty: str = "1", unit_price_kopecks: str = "10000") -> dict[str, str]:
    """Build one order line the way the warehouse export delivers it."""
    return {"sku": sku, "qty": qty, "unit_price_kopecks": unit_price_kopecks}


def test_smoke_single_line_without_delivery() -> None:
    """One line, no promo code, no delivery. Works out to 100.00 rub + 20% VAT."""
    assert validate_order([line()]) is None
    assert calculate_order_total([line()]) == 12_000


def test_empty_order_is_rejected() -> None:
    """Spec 3, rule 1: an order without lines cannot be processed."""
    assert validate_order([]) == "empty_order"
    assert calculate_order_total([]) is None


def test_empty_sku_is_rejected() -> None:
    """Spec 3, rule 2: a blank article code is not allowed."""
    assert validate_order([line(sku="")]) == "invalid_sku"


def test_missing_line_key_is_rejected() -> None:
    """Spec 3, rule 3: every required key must be present."""
    bad = {"qty": "1", "unit_price_kopecks": "10000"}
    assert validate_order([bad]) == "missing_key"


def test_non_numeric_quantity_is_rejected() -> None:
    """Spec 3, rule 4: `qty` must be a whole number."""
    assert validate_order([line(qty="abc")]) == "invalid_quantity"
    assert validate_order([line(qty="1.5")]) == "invalid_quantity"


def test_zero_quantity_is_rejected() -> None:
    """Spec 3, rule 5: `qty` must be greater than zero."""
    assert validate_order([line(qty="0")]) == "invalid_quantity"
    assert validate_order([line(qty="-1")]) == "invalid_quantity"


def test_non_numeric_price_is_rejected() -> None:
    """Spec 3, rule 6: `unit_price_kopecks` must be a whole number."""
    assert validate_order([line(unit_price_kopecks="abc")]) == "invalid_price"
    assert validate_order([line(unit_price_kopecks="10.5")]) == "invalid_price"


def test_negative_price_is_rejected() -> None:
    """Spec 3, rule 7: a price may not be negative."""
    assert validate_order([line(unit_price_kopecks="-100")]) == "invalid_price"
    assert validate_order([line(unit_price_kopecks="0")]) == "invalid_price"


def test_duplicate_sku_is_rejected() -> None:
    """Spec 3, rule 8: the same article may appear only once."""
    assert validate_order([line("SKU-1"), line("SKU-1")]) == "duplicate_sku"


def test_unknown_promo_code_is_rejected() -> None:
    """Spec 3, rule 9: only codes from PROMO_CODES exist."""
    assert validate_order([line()], promo_code="UNKNOWN") == "invalid_promo_code"


def test_unsupported_city_is_rejected() -> None:
    """Spec 3, rule 10: only cities from SUPPORTED_CITIES are served."""
    assert validate_order([line()], shipping_city="london") == "unsupported_city"


def test_valid_order_passes_validation() -> None:
    """Spec 3: a good order gets None back instead of a reason."""
    assert validate_order([line()], promo_code="WELCOME10", shipping_city="msk") is None


def test_no_discount_below_first_tier() -> None:
    """Spec 4, steps 1-2: 9 units are below every threshold."""
    # 9 * 10000 = 90000. No delivery (empty city), no discount. VAT 20% = 18000. Total = 108000
    assert calculate_order_total([line(qty="9")]) == 108_000


def test_tier_discount_at_first_threshold() -> None:
    """Spec 4, steps 2-5: 10 units give 5%. Compare with example 2."""
    # 10 * 10000 = 100000. Discount 5% = 5000. Subtotal = 95000. VAT 20% = 19000. Total = 114000
    assert calculate_order_total([line(qty="10")]) == 114_000


def test_tier_discount_at_highest_threshold() -> None:
    """Spec 4, steps 2-5: 50 units give 15%, not 5% + 10%."""
    # 50 * 10000 = 500000. Discount 15% = 75000. Subtotal = 425000. VAT 20% = 85000. Total = 510000
    assert calculate_order_total([line(qty="50")]) == 510_000


def test_promo_code_beats_tier_discount() -> None:
    """Spec 4, steps 3-4: the bigger percentage wins, the two do not add up."""
    # 10 units (5% tier) + WELCOME10 (10% promo) -> Wins 10%.
    # Subtotal 100000 - 10% = 90000. VAT 20% = 18000. Total = 108000
    assert calculate_order_total([line(qty="10")], promo_code="WELCOME10") == 108_000


def test_discount_is_capped_at_thirty_percent() -> None:
    """Spec 4, step 5: VIP35 gives 35%, but the cap is 30%. Compare with example 4."""
    # 1 unit * 10000 = 10000. VIP35 -> 35% capped to 30% -> 3000 discount.
    # Subtotal = 7000. VAT 20% = 1400. Total = 8400
    assert calculate_order_total([line(qty="1")], promo_code="VIP35") == 8_400


def test_delivery_is_charged_for_small_order() -> None:
    """Spec 4, steps 7-10: a city adds SHIPPING_KOPEKS and VAT is charged on it."""
    # 1 unit * 10000 = 10000. City msk -> adds 49000 delivery because subtotal < 500000.
    # Subtotal + delivery = 59000. VAT 20% = 11800. Total = 70800
    assert calculate_order_total([line(qty="1")], shipping_city="msk") == 70_800


def test_free_delivery_uses_discounted_subtotal() -> None:
    """Spec 4, step 7: the threshold is checked against the sum after the discount."""
    # 50 units * 10000 = 500000. Tier discount 15% = 75000. Discounted subtotal = 425000.
    # 425000 < 500000 -> delivery IS charged (49000). Total base = 474000. VAT 20% = 94800. Total = 568800
    assert calculate_order_total([line(qty="50")], shipping_city="spb") == 568_800


def test_vat_is_charged_on_the_discounted_sum() -> None:
    """Spec 4, steps 8-10: base = discounted subtotal + delivery."""
    # Проверка цепочки: 60 * 10000 = 600000. Discount 15% = 90000. Subtotal = 510000.
    # 510000 >= 500000 -> free delivery. Base = 510000. VAT 20% = 102000. Total = 612000
    assert calculate_order_total([line(qty="60")], shipping_city="msk") == 612_000
