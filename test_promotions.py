from app.promotions import calculate_best_discount


def check(name, price, member, code, expected_discount, expected_final):
    result = calculate_best_discount(price, member, code)

    assert result["discount"] == expected_discount, (
        f"{name}: incorrect discount: {result}"
    )
    assert result["final_price"] == expected_final, (
        f"{name}: incorrect final price: {result}"
    )
    assert 0 <= result["final_price"] <= price

    print(f"PASS: {name}")


check("normal customer", 1600, False, "", 0, 1600)
check("member discount", 1600, True, "", 160, 1440)
check("promo code", 1600, False, "FOOTBALL100", 100, 1500)
check("best discount wins", 1600, True, "FOOTBALL100", 160, 1440)
check("promo beats member", 800, True, "FOOTBALL100", 100, 700)
check("discount capped at price", 80, False, "FOOTBALL100", 80, 0)
check("lowercase code", 1600, False, "football100", 100, 1500)
check("invalid code", 1600, False, "INVALID", 0, 1600)
check("zero price", 0, True, "FOOTBALL100", 0, 0)

try:
    calculate_best_discount(-100)
except ValueError:
    print("PASS: negative price rejected")
else:
    raise AssertionError("Negative price was accepted")

print("PASS: all promotion tests")