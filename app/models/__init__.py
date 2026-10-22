
from app import db


class FootballField(db.Model):
    __tablename__ = "football_fields"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)

    field_type = db.Column(db.String(50), nullable=False)

    price_per_hour = db.Column(db.Integer, nullable=False)

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)

    field_id = db.Column(
        db.Integer,
        db.ForeignKey("football_fields.id"),
        nullable=False
    )

    customer_name = db.Column(
        db.String(100),
        nullable=False
    )

    phone = db.Column(
        db.String(20),
        nullable=False
    )

    booking_date = db.Column(
        db.Date,
        nullable=False
    )

    start_time = db.Column(
        db.Time,
        nullable=False
    )

    end_time = db.Column(
        db.Time,
        nullable=False
    )

    total_price = db.Column(
        db.Integer,
        nullable=False
    )

    status = db.Column(
        db.String(20),
        default="confirmed",
        nullable=False
    )

    field = db.relationship(
        "FootballField",
        backref="bookings"
    )

from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class BookingOwner(db.Model):
    """Maps bookings to accounts without changing the existing bookings table."""
    __tablename__ = "booking_owners"
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    
class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)

    booking_id = db.Column(
        db.Integer,
        db.ForeignKey("bookings.id"),
        nullable=False,
        unique=True,
        index=True
    )

    amount = db.Column(db.Integer, nullable=False)

    status = db.Column(
        db.String(20),
        nullable=False,
        default="pending"
    )

    method = db.Column(db.String(30), nullable=True)

    provider = db.Column(db.String(50), nullable=True)

    transaction_ref = db.Column(
        db.String(100),
        nullable=True,
        unique=True
    )

    paid_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=db.func.now()
    )

    booking = db.relationship(
        "Booking",
        backref=db.backref(
            "payment",
            uselist=False
        )
    )

