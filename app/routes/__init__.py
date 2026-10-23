"""Routes for Football Booking Platform (recovered from supplied project)."""
import hmac
import re
import secrets
from datetime import datetime, timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import Booking, BookingOwner, FootballField, User, Payment

main = Blueprint('main', __name__)


def csrf_for(key):
    if key not in session:
        session[key] = secrets.token_urlsafe(32)
    return session[key]


def valid_csrf(key):
    stored = session.get(key, '')
    provided = request.form.get('csrf_token', '')
    return bool(stored and provided and hmac.compare_digest(stored, provided))


def require_admin():
    user_id = session.get('user_id')

    if not user_id:
        abort(401)

    user = db.session.get(User, user_id)

    if not user or not user.is_admin:
        abort(403)

    return user


@main.route('/')
def home():
    return render_template('home.html')


@main.route('/fields')
def fields():
    available = FootballField.query.filter_by(is_active=True).order_by(FootballField.id).all()
    return render_template('fields.html', fields=available)


@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if not valid_csrf('register_csrf'):
            abort(400, 'คำขอไม่ถูกต้อง กรุณาโหลดหน้าใหม่')
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirmation = request.form.get('confirm_password', '')
        if not (3 <= len(username) <= 80) or not (email and len(email) <= 120 and '@' in email):
            flash('กรุณากรอกชื่อผู้ใช้และอีเมลให้ถูกต้อง', 'error')
        elif len(password) < 8 or password != confirmation:
            flash('รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษรและตรงกัน', 'error')
        elif User.query.filter(or_(User.username == username, User.email == email)).first():
            flash('ชื่อผู้ใช้หรืออีเมลนี้ถูกใช้แล้ว', 'error')
        else:
            user = User(username=username, email=email, is_admin=False)
            user.set_password(password)
            db.session.add(user)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash('ชื่อผู้ใช้หรืออีเมลนี้ถูกใช้แล้ว', 'error')
            else:
                flash('สมัครสมาชิกสำเร็จ กรุณาเข้าสู่ระบบ', 'success')
                return redirect(url_for('main.login'))
    return render_template('register.html', csrf_token=csrf_for('register_csrf'))


@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if not valid_csrf('login_csrf'):
            abort(400, 'คำขอไม่ถูกต้อง กรุณาโหลดหน้าใหม่')
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session.clear()
            session['user_id'] = user.id
            session['username'] = user.username
            csrf_for('logout_csrf_token')
            flash('เข้าสู่ระบบสำเร็จ', 'success')
            return redirect(url_for('main.home'))
        flash('ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง', 'error')
    return render_template('login.html', csrf_token=csrf_for('login_csrf'))


@main.route('/admin/change-password', methods=['GET', 'POST'])
def admin_change_password():
    if not session.get('user_id'):
        return redirect(url_for('main.login'))

    user = db.session.get(User, session['user_id'])

    if user is None or not user.is_admin:
        abort(403)

    if request.method == 'POST':
        if not valid_csrf('admin_password_csrf'):
            abort(400, 'คำขอไม่ถูกต้อง กรุณาโหลดหน้าใหม่')

        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not user.check_password(current_password):
            flash('รหัสผ่านปัจจุบันไม่ถูกต้อง', 'error')
        elif len(new_password) < 12:
            flash('รหัสผ่านใหม่ต้องมีอย่างน้อย 12 ตัวอักษร', 'error')
        elif new_password != confirm_password:
            flash('รหัสผ่านใหม่ทั้งสองช่องไม่ตรงกัน', 'error')
        elif user.check_password(new_password):
            flash('กรุณาใช้รหัสผ่านใหม่ที่แตกต่างจากเดิม', 'error')
        else:
            user.set_password(new_password)
            db.session.commit()
            session.clear()
            flash('เปลี่ยนรหัสผ่านสำเร็จ กรุณาเข้าสู่ระบบใหม่', 'success')
            return redirect(url_for('main.login'))

    return render_template(
        'admin_change_password.html',
        csrf_token=csrf_for('admin_password_csrf')
    )


@main.route('/logout', methods=['POST'])
def logout():
    if not valid_csrf('logout_csrf_token'):
        abort(400, 'คำขอไม่ถูกต้อง')
    session.clear()
    return redirect(url_for('main.home'))


