"""Test booking behavior using a disposable SQLite database only."""
import os
import secrets
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

with tempfile.TemporaryDirectory(prefix="football_booking_test_") as folder:
    database = Path(folder) / "booking_test.db"

    # Force tests to use a disposable SQLite database, not Neon.
    os.environ["DATABASE_URL"] = "sqlite:///" + database.as_posix()
    os.environ["SECRET_KEY"] = secrets.token_hex(32)
    os.environ["COOKIE_SECURE"] = "false"

    from app import create_app, db
    from app.models import Booking, FootballField

    app = create_app()
    app.config["TESTING"] = True

    # Safety check: never run this test against a production database.
    with app.app_context():
        assert db.engine.dialect.name == "sqlite", (
            "Safety error: test database must be SQLite"
        )
        assert Path(db.engine.url.database).resolve() == database.resolve(), (
            "Safety error: unexpected database path"
        )

    try:
        with app.app_context():
            # Create tables only in the temporary SQLite database.
            db.create_all()

            field = FootballField(
                name="สนามทดสอบ A",
                field_type="7-a-side",
                price_per_hour=800,
                is_active=True,
            )

            db.session.add(field)
            db.session.commit()
            field_id = field.id

        # Use a future date and a time that does not cross midnight.
        booking_date = (
            datetime.now() + timedelta(days=14)
        ).date().isoformat()

        data = {
            "customer_name": "สมชาย ทดสอบ",
            "phone": "0800000000",
            "booking_date": booking_date,
            "start_time": "10:00",
            "hours": "2",
        }

        with app.test_client() as client:
            # Open booking form and retrieve CSRF token.
            response = client.get(f"/book/{field_id}")
            assert response.status_code == 200, (
                f"Booking form: HTTP {response.status_code}"
            )

            with client.session_transaction() as sess:
                token = sess["book_field_csrf"]

            # Test 1: Create a booking and verify price.
            response = client.post(
                f"/book/{field_id}",
                data={**data, "csrf_token": token},
                follow_redirects=False,
            )

            assert response.status_code in (302, 303), (
                f"First booking: HTTP {response.status_code}"
            )

            with app.app_context():
                bookings = Booking.query.filter_by(
                    field_id=field_id
                ).all()

                assert len(bookings) == 1, (
                    f"Expected 1 booking, got {len(bookings)}"
                )

                assert bookings[0].total_price == 1600, (
                    f"Incorrect price: {bookings[0].total_price}"
                )

            print("PASS: create booking and calculate price")

            # Test 2: Reject overlapping booking.
            overlap = {
                **data,
                "start_time": "11:00",
                "hours": "2",
                "csrf_token": token,
            }

            response = client.post(
                f"/book/{field_id}",
                data=overlap,
                follow_redirects=False,
            )

            assert response.status_code in (302, 303), (
                f"Overlap: HTTP {response.status_code}"
            )

            with app.app_context():
                count = Booking.query.filter_by(
                    field_id=field_id
                ).count()

                assert count == 1, (
                    f"Overlapping booking accepted: {count} records"
                )

            print("PASS: reject overlapping booking")

            # Test 3: Reject missing CSRF token.
            response = client.post(
                f"/book/{field_id}",
                data=data,
            )

            assert response.status_code == 400, (
                f"Missing CSRF: HTTP {response.status_code}"
            )

            print("PASS: reject missing CSRF token")

        print("PASS: isolated booking tests")

    finally:
        with app.app_context():
            db.session.remove()
            db.engine.dispose()
