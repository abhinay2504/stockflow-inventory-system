# StockFlow MVP

A server-backed multi-tenant inventory management MVP built with Python, Flask, SQLite, server-rendered HTML/CSS.

## Features
- Signup/login with email validation and scrypt password hashes. Signup enforces 8–128 characters, uppercase, lowercase, a number, and a special character.
- Signed server sessions, HTTP-only and SameSite cookies, CSRF protection on every POST.
- Signup creates an organization; one owner per organization in this MVP.
- Product CRUD; database-enforced SKU uniqueness per organization.
- Quantity, optional cost/selling prices, description and optional per-product threshold.
- Dashboard product/unit summaries and low-stock alerts.
- Product search/status filters and organization name/default threshold settings.
- Server-side organization scoping on every product read/update/delete.

## Run locally
Python 3.10+ recommended.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
# Set SECRET_KEY before starting (PowerShell example below)
$env:SECRET_KEY = (python -c "import secrets; print(secrets.token_hex(32))")
python app.py
```

Open http://127.0.0.1:5000.

For deployment, configure a long random `SECRET_KEY`, set `COOKIE_SECURE=1` behind HTTPS, and configure a persistent writable database path using `STOCKFLOW_DB`. SQLite is suitable for this demo; production multi-instance usage should use managed PostgreSQL.

## Tests
Run the Flask integration suite (dependencies required):

```bash
python -m unittest -v test_app.py
```

Browser tests require Playwright and Chromium; see `requirements-test.txt` and `tests/e2e_playwright.py`.

## MVP boundaries
Password reset, email verification, staff/invites, roles, stock movement history, warehouses, orders, integrations, CSV import, external API, billing, and audit logs are out of scope.