@main.route('/book/<int:field_id>', methods=['GET', 'POST'])
def book_field(field_id):
    field = db.get_or_404(FootballField, field_id)
    if not field.is_active:
        abort(404, 'สนามนี้ยังไม่เปิดให้จอง')
    if request.method == 'POST':
        if not valid_csrf('book_field_csrf'):
            abort(400, 'คำขอไม่ถูกต้อง กรุณาโหลดหน้าใหม่')
        try:
            customer_name = request.form['customer_name'].strip()
            phone = request.form['phone'].strip()
            booking_date = datetime.strptime(request.form['booking_date'], '%Y-%m-%d').date()
            start_time = datetime.strptime(request.form['start_time'], '%H:%M').time()
            hours = int(request.form['hours'])
            if not customer_name or len(customer_name) > 100:
                raise ValueError('กรุณาระบุชื่อผู้จอง')
            if not re.fullmatch(r'[0-9+()\-\s]{9,20}', phone):
                raise ValueError('เบอร์โทรศัพท์ไม่ถูกต้อง')
            if hours not in range(1, 7):
                raise ValueError('เลือกเวลา 1–6 ชั่วโมง')
            start_dt = datetime.combine(booking_date, start_time)
            end_dt = start_dt + timedelta(hours=hours)
            if start_dt <= datetime.now():
                raise ValueError('กรุณาเลือกเวลาในอนาคต')
            if end_dt.date() != booking_date:
                raise ValueError('ไม่รองรับการจองข้ามวัน')
            conflict = Booking.query.filter(
                Booking.field_id == field_id,
                Booking.booking_date == booking_date,
                Booking.status != 'cancelled',
                Booking.start_time < end_dt.time(),
                Booking.end_time > start_time,
            ).first()
            if conflict:
                flash('ช่วงเวลานี้มีผู้จองแล้ว กรุณาเลือกเวลาอื่น', 'error')
                return redirect(url_for('main.book_field', field_id=field_id))
            booking = Booking(
                field_id=field_id, customer_name=customer_name, phone=phone,
                booking_date=booking_date, start_time=start_time,
                end_time=end_dt.time(), total_price=field.price_per_hour * hours,
                status='confirmed',
            )
            db.session.add(booking)
            db.session.flush()
            if session.get('user_id') and db.session.get(User, session['user_id']):
                db.session.add(BookingOwner(booking_id=booking.id, user_id=session['user_id']))
            db.session.commit()
            guest_ids = session.get('guest_booking_ids', [])
            guest_ids.append(booking.id)
            session['guest_booking_ids'] = guest_ids[-30:]
            return redirect(url_for('main.booking_success', booking_id=booking.id))
        except (KeyError, ValueError, TypeError) as exc:
            flash(f'ข้อมูลไม่ถูกต้อง: {exc}', 'error')
        except Exception:
            db.session.rollback()
            raise
    return render_template('booking.html', field=field, csrf_token=csrf_for('book_field_csrf'))


@main.route('/booking/success/<int:booking_id>')
def booking_success(booking_id):
    booking = db.get_or_404(Booking, booking_id)
    owner = db.session.get(BookingOwner, booking_id)
    owned = bool(owner and owner.user_id == session.get('user_id'))
    guest_access = booking_id in session.get('guest_booking_ids', [])
    if not (owned or guest_access or (session.get('user_id') and require_admin_if_present())):
        abort(403)
    return render_template('booking_success.html', booking=booking)


def require_admin_if_present():
    user = db.session.get(User, session['user_id'])
    return bool(user and user.is_admin)


@main.route('/my-bookings')
def my_bookings():
    if not session.get('user_id'):
        return redirect(url_for('main.login'))
    bookings = (Booking.query.join(BookingOwner, BookingOwner.booking_id == Booking.id)
                .filter(BookingOwner.user_id == session['user_id'])
                .order_by(Booking.booking_date.desc(), Booking.start_time.desc()).all())
    return render_template('my_bookings.html', bookings=bookings,
                           csrf_token=csrf_for('booking_action_csrf'))


