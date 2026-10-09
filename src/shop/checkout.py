"""Order checkout.

The rules live in `src/shop/specs/checkout.md` - read it first.
Both functions below are stubs: their signature is final, the bodies are yours.
Do not change the constants: the tests rely on them.
"""

from shop.money import percent_of

PROMO_CODES = {"WELCOME10": 10, "SUMMER15": 15, "VIP35": 35}
SUPPORTED_CITIES = ("msk", "spb")
MAX_DISCOUNT_PERCENT = 30
VAT_PERCENT = 20
SHIPPING_KOPEKS = 49_000
FREE_DELIVERY_FROM_KOPEKS = 500_000
TIER_DISCOUNTS = ((10, 5), (25, 10), (50, 15))
REQUIRED_LINE_KEYS = ("sku", "qty", "unit_price_kopecks")


def _parse_positive_int(raw: str) -> int | None:
    """Parse a raw string into a positive integer in canonical decimal form.

    Returns None when the text is not a plain positive integer. The check is
    done by hand so the module never needs try/except or raise.
    """
    if not raw.isascii() or not raw.isdigit():
        return None
    value = int(raw)
    if value <= 0 or str(value) != raw:
        return None
    return value


def _validate_line(line: dict[str, str], skus: set[str]) -> str | None:
    """Helper to validate a single order line and reduce complexity."""
    for key in REQUIRED_LINE_KEYS:
        if key not in line:
            return "missing_key"

    sku = line["sku"]
    if not sku:
        return "invalid_sku"

    if sku in skus:
        return "duplicate_sku"
    skus.add(sku)

    if _parse_positive_int(line["qty"]) is None:
        return "invalid_quantity"

    if _parse_positive_int(line["unit_price_kopecks"]) is None:
        return "invalid_price"

    return None


def validate_order(
    lines: list[dict[str, str]],
    promo_code: str = "",
    shipping_city: str = "",
) -> str | None:
    """Return a human readable reason why the order is invalid, or None if it is fine."""
    if not lines:
        return "empty_order"

    if shipping_city and shipping_city not in SUPPORTED_CITIES:
        return "unsupported_city"

    if promo_code and promo_code not in PROMO_CODES:
        return "invalid_promo_code"

    skus: set[str] = set()
    for line in lines:
        error = _validate_line(line, skus)
        if error is not None:
            return error

    return None


def calculate_order_total(
    lines: list[dict[str, str]],
    promo_code: str = "",
    shipping_city: str = "",
) -> int | None:
    """Return the order total in kopecks, or None if the order is invalid."""
    if validate_order(lines, promo_code, shipping_city) is not None:
        return None

    total_qty = 0
    raw_subtotal = 0
    for line in lines:
        qty = int(line["qty"])
        price = int(line["unit_price_kopecks"])
        total_qty += qty
        raw_subtotal += qty * price

    # The biggest qualifying tier applies; tiers never stack.
    tier_discount_percent = 0
    for threshold, discount in TIER_DISCOUNTS:
        if total_qty >= threshold:
            tier_discount_percent = max(tier_discount_percent, discount)

    # An unknown or empty code is no discount at all.
    promo_discount_percent = PROMO_CODES.get(promo_code, 0) if promo_code else 0

    # Tier and promo compete: the larger one wins, then the cap clamps it.
    final_discount_percent = max(tier_discount_percent, promo_discount_percent)
    if final_discount_percent > MAX_DISCOUNT_PERCENT:
        final_discount_percent = MAX_DISCOUNT_PERCENT

    discount_amount = percent_of(raw_subtotal, final_discount_percent)
    discounted_subtotal = raw_subtotal - discount_amount

    # Pickup (empty city) is free; delivery only survives below the free threshold.
    shipping = 0
    if shipping_city and discounted_subtotal < FREE_DELIVERY_FROM_KOPEKS:
        shipping = SHIPPING_KOPEKS

    total_before_vat = discounted_subtotal + shipping
    vat_amount = percent_of(total_before_vat, VAT_PERCENT)

    return total_before_vat + vat_amount
