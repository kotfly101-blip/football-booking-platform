import os
import secrets
import tempfile
from datetime import date, time, timedelta
from pathlib import Path

with tempfile.TemporaryDirectory(prefix="football_qr_test_") as folder:
    database = Path(folder) / "qr_test.db"
    os.environ["DATABASE_URL"] = "sqlite:///" + database.as_posix()
    os.environ["SECRET_KEY"] = secrets.token_hex(32)
    os.environ["COOKIE_SECURE"] = "false"

    from app import create_app, db
    from app.models import Booking, BookingOwner, FootballField, Payment, User

    app = create_app()
    app.config["TESTING"] = True

    try:
        with app.app_context():
            assert db.engine.dialect.name == "sqlite", (
                "Safety error: test database must be SQLite"
            )
            assert Path(db.engine.url.database).resolve() == database.resolve(), (
                "Safety error: unexpected database path"
            )

            db.create_all()

            field = FootballField(
                name="Test Field",
                field_type="7-a-side",
                price_per_hour=800,
                is_active=True
            )

            user = User(
                username="qr_test_member",
                email="qr@example.test"
            )
            user.set_password(secrets.token_urlsafe(20))

            db.session.add_all([field, user])
            db.session.flush()

            booking = Booking(
                field_id=field.id,
                customer_name="Test Customer",
                phone="0800000000",
                booking_date=date.today() + timedelta(days=14),
                start_time=time(10, 0),
                end_time=time(12, 0),
                total_price=1600,
                status="confirmed"
            )

            db.session.add(booking)
            db.session.flush()

            db.session.add(
                BookingOwner(
                    booking_id=booking.id,
                    user_id=user.id
                )
            )

            booking_id = booking.id
            user_id = user.id
            db.session.commit()

        with app.test_client() as client:
            url = f"/booking/{booking_id}/test-qr.png"

            # Test 1: Unauthorized access
            response = client.get(url)
            assert response.status_code == 403, response.status_code
            print("PASS: unauthorized access denied")

            # Test 2: Owner can view unpaid QR
            with client.session_transaction() as sess:
                sess["user_id"] = user_id

            response = client.get(url)
            assert response.status_code == 200, response.status_code
            assert response.data.startswith(b"\x89PNG\r\n\x1a\n")
            assert response.headers.get("Cache-Control") == "no-store"
            print("PASS: owner can view unpaid test QR")

            # Test 3: Paid booking QR denied
            with app.app_context():
                db.session.add(
                    Payment(
                        booking_id=booking_id,
                        amount=1600,
                        status="paid",
                        method="cash"
                    )
                )
                db.session.commit()

            response = client.get(url)
            assert response.status_code == 403, response.status_code
            print("PASS: paid booking QR denied")

            # Test 4: Cancelled booking QR denied
            with app.app_context():
                Payment.query.filter_by(
                    booking_id=booking_id
                ).delete()

                booking = db.session.get(Booking, booking_id)
                booking.status = "cancelled"
                db.session.commit()

            response = client.get(url)
            assert response.status_code == 403, response.status_code
            print("PASS: cancelled booking QR denied")

        print("PASS: all isolated QR tests")

    finally:
        with app.app_context():
            db.session.remove()
            db.engine.dispose()