@main.route('/my-bookings/<int:booking_id>/cancel', methods=['POST'])
def cancel_booking(booking_id):
    if not session.get('user_id'):
        return redirect(url_for('main.login'))

    if not valid_csrf('booking_action_csrf'):
        abort(400, 'คำขอไม่ถูกต้อง')

    booking = db.get_or_404(Booking, booking_id)

    owner = db.session.get(BookingOwner, booking_id)
    if not owner or owner.user_id != session['user_id']:
        abort(403)

    # ป้องกันการยกเลิกการจองที่ชำระเงินแล้ว
    paid_payment = Payment.query.filter_by(
        booking_id=booking.id,
        status='paid'
    ).first()

    if paid_payment:
        flash(
            'รายการนี้ชำระเงินแล้ว ไม่สามารถยกเลิกได้ กรุณาติดต่อเจ้าหน้าที่เพื่อดำเนินการคืนเงิน',
            'error'
        )
        return redirect(url_for('main.my_bookings'))

    # ป้องกันการยกเลิกการจองที่เริ่มไปแล้ว
    if datetime.combine(
        booking.booking_date,
        booking.start_time
    ) <= datetime.now():
        flash('ไม่สามารถยกเลิกการจองที่เริ่มแล้ว', 'error')

    elif booking.status != 'cancelled':
        booking.status = 'cancelled'
        db.session.commit()
        flash('ยกเลิกการจองแล้ว', 'success')

    return redirect(url_for('main.my_bookings'))


@main.route('/admin')
def admin_dashboard():
    if not session.get('user_id'):
        return redirect(url_for('main.login'))

    user = require_admin()

    total_users = User.query.count()
    total_bookings = Booking.query.count()

    confirmed_bookings = Booking.query.filter_by(
        status='confirmed'
    ).count()

    cancelled_bookings = Booking.query.filter_by(
        status='cancelled'
    ).count()

    confirmed_revenue = db.session.query(
        db.func.coalesce(
            db.func.sum(Booking.total_price), 0
        )
    ).filter(
        Booking.status == 'confirmed'
    ).scalar()

    return render_template(
        'admin_dashboard.html',
        user=user,
        total_users=total_users,
        total_bookings=total_bookings,
        confirmed_bookings=confirmed_bookings,
        cancelled_bookings=cancelled_bookings,
        confirmed_revenue=confirmed_revenue
    )



@main.route('/admin/bookings')
def admin_bookings():
    if not session.get('user_id'):
        return redirect(url_for('main.login'))

    require_admin()

    bookings = Booking.query.order_by(
        Booking.booking_date.desc(),
        Booking.start_time.desc()
    ).all()

    payments = {
        payment.booking_id: payment
        for payment in Payment.query.all()
    }

    now = datetime.now()

    return render_template(
        'admin_bookings.html',
        bookings=bookings,
        payments=payments,
        today=now.date(),
        now_time=now.time(),
        csrf_token=csrf_for('admin_booking_csrf')
    )


@main.route('/admin/bookings/<int:booking_id>/status', methods=['POST'])
def admin_update_booking_status(booking_id):
    if not session.get('user_id'):
        return redirect(url_for('main.login'))

    require_admin()

    if not valid_csrf('admin_booking_csrf'):
        abort(400, 'คำขอไม่ถูกต้อง')

    booking = db.get_or_404(Booking, booking_id)
    new_status = request.form.get('status', '')

    if new_status not in ('confirmed', 'cancelled'):
        abort(400, 'สถานะไม่ถูกต้อง')

    if datetime.combine(booking.booking_date, booking.start_time) <= datetime.now():
        flash('ไม่สามารถแก้ไขการจองที่เริ่มแล้ว', 'error')
        return redirect(url_for('main.admin_bookings'))

    if new_status == 'confirmed':
        conflict = Booking.query.filter(
            Booking.id != booking.id,
            Booking.field_id == booking.field_id,
            Booking.booking_date == booking.booking_date,
            Booking.status != 'cancelled',
            Booking.start_time < booking.end_time,
            Booking.end_time > booking.start_time,
        ).first()

        if conflict:
            flash('ไม่สามารถยืนยันได้ เพราะมีรายการจองซ้อน', 'error')
            return redirect(url_for('main.admin_bookings'))

    # ป้องกันการยกเลิกการจองที่ชำระเงินแล้ว
    if new_status == 'cancelled':
        paid_payment = Payment.query.filter_by(
            booking_id=booking.id,
            status='paid'
        ).first()

        if paid_payment:
            flash(
                'รายการนี้ชำระเงินแล้ว ไม่สามารถยกเลิกได้ กรุณาดำเนินการคืนเงินก่อน',
                'error'
            )
            return redirect(url_for('main.admin_bookings'))

    booking.status = new_status
    db.session.commit()

    flash('อัปเดตสถานะการจองสำเร็จ', 'success')
    return redirect(url_for('main.admin_bookings'))


