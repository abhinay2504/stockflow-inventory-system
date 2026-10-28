"""Browser E2E smoke test for a locally running StockFlow Flask server.

Install test dependencies with: pip install -r requirements-test.txt
Start the app separately with: python app.py
Run with: python tests/e2e_playwright.py
"""
import os
import re
import uuid
from playwright.sync_api import sync_playwright, expect

BASE_URL = os.environ.get("STOCKFLOW_BASE_URL", "http://127.0.0.1:5000")
EMAIL = f"e2e-{uuid.uuid4().hex[:10]}@example.test"
PASSWORD = "StrongPass123!"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        response = page.goto(BASE_URL + "/signup", wait_until="domcontentloaded")
        assert response and response.status == 200, "Signup page did not load"

        # Verify the browser rejects a punctuation-only organization name.
        page.locator("#organizationName").fill("!!!")
        page.locator("input[name=email]").fill(EMAIL)
        page.locator("#password").fill(PASSWORD)
        page.locator("#confirmPassword").fill(PASSWORD)
        page.get_by_role("button", name="Create account").click()
        assert page.locator("#organizationName").evaluate("el => el.validity.valid") is False
        expect(page.locator("#organizationNameMessage")).to_contain_text("include a letter or number")
        assert "/signup" in page.url, "Invalid organization name unexpectedly submitted"

        # Valid international organization name should be accepted and normalized.
        page.locator("#organizationName").fill("  Café   E2E Store  ")
        assert page.locator("#organizationName").evaluate("el => el.validity.valid") is True
        page.get_by_role("button", name="Create account").click()
        expect(page).to_have_url(re.compile(r".*/dashboard$"))
        expect(page.get_by_role("heading", name="Good to see you again")).to_be_visible()

        # Create product and check it appears in the catalog/dashboard low-stock UI.
        page.get_by_role("link", name="Add product").first.click()
        page.locator('input[name="name"]').fill("E2E Test Widget")
        page.locator('input[name="sku"]').fill("E2E-" + uuid.uuid4().hex[:6].upper())
        page.locator('input[name="quantity"]').fill("2")
        page.locator('input[name="cost_price"]').fill("10.50")
        page.locator('input[name="selling_price"]').fill("15.00")
        page.get_by_role("button", name="Save product").click()
        expect(page.get_by_text("E2E Test Widget").first).to_be_visible()
        page.goto(BASE_URL + "/dashboard")
        expect(page.get_by_text("E2E Test Widget").first).to_be_visible()
        expect(page.get_by_text("2 left")).to_be_visible()

        # Organization name validation must also be active in Settings.
        page.goto(BASE_URL + "/settings")
        page.locator("#settingsOrganizationName").fill("!!!")
        page.get_by_role("button", name="Save settings").click()
        assert page.locator("#settingsOrganizationName").evaluate("el => el.validity.valid") is False
        expect(page.locator("#settingsOrganizationNameMessage")).to_contain_text("include a letter or number")

        # Logout and verify protected pages redirect to login.
        page.locator('form[action="/logout"] button').click()
        expect(page).to_have_url(re.compile(r".*/login$"))
        page.goto(BASE_URL + "/dashboard")
        expect(page).to_have_url(re.compile(r".*/login$"))
        browser.close()
    print("PASS: browser E2E signup, organization-name validation, product flow, low-stock dashboard, settings validation, and logout")


if __name__ == "__main__":
    main()
