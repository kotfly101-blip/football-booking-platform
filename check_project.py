"""Read-only Flask smoke check: no booking, payment, or user data is changed."""
import os
import sys

if not os.environ.get("SECRET_KEY"):
    print("ERROR: SECRET_KEY not set. Run in the same terminal as the app.")
    sys.exit(1)

from app import create_app

app = create_app()
checks = []
with app.test_client() as client:
    for path in ("/", "/fields", "/register", "/login"):
        response = client.get(path)
        checks.append((path, response.status_code == 200, response.status_code))
    for path in ("/admin", "/admin/bookings", "/admin/payments", "/admin/revenue"):
        response = client.get(path, follow_redirects=False)
        checks.append((path + " (guest)", response.status_code == 302, response.status_code))

with app.app_context():
    tpl = app.jinja_env.get_template("admin_payments.html")
    source, _, _ = app.jinja_loader.get_source(app.jinja_env, "admin_payments.html")
    checks.append(("payment template class", "payment-card" in source, "present" if "payment-card" in source else "missing"))
    checks.append(("template auto reload disabled", app.jinja_env.auto_reload is False, app.jinja_env.auto_reload))

for label, ok, result in checks:
    print(("PASS" if ok else "FAIL"), label, result)
print("TOTAL:", sum(ok for _, ok, _ in checks), "/", len(checks))
sys.exit(0 if all(ok for _, ok, _ in checks) else 1)