@main.route('/admin/members')
def admin_members():
    if not session.get('user_id'):
        return redirect(url_for('main.login'))

    require_admin()

    keyword = request.args.get('q', '').strip()

    query = User.query

    if keyword:
        query = query.filter(
            db.or_(
                User.username.ilike(f'%{keyword}%'),
                User.email.ilike(f'%{keyword}%')
            )
        )

    members = query.order_by(User.id.asc()).all()

    return render_template(
        'admin_members.html',
        members=members,
        keyword=keyword
    )

@main.route('/admin/members/<int:member_id>/edit', methods=['GET', 'POST'])
def admin_edit_member(member_id):
    if not session.get('user_id'):
        return redirect(url_for('main.login'))

    require_admin()

    member = db.get_or_404(User, member_id)

    if request.method == 'POST':
        if not valid_csrf('admin_member_edit_csrf'):
            abort(400, 'คำขอไม่ถูกต้อง')

        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()

        if not username or not email:
            flash('กรุณากรอกชื่อผู้ใช้และอีเมล', 'error')

        elif len(username) > 80:
            flash('ชื่อผู้ใช้ต้องไม่เกิน 80 ตัวอักษร', 'error')

        elif len(email) > 120:
            flash('อีเมลต้องไม่เกิน 120 ตัวอักษร', 'error')

        elif (
            email.count('@') != 1
            or not email.split('@')[0]
            or '.' not in email.split('@')[1]
            or email.split('@')[1].startswith('.')
            or email.split('@')[1].endswith('.')
            or any(char.isspace() for char in email)
        ):
            flash('รูปแบบอีเมลไม่ถูกต้อง', 'error')

        elif User.query.filter(
            User.username == username,
            User.id != member.id
        ).first():
            flash('ชื่อผู้ใช้นี้ถูกใช้แล้ว', 'error')

        elif User.query.filter(
            User.email == email,
            User.id != member.id
        ).first():
            flash('อีเมลนี้ถูกใช้แล้ว', 'error')

        else:
            member.username = username
            member.email = email

            db.session.commit()

            flash('แก้ไขข้อมูลสมาชิกสำเร็จ', 'success')
            return redirect(url_for('main.admin_members'))

    return render_template(
        'admin_edit_member.html',
        member=member,
        csrf_token=csrf_for('admin_member_edit_csrf')
    )

@main.route('/admin/fields')
def admin_fields():
    if not session.get('user_id'):
        return redirect(url_for('main.login'))
    require_admin()
    all_fields = FootballField.query.order_by(FootballField.id).all()
    return render_template('admin_fields.html', fields=all_fields,
                           csrf_token=csrf_for('admin_fields_csrf'))


@main.route('/admin/fields/<int:field_id>/edit', methods=['GET', 'POST'])
def admin_edit_field(field_id):
    if not session.get('user_id'):
        return redirect(url_for('main.login'))
    require_admin()
    field = db.get_or_404(FootballField, field_id)
    if request.method == 'POST':
        if not valid_csrf('admin_fields_csrf'):
            abort(400, 'คำขอไม่ถูกต้อง')
        name = request.form.get('name', '').strip()
        field_type = request.form.get('field_type', '').strip()
        try:
            price = int(request.form.get('price_per_hour', ''))
        except ValueError:
            price = 0
        active = request.form.get('is_active') == 'on'
        if not (1 <= len(name) <= 100 and 1 <= len(field_type) <= 50 and 1 <= price <= 1000000):
            flash('กรุณากรอกชื่อ ประเภท และราคาสนามให้ถูกต้อง', 'error')
        else:
            field.name = name
            field.field_type = field_type
            field.price_per_hour = price
            field.is_active = active
            db.session.commit()
            flash('บันทึกข้อมูลสนามเรียบร้อย', 'success')
            return redirect(url_for('main.admin_fields'))
    return render_template('admin_edit_field.html', field=field,
                           csrf_token=csrf_for('admin_fields_csrf'))


