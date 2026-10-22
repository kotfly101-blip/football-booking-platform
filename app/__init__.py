
import os

from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)

    # ใช้ SECRET_KEY จาก Environment Variable
    secret_key = os.environ.get("SECRET_KEY")

    if not secret_key:
        raise RuntimeError(
            "SECRET_KEY is not configured. "
            "Please set the SECRET_KEY environment variable."
        )

    app.config["SECRET_KEY"] = secret_key

    # ตั้งค่าฐานข้อมูล
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///football.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # ตั้งค่าความปลอดภัยของ Session
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = (
        os.environ.get("COOKIE_SECURE", "false").lower() == "true"
    )

    # เชื่อมต่อฐานข้อมูล
    db.init_app(app)

    # โหลด Models
    from app import models

    # สร้างตารางที่ยังไม่มี
    with app.app_context():
        db.create_all()

    # ลงทะเบียน Routes
    from app.routes import main
    app.register_blueprint(main)

    # ส่งสถานะ Admin ไปยัง Templates
    @app.context_processor
    def inject_admin_status():
        from app.models import User

        user_id = session.get("user_id")
        is_admin = False

        if user_id:
            user = db.session.get(User, user_id)
            is_admin = bool(user and user.is_admin)

        return {"is_admin": is_admin}

    return app
