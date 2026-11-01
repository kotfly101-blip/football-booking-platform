"""Test booking behavior using a disposable SQLite database only."""
import os
import secrets
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

with tempfile.TemporaryDirectory(prefix="football_booking_test_") as folder:
    database = Path(folder) / "booking_test.db"
    os.environ["DATABASE_URL"] = "sqlite:///" + database.as_posix()
    os.environ["SECRET_KEY"] = secrets.token_hex(32)
    os.environ["COOKIE_SECURE"] = "false"

    from app import create_app, db
    from app.models import Booking, FootballField

    app = create_app()
    app.config["TESTING"] = True
    try:
        with app.app_context():
            field = FootballField(name="สนามทดสอบ A", field_type="7-a-side", price_per_hour=800, is_active=True)
            db.session.add(field)
            db.session.commit()
            field_id = field.id

        # Use a date safely in the future and an hour that does not cross midnight.
        booking_date = (datetime.now() + timedelta(days=14)).date().isoformat()
        data = {
            "customer_name": "สมชาย ทดสอบ",
            "phone": "0800000000",
            "booking_date": booking_date,
            "start_time": "10:00",
            "hours": "2",
        }

        with app.test_client() as client:
            response = client.get(f"/book/{field_id}")
            assert response.status_code == 200, f"Booking form: HTTP {response.status_code}"
            with client.session_transaction() as sess:
                token = sess["book_field_csrf"]
            response = client.post(f"/book/{field_id}", data={**data, "csrf_token": token}, follow_redirects=False)
            assert response.status_code in (302, 303), f"First booking: HTTP {response.status_code}"
            with app.app_context():
                bookings = Booking.query.filter_by(field_id=field_id).all()
                assert len(bookings) == 1, f"Expected 1 booking, got {len(bookings)}"
                assert bookings[0].total_price == 1600, f"Incorrect price: {bookings[0].total_price}"
            print("PASS: create booking and calculate price")

            # Overlapping reservation must not create a second booking.
            overlap = {**data, "start_time": "11:00", "hours": "2", "csrf_token": token}
            response = client.post(f"/book/{field_id}", data=overlap, follow_redirects=False)
            assert response.status_code in (302, 303), f"Overlap: HTTP {response.status_code}"
            with app.app_context():
                count = Booking.query.filter_by(field_id=field_id).count()
                assert count == 1, f"Overlapping booking accepted: {count} records"
            print("PASS: reject overlapping booking")

            # Missing CSRF token must be rejected.
            response = client.post(f"/book/{field_id}", data=data)
            assert response.status_code == 400, f"Missing CSRF: HTTP {response.status_code}"
            print("PASS: reject missing CSRF token")

        print("PASS: isolated booking tests")
    finally:
        with app.app_context():
            db.session.remove()
            db.engine.dispose()
