# Football Booking Platform — Updated build

This package is based on the supplied Flask project. It adds admin field editing, confirmed-booking-value reporting, and fixes cancelled-booking action labels. It does **not** yet implement payments, QR ordering, loyalty, inventory, staff, or deployment.

## Local installation (Windows PowerShell)

```powershell
py -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe seed.py
.\venv\Scripts\python.exe run.py
```

Visit http://127.0.0.1:5000 . Seed data is intended for development only. Never upload your real `instance/football.db` or `.env` to GitHub. To use existing data, **back up** your current instance directory and copy `football.db` into the new project's `instance/` while the server is stopped. Do not replace or overwrite the only copy.

The revenue page shows *confirmed booking value*, not verified paid revenue. This project requires additional security, integration, and production testing before public deployment. Configure a strong SECRET_KEY for deployment; do not use the development fallback.
