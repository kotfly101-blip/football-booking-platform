"""Isolated tests for admin booking status changes.

Uses a temporary SQLite database, not the production database.
"""

import os
import secrets
import tempfile
from datetime import date, time, timedelta
from pathlib import Path

with tempfile.TemporaryDirectory(prefix="football_admin_test_") as folder:
    database = Path(folder) / "admin_test.db"

    os.environ["DATABASE_URL"] = "sqlite:///" + database.as_posix()
    os.environ["SECRET_KEY"] = secrets.token_hex(32)
    os.environ["COOKIE_SECURE"] = "false"

    from app import create_app, db
    from app.models import Booking, FootballField, Payment, User

    app = create_app()
    app.config["TESTING"] = True

    def make_booking(field_id, start_hour, end_hour, status="confirmed"):
        booking = Booking(
            field_id=field_id,
            customer_name="Admin Test Customer",
            phone="0800000000",
            booking_date=date.today() + timedelta(days=14),
            start_time=time(start_hour, 0),
            end_time=time(end_hour, 0),
            total_price=(end_hour - start_hour) * 800,
            status=status,
        )
        db.session.add(booking)
        db.session.commit()
        return booking.id

    def get_status(booking_id):
        with app.app_context():
            return db.session.get(Booking, booking_id).status

    try:
        with app.app_context():
            db.create_all()

            field = FootballField(
                name="Admin Test Field",
                field_type="7-a-side",
                price_per_hour=800,
                is_active=True,
            )

            admin = User(
                username="admin_test",
                email="admin@example.test",
                is_admin=True,
            )
            admin.set_password(secrets.token_urlsafe(20))

            member = User(
                username="member_test",
                email="member@example.test",
                is_admin=False,
            )
            member.set_password(secrets.token_urlsafe(20))

            db.session.add_all([field, admin, member])
            db.session.commit()

            field_id = field.id
            admin_id = admin.id
            member_id = member.id

            booking_id = make_booking(
                field_id, 10, 12, status="cancelled"
            )

        url = f"/admin/bookings/{booking_id}/status"

        with app.test_client() as client:
            # 1. Unauthenticated access
            response = client.post(
                url, data={"status": "confirmed"}
            )
            assert response.status_code == 302, response.status_code
            assert get_status(booking_id) == "cancelled"
            print("PASS: unauthenticated admin access blocked")

            # 2. Non-admin access
            with client.session_transaction() as sess:
                sess["user_id"] = member_id
                sess["admin_booking_csrf"] = "test-token"

            response = client.post(
                url,
                data={
                    "status": "confirmed",
                    "csrf_token": "test-token",
                },
            )
            assert response.status_code == 403, response.status_code
            assert get_status(booking_id) == "cancelled"
            print("PASS: non-admin access blocked")

            # Log in as test admin
            with client.session_transaction() as sess:
                sess["user_id"] = admin_id
                sess["admin_booking_csrf"] = "test-token"

            # 3. Invalid CSRF
            response = client.post(
                url,
                data={
                    "status": "confirmed",
                    "csrf_token": "wrong-token",
                },
            )
            assert response.status_code == 400, response.status_code
            assert get_status(booking_id) == "cancelled"
            print("PASS: invalid CSRF rejected")

            # 4. Invalid status
            response = client.post(
                url,
                data={
                    "status": "invalid",
                    "csrf_token": "test-token",
                },
            )
            assert response.status_code == 400, response.status_code
            assert get_status(booking_id) == "cancelled"
            print("PASS: invalid booking status rejected")

            # 5. Confirm booking
            response = client.post(
                url,
                data={
                    "status": "confirmed",
                    "csrf_token": "test-token",
                },
            )
            assert response.status_code == 302, response.status_code
            assert get_status(booking_id) == "confirmed"
            print("PASS: admin confirms booking")

            # 6. Reject overlapping booking
            with app.app_context():
                overlapping_id = make_booking(
                    field_id, 11, 13, status="cancelled"
                )

            response = client.post(
                f"/admin/bookings/{overlapping_id}/status",
                data={
                    "status": "confirmed",
                    "csrf_token": "test-token",
                },
            )
            assert response.status_code == 302, response.status_code
            assert get_status(overlapping_id) == "cancelled"
            print("PASS: overlapping booking confirmation denied")

            # 7. Reject cancellation of paid booking
            with app.app_context():
                db.session.add(
                    Payment(
                        booking_id=booking_id,
                        amount=1600,
                        status="paid",
                        method="cash",
                    )
                )
                db.session.commit()

            response = client.post(
                url,
                data={
                    "status": "cancelled",
                    "csrf_token": "test-token",
                },
            )
            assert response.status_code == 302, response.status_code
            assert get_status(booking_id) == "confirmed"
            print("PASS: paid booking cancellation denied")

            # 8. Allow cancellation of unpaid booking
            with app.app_context():
                unpaid_id = make_booking(
                    field_id, 14, 16, status="confirmed"
                )

            response = client.post(
                f"/admin/bookings/{unpaid_id}/status",
                data={
                    "status": "cancelled",
                    "csrf_token": "test-token",
                },
            )
            assert response.status_code == 302, response.status_code
            assert get_status(unpaid_id) == "cancelled"
            print("PASS: unpaid booking cancelled")

        print("PASS: all isolated admin tests")

    finally:
        with app.app_context():
            db.session.remove()
            db.engine.dispose()