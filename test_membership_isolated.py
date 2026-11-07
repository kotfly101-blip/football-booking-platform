
"""Isolated membership and admin access tests."""

import os
import secrets
import tempfile
from pathlib import Path

from sqlalchemy.pool import NullPool

with tempfile.TemporaryDirectory(prefix="football_member_test_") as folder:
    db_path = Path(folder) / "members.db"

    os.environ["DATABASE_URL"] = "sqlite:///" + db_path.as_posix()
    os.environ["SECRET_KEY"] = secrets.token_hex(32)
    os.environ["COOKIE_SECURE"] = "false"

    from app import create_app, db
    from app.models import User

    app = create_app()
    app.config["TESTING"] = True

    with app.app_context():
        db.create_all()

    try:
        with app.test_client() as client:

            # 1. Register a fictional member.
            client.get("/register")

            with client.session_transaction() as sess:
                csrf = sess["register_csrf"]

            response = client.post(
                "/register",
                data={
                    "username": "testfootball01",
                    "email": "testfootball01@example.com",
                    "password": "TestOnly2026!Strong",
                    "confirm_password": "TestOnly2026!Strong",
                    "csrf_token": csrf,
                },
                follow_redirects=False,
            )

            with app.app_context():
                member = User.query.filter_by(
                    username="testfootball01"
                ).first()

                assert member is not None, "Registration failed"
                assert member.is_admin is False

            print("PASS: member registration")

            # 2. Log in with the test member.
            client.get("/login")

            with client.session_transaction() as sess:
                csrf = sess["login_csrf"]

            response = client.post(
                "/login",
                data={
                    "username": "testfootball01",
                    "password": "TestOnly2026!Strong",
                    "csrf_token": csrf,
                },
                follow_redirects=False,
            )

            with client.session_transaction() as sess:
                assert sess.get("user_id"), "Login failed"

            print("PASS: member login")

            # 3. Regular members cannot access Admin.
            response = client.get("/admin")
            assert response.status_code == 403, (
                f"Expected 403, got {response.status_code}"
            )

            print("PASS: admin access denied")
            print("PASS: membership security tests")

    finally:
        with app.app_context():
            db.session.remove()
            db.engine.dispose()
