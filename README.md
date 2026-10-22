# Football Booking Platform — MVP Update

This ZIP is a **code-only** update based on the latest `football-booking-platform` in the uploaded archive. It deliberately excludes `venv`, `instance/football.db`, passwords and old backups.

## Install safely
1. Back up your current `football-booking-platform` folder and particularly `instance/football.db`.
2. Stop Flask (Ctrl+C).
3. Copy `app` from this ZIP into your existing `football-booking-platform` folder, replacing the corresponding files. Keep your original `instance` and `venv` folders.
4. Activate your virtual environment and run `python run.py`.
5. Sign in, book a **new** future slot, then open `/my-bookings`. Test cancellation and verify the slot can be rebooked.

## Limitations
- Existing bookings cannot be reliably assigned to user accounts automatically; only bookings made while logged in **after** this update appear in `/my-bookings`.
- This version adds `booking_owners` as a separate table, so it does not need to alter the existing `bookings` table. `db.create_all()` creates this new table.
- Guest booking receipts are visible only during the original browser session. Historical receipts may return 403 until an account-linking process is implemented.
- Payments, admin dashboard, production security and deployment are NOT implemented.
- Set a strong random `SECRET_KEY` environment variable before public deployment. Changing it invalidates existing sessions.
- Do not deploy Flask debug mode publicly. Add rate limiting, migrations, and proper payment integration before real customers use this system.
