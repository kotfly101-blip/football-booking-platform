
import unittest

from app.promotions import calculate_best_discount


class TestPromotions(unittest.TestCase):

    def test_member_discount(self):
        result = calculate_best_discount(2000, is_member=True)
        self.assertEqual(result["discount"], 200)
        self.assertEqual(result["final_price"], 1800)

    def test_promo_code(self):
        result = calculate_best_discount(
            2000, promo_code="FOOTBALL100"
        )
        self.assertEqual(result["discount"], 100)
        self.assertEqual(result["final_price"], 1900)

    def test_best_discount(self):
        result = calculate_best_discount(
            2000, is_member=True, promo_code="FOOTBALL100"
        )
        self.assertEqual(result["discount"], 200)
        self.assertEqual(result["discount_type"], "member")

    def test_normal_price(self):
        result = calculate_best_discount(2000)
        self.assertEqual(result["discount"], 0)
        self.assertEqual(result["final_price"], 2000)

    def test_invalid_price(self):
        with self.assertRaises(ValueError):
            calculate_best_discount(-100)

    def test_small_price(self):
        result = calculate_best_discount(
            80, promo_code="FOOTBALL100"
        )
        self.assertEqual(result["discount"], 80)
        self.assertEqual(result["final_price"], 0)


if __name__ == "__main__":
    unittest.main()
