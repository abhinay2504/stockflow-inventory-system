# StockFlow MVP Test Report

## Changes in this revision
- Added server-side organization-name validation to signup and Settings.
- Organization names are trimmed and repeated whitespace is collapsed.
- Valid names must be 2–80 characters, contain at least one Unicode letter or number, and contain no control characters. Common punctuation and international names are allowed.
- Added browser-side feedback for invalid organization names on signup and Settings.
- Added integration tests for blank, whitespace-only, one-character, punctuation-only, overlong, control-character, normalized, and international organization names.
- Added a Playwright browser E2E script for signup, validation, product creation, low-stock dashboard, settings validation, and logout.

## Checks run in this build environment
- Python syntax compilation for app and test modules: PASS.
- Server-side validation function checks (14 cases across organization names and passwords): PASS.
- JavaScript syntax checks for signup and Settings scripts: PASS.
- Full Flask integration test suite: NOT RUN. Flask is not installed in this environment and package download failed because outbound network/DNS is unavailable.
- Real browser E2E against the Flask server: NOT RUN. The Flask server could not be started here; the Playwright E2E script is included for execution on a machine with the declared dependencies installed.

Do not interpret source-level checks as proof that the complete application has passed end-to-end testing. Run the commands below before deployment.

## Run integration tests locally
```bash
python -m pip install -r requirements.txt
python -m unittest -v test_app.py
```

## Run browser E2E locally
Terminal 1:
```bash
python app.py
```
Terminal 2:
```bash
python -m pip install -r requirements-test.txt
python -m playwright install chromium
python tests/e2e_playwright.py
```

## Follow-up fixes after Windows test run (2026-10-28)

The first user-run test execution exposed three test-suite issues. Fixed in this package:

- Database inspection connections in `test_app.py` now use `contextlib.closing(...)` so SQLite files can be deleted on Windows after each test.
- The negative-quantity test now asserts the actual server-side message (`quantity must be between 0 and 2000000000`).
- The browser E2E product assertions now use the first matching product text, avoiding Playwright strict-mode errors when the product appears in more than one UI location.

Python compilation passed after these edits. The complete Flask integration and browser suites still need to be rerun on the user's Windows machine to confirm all runtime checks pass.
