from __future__ import annotations

import re
import unittest
from typing import TYPE_CHECKING, Any, Optional

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings

if TYPE_CHECKING:
    from playwright.sync_api import Browser, BrowserContext, Page, Playwright

sync_playwright_fn: Any = None
axe_runner_factory: Any = None

try:
    from axe_playwright_python.sync_playwright import Axe as imported_axe_runner
    from playwright.sync_api import sync_playwright as imported_sync_playwright

    sync_playwright_fn = imported_sync_playwright
    axe_runner_factory = imported_axe_runner
    PLAYWRIGHT_TESTS_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_TESTS_AVAILABLE = False


@unittest.skipUnless(
    PLAYWRIGHT_TESTS_AVAILABLE,
    "Playwright browser tests require dependencies from requirements-dev.txt.",
)
@override_settings(ALLOWED_HOSTS=["127.0.0.1", "localhost", "testserver", "[::1]"])
class PollBrowserTests(StaticLiveServerTestCase):
    playwright: Optional["Playwright"] = None
    browser: Optional["Browser"] = None
    axe: Any = None
    context: Optional["BrowserContext"] = None
    page: Optional["Page"] = None

    def setUp(self) -> None:
        if sync_playwright_fn is None or axe_runner_factory is None:
            raise unittest.SkipTest(
                "Playwright browser tests require dependencies from requirements-dev.txt."
            )

        try:
            self.playwright = sync_playwright_fn().start()
            self.browser = self.playwright.chromium.launch()
            self.context = self.browser.new_context(base_url=self.live_server_url)
            self.page = self.context.new_page()
            self.axe = axe_runner_factory()
        except Exception as exc:  # pragma: no cover
            self._cleanup_playwright_session()
            raise unittest.SkipTest(
                "Playwright browsers are not installed. Run `make install-browser`."
            ) from exc

        self.addCleanup(self._cleanup_playwright_session)
        self.page.set_default_timeout(15000)

    def _cleanup_playwright_session(self) -> None:
        if self.page is not None:
            self.page.close()
            self.page = None
        if self.context is not None:
            self.context.close()
            self.context = None
        if self.browser is not None:
            self.browser.close()
            self.browser = None
        if self.playwright is not None:
            self.playwright.stop()
            self.playwright = None

    def require_page(self) -> "Page":
        if self.page is None:
            raise unittest.SkipTest("Playwright page is not available for this test run.")
        return self.page

    def require_axe(self) -> Any:
        if self.axe is None:
            raise unittest.SkipTest("axe runner is not available for this test run.")
        return self.axe

    def open_home_page(self) -> None:
        page = self.require_page()
        page.goto("/", wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.locator("#app").wait_for(state="visible")
        page.get_by_role("heading", name="TimePoll").wait_for()

    def login(self, *, name: str = "playwright-user", pin: str = "1234") -> None:
        page = self.require_page()
        page.get_by_role("button", name="Login").click()
        dialog = page.get_by_role("dialog")
        dialog.get_by_label("Name").fill(name)
        dialog.get_by_label("PIN code").fill(pin)
        dialog.get_by_role("button", name="Login").click()
        page.get_by_role("button", name="Logout").wait_for()

    def assert_no_axe_violations(self, results: Any) -> None:
        violations = list(results.response.get("violations", []))
        details = "\n".join(
            f"- {item['id']}: {item['help']} ({len(item.get('nodes', []))} nodes)"
            for item in violations[:5]
        )
        self.assertEqual(results.violations_count, 0, details)

    def test_home_page_has_no_accessibility_violations(self) -> None:
        self.open_home_page()
        page = self.require_page()
        axe = self.require_axe()
        results = axe.run(page)
        self.assert_no_axe_violations(results)

    def test_user_can_login_and_create_poll(self) -> None:
        self.open_home_page()
        self.login()
        page = self.require_page()

        page.get_by_role("button", name="Create new poll").click()
        page.get_by_label("Title").fill("Browser smoke poll")
        page.get_by_label("Description").fill("Created by Playwright.")
        page.get_by_label("Poll identifier").fill("browser_smoke_poll")
        page.get_by_label("Timezone").fill("Europe/Helsinki")
        page.get_by_label("Start date").fill("2026-04-01")
        page.get_by_label("End date").fill("2026-04-02")
        page.get_by_role("button", name="Create new poll").click()

        page.locator(".details-title").filter(has_text="Browser smoke poll").wait_for()
        self.assertRegex(page.url, re.compile(r"[?&]id="))
        self.assertIn(
            "Created by: playwright-user",
            page.locator(".details-header").inner_text(),
        )
