from decimal import Decimal, InvalidOperation
from io import BytesIO

import qrcode


def create_test_qr(amount):
    """Generate a non-payable QR for local testing only."""
    try:
        value = Decimal(str(amount))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Invalid payment amount")

    if not value.is_finite() or value <= 0:
        raise ValueError("Payment amount must be positive")

    if value != value.quantize(Decimal("0.01")):
        raise ValueError("Amount must have at most 2 decimal places")

    if value > Decimal("999999.99"):
        raise ValueError("Amount exceeds test limit")

    payload = f"FOOTBALL-TEST-ONLY|THB|{value:.2f}"

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(payload)
    qr.make(fit=True)

    image = qr.make_image(fill_color="black", back_color="white")
    output = BytesIO()
    image.save(output, format="PNG")

    return output.getvalue()
