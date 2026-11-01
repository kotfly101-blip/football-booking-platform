
"""Test Flask with a temporary SQLite database, without touching production data."""

import os
import secrets
import tempfile
from pathlib import Path

from sqlalchemy import event

# Keep the original environment settings so they can be restored.
original_database_url = os.environ.get("DATABASE_URL")
original_secret_key = os.environ.get("SECRET_KEY")
original_cookie_secure = os.environ.get("COOKIE_SECURE")

try:
    with tempfile.TemporaryDirectory(prefix="football_smoke_") as directory:
        db_path = Path(directory) / "smoke.db"

        # Use an isolated test database.
        os.environ["DATABASE_URL"] = (
            "sqlite:///" + db_path.as_posix()
        )
        os.environ["SECRET_KEY"] = secrets.token_hex(32)
        os.environ["COOKIE_SECURE"] = "false"

        from app import create_app, db

        app = create_app()
        app.config["TESTING"] = True

        try:
            with app.test_client() as client:
                paths = (
                    "/",
                    "/fields",
                    "/login",
                    "/register",
                )

                for path in paths:
                    response = client.get(path)
                    print(f"{path}: HTTP {response.status_code}")

                    assert response.status_code == 200, (
                        f"Unexpected status at {path}: "
                        f"{response.status_code}"
                    )

            print("PASS: isolated smoke test")

        finally:
            # Release SQLAlchemy connections before Windows
            # attempts to delete the temporary database.
            with app.app_context():
                db.session.remove()
                db.engine.dispose()

finally:
    # Restore the environment variables.
    for name, original_value in (
        ("DATABASE_URL", original_database_url),
        ("SECRET_KEY", original_secret_key),
        ("COOKIE_SECURE", original_cookie_secure),
    ):
        if original_value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = original_value
