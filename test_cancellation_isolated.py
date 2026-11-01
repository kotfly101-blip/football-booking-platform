"""Isolated cancellation tests. Never opens the real instance/football.db."""
import os
import secrets
import tempfile
from datetime import datetime, timedelta, time
from pathlib import Path

with tempfile.TemporaryDirectory(prefix="football_cancel_test_") as folder:
    db_path = Path(folder) / "cancel_test.db"
    os.environ["DATABASE_URL"] = "sqlite:///" + db_path.as_posix()
    os.environ["SECRET_KEY"] = secrets.token_hex(32)
    os.environ["COOKIE_SECURE"] = "false"

    from app import create_app, db
    from app.models import Booking, BookingOwner, FootballField, Payment, User

    app = create_app()
    app.config["TESTING"] = True
    try:
        with app.app_context():
            field = FootballField(name="สนามทดสอบ A", field_type="7-a-side", price_per_hour=800, is_active=True)
            owner = User(username="testfootball01", email="testfootball01@example.invalid", is_admin=False)
            owner.set_password("TestOnly2026!Strong")
            stranger = User(username="testfootball02", email="testfootball02@example.invalid", is_admin=False)
            stranger.set_password("TestOnly2026!Strong")
            db.session.add_all([field, owner, stranger])
            db.session.flush()
            owner_id, stranger_id = owner.id, stranger.id
            future = (datetime.now() + timedelta(days=14)).date()
            past = (datetime.now() - timedelta(days=14)).date()
            bookings = []
            for day in [future, future, future, past]:
                b = Booking(field_id=field.id, customer_name="สมชาย ทดสอบ", phone="0800000000",
                            booking_date=day, start_time=time(10, 0), end_time=time(12, 0),
                            total_price=1600, status="confirmed")
                db.session.add(b)
                db.session.flush()
                db.session.add(BookingOwner(booking_id=b.id, user_id=owner_id))
                bookings.append(b.id)
            db.session.add(Payment(booking_id=bookings[2], amount=1600, status="paid"))
            db.session.commit()

        def status(booking_id):
            with app.app_context():
                return db.session.get(Booking, booking_id).status

        with app.test_client() as client:
            cancel_url = lambda bid: f"/my-bookings/{bid}/cancel"
            response = client.post(cancel_url(bookings[0]), follow_redirects=False)
            assert response.status_code in (302, 303), f"Unauthenticated: HTTP {response.status_code}"
            assert status(bookings[0]) == "confirmed"
            print("PASS: unauthenticated cancellation blocked")

            with client.session_transaction() as sess:
                sess["user_id"] = owner_id
            response = client.get("/my-bookings")
            assert response.status_code == 200, f"My bookings: HTTP {response.status_code}"
            with client.session_transaction() as sess:
                token = sess["booking_action_csrf"]

            response = client.post(cancel_url(bookings[0]))
            assert response.status_code == 400, f"Missing CSRF: HTTP {response.status_code}"
            assert status(bookings[0]) == "confirmed"
            print("PASS: missing CSRF rejected")

            with client.session_transaction() as sess:
                sess["user_id"] = stranger_id
            response = client.post(cancel_url(bookings[0]), data={"csrf_token": token})
            assert response.status_code == 403, f"Not owner: HTTP {response.status_code}"
            assert status(bookings[0]) == "confirmed"
            print("PASS: non-owner cancellation rejected")

            with client.session_transaction() as sess:
                sess["user_id"] = owner_id
            response = client.post(cancel_url(bookings[2]), data={"csrf_token": token})
            assert response.status_code in (302, 303), f"Paid booking: HTTP {response.status_code}"
            assert status(bookings[2]) == "confirmed"
            print("PASS: paid booking cannot be cancelled")

            response = client.post(cancel_url(bookings[3]), data={"csrf_token": token})
            assert response.status_code in (302, 303), f"Past booking: HTTP {response.status_code}"
            assert status(bookings[3]) == "confirmed"
            print("PASS: started booking cannot be cancelled")

            response = client.post(cancel_url(bookings[0]), data={"csrf_token": token})
            assert response.status_code in (302, 303), f"Valid cancellation: HTTP {response.status_code}"
            assert status(bookings[0]) == "cancelled"
            print("PASS: owner can cancel future unpaid booking")

            response = client.post(cancel_url(bookings[0]), data={"csrf_token": token})
            assert response.status_code in (302, 303), f"Repeat cancellation: HTTP {response.status_code}"
            assert status(bookings[0]) == "cancelled"
            print("PASS: repeated cancellation leaves status unchanged")

        print("PASS: isolated cancellation tests")
    finally:
        with app.app_context():
            db.session.remove()
            db.engine.dispose()
