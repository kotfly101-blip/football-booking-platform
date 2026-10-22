
from app import create_app, db
from app.models import FootballField

app = create_app()

fields = [
    ("สนาม A", "11 คน", 1500),
    ("สนาม B", "11 คน", 1500),
    ("สนาม C", "9 คน", 1200),
    ("สนาม D", "ฟุตซอล", 800),
    ("สนาม E", "7 คน", 1000),
]

with app.app_context():
    db.create_all()

    for name, field_type, price in fields:
        existing = FootballField.query.filter_by(name=name).first()

        if existing is None:
            field = FootballField(
                name=name,
                field_type=field_type,
                price_per_hour=price,
                is_active=True
            )
            db.session.add(field)

    db.session.commit()

    print("บันทึกข้อมูลสนามฟุตบอลสำเร็จ")

    for field in FootballField.query.order_by(FootballField.id).all():
        print(
            field.id,
            field.name,
            field.field_type,
            field.price_per_hour
        )
