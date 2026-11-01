"""Isolated tests for admin manual payment recording. Does not touch production DB."""
import os
import secrets
import tempfile
from datetime import datetime, timedelta, time
from pathlib import Path

with tempfile.TemporaryDirectory(prefix="football_payment_test_") as folder:
    db_path = Path(folder) / "payment_test.db"
    os.environ["DATABASE_URL"] = "sqlite:///" + db_path.as_posix()
    os.environ["SECRET_KEY"] = secrets.token_hex(32)
    os.environ["COOKIE_SECURE"] = "false"

    from app import create_app, db
    from app.models import Booking, FootballField, Payment, User

    app = create_app()
    app.config["TESTING"] = True
    try:
        with app.app_context():
            field = FootballField(name="สนามทดสอบ A", field_type="7-a-side", price_per_hour=800, is_active=True)
            admin = User(username="footballadmin", email="footballadmin@example.invalid", is_admin=True)
            admin.set_password("TestOnly2026!Strong")
            member = User(username="testfootball01", email="testfootball01@example.invalid", is_admin=False)
            member.set_password("TestOnly2026!Strong")
            db.session.add_all([field, admin, member])
            db.session.flush()
            admin_id, member_id = admin.id, member.id
            future = (datetime.now() + timedelta(days=14)).date()
            ids = []
            for status, price in [("confirmed", 1600), ("confirmed", 900), ("cancelled", 800), ("confirmed", 0), ("confirmed", 700)]:
                booking = Booking(field_id=field.id, customer_name="สมชาย ทดสอบ", phone="0800000000",
                                  booking_date=future, start_time=time(10), end_time=time(12),
                                  total_price=price, status=status)
                db.session.add(booking)
                db.session.flush()
                ids.append(booking.id)
            db.session.commit()

        def payment_count(booking_id):
            with app.app_context():
                return Payment.query.filter_by(booking_id=booking_id).count()

        def payment_for(booking_id):
            with app.app_context():
                p = Payment.query.filter_by(booking_id=booking_id).first()
                return None if p is None else (p.amount, p.method, p.status, p.provider, p.paid_at)

        url = lambda bid: f"/admin/bookings/{bid}/payment"
        with app.test_client() as client:
            r = client.post(url(ids[0]), data={"method": "cash"})
            assert r.status_code in (302, 303) and payment_count(ids[0]) == 0
            print("PASS: unauthenticated payment blocked")

            with client.session_transaction() as sess:
                sess["user_id"] = member_id
                sess["admin_booking_csrf"] = secrets.token_urlsafe(32)
                token = sess["admin_booking_csrf"]
            r = client.post(url(ids[0]), data={"method": "cash", "csrf_token": token})
            assert r.status_code == 403 and payment_count(ids[0]) == 0
            print("PASS: non-admin payment blocked")

            with client.session_transaction() as sess:
                sess["user_id"] = admin_id
            r = client.post(url(ids[0]), data={"method": "cash"})
            assert r.status_code == 400 and payment_count(ids[0]) == 0
            print("PASS: missing CSRF rejected")

            r = client.post(url(ids[0]), data={"method": "card", "csrf_token": token})
            assert r.status_code in (302, 303) and payment_count(ids[0]) == 0
            print("PASS: invalid payment method rejected")

            r = client.post(url(ids[2]), data={"method": "cash", "csrf_token": token})
            assert r.status_code in (302, 303) and payment_count(ids[2]) == 0
            print("PASS: cancelled booking payment rejected")

            r = client.post(url(ids[3]), data={"method": "cash", "csrf_token": token})
            assert r.status_code in (302, 303) and payment_count(ids[3]) == 0
            print("PASS: zero-amount payment rejected")

            r = client.post(url(ids[0]), data={"method": "cash", "csrf_token": token})
            p = payment_for(ids[0])
            assert r.status_code in (302, 303) and p is not None
            assert p[0] == 1600 and p[1] == "cash" and p[2] == "paid" and p[3] == "manual" and p[4] is not None
            print("PASS: cash payment recorded correctly")

            r = client.post(url(ids[1]), data={"method": "bank_transfer", "csrf_token": token})
            p = payment_for(ids[1])
            assert r.status_code in (302, 303) and p is not None
            assert p[0] == 900 and p[1] == "bank_transfer" and p[2] == "paid"
            print("PASS: bank transfer payment recorded correctly")

            r = client.post(url(ids[0]), data={"method": "cash", "csrf_token": token})
            assert r.status_code in (302, 303) and payment_count(ids[0]) == 1
            print("PASS: duplicate payment rejected")

            with app.app_context():
                paid = Payment.query.filter_by(status="paid").all()
                assert len(paid) == 2 and sum(p.amount for p in paid) == 2500
            print("PASS: paid totals are correct")

        print("PASS: isolated payment tests")
    finally:
        with app.app_context():
            db.session.remove()
            db.engine.dispose()
