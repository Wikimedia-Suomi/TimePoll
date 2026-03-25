from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path
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

    def open_home_page(self, page: Optional["Page"] = None, path: str = "/") -> None:
        page = page or self.require_page()
        page.goto(path, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.locator("#app").wait_for(state="visible")
        page.get_by_role("heading", name="TimePoll").wait_for()

    def login(
        self,
        *,
        name: str = "playwright-user",
        pin: str = "1234",
        page: Optional["Page"] = None,
    ) -> None:
        page = page or self.require_page()
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

    def wait_for_first_vote_state(
        self,
        selector: str,
        checked: bool,
        *,
        page: Optional["Page"] = None,
    ) -> None:
        page = page or self.require_page()
        expected = "true" if checked else "false"
        page.wait_for_function(
            """
            ([voteSelector, expectedState]) => {
              const element = document.querySelector(voteSelector);
              return Boolean(element) && element.getAttribute("aria-checked") === expectedState;
            }
            """,
            arg=[selector, expected],
        )

    def test_home_page_has_no_accessibility_violations(self) -> None:
        self.open_home_page()
        page = self.require_page()
        axe = self.require_axe()
        results = axe.run(page)
        self.assert_no_axe_violations(results)

    def test_js_unit_runner_passes_in_browser(self) -> None:
        page = self.require_page()

        page.goto("/static/polls/js/tests/runner.html", wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.locator("#summary[data-status='passed']").wait_for()

        summary_text = page.locator("#summary").inner_text()
        details_text = page.locator("#details").inner_text()

        self.assertIn("JS unit tests passed", summary_text)
        self.assertIn("All tests passed.", details_text)

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

    def test_browser_creator_can_edit_close_reopen_and_voter_sees_locked_poll(self) -> None:
        creator_page = self.require_page()
        poll_identifier = "browser_edit_lock_poll"

        self.open_home_page()
        self.login(name="browser-creator")

        creator_page.get_by_role("button", name="Create new poll").click()
        creator_page.get_by_label("Title").fill("Browser lifecycle poll")
        creator_page.get_by_label("Description").fill("Lifecycle coverage.")
        creator_page.get_by_label("Poll identifier").fill(poll_identifier)
        creator_page.get_by_label("Timezone").fill("Europe/Helsinki")
        creator_page.get_by_label("Start date").fill("2026-04-01")
        creator_page.get_by_label("End date").fill("2026-04-02")
        creator_page.get_by_role("button", name="Create new poll").click()

        creator_page.locator(".details-title").filter(has_text="Browser lifecycle poll").wait_for()
        creator_page.get_by_role("button", name="Edit poll").click()
        creator_page.locator("#edit-title").fill("Browser lifecycle poll updated")
        creator_page.get_by_role("button", name="Save changes").click()
        creator_page.locator(".details-title").filter(
            has_text="Browser lifecycle poll updated"
        ).wait_for()

        browser = self.browser
        if browser is None:
            raise unittest.SkipTest("Playwright browser is not available for this test run.")

        voter_context = browser.new_context(base_url=self.live_server_url)
        self.addCleanup(voter_context.close)
        voter_page = voter_context.new_page()
        voter_page.set_default_timeout(15000)

        self.open_home_page(voter_page, f"/?id={poll_identifier}")
        self.login(name="browser-voter", page=voter_page)
        voter_page.locator(".details-title").filter(
            has_text="Browser lifecycle poll updated"
        ).wait_for()

        first_yes_button = voter_page.locator(".vote-switch-option-yes").first
        self.assertFalse(first_yes_button.is_disabled())

        creator_page.get_by_role("button", name="Close poll").click()
        creator_page.get_by_text("Poll is closed").first.wait_for()

        voter_page.reload(wait_until="domcontentloaded")
        voter_page.wait_for_load_state("networkidle")
        voter_page.get_by_text("Poll is closed").first.wait_for()
        self.assertTrue(first_yes_button.is_disabled())

        creator_page.get_by_role("button", name="Reopen poll").click()
        creator_page.get_by_text("Poll is open").first.wait_for()

        voter_page.reload(wait_until="domcontentloaded")
        voter_page.wait_for_load_state("networkidle")
        voter_page.get_by_text("Poll is open").first.wait_for()
        self.assertFalse(first_yes_button.is_disabled())

    def test_browser_profile_open_export_delete_flow(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="profile-owner")

        page.get_by_role("button", name="Create new poll").click()
        page.get_by_label("Title").fill("Profile poll")
        page.get_by_label("Description").fill("Used by profile flow.")
        page.get_by_label("Poll identifier").fill("profile_poll")
        page.get_by_label("Timezone").fill("Europe/Helsinki")
        page.get_by_label("Start date").fill("2026-04-03")
        page.get_by_label("End date").fill("2026-04-03")
        page.get_by_role("button", name="Create new poll").click()

        page.locator(".details-title").filter(has_text="Profile poll").wait_for()
        first_yes_button = page.locator(".vote-switch-option-yes").first
        first_yes_button.click()
        page.locator(".vote-switch-option-yes.is-selected").first.wait_for()

        page.locator(".auth-name-link").click()
        page.get_by_role("heading", name="My data").wait_for()
        page.get_by_text("Vote count: 1").wait_for()
        page.get_by_text("Created polls: 1").wait_for()
        page.get_by_role("button", name="Profile poll").wait_for()
        page.get_by_text("My vote: Yes").wait_for()

        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        download_path = Path(temp_dir.name) / "profile-data.json"
        with page.expect_download() as download_info:
            page.get_by_role("button", name="Download JSON").click()
        download = download_info.value
        self.assertEqual(download.suggested_filename, "timepoll-profile-owner-data.json")
        download.save_as(str(download_path))

        downloaded_payload = json.loads(download_path.read_text(encoding="utf-8"))
        self.assertEqual(downloaded_payload["identity"]["name"], "profile-owner")
        self.assertEqual(downloaded_payload["stats"]["created_poll_count"], 1)

        page.on("dialog", lambda dialog: dialog.accept())
        page.get_by_role("button", name="Delete own data").click()
        page.get_by_text("All personal data removed. Your account was deleted.").wait_for()
        page.get_by_role("button", name="Login").wait_for()
        page.get_by_text("No polls yet.").wait_for()

    def test_browser_language_switch_vote_flow_and_reload_persistence(self) -> None:
        page = self.require_page()
        poll_identifier = "language_vote_poll"

        self.open_home_page()
        self.login(name="language-voter")

        page.locator("#language-select").select_option("fi")
        page.get_by_role("button", name="Kirjaudu ulos").wait_for()
        self.assertEqual(page.locator("#language-select").input_value(), "fi")

        page.get_by_role("button", name="Luo uusi kysely").click()
        page.locator("#poll-title").fill("Language persistence poll")
        page.locator("#poll-description").fill("Used for language and vote persistence.")
        page.locator("#poll-identifier").fill(poll_identifier)
        page.locator("#poll-timezone").fill("Europe/Helsinki")
        page.locator("#start-date").fill("2026-04-06")
        page.locator("#end-date").fill("2026-04-06")
        page.locator("#section-panel-create button[type='submit']").click()

        page.locator(".details-title").filter(has_text="Language persistence poll").wait_for()
        self.assertIn(f"id={poll_identifier}", page.url)

        first_yes_button = page.locator(".vote-switch-option-yes").first
        first_maybe_button = page.locator(".vote-switch-option-maybe").first

        first_yes_button.click()
        self.wait_for_first_vote_state(".vote-switch-option-yes", True, page=page)
        self.assertEqual(first_yes_button.get_attribute("aria-checked"), "true")

        first_maybe_button.click()
        self.wait_for_first_vote_state(".vote-switch-option-maybe", True, page=page)
        self.assertEqual(first_maybe_button.get_attribute("aria-checked"), "true")
        self.assertEqual(first_yes_button.get_attribute("aria-checked"), "false")

        first_maybe_button.click()
        self.wait_for_first_vote_state(".vote-switch-option-maybe", False, page=page)
        self.wait_for_first_vote_state(".vote-switch-option-yes", False, page=page)
        self.assertEqual(first_maybe_button.get_attribute("aria-checked"), "false")
        self.assertEqual(first_yes_button.get_attribute("aria-checked"), "false")

        page.reload(wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.locator(".details-title").filter(has_text="Language persistence poll").wait_for()
        page.get_by_role("button", name="Kirjaudu ulos").wait_for()

        self.assertEqual(page.locator("#language-select").input_value(), "fi")
        self.assertEqual(
            page.evaluate("() => window.localStorage.getItem('timepoll-language')"),
            "fi",
        )
        self.assertEqual(first_maybe_button.get_attribute("aria-checked"), "false")
        self.assertEqual(first_yes_button.get_attribute("aria-checked"), "false")