@main.route('/admin/revenue')
def admin_revenue():
    if not session.get('user_id'):
        return redirect(url_for('main.login'))
    require_admin()
    rows = (db.session.query(Booking.booking_date,
             db.func.count(Booking.id), db.func.sum(Booking.total_price))
            .filter(Booking.status == 'confirmed')
            .group_by(Booking.booking_date)
            .order_by(Booking.booking_date.desc()).all())
    return render_template('admin_revenue.html', rows=rows,
                           total=sum(int(row[2] or 0) for row in rows))


@main.route('/admin/payments')
def admin_payments():
    if not session.get('user_id'):
        return redirect(url_for('main.login'))

    require_admin()

    payments = (
        Payment.query
        .filter_by(status='paid')
        .order_by(Payment.paid_at.desc())
        .all()
    )

    total_cash = sum(
        p.amount for p in payments
        if p.method == 'cash'
    )

    total_transfer = sum(
        p.amount for p in payments
        if p.method == 'bank_transfer'
    )

    total_paid = sum(p.amount for p in payments)

    return render_template(
        'admin_payments.html',
        payments=payments,
        total_cash=total_cash,
        total_transfer=total_transfer,
        total_paid=total_paid
    )


@main.route('/admin/bookings/<int:booking_id>/payment', methods=['POST'])
def admin_record_payment(booking_id):
    if not session.get('user_id'):
        return redirect(url_for('main.login'))

    require_admin()

    if not valid_csrf('admin_booking_csrf'):
        abort(400, 'คำขอไม่ถูกต้อง')

    booking = db.get_or_404(Booking, booking_id)

    if booking.status != 'confirmed':
        flash('รับชำระเงินได้เฉพาะรายการจองที่ยืนยันแล้ว', 'error')
        return redirect(url_for('main.admin_bookings'))

    method = request.form.get('method', '').strip()

    if method not in ('cash', 'bank_transfer'):
        flash('วิธีชำระเงินไม่ถูกต้อง', 'error')
        return redirect(url_for('main.admin_bookings'))

    existing_payment = Payment.query.filter_by(
        booking_id=booking.id
    ).first()

    if existing_payment:
        flash('รายการนี้มีข้อมูลการชำระเงินแล้ว ไม่สามารถบันทึกซ้ำได้', 'error')
        return redirect(url_for('main.admin_bookings'))

    if booking.total_price <= 0:
        flash('ยอดชำระเงินไม่ถูกต้อง', 'error')
        return redirect(url_for('main.admin_bookings'))

    payment = Payment(
        booking_id=booking.id,
        amount=booking.total_price,
        status='paid',
        method=method,
        provider='manual',
        paid_at=datetime.now()
    )

    db.session.add(payment)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash('รายการนี้ถูกบันทึกการชำระเงินแล้ว', 'error')
        return redirect(url_for('main.admin_bookings'))

    flash('บันทึกการชำระเงินสำเร็จ', 'success')
    return redirect(url_for('main.admin_bookings'))


@main.route('/receipts/<int:booking_id>')
def view_receipt(booking_id):
    if not session.get('user_id'):
        return redirect(url_for('main.login'))

    user = db.session.get(User, session['user_id'])

    if not user:
        abort(403)

    booking = db.get_or_404(Booking, booking_id)

    # อนุญาตเฉพาะ Admin หรือเจ้าของการจอง
    if not user.is_admin:
        owner = db.session.get(BookingOwner, booking_id)

        if not owner or owner.user_id != user.id:
            abort(403)

    # ต้องเป็นรายการที่ชำระเงินแล้วเท่านั้น
    payment = Payment.query.filter_by(
        booking_id=booking.id,
        status='paid'
    ).first()

    if not payment:
        abort(404)

    return render_template(
        'receipt.html',
        booking=booking,
        payment=payment
    )
