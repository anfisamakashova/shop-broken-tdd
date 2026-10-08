"""Order checkout.

The rules live in `src/shop/specs/checkout.md` - read it first.
Both functions below are stubs: their signature is final, the bodies are yours.
Do not change the constants: the tests rely on them.
"""

PROMO_CODES = {"WELCOME10": 10, "SUMMER15": 15, "VIP35": 35}
SUPPORTED_CITIES = ("msk", "spb")
MAX_DISCOUNT_PERCENT = 30
VAT_PERCENT = 20
SHIPPING_KOPEKS = 49_000
FREE_DELIVERY_FROM_KOPEKS = 500_000
TIER_DISCOUNTS = ((10, 5), (25, 10), (50, 15))
REQUIRED_LINE_KEYS = ("sku", "qty", "unit_price_kopecks")


def _validate_line(line: dict[str, str], skus: set[str]) -> str | None:
    """Helper to validate a single order line and reduce complexity."""
    for key in REQUIRED_LINE_KEYS:
        if key not in line:
            return "missing_key"

    if not line["sku"]:
        return "invalid_sku"

    if line["sku"] in skus:
        return "duplicate_sku"
    skus.add(line["sku"])

    try:
        qty = int(line["qty"])
        if str(qty) != line["qty"] or qty <= 0:
            return "invalid_quantity"
    except ValueError:
        return "invalid_quantity"

    try:
        price = int(line["unit_price_kopecks"])
        if str(price) != line["unit_price_kopecks"] or price <= 0:
            return "invalid_price"
    except ValueError:
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

    # 1. Вычисляем многоуровневую скидку (Tier Discount)
    tier_discount_percent = 0
    for threshold, discount in TIER_DISCOUNTS:
        if total_qty >= threshold:
            tier_discount_percent = max(tier_discount_percent, discount)

    # 2. Вычисляем промокод
    promo_discount_percent = PROMO_CODES.get(promo_code, 0) if promo_code else 0

    # 3. Применяем лучшее предложение и проверяем лимит (Cap)
    final_discount_percent = max(tier_discount_percent, promo_discount_percent)
    if final_discount_percent > MAX_DISCOUNT_PERCENT:
        final_discount_percent = MAX_DISCOUNT_PERCENT

    # 4. Рассчитываем сумму после скидки
    discount_amount = (raw_subtotal * final_discount_percent) // 100
    discounted_subtotal = raw_subtotal - discount_amount

    # 5. Стоимость доставки (Исправлено SIM102: объединенный if)
    shipping = 0
    if shipping_city and discounted_subtotal < FREE_DELIVERY_FROM_KOPEKS:
        shipping = SHIPPING_KOPEKS

    # 6. База для НДС и итоговый расчет
    total_before_vat = discounted_subtotal + shipping
    vat_amount = (total_before_vat * VAT_PERCENT) // 100

    return total_before_vat + vat_amount
