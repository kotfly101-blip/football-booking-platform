def calculate_best_discount(
    original_price,
    is_member=False,
    promo_code=""
):
    """Return the best single discount for a booking."""

    if not isinstance(original_price, int) or original_price < 0:
        raise ValueError("Invalid original price")

    member_discount = (
        original_price * 10 // 100
        if is_member else 0
    )

    code_discount = 0

    if promo_code.strip().upper() == "FOOTBALL100":
        code_discount = min(100, original_price)

    if member_discount >= code_discount:
        discount = member_discount
        discount_type = "member" if discount > 0 else "none"
    else:
        discount = code_discount
        discount_type = "promo_code"

    final_price = original_price - discount

    return {
        "original_price": original_price,
        "discount": discount,
        "discount_type": discount_type,
        "final_price": final_price
    }