from __future__ import annotations

import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings, tag

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

REQUIRE_BROWSER_TESTS = os.environ.get("TIMEPOLL_REQUIRE_BROWSER_TESTS", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
AXE_RULE_TAGS = (
    "wcag2a",
    "wcag2aa",
    "wcag21a",
    "wcag21aa",
    "wcag22aa",
    "best-practice",
    "wcag2aaa",
)
AXE_RUN_OPTIONS = {
    "resultTypes": ["violations"],
    "runOnly": {"type": "tag", "values": list(AXE_RULE_TAGS)},
}


@tag("browser")
@override_settings(ALLOWED_HOSTS=["127.0.0.1", "localhost", "testserver", "[::1]"])
class PollBrowserTests(StaticLiveServerTestCase):
    playwright: Optional["Playwright"] = None
    browser: Optional["Browser"] = None
    axe: Any = None
    context: Optional["BrowserContext"] = None
    page: Optional["Page"] = None

    @classmethod
    def setUpClass(cls) -> None:
        if not PLAYWRIGHT_TESTS_AVAILABLE:
            message = "Playwright browser tests require dependencies from requirements-dev.txt."
            if REQUIRE_BROWSER_TESTS:
                raise AssertionError(message)
            raise unittest.SkipTest(message)
        super().setUpClass()

    def setUp(self) -> None:
        if sync_playwright_fn is None or axe_runner_factory is None:
            message = "Playwright browser tests require dependencies from requirements-dev.txt."
            if REQUIRE_BROWSER_TESTS:
                raise AssertionError(message)
            raise unittest.SkipTest(message)

        try:
            self.playwright = sync_playwright_fn().start()
            self.browser = self.playwright.chromium.launch()
            self.context = self.browser.new_context(base_url=self.live_server_url)
            self.page = self.context.new_page()
            self.axe = axe_runner_factory()
        except Exception as exc:  # pragma: no cover
            self._cleanup_playwright_session()
            message = "Playwright browsers are not installed. Run `sh tools/install-browser.sh`."
            if REQUIRE_BROWSER_TESTS:
                raise AssertionError(message) from exc
            raise unittest.SkipTest(message) from exc

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

    def run_accessibility_audit(
        self,
        *,
        page: Optional["Page"] = None,
        context: Any = None,
    ) -> Any:
        page = page or self.require_page()
        axe = self.require_axe()
        return axe.run(page, context=context, options=AXE_RUN_OPTIONS)

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
        page.get_by_role("button", name="Logout", exact=True).wait_for()

    def format_axe_violation(self, violation: dict[str, Any]) -> str:
        targets: list[str] = []
        for node in violation.get("nodes", [])[:3]:
            for target in node.get("target", [])[:3]:
                if isinstance(target, str):
                    targets.append(target)
        target_suffix = f" targets={', '.join(targets)}" if targets else ""
        return (
            f"- {violation['id']}: {violation['help']} "
            f"({len(violation.get('nodes', []))} nodes){target_suffix}"
        )

    def assert_no_axe_violations(self, results: Any, *, page_name: str) -> None:
        violations = list(results.response.get("violations", []))
        details = "\n".join(self.format_axe_violation(item) for item in violations[:10])
        summary = (
            f"Axe violations on {page_name} "
            f"for tags {', '.join(AXE_RULE_TAGS)}."
        )
        if details:
            summary = f"{summary}\n{details}"
        self.assertEqual(results.violations_count, 0, summary)

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

    def create_poll(
        self,
        *,
        title: str,
        identifier: str,
        start_date: str,
        end_date: str,
        description: str = "",
        timezone: str = "Europe/Helsinki",
        daily_start_hour: Optional[int] = None,
        daily_end_hour: Optional[int] = None,
        allowed_weekdays: Optional[list[int]] = None,
        page: Optional["Page"] = None,
    ) -> None:
        page = page or self.require_page()
        page.get_by_role("button", name="Create new poll").click()
        page.locator("#poll-title").fill(title)
        page.locator("#poll-description").fill(description)
        page.locator("#poll-identifier").fill(identifier)
        page.locator("#poll-timezone").fill(timezone)
        page.locator("#start-date").fill(start_date)
        page.locator("#end-date").fill(end_date)
        if daily_start_hour is not None:
            page.locator("#daily-start-hour").select_option(str(daily_start_hour))
        if daily_end_hour is not None:
            page.locator("#daily-end-hour").select_option(str(daily_end_hour))
        if allowed_weekdays is not None:
            normalized_weekdays = {value for value in allowed_weekdays if isinstance(value, int) and 0 <= value <= 6}
            weekday_inputs = page.locator("#section-panel-create .weekday-item input")
            for index in range(7):
                weekday_inputs.nth(index).set_checked(index in normalized_weekdays)
        page.locator("#section-panel-create button[type='submit']").click()
        try:
            page.locator(".details-title").filter(has_text=title).wait_for()
        except Exception as exc:
            field_errors = page.locator(".field-error").all_inner_texts()
            feedback_messages = page.locator(".feedback").all_inner_texts()
            raise AssertionError(
                "Poll creation did not reach the details view. "
                f"url={page.url!r} field_errors={field_errors!r} feedback={feedback_messages!r}"
            ) from exc

    def wait_for_vote_switch_count(self, expected_count: int, *, page: Optional["Page"] = None) -> None:
        page = page or self.require_page()
        page.wait_for_function(
            """
            (count) => document.querySelectorAll('.calendar-table tbody .vote-switch').length === count
            """,
            arg=expected_count,
        )

    def submit_auth_dialog(
        self,
        *,
        name: str,
        pin: str = "1234",
        page: Optional["Page"] = None,
    ) -> None:
        page = page or self.require_page()
        dialog = page.get_by_role("dialog")
        dialog.wait_for()
        dialog.get_by_label("Name").fill(name)
        dialog.get_by_label("PIN code").fill(pin)
        dialog.get_by_role("button", name="Login").click()

    def open_logged_in_poll_page(
        self,
        *,
        poll_identifier: str,
        name: str,
    ) -> "Page":
        browser = self.browser
        if browser is None:
            raise unittest.SkipTest("Playwright browser is not available for this test run.")

        context = browser.new_context(base_url=self.live_server_url)
        self.addCleanup(context.close)
        page = context.new_page()
        page.set_default_timeout(15000)
        self.open_home_page(page, f"/?id={poll_identifier}")
        self.login(name=name, page=page)
        return page

    def active_element_snapshot(self, page: Optional["Page"] = None) -> dict[str, str]:
        page = page or self.require_page()
        return page.evaluate(
            """
            () => {
              const element = document.activeElement;
              return {
                id: element?.id || "",
                text: (element?.textContent || "").trim(),
                className: typeof element?.className === "string" ? element.className : "",
                role: element?.getAttribute?.("role") || "",
                status: element?.getAttribute?.("data-vote-status") || "",
                optionId: element?.getAttribute?.("data-vote-option-id") || ""
              };
            }
            """
        )

    def active_element_has_visible_focus(self, page: Optional["Page"] = None) -> bool:
        page = page or self.require_page()
        return bool(
            page.evaluate(
                """
                () => {
                  const element = document.activeElement;
                  if (!element) {
                    return false;
                  }
                  const style = window.getComputedStyle(element);
                  const hasOutline = style.outlineStyle !== "none" && style.outlineWidth !== "0px";
                  const hasBoxShadow = style.boxShadow && style.boxShadow !== "none";
                  return hasOutline || hasBoxShadow;
                }
                """
            )
        )

    def mock_fetch_json(
        self,
        *,
        url_part: str,
        method: str = "GET",
        status: int = 500,
        body: Optional[dict[str, Any]] = None,
        page: Optional["Page"] = None,
    ) -> None:
        page = page or self.require_page()
        payload = body if body is not None else {"detail": "Mocked request failed."}
        page.evaluate(
            """
            ([mockUrlPart, mockMethod, mockStatus, mockBody]) => {
              if (!window.__timepollOriginalFetch) {
                window.__timepollOriginalFetch = window.fetch.bind(window);
                window.__timepollFetchMocks = [];
                window.fetch = async (input, init = {}) => {
                  const requestUrl = typeof input === 'string' ? input : input.url;
                  const requestMethod = String(
                    (init && init.method)
                    || (typeof input === 'object' && input && input.method)
                    || 'GET'
                  ).toUpperCase();
                  const mockIndex = window.__timepollFetchMocks.findIndex((mock) => {
                    const methodMatches = !mock.method || mock.method === requestMethod;
                    return methodMatches && requestUrl.includes(mock.urlPart);
                  });
                  if (mockIndex >= 0) {
                    const mock = window.__timepollFetchMocks.splice(mockIndex, 1)[0];
                    return new Response(JSON.stringify(mock.body), {
                      status: mock.status,
                      headers: { 'Content-Type': 'application/json' }
                    });
                  }
                  return window.__timepollOriginalFetch(input, init);
                };
              }
              window.__timepollFetchMocks.push({
                urlPart: mockUrlPart,
                method: String(mockMethod || 'GET').toUpperCase(),
                status: Number(mockStatus) || 500,
                body: mockBody || { detail: 'Mocked request failed.' }
              });
            }
            """,
            [url_part, method, status, payload],
        )

    def test_home_page_has_no_accessibility_violations(self) -> None:
        self.open_home_page()
        results = self.run_accessibility_audit()
        self.assert_no_axe_violations(results, page_name="home page")

    def test_login_dialog_has_no_accessibility_violations(self) -> None:
        page = self.require_page()

        self.open_home_page()
        page.get_by_role("button", name="Login").click()
        page.get_by_role("dialog").wait_for()

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="login dialog")

    def test_create_poll_form_has_no_accessibility_violations(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="create-a11y-user")
        page.get_by_role("button", name="Create new poll").click()
        page.locator("#section-panel-create").wait_for()

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="create poll form")

    def test_poll_details_page_has_no_accessibility_violations(self) -> None:
        self.open_home_page()
        self.login(name="details-a11y-user")
        self.create_poll(
            title="Accessibility details poll",
            description="Used for accessibility coverage on the details view.",
            identifier="accessibility_details_poll",
            timezone="Europe/Helsinki",
            start_date="2026-04-10",
            end_date="2026-04-10",
        )

        results = self.run_accessibility_audit()
        self.assert_no_axe_violations(results, page_name="poll details page")

    def test_profile_page_has_no_accessibility_violations(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="profile-a11y-user")
        self.create_poll(
            title="Accessibility profile poll",
            description="Used for accessibility coverage on the profile view.",
            identifier="accessibility_profile_poll",
            timezone="Europe/Helsinki",
            start_date="2026-04-13",
            end_date="2026-04-13",
        )
        page.locator(".vote-switch-option-yes").first.click()
        page.locator(".vote-switch-option-yes.is-selected").first.wait_for()
        page.locator(".auth-name-link").click()
        page.get_by_role("heading", name="My data").wait_for()

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="profile page")

    def test_create_form_validation_errors_have_no_accessibility_violations(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="validation-a11y-owner")
        page.get_by_role("button", name="Create new poll").click()

        page.locator("#poll-identifier").fill("bad-id")
        page.get_by_text("Identifier may contain only A-Z, a-z, 0-9 and underscore (_).").wait_for()
        page.locator("#poll-timezone").fill("")
        weekday_inputs = page.locator("#section-panel-create .weekday-item input")
        for index in range(5):
            weekday_inputs.nth(index).set_checked(False)

        page.locator("#section-panel-create button[type='submit']").click()
        page.get_by_text("Title is required.").first.wait_for()
        page.get_by_text("Timezone is required.").first.wait_for()
        page.get_by_text("Start date is required.").first.wait_for()
        page.get_by_text("End date is required.").first.wait_for()
        page.get_by_text("Select at least one weekday.").first.wait_for()

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="create form validation error state")

    def test_create_form_identifier_conflict_state_has_no_accessibility_violations(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="duplicate-a11y-owner")
        self.create_poll(
            title="Duplicate accessibility source poll",
            description="Original poll for duplicate identifier accessibility coverage.",
            identifier="duplicate_identifier_a11y_poll",
            timezone="Europe/Helsinki",
            start_date="2026-05-01",
            end_date="2026-05-01",
        )

        page.locator(".title-home").click()
        page.get_by_role("button", name="Create new poll").click()
        page.locator("#poll-title").fill("Duplicate accessibility target poll")
        page.locator("#poll-description").fill("Should show duplicate identifier state.")
        page.locator("#poll-identifier").fill("duplicate_identifier_a11y_poll")
        page.locator("#poll-timezone").fill("Europe/Helsinki")
        page.locator("#start-date").fill("2026-05-02")
        page.locator("#end-date").fill("2026-05-02")
        page.locator("#section-panel-create button[type='submit']").click()

        page.get_by_role("alert").filter(has_text="This identifier is already in use.").wait_for()
        page.locator("#section-panel-create .field-error").filter(
            has_text="This identifier is already in use."
        ).first.wait_for()

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="create form duplicate identifier error state")

    def test_edit_form_conflict_state_has_no_accessibility_violations(self) -> None:
        page = self.require_page()
        poll_identifier = "edit_conflict_a11y_poll"

        self.open_home_page()
        self.login(name="edit-conflict-a11y-owner")
        self.create_poll(
            title="Edit conflict accessibility poll",
            description="Used for edit conflict accessibility coverage.",
            identifier=poll_identifier,
            timezone="Europe/Helsinki",
            start_date="2026-05-04",
            end_date="2026-05-04",
        )

        browser = self.browser
        if browser is None:
            raise unittest.SkipTest("Playwright browser is not available for this test run.")

        voter_context = browser.new_context(base_url=self.live_server_url)
        self.addCleanup(voter_context.close)
        voter_page = voter_context.new_page()
        voter_page.set_default_timeout(15000)

        self.open_home_page(voter_page, f"/?id={poll_identifier}")
        self.login(name="edit-conflict-a11y-voter", page=voter_page)
        voter_page.locator(".vote-switch-option-yes").first.click()
        self.wait_for_first_vote_state(".vote-switch-option-yes", True, page=voter_page)

        page.reload(wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.locator(".details-title").filter(has_text="Edit conflict accessibility poll").wait_for()
        page.get_by_role("button", name="Edit poll").click()

        edit_weekdays = page.locator("#section-panel-selected .weekday-item input")
        edit_weekdays.nth(0).set_checked(False)
        edit_weekdays.nth(1).set_checked(True)
        page.get_by_role("button", name="Save changes").click()

        page.get_by_role("alert").filter(
            has_text="You cannot remove time slots that already have votes."
        ).wait_for()
        page.locator("#section-panel-selected .field-error").filter(
            has_text="You cannot remove time slots that already have votes."
        ).first.wait_for()

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="edit form conflict error state")

    def test_closed_poll_state_has_no_accessibility_violations(self) -> None:
        creator_page = self.require_page()
        poll_identifier = "closed_poll_a11y_poll"

        self.open_home_page()
        self.login(name="closed-a11y-creator")
        self.create_poll(
            title="Closed poll accessibility poll",
            description="Used for closed poll accessibility coverage.",
            identifier=poll_identifier,
            timezone="Europe/Helsinki",
            start_date="2026-05-06",
            end_date="2026-05-06",
        )

        browser = self.browser
        if browser is None:
            raise unittest.SkipTest("Playwright browser is not available for this test run.")

        voter_context = browser.new_context(base_url=self.live_server_url)
        self.addCleanup(voter_context.close)
        voter_page = voter_context.new_page()
        voter_page.set_default_timeout(15000)

        self.open_home_page(voter_page, f"/?id={poll_identifier}")
        self.login(name="closed-a11y-voter", page=voter_page)
        voter_page.locator(".details-title").filter(
            has_text="Closed poll accessibility poll"
        ).wait_for()

        creator_page.get_by_role("button", name="Close poll").click()
        creator_page.get_by_text("Poll is closed").first.wait_for()

        voter_page.reload(wait_until="domcontentloaded")
        voter_page.wait_for_load_state("networkidle")
        voter_page.get_by_text("Poll is closed").first.wait_for()
        self.assertTrue(voter_page.locator(".vote-switch-option-yes").first.is_disabled())

        results = self.run_accessibility_audit(page=voter_page)
        self.assert_no_axe_violations(results, page_name="closed poll details state")

    def test_error_toast_state_has_no_accessibility_violations(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="toast-a11y-owner")
        self.create_poll(
            title="Toast accessibility poll",
            description="Used for error toast accessibility coverage.",
            identifier="toast_accessibility_poll",
            timezone="Europe/Helsinki",
            start_date="2026-05-07",
            end_date="2026-05-07",
        )

        self.mock_fetch_json(
            url_part="/api/polls/toast_accessibility_poll/close/",
            method="POST",
            status=500,
            body={"detail": "Temporarily unavailable."},
            page=page,
        )
        page.get_by_role("button", name="Close poll").click()
        page.get_by_role("alert").filter(has_text="Temporarily unavailable.").wait_for()

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="error toast state")

    def test_bulk_vote_menu_open_state_has_no_accessibility_violations(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="bulk-menu-a11y-owner")
        self.create_poll(
            title="Bulk menu accessibility poll",
            description="Used for bulk menu accessibility coverage.",
            identifier="bulk_menu_accessibility_poll",
            timezone="Europe/Helsinki",
            start_date="2026-05-08",
            end_date="2026-05-09",
            daily_start_hour=9,
            daily_end_hour=12,
        )

        first_day_header = page.locator(".calendar-day-col").first
        first_day_header.locator(".bulk-day-trigger").click()
        first_day_header.locator(".bulk-menu").wait_for()

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="bulk vote menu state")

    def test_timezone_suggestion_listbox_state_has_no_accessibility_violations(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="timezone-listbox-a11y-owner")
        page.get_by_role("button", name="Create new poll").click()
        page.locator("#poll-timezone").fill("europe/hel")
        page.locator(".timezone-suggestions").wait_for()

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="timezone suggestion listbox state")

    def test_result_mode_filtered_calendar_state_has_no_accessibility_violations(self) -> None:
        page = self.require_page()
        poll_identifier = "yes_filter_a11y_poll"

        self.open_home_page()
        self.login(name="yes-filter-a11y-creator")
        self.create_poll(
            title="Yes filter accessibility poll",
            description="Used for filtered result mode accessibility coverage.",
            identifier=poll_identifier,
            timezone="Europe/Helsinki",
            start_date="2026-05-12",
            end_date="2026-05-13",
            daily_start_hour=9,
            daily_end_hour=11,
        )

        creator_yes_buttons = page.locator(".vote-switch-option-yes")
        creator_yes_buttons.nth(0).click()
        creator_yes_buttons.nth(1).click()
        self.wait_for_first_vote_state(".vote-switch-option-yes", True, page=page)

        browser = self.browser
        if browser is None:
            raise unittest.SkipTest("Playwright browser is not available for this test run.")

        voter_context = browser.new_context(base_url=self.live_server_url)
        self.addCleanup(voter_context.close)
        voter_page = voter_context.new_page()
        voter_page.set_default_timeout(15000)

        self.open_home_page(voter_page, f"/?id={poll_identifier}")
        self.login(name="yes-filter-a11y-voter", page=voter_page)
        voter_page.locator(".vote-switch-option-yes").first.click()
        self.wait_for_first_vote_state(".vote-switch-option-yes", True, page=voter_page)

        page.reload(wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.locator(".details-title").filter(has_text="Yes filter accessibility poll").wait_for()
        page.locator(".calendar-vote-mode-item").filter(has_text="Result mode").click()
        self.wait_for_vote_switch_count(4, page=page)
        page.locator("#min-yes-filter").select_option("2")
        self.wait_for_vote_switch_count(1, page=page)

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="result mode with yes filter state")

    def test_calendar_timezone_listbox_state_has_no_accessibility_violations(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="calendar-timezone-listbox-a11y-owner")
        self.create_poll(
            title="Calendar timezone listbox poll",
            description="Used for details timezone suggestion accessibility coverage.",
            identifier="calendar_timezone_listbox_poll",
            timezone="UTC",
            start_date="2026-05-14",
            end_date="2026-05-14",
            daily_start_hour=23,
            daily_end_hour=24,
        )

        page.locator(".calendar-timezone-mode-item-custom").click()
        page.locator("#calendar-timezone").fill("pacific/hon")
        page.locator(".timezone-suggestions").wait_for()

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="calendar timezone suggestion listbox state")

    def test_custom_calendar_timezone_applied_state_has_no_accessibility_violations(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="calendar-timezone-a11y-owner")
        self.create_poll(
            title="Custom timezone accessibility poll",
            description="Used for applied custom timezone accessibility coverage.",
            identifier="custom_timezone_accessibility_poll",
            timezone="UTC",
            start_date="2026-05-15",
            end_date="2026-05-15",
            daily_start_hour=23,
            daily_end_hour=24,
        )

        page.locator(".calendar-timezone-mode-item-custom").click()
        page.locator("#calendar-timezone").fill("pacific/hon")
        page.locator(".timezone-suggestion").filter(has_text="Pacific/Honolulu").first.click()
        page.wait_for_function(
            """
            () => {
              const rowLabel = document.querySelector('.bulk-time-trigger');
              if (!rowLabel) {
                return false;
              }
              return rowLabel.textContent.trim() === '13:00';
            }
            """
        )

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="custom calendar timezone applied state")

    def test_mobile_paginated_calendar_state_has_no_accessibility_violations(self) -> None:
        page = self.require_page()
        page.set_viewport_size({"width": 480, "height": 900})

        self.open_home_page()
        self.login(name="pagination-a11y-owner")
        self.create_poll(
            title="Paginated accessibility poll",
            description="Used for mobile calendar accessibility coverage.",
            identifier="paginated_accessibility_poll",
            timezone="Europe/Helsinki",
            start_date="2026-05-12",
            end_date="2026-05-18",
            daily_start_hour=9,
            daily_end_hour=10,
            allowed_weekdays=[0, 1, 2, 3, 4, 5, 6],
        )

        page.locator(".calendar-nav-range").wait_for()
        next_button = page.get_by_role("button", name="Next days")
        if next_button.is_enabled():
            next_button.click()
        page.locator(".calendar-nav-range").wait_for()

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="mobile paginated calendar state")

    def test_logout_anonymous_details_state_has_no_accessibility_violations(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="logout-a11y-owner")
        self.create_poll(
            title="Logout accessibility poll",
            description="Used for anonymous details accessibility coverage.",
            identifier="logout_accessibility_poll",
            timezone="Europe/Helsinki",
            start_date="2026-05-18",
            end_date="2026-05-18",
        )

        page.get_by_role("button", name="Logout", exact=True).click()
        page.get_by_role("button", name="Login").wait_for()
        page.locator(".details-title").filter(has_text="Logout accessibility poll").wait_for()
        page.get_by_text("Enter your name and PIN to continue.").wait_for()

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="anonymous details state after logout")

    def test_profile_partial_delete_summary_state_has_no_accessibility_violations(self) -> None:
        page = self.require_page()
        keep_identifier = "profile_keep_a11y_poll"
        delete_identifier = "profile_delete_a11y_poll"

        self.open_home_page()
        self.login(name="partial-delete-a11y-owner")
        self.create_poll(
            title="Profile keep accessibility poll",
            description="Poll that should remain after delete own data.",
            identifier=keep_identifier,
            timezone="Europe/Helsinki",
            start_date="2026-05-19",
            end_date="2026-05-19",
        )
        page.locator(".vote-switch-option-yes").first.click()
        self.wait_for_first_vote_state(".vote-switch-option-yes", True, page=page)

        page.locator(".title-home").click()
        page.get_by_role("heading", name="Polls").wait_for()
        page.get_by_role("button", name="Create new poll").click()
        page.locator("#poll-title").fill("Profile delete accessibility poll")
        page.locator("#poll-description").fill("Poll that should be deleted.")
        page.locator("#poll-identifier").fill(delete_identifier)
        page.locator("#poll-timezone").fill("Europe/Helsinki")
        page.locator("#start-date").fill("2026-05-20")
        page.locator("#end-date").fill("2026-05-20")
        page.locator("#section-panel-create button[type='submit']").click()
        page.locator(".details-title").filter(has_text="Profile delete accessibility poll").wait_for()
        page.locator(".vote-switch-option-yes").first.click()
        self.wait_for_first_vote_state(".vote-switch-option-yes", True, page=page)

        browser = self.browser
        if browser is None:
            raise unittest.SkipTest("Playwright browser is not available for this test run.")

        guest_context = browser.new_context(base_url=self.live_server_url)
        self.addCleanup(guest_context.close)
        guest_page = guest_context.new_page()
        guest_page.set_default_timeout(15000)

        self.open_home_page(guest_page, f"/?id={keep_identifier}")
        self.login(name="partial-delete-a11y-guest", page=guest_page)
        guest_page.locator(".vote-switch-option-no").first.click()
        self.wait_for_first_vote_state(".vote-switch-option-no", True, page=guest_page)

        page.locator(".auth-name-link").click()
        page.get_by_role("heading", name="My data").wait_for()
        page.get_by_text("Vote count: 2").wait_for()
        page.on("dialog", lambda dialog: dialog.accept())
        page.get_by_role("button", name="Delete own data").click()
        page.get_by_role("status").filter(has_text="Own data deleted where possible.").wait_for()
        page.get_by_text("Deleted votes: 2").wait_for()
        page.get_by_text("Deleted polls: 1").wait_for()
        page.get_by_text("Remaining created polls: 1").wait_for()
        page.get_by_text("Remaining polls with other users' votes: 1").wait_for()

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="profile partial delete summary state")

    def test_profile_account_removed_home_state_has_no_accessibility_violations(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="profile-delete-account-a11y-owner")
        self.create_poll(
            title="Profile account removed accessibility poll",
            description="Used for full account removal accessibility coverage.",
            identifier="profile_account_removed_a11y_poll",
            timezone="Europe/Helsinki",
            start_date="2026-05-21",
            end_date="2026-05-21",
        )

        page.locator(".auth-name-link").click()
        page.get_by_role("heading", name="My data").wait_for()
        page.on("dialog", lambda dialog: dialog.accept())
        page.get_by_role("button", name="Delete own data").click()
        page.get_by_role("status").filter(
            has_text="All personal data removed. Your account was deleted."
        ).wait_for()
        page.get_by_role("button", name="Login").wait_for()
        page.get_by_text("No polls yet.").wait_for()

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="account removed home success state")

    def test_create_success_state_has_no_accessibility_violations(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="create-success-a11y-owner")
        self.create_poll(
            title="Create success accessibility poll",
            description="Used for create success accessibility coverage.",
            identifier="create_success_a11y_poll",
            timezone="Europe/Helsinki",
            start_date="2026-05-25",
            end_date="2026-05-25",
        )

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="create success state")

    def test_edit_success_state_has_no_accessibility_violations(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="edit-success-a11y-owner")
        self.create_poll(
            title="Edit success accessibility poll",
            description="Used for edit success accessibility coverage.",
            identifier="edit_success_a11y_poll",
            timezone="Europe/Helsinki",
            start_date="2026-05-26",
            end_date="2026-05-26",
        )

        page.get_by_role("button", name="Edit poll").click()
        page.locator("#edit-title").fill("Edit success accessibility poll updated")
        page.get_by_role("button", name="Save changes").click()
        page.get_by_role("status").filter(has_text="Poll updated successfully.").wait_for()
        page.locator(".details-title").filter(
            has_text="Edit success accessibility poll updated"
        ).wait_for()

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="edit success state")

    def test_reopen_success_state_has_no_accessibility_violations(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="reopen-success-a11y-owner")
        self.create_poll(
            title="Reopen success accessibility poll",
            description="Used for reopen success accessibility coverage.",
            identifier="reopen_success_a11y_poll",
            timezone="Europe/Helsinki",
            start_date="2026-05-27",
            end_date="2026-05-27",
        )

        page.get_by_role("button", name="Close poll").click()
        page.get_by_role("status").filter(has_text="Poll closed.").wait_for()
        page.get_by_role("button", name="Reopen poll").click()
        page.get_by_role("status").filter(has_text="Poll reopened.").wait_for()
        page.get_by_text("Poll is open").first.wait_for()

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="reopen success state")

    def test_profile_vote_delete_success_state_has_no_accessibility_violations(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="vote-delete-success-a11y-owner")
        self.create_poll(
            title="Vote delete success accessibility poll",
            description="Used for vote delete success accessibility coverage.",
            identifier="vote_delete_success_a11y_poll",
            timezone="Europe/Helsinki",
            start_date="2026-05-28",
            end_date="2026-05-28",
        )

        page.locator(".vote-switch-option-yes").first.click()
        self.wait_for_first_vote_state(".vote-switch-option-yes", True, page=page)
        page.locator(".auth-name-link").click()
        page.get_by_role("heading", name="My data").wait_for()
        page.get_by_role("button", name="Delete vote").click()
        page.get_by_role("status").filter(has_text="Vote deleted.").wait_for()
        page.get_by_text("No votes.").wait_for()

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="profile vote delete success state")

    def test_pending_vote_resume_success_state_has_no_accessibility_violations(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="pending-vote-success-creator")
        self.create_poll(
            title="Pending vote success accessibility poll",
            description="Used for pending vote resume accessibility coverage.",
            identifier="pending_vote_success_a11y_poll",
            timezone="Europe/Helsinki",
            start_date="2026-05-29",
            end_date="2026-05-29",
        )

        page.get_by_role("button", name="Logout", exact=True).click()
        page.get_by_role("button", name="Login").wait_for()
        first_yes_button = page.locator(".vote-switch-option-yes").first
        first_yes_button.click()
        page.get_by_role("dialog").wait_for()

        self.submit_auth_dialog(name="pending-vote-success-user")
        page.get_by_role("dialog").wait_for(state="hidden")
        self.wait_for_first_vote_state(".vote-switch-option-yes", True, page=page)
        page.get_by_role("button", name="Logout", exact=True).wait_for()

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="pending vote resume success state")

    def test_pending_create_resume_success_state_has_no_accessibility_violations(self) -> None:
        page = self.require_page()

        self.open_home_page()
        page.get_by_role("button", name="Create new poll").click()
        page.locator("#poll-title").fill("Pending create success accessibility poll")
        page.locator("#poll-description").fill("Used for pending create resume accessibility coverage.")
        page.locator("#poll-identifier").fill("pending_create_success_a11y_poll")
        page.locator("#poll-timezone").fill("Europe/Helsinki")
        page.locator("#start-date").fill("2026-06-01")
        page.locator("#end-date").fill("2026-06-01")
        page.locator("#section-panel-create button[type='submit']").click()
        page.get_by_role("dialog").wait_for()

        self.submit_auth_dialog(name="pending-create-success-user")
        page.locator(".details-title").filter(has_text="Pending create success accessibility poll").wait_for()

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="pending create resume success state")

    def test_open_poll_failure_toast_state_has_no_accessibility_violations(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="open-error-a11y-owner")
        self.create_poll(
            title="Open error accessibility poll",
            description="Used for open error accessibility coverage.",
            identifier="open_error_a11y_poll",
            timezone="Europe/Helsinki",
            start_date="2026-06-01",
            end_date="2026-06-01",
        )

        page.locator(".title-home").click()
        page.get_by_role("heading", name="Polls").wait_for()
        self.mock_fetch_json(
            url_part="/api/polls/open_error_a11y_poll/",
            method="GET",
            status=500,
            body={"detail": "Temporarily unavailable."},
            page=page,
        )
        page.locator(".poll-item").filter(has_text="Open error accessibility poll").click()
        page.get_by_role("alert").filter(has_text="Temporarily unavailable.").wait_for()
        page.get_by_role("heading", name="Polls").wait_for()

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="open poll failure toast state")

    def test_close_poll_failure_toast_state_has_no_accessibility_violations(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="close-error-a11y-owner")
        self.create_poll(
            title="Close error accessibility poll",
            description="Used for close error accessibility coverage.",
            identifier="close_error_a11y_poll",
            timezone="Europe/Helsinki",
            start_date="2026-06-02",
            end_date="2026-06-02",
        )

        self.mock_fetch_json(
            url_part="/api/polls/close_error_a11y_poll/close/",
            method="POST",
            status=500,
            body={"detail": "Close failed from mock."},
            page=page,
        )
        page.get_by_role("button", name="Close poll").click()
        page.get_by_role("alert").filter(has_text="Close failed from mock.").wait_for()
        page.get_by_text("Poll is open").first.wait_for()

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="close poll failure toast state")

    def test_logout_failure_toast_state_has_no_accessibility_violations(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="logout-error-a11y-owner")
        self.mock_fetch_json(
            url_part="/api/auth/logout/",
            method="POST",
            status=500,
            body={"detail": "Logout failed from mock."},
            page=page,
        )

        page.get_by_role("button", name="Logout", exact=True).click()
        page.get_by_role("alert").filter(has_text="Logout failed from mock.").wait_for()
        page.get_by_role("button", name="Hello, logout-error-a11y-owner").wait_for()

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="logout failure toast state")

    def test_invalid_poll_id_fallback_state_has_no_accessibility_violations(self) -> None:
        page = self.require_page()

        self.open_home_page(path="/?id=missing_poll_2026")
        page.wait_for_function("() => !window.location.search.includes('id=')")
        page.get_by_role("heading", name="Polls").wait_for()
        page.get_by_text("No polls yet.").wait_for()

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="invalid poll id fallback state")

    def test_browser_timezone_fallback_state_has_no_accessibility_violations(self) -> None:
        browser = self.browser
        if browser is None:
            raise unittest.SkipTest("Playwright browser is not available for this test run.")

        utc_context = browser.new_context(base_url=self.live_server_url, timezone_id="UTC")
        self.addCleanup(utc_context.close)
        utc_page = utc_context.new_page()
        utc_page.set_default_timeout(15000)

        self.open_home_page(utc_page)
        self.login(name="browser-tz-a11y-owner", page=utc_page)
        identity_id = utc_page.evaluate(
            """
            async () => {
              const response = await fetch('/api/auth/session/', { credentials: 'same-origin' });
              const payload = await response.json();
              return payload.identity.id;
            }
            """
        )
        utc_page.evaluate(
            """
            ([identityId, value]) => {
              window.localStorage.setItem(`timepoll-calendar-timezone:${identityId}`, value);
            }
            """,
            [identity_id, '{"mode":"browser","timezone":"UTC"}'],
        )

        self.create_poll(
            title="Browser timezone accessibility fallback poll",
            description="Used for browser timezone fallback accessibility coverage.",
            identifier="browser_timezone_fallback_a11y_poll",
            timezone="UTC",
            start_date="2026-06-03",
            end_date="2026-06-03",
            daily_start_hour=9,
            daily_end_hour=10,
            page=utc_page,
        )
        utc_page.locator(".details-title").filter(
            has_text="Browser timezone accessibility fallback poll"
        ).wait_for()
        self.assertTrue(
            utc_page.locator("input[name='calendar-timezone-mode'][value='poll']").is_checked()
        )

        results = self.run_accessibility_audit(page=utc_page)
        self.assert_no_axe_violations(results, page_name="browser timezone fallback state")

    def test_result_mode_unfiltered_calendar_state_has_no_accessibility_violations(self) -> None:
        page = self.require_page()
        poll_identifier = "result_mode_unfiltered_a11y_poll"

        self.open_home_page()
        self.login(name="result-mode-unfiltered-a11y-creator")
        self.create_poll(
            title="Result mode unfiltered accessibility poll",
            description="Used for unfiltered result mode accessibility coverage.",
            identifier=poll_identifier,
            timezone="Europe/Helsinki",
            start_date="2026-06-08",
            end_date="2026-06-09",
            daily_start_hour=9,
            daily_end_hour=11,
        )

        creator_yes_buttons = page.locator(".vote-switch-option-yes")
        creator_yes_buttons.nth(0).click()
        self.wait_for_first_vote_state(".vote-switch-option-yes", True, page=page)

        voter_page = self.open_logged_in_poll_page(
            poll_identifier=poll_identifier,
            name="result-mode-unfiltered-a11y-voter",
        )
        voter_page.locator(".vote-switch-option-yes").first.click()
        self.wait_for_first_vote_state(".vote-switch-option-yes", True, page=voter_page)

        page.reload(wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.locator(".details-title").filter(
            has_text="Result mode unfiltered accessibility poll"
        ).wait_for()
        page.locator(".calendar-vote-mode-item").filter(has_text="Result mode").click()
        self.wait_for_vote_switch_count(4, page=page)

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="result mode unfiltered state")

    def test_profile_vote_deleted_details_state_has_no_accessibility_violations(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="profile-vote-details-a11y-owner")
        self.create_poll(
            title="Profile vote delete details accessibility poll",
            description="Used for vote delete details accessibility coverage.",
            identifier="profile_vote_delete_details_a11y_poll",
            timezone="Europe/Helsinki",
            start_date="2026-06-04",
            end_date="2026-06-04",
        )

        page.locator(".vote-switch-option-yes").first.click()
        self.wait_for_first_vote_state(".vote-switch-option-yes", True, page=page)
        page.locator(".auth-name-link").click()
        page.get_by_role("heading", name="My data").wait_for()
        page.get_by_role("button", name="Delete vote").click()
        page.get_by_role("status").filter(has_text="Vote deleted.").wait_for()
        page.get_by_text("No votes.").wait_for()

        page.get_by_role("button", name="Profile vote delete details accessibility poll").click()
        page.locator(".details-title").filter(
            has_text="Profile vote delete details accessibility poll"
        ).wait_for()
        self.assertEqual(page.locator(".vote-switch-option-yes").first.get_attribute("aria-checked"), "false")

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="profile vote deleted details state")

    def test_history_restored_details_states_have_no_accessibility_violations(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="history-a11y-owner")
        self.create_poll(
            title="History accessibility first poll",
            description="First history accessibility target.",
            identifier="history_a11y_first_poll",
            timezone="Europe/Helsinki",
            start_date="2026-06-08",
            end_date="2026-06-08",
        )

        page.locator(".title-home").click()
        page.get_by_role("heading", name="Polls").wait_for()
        self.create_poll(
            title="History accessibility second poll",
            description="Second history accessibility target.",
            identifier="history_a11y_second_poll",
            timezone="Europe/Helsinki",
            start_date="2026-06-09",
            end_date="2026-06-09",
        )

        page.locator(".title-home").click()
        page.get_by_role("heading", name="Polls").wait_for()
        page.locator(".poll-item").filter(has_text="History accessibility first poll").click()
        page.locator(".details-title").filter(has_text="History accessibility first poll").wait_for()

        page.locator(".title-home").click()
        page.get_by_role("heading", name="Polls").wait_for()
        page.locator(".poll-item").filter(has_text="History accessibility second poll").click()
        page.locator(".details-title").filter(has_text="History accessibility second poll").wait_for()

        page.go_back()
        page.get_by_role("heading", name="Polls").wait_for()
        page.wait_for_function("() => !window.location.search.includes('id=')")

        page.go_back()
        page.locator(".details-title").filter(has_text="History accessibility first poll").wait_for()
        page.wait_for_function("() => window.location.search.includes('id=history_a11y_first_poll')")
        first_results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(first_results, page_name="history restored first poll state")

        page.go_forward()
        page.get_by_role("heading", name="Polls").wait_for()
        page.wait_for_function("() => !window.location.search.includes('id=')")

        page.go_forward()
        page.locator(".details-title").filter(has_text="History accessibility second poll").wait_for()
        page.wait_for_function("() => window.location.search.includes('id=history_a11y_second_poll')")
        second_results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(second_results, page_name="history restored second poll state")

    def test_custom_calendar_timezone_persisted_state_has_no_accessibility_violations(self) -> None:
        page = self.require_page()
        poll_identifier = "custom_timezone_persisted_a11y_poll"

        self.open_home_page()
        self.login(name="timezone-persisted-a11y-owner")
        self.create_poll(
            title="Custom timezone persisted accessibility poll",
            description="Used for persisted timezone accessibility coverage.",
            identifier=poll_identifier,
            timezone="UTC",
            start_date="2026-06-10",
            end_date="2026-06-10",
            daily_start_hour=23,
            daily_end_hour=24,
        )

        page.locator(".calendar-timezone-mode-item-custom").click()
        page.locator("#calendar-timezone").fill("Pacific/Honolulu")
        page.locator(".details-title").click()
        page.wait_for_function(
            """
            () => {
              const rowLabel = document.querySelector('.bulk-time-trigger');
              if (!rowLabel) {
                return false;
              }
              return rowLabel.textContent.trim() === '13:00';
            }
            """
        )
        page.wait_for_function(
            """
            () => {
              const entry = Object.entries(window.localStorage)
                .find(([key]) => key.startsWith('timepoll-calendar-timezone:'));
              return Boolean(entry) && entry[1] === '{"mode":"custom","timezone":"Pacific/Honolulu"}';
            }
            """
        )

        page.reload(wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.locator(".details-title").filter(
            has_text="Custom timezone persisted accessibility poll"
        ).wait_for()
        self.assertTrue(
            page.locator("input[name='calendar-timezone-mode'][value='custom']").is_checked()
        )
        self.assertEqual(page.locator("#calendar-timezone").input_value(), "Pacific/Honolulu")
        self.assertEqual(page.locator(".bulk-time-trigger").first.inner_text().strip(), "13:00")

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="custom timezone persisted state")

    def test_mobile_first_page_calendar_state_has_no_accessibility_violations(self) -> None:
        page = self.require_page()
        page.set_viewport_size({"width": 480, "height": 900})

        self.open_home_page()
        self.login(name="pagination-first-a11y-owner")
        self.create_poll(
            title="Paginated first-page accessibility poll",
            description="Used for first mobile page accessibility coverage.",
            identifier="paginated_first_page_a11y_poll",
            timezone="Europe/Helsinki",
            start_date="2026-06-08",
            end_date="2026-06-14",
            daily_start_hour=9,
            daily_end_hour=10,
            allowed_weekdays=[0, 1, 2, 3, 4, 5, 6],
        )

        nav_range = page.locator(".calendar-nav-range")
        nav_range.wait_for()
        visible_days = page.locator(".calendar-day-col").count()
        page.wait_for_function(
            """
            (endDay) => {
              const range = document.querySelector('.calendar-nav-range');
              return Boolean(range) && range.textContent.trim() === `Days 1-${endDay}/7`;
            }
            """,
            arg=visible_days,
        )

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="mobile first page calendar state")

    def test_mobile_last_page_calendar_state_has_no_accessibility_violations(self) -> None:
        page = self.require_page()
        page.set_viewport_size({"width": 480, "height": 900})

        self.open_home_page()
        self.login(name="pagination-last-a11y-owner")
        self.create_poll(
            title="Paginated last-page accessibility poll",
            description="Used for last mobile page accessibility coverage.",
            identifier="paginated_last_page_a11y_poll",
            timezone="Europe/Helsinki",
            start_date="2026-06-08",
            end_date="2026-06-14",
            daily_start_hour=9,
            daily_end_hour=10,
            allowed_weekdays=[0, 1, 2, 3, 4, 5, 6],
        )

        nav_range = page.locator(".calendar-nav-range")
        nav_range.wait_for()
        visible_days = page.locator(".calendar-day-col").count()
        next_button = page.get_by_role("button", name="Next days")
        while next_button.is_enabled():
            next_button.click()

        last_start = 7 - visible_days + 1
        page.wait_for_function(
            """
            ([startDay, endDay]) => {
              const range = document.querySelector('.calendar-nav-range');
              return Boolean(range) && range.textContent.trim() === `Days ${startDay}-${endDay}/7`;
            }
            """,
            arg=[last_start, 7],
        )

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="mobile last page calendar state")

    def test_profile_empty_state_has_no_accessibility_violations(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="profile-empty-a11y-user")
        page.locator(".auth-name-link").click()
        page.get_by_role("heading", name="My data").wait_for()
        page.get_by_text("No created polls.").wait_for()
        page.get_by_text("No votes.").wait_for()

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="profile empty state")

    def test_result_mode_no_rows_match_filter_state_has_no_accessibility_violations(self) -> None:
        page = self.require_page()
        poll_identifier = "no_rows_filter_a11y_poll"

        self.open_home_page()
        self.login(name="no-rows-filter-a11y-creator")
        self.create_poll(
            title="No rows filter accessibility poll",
            description="Used for empty result filter accessibility coverage.",
            identifier=poll_identifier,
            timezone="Europe/Helsinki",
            start_date="2026-06-08",
            end_date="2026-06-15",
            daily_start_hour=9,
            daily_end_hour=10,
            allowed_weekdays=[0, 1, 2, 3, 4, 5, 6],
        )

        page.locator(".vote-switch-option-yes").first.click()
        self.wait_for_first_vote_state(".vote-switch-option-yes", True, page=page)

        voter_page = self.open_logged_in_poll_page(
            poll_identifier=poll_identifier,
            name="no-rows-filter-a11y-voter",
        )
        voter_page.locator(".vote-switch-option-yes").first.click()
        self.wait_for_first_vote_state(".vote-switch-option-yes", True, page=voter_page)

        page.reload(wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.locator(".details-title").filter(has_text="No rows filter accessibility poll").wait_for()
        page.locator(".calendar-vote-mode-item").filter(has_text="Result mode").click()
        page.locator("#min-yes-filter").select_option("2")
        page.get_by_text("No options match the current Yes filter.").wait_for()

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="result mode no rows match filter state")

    def test_create_form_no_slots_error_state_has_no_accessibility_violations(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="no-slots-a11y-owner")
        page.get_by_role("button", name="Create new poll").click()
        page.locator("#poll-title").fill("No slots accessibility poll")
        page.locator("#poll-description").fill("Used for no slots accessibility coverage.")
        page.locator("#poll-identifier").fill("no_slots_a11y_poll")
        page.locator("#poll-timezone").fill("Europe/Helsinki")
        page.locator("#start-date").fill("2026-06-06")
        page.locator("#end-date").fill("2026-06-06")
        page.locator("#section-panel-create button[type='submit']").click()
        page.get_by_role("alert").filter(
            has_text="No slots were generated. Adjust date range, weekdays or daily hours."
        ).wait_for()

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="create form no slots error state")

    def test_browser_auth_dialog_keyboard_focus_is_trapped_and_restored_on_escape(self) -> None:
        page = self.require_page()

        self.open_home_page()
        login_button = page.get_by_role("button", name="Login").first
        login_button.click()
        page.get_by_role("dialog").wait_for()

        self.assertEqual(self.active_element_snapshot(page)["id"], "auth-name")

        page.keyboard.press("Tab")
        self.assertEqual(self.active_element_snapshot(page)["id"], "auth-pin")

        page.keyboard.press("Tab")
        self.assertEqual(self.active_element_snapshot(page)["text"], "Login")
        self.assertTrue(self.active_element_has_visible_focus(page))

        page.keyboard.press("Tab")
        self.assertEqual(self.active_element_snapshot(page)["id"], "auth-name")

        page.keyboard.press("Shift+Tab")
        self.assertEqual(self.active_element_snapshot(page)["text"], "Login")

        page.keyboard.press("Escape")
        page.get_by_role("dialog").wait_for(state="hidden")
        self.assertTrue(login_button.evaluate("element => document.activeElement === element"))

    def test_browser_create_timezone_listbox_supports_keyboard_navigation(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="timezone-keyboard-a11y-owner")
        page.get_by_role("button", name="Create new poll").click()

        timezone_input = page.locator("#poll-timezone")
        timezone_input.fill("europe/hel")
        page.locator("#create-timezone-suggestions").wait_for()

        page.keyboard.press("ArrowDown")
        self.assertEqual(timezone_input.get_attribute("aria-activedescendant"), "create-timezone-suggestion-0")
        self.assertTrue(page.locator("#create-timezone-suggestions .timezone-suggestion.is-active").is_visible())

        page.keyboard.press("Escape")
        page.locator("#create-timezone-suggestions").wait_for(state="hidden")

        timezone_input.fill("europe/hel")
        page.locator("#create-timezone-suggestions").wait_for()
        page.keyboard.press("ArrowDown")
        page.keyboard.press("Enter")

        page.locator("#create-timezone-suggestions").wait_for(state="hidden")
        self.assertEqual(timezone_input.input_value(), "Europe/Helsinki")

    def test_browser_calendar_timezone_listbox_supports_keyboard_navigation(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="calendar-timezone-keyboard-a11y-owner")
        self.create_poll(
            title="Calendar timezone keyboard accessibility poll",
            description="Used for calendar timezone keyboard coverage.",
            identifier="calendar_timezone_keyboard_a11y_poll",
            timezone="UTC",
            start_date="2026-06-10",
            end_date="2026-06-10",
            daily_start_hour=23,
            daily_end_hour=24,
        )

        page.locator(".calendar-timezone-mode-item-custom").click()
        timezone_input = page.locator("#calendar-timezone")
        timezone_input.fill("pacific/hon")
        page.locator("#calendar-timezone-suggestions").wait_for()

        page.keyboard.press("ArrowDown")
        self.assertEqual(timezone_input.get_attribute("aria-activedescendant"), "calendar-timezone-suggestion-0")
        self.assertTrue(page.locator("#calendar-timezone-suggestions .timezone-suggestion.is-active").is_visible())

        page.keyboard.press("Enter")
        page.locator("#calendar-timezone-suggestions").wait_for(state="hidden")
        page.wait_for_function(
            """
            () => {
              const rowLabel = document.querySelector('.bulk-time-trigger');
              return Boolean(rowLabel) && rowLabel.textContent.trim() === '13:00';
            }
            """
        )
        self.assertEqual(timezone_input.input_value(), "Pacific/Honolulu")

    def test_browser_bulk_menu_supports_keyboard_navigation(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="bulk-menu-keyboard-a11y-owner")
        self.create_poll(
            title="Bulk menu keyboard accessibility poll",
            description="Used for bulk menu keyboard coverage.",
            identifier="bulk_menu_keyboard_a11y_poll",
            timezone="Europe/Helsinki",
            start_date="2026-06-11",
            end_date="2026-06-12",
            daily_start_hour=9,
            daily_end_hour=11,
        )

        first_day_trigger = page.locator(".bulk-day-trigger").first
        first_day_trigger.focus()
        page.keyboard.press("ArrowDown")
        page.locator(".bulk-menu").wait_for()
        self.assertEqual(self.active_element_snapshot(page)["text"], "No vote")
        self.assertTrue(self.active_element_has_visible_focus(page))

        page.keyboard.press("ArrowDown")
        self.assertEqual(self.active_element_snapshot(page)["text"], "Yes")

        page.keyboard.press("Enter")
        page.locator(".bulk-menu").wait_for(state="hidden")
        self.assertTrue(first_day_trigger.evaluate("element => document.activeElement === element"))
        page.wait_for_function(
            """
            () => {
              const table = document.querySelector('.calendar-table');
              if (!table) {
                return false;
              }
              const firstDayHeader = table.querySelector('thead th.calendar-day-col');
              if (!firstDayHeader || !firstDayHeader.parentElement) {
                return false;
              }
              const columnIndex = Array.from(firstDayHeader.parentElement.children).indexOf(firstDayHeader);
              const rows = Array.from(table.querySelectorAll('tbody tr'))
                .filter((row) => row.querySelector('td.calendar-cell'));
              if (!rows.length) {
                return false;
              }
              return rows.every((row) => {
                const cell = row.children[columnIndex];
                const button = cell && cell.querySelector('.vote-switch-option-yes');
                return Boolean(button) && button.getAttribute('aria-checked') === 'true';
              });
            }
            """
        )

    def test_browser_vote_radiogroup_supports_arrow_keys_and_visible_focus(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="vote-radiogroup-keyboard-a11y-owner")
        self.create_poll(
            title="Vote radiogroup keyboard accessibility poll",
            description="Used for vote radiogroup keyboard coverage.",
            identifier="vote_radiogroup_keyboard_a11y_poll",
            timezone="Europe/Helsinki",
            start_date="2026-06-15",
            end_date="2026-06-15",
        )

        yes_button = page.locator(".vote-switch-option-yes").first
        yes_button.focus()

        page.keyboard.press("ArrowRight")
        page.wait_for_function(
            """
            () => {
              const button = document.querySelector('.vote-switch-option-maybe');
              return Boolean(button)
                && button.getAttribute('aria-checked') === 'true'
                && document.activeElement === button;
            }
            """
        )
        self.assertEqual(self.active_element_snapshot(page)["status"], "maybe")
        self.assertTrue(self.active_element_has_visible_focus(page))

        page.keyboard.press("ArrowRight")
        page.wait_for_function(
            """
            () => {
              const button = document.querySelector('.vote-switch-option-no');
              return Boolean(button)
                && button.getAttribute('aria-checked') === 'true'
                && document.activeElement === button;
            }
            """
        )
        self.assertEqual(self.active_element_snapshot(page)["status"], "no")

        page.keyboard.press("Home")
        page.wait_for_function(
            """
            () => {
              const button = document.querySelector('.vote-switch-option-yes');
              return Boolean(button)
                && button.getAttribute('aria-checked') === 'true'
                && document.activeElement === button;
            }
            """
        )
        self.assertEqual(self.active_element_snapshot(page)["status"], "yes")

        page.keyboard.press("End")
        page.wait_for_function(
            """
            () => {
              const button = document.querySelector('.vote-switch-option-no');
              return Boolean(button)
                && button.getAttribute('aria-checked') === 'true'
                && document.activeElement === button;
            }
            """
        )
        self.assertEqual(self.active_element_snapshot(page)["status"], "no")

    def test_browser_language_switcher_supports_basic_switching_and_visible_focus(self) -> None:
        page = self.require_page()

        self.open_home_page()
        language_select = page.locator("#language-select")

        language_select.focus()
        self.assertTrue(self.active_element_has_visible_focus(page))
        language_select.select_option("fi")

        page.get_by_role("button", name="Kirjaudu").wait_for()
        self.assertEqual(language_select.input_value(), "fi")
        self.assertEqual(page.locator("label[for='language-select']").inner_text().strip(), "Kieli")
        self.assertEqual(page.evaluate("() => document.documentElement.lang"), "fi")
        self.assertEqual(
            page.evaluate("() => window.localStorage.getItem('timepoll-language')"),
            "fi",
        )

    def test_browser_calendar_pagination_buttons_support_keyboard_navigation_and_visible_focus(self) -> None:
        page = self.require_page()
        page.set_viewport_size({"width": 480, "height": 900})

        self.open_home_page()
        self.login(name="pagination-keyboard-owner")
        self.create_poll(
            title="Paginated keyboard accessibility poll",
            description="Used for calendar pagination keyboard coverage.",
            identifier="paginated_keyboard_accessibility_poll",
            timezone="Europe/Helsinki",
            start_date="2026-06-22",
            end_date="2026-06-28",
            daily_start_hour=9,
            daily_end_hour=10,
            allowed_weekdays=[0, 1, 2, 3, 4, 5, 6],
        )

        nav_range = page.locator(".calendar-nav-range")
        nav_range.wait_for()
        visible_days = page.locator(".calendar-day-col").count()
        self.assertGreater(visible_days, 0)
        self.assertLess(visible_days, 7)

        next_button = page.get_by_role("button", name="Next days")
        next_button.focus()
        self.assertTrue(next_button.evaluate("element => document.activeElement === element"))

        page.keyboard.press("Enter")
        page.wait_for_function(
            """
            ([startDay, endDay]) => {
              const range = document.querySelector('.calendar-nav-range');
              return Boolean(range) && range.textContent.trim() === `Days ${startDay}-${endDay}/7`;
            }
            """,
            arg=[2, visible_days + 1],
        )

        previous_button = page.get_by_role("button", name="Previous days")
        previous_button.focus()
        self.assertTrue(previous_button.evaluate("element => document.activeElement === element"))

        page.keyboard.press("Space")
        page.wait_for_function(
            """
            (endDay) => {
              const range = document.querySelector('.calendar-nav-range');
              return Boolean(range) && range.textContent.trim() === `Days 1-${endDay}/7`;
            }
            """,
            arg=visible_days,
        )

    def test_browser_result_mode_filter_controls_support_keyboard_navigation(self) -> None:
        page = self.require_page()
        poll_identifier = "result_filter_keyboard_poll"

        self.open_home_page()
        self.login(name="result-filter-keyboard-owner")
        self.create_poll(
            title="Result filter keyboard accessibility poll",
            description="Used for result mode filter keyboard coverage.",
            identifier=poll_identifier,
            timezone="Europe/Helsinki",
            start_date="2026-06-29",
            end_date="2026-06-30",
            daily_start_hour=9,
            daily_end_hour=11,
        )

        creator_yes_buttons = page.locator(".vote-switch-option-yes")
        creator_yes_buttons.nth(0).click()
        creator_yes_buttons.nth(1).click()
        self.wait_for_first_vote_state(".vote-switch-option-yes", True, page=page)

        voter_page = self.open_logged_in_poll_page(
            poll_identifier=poll_identifier,
            name="result-filter-keyboard-voter",
        )
        voter_page.locator(".vote-switch-option-yes").first.click()
        self.wait_for_first_vote_state(".vote-switch-option-yes", True, page=voter_page)

        page.reload(wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.locator(".details-title").filter(
            has_text="Result filter keyboard accessibility poll"
        ).wait_for()

        results_mode_radio = page.locator("input[name='calendar-vote-mode'][value='results']")
        results_mode_radio.focus()
        page.keyboard.press("Space")
        page.wait_for_function(
            """
            () => {
              const radio = document.querySelector("input[name='calendar-vote-mode'][value='results']");
              return Boolean(radio) && radio.checked;
            }
            """
        )

        yes_filter = page.locator("#min-yes-filter")
        yes_filter.focus()
        self.assertTrue(yes_filter.evaluate("element => document.activeElement === element"))
        self.assertTrue(self.active_element_has_visible_focus(page))

        yes_filter.select_option("2")
        page.wait_for_function(
            """
            () => {
              const select = document.querySelector('#min-yes-filter');
              return Boolean(select) && select.value === '2';
            }
            """
        )
        self.wait_for_vote_switch_count(1, page=page)

    def test_browser_profile_controls_support_keyboard_navigation(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="profile-controls-keyboard-owner")
        self.create_poll(
            title="Profile controls keyboard accessibility poll",
            description="Used for profile keyboard coverage.",
            identifier="profile_controls_keyboard_accessibility_poll",
            timezone="Europe/Helsinki",
            start_date="2026-07-01",
            end_date="2026-07-01",
        )

        page.locator(".vote-switch-option-yes").first.click()
        self.wait_for_first_vote_state(".vote-switch-option-yes", True, page=page)

        page.locator(".auth-name-link").click()
        page.get_by_role("heading", name="My data").wait_for()

        download_button = page.get_by_role("button", name="Download JSON")
        download_button.focus()
        self.assertTrue(download_button.evaluate("element => document.activeElement === element"))

        page.keyboard.press("Tab")
        self.assertEqual(self.active_element_snapshot(page)["text"], "Delete own data")

        open_poll_button = page.locator("#section-panel-profile .profile-open-poll-btn").first
        open_poll_button.focus()
        self.assertTrue(open_poll_button.evaluate("element => document.activeElement === element"))

        page.keyboard.press("Enter")
        page.locator(".details-title").filter(
            has_text="Profile controls keyboard accessibility poll"
        ).wait_for()

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
        self.assertEqual(page.evaluate("() => document.documentElement.lang"), "fi")
        self.assertEqual(
            page.evaluate("() => window.localStorage.getItem('timepoll-language')"),
            "fi",
        )
        self.assertEqual(first_maybe_button.get_attribute("aria-checked"), "false")
        self.assertEqual(first_yes_button.get_attribute("aria-checked"), "false")

    def test_browser_bulk_vote_by_day_and_time_row(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="bulk-voter")
        self.create_poll(
            title="Bulk vote poll",
            description="Used for bulk vote coverage.",
            identifier="bulk_vote_poll",
            timezone="Europe/Helsinki",
            start_date="2026-04-07",
            end_date="2026-04-08",
            daily_start_hour=9,
            daily_end_hour=12,
        )

        first_day_header = page.locator(".calendar-day-col").first
        first_day_header.locator(".bulk-day-trigger").click()
        first_day_header.locator(".bulk-menu-item").filter(has_text="Yes").click()
        page.wait_for_function(
            """
            () => {
              const table = document.querySelector('.calendar-table');
              if (!table) {
                return false;
              }
              const firstDayHeader = table.querySelector('thead th.calendar-day-col');
              if (!firstDayHeader || !firstDayHeader.parentElement) {
                return false;
              }
              const columnIndex = Array.from(firstDayHeader.parentElement.children).indexOf(firstDayHeader);
              const rows = Array.from(table.querySelectorAll('tbody tr'))
                .filter((row) => row.querySelector('td.calendar-cell'));
              if (!rows.length) {
                return false;
              }
              return rows.every((row) => {
                const cell = row.children[columnIndex];
                const button = cell && cell.querySelector('.vote-switch-option-yes');
                return Boolean(button) && button.getAttribute('aria-checked') === 'true';
              });
            }
            """
        )

        first_time_row = page.locator(".calendar-time-row").first
        first_time_row.locator(".bulk-time-trigger").click()
        first_time_row.locator(".bulk-menu-item").filter(has_text="Maybe").click()
        page.wait_for_function(
            """
            () => {
              const firstRow = document.querySelector('.calendar-table tbody tr');
              if (!firstRow) {
                return false;
              }
              const cells = Array.from(firstRow.querySelectorAll('td.calendar-cell'));
              if (!cells.length) {
                return false;
              }
              return cells.every((cell) => {
                const maybeButton = cell.querySelector('.vote-switch-option-maybe');
                return Boolean(maybeButton) && maybeButton.getAttribute('aria-checked') === 'true';
              });
            }
            """
        )
        page.wait_for_function(
            """
            () => {
              const secondRow = document.querySelectorAll('.calendar-table tbody tr')[1];
              if (!secondRow) {
                return false;
              }
              const firstVoteCell = secondRow.querySelector('td.calendar-cell');
              if (!firstVoteCell) {
                return false;
              }
              const yesButton = firstVoteCell.querySelector('.vote-switch-option-yes');
              return Boolean(yesButton) && yesButton.getAttribute('aria-checked') === 'true';
            }
            """
        )

    def test_browser_yes_filter_hides_rows_below_selected_threshold(self) -> None:
        page = self.require_page()
        poll_identifier = "yes_filter_poll"

        self.open_home_page()
        self.login(name="yes-filter-creator")
        self.create_poll(
            title="Yes filter poll",
            description="Used for yes vote filter coverage.",
            identifier=poll_identifier,
            timezone="Europe/Helsinki",
            start_date="2026-04-13",
            end_date="2026-04-14",
            daily_start_hour=9,
            daily_end_hour=11,
        )

        creator_yes_buttons = page.locator(".vote-switch-option-yes")
        creator_yes_buttons.nth(0).click()
        creator_yes_buttons.nth(1).click()
        self.wait_for_first_vote_state(".vote-switch-option-yes", True, page=page)

        browser = self.browser
        if browser is None:
            raise unittest.SkipTest("Playwright browser is not available for this test run.")

        voter_context = browser.new_context(base_url=self.live_server_url)
        self.addCleanup(voter_context.close)
        voter_page = voter_context.new_page()
        voter_page.set_default_timeout(15000)

        self.open_home_page(voter_page, f"/?id={poll_identifier}")
        self.login(name="yes-filter-voter", page=voter_page)
        voter_page.locator(".vote-switch-option-yes").first.click()
        self.wait_for_first_vote_state(".vote-switch-option-yes", True, page=voter_page)

        page.reload(wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.locator(".details-title").filter(has_text="Yes filter poll").wait_for()
        page.locator(".calendar-vote-mode-item").filter(has_text="Result mode").click()
        self.wait_for_vote_switch_count(4, page=page)

        page.locator("#min-yes-filter").select_option("2")
        self.wait_for_vote_switch_count(1, page=page)

        visible_yes_count = page.locator(".vote-switch-option-yes .vote-switch-count").first.inner_text()
        self.assertEqual(visible_yes_count, "2")
        self.assertEqual(page.locator("#min-yes-filter").input_value(), "2")

    def test_browser_custom_calendar_timezone_persists_after_reload(self) -> None:
        page = self.require_page()
        poll_identifier = "custom_timezone_poll"

        self.open_home_page()
        self.login(name="timezone-owner")
        self.create_poll(
            title="Custom timezone poll",
            description="Used for timezone persistence coverage.",
            identifier=poll_identifier,
            timezone="UTC",
            start_date="2026-04-15",
            end_date="2026-04-15",
            daily_start_hour=23,
            daily_end_hour=24,
        )

        first_time_label = page.locator(".bulk-time-trigger").first
        self.assertEqual(first_time_label.inner_text().strip(), "23:00")

        page.locator(".calendar-timezone-mode-item-custom").click()
        page.locator("#calendar-timezone").fill("Pacific/Honolulu")
        page.locator(".details-title").click()
        page.wait_for_function(
            """
            () => {
              const rowLabel = document.querySelector('.bulk-time-trigger');
              if (!rowLabel) {
                return false;
              }
              return rowLabel.textContent.trim() === '13:00';
            }
            """
        )
        page.wait_for_function(
            """
            () => {
              const entry = Object.entries(window.localStorage)
                .find(([key]) => key.startsWith('timepoll-calendar-timezone:'));
              return Boolean(entry) && entry[1] === '{"mode":"custom","timezone":"Pacific/Honolulu"}';
            }
            """
        )

        stored_preference = page.evaluate(
            """
            () => {
              const entry = Object.entries(window.localStorage)
                .find(([key]) => key.startsWith('timepoll-calendar-timezone:'));
              return entry ? entry[1] : '';
            }
            """
        )
        self.assertEqual(
            stored_preference,
            '{"mode":"custom","timezone":"Pacific/Honolulu"}',
        )

        page.reload(wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.locator(".details-title").filter(has_text="Custom timezone poll").wait_for()
        self.assertTrue(
            page.locator("input[name='calendar-timezone-mode'][value='custom']").is_checked()
        )
        self.assertEqual(page.locator("#calendar-timezone").input_value(), "Pacific/Honolulu")
        self.assertEqual(page.locator(".bulk-time-trigger").first.inner_text().strip(), "13:00")

    def test_browser_profile_can_delete_single_vote_and_refresh_poll_view(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="profile-vote-owner")
        self.create_poll(
            title="Profile vote delete poll",
            description="Used for profile vote deletion coverage.",
            identifier="profile_vote_delete_poll",
            timezone="Europe/Helsinki",
            start_date="2026-04-16",
            end_date="2026-04-16",
        )

        first_yes_button = page.locator(".vote-switch-option-yes").first
        first_yes_button.click()
        self.wait_for_first_vote_state(".vote-switch-option-yes", True, page=page)

        page.locator(".auth-name-link").click()
        page.get_by_role("heading", name="My data").wait_for()
        page.get_by_text("My vote: Yes").wait_for()
        page.get_by_role("button", name="Delete vote").click()
        page.get_by_role("status").filter(has_text="Vote deleted.").wait_for()
        page.get_by_text("No votes.").wait_for()

        page.get_by_role("button", name="Profile vote delete poll").click()
        page.locator(".details-title").filter(has_text="Profile vote delete poll").wait_for()
        self.assertEqual(page.locator(".vote-switch-option-yes").first.get_attribute("aria-checked"), "false")

    def test_browser_invalid_poll_id_in_url_falls_back_to_list_and_cleans_query(self) -> None:
        page = self.require_page()

        self.open_home_page(path="/?id=missing_poll_2026")
        page.wait_for_function("() => !window.location.search.includes('id=')")
        page.get_by_role("heading", name="Polls").wait_for()
        page.get_by_text("No polls yet.").wait_for()

        self.assertNotIn("id=", page.url)
        self.assertTrue(page.url.endswith("/"))

    def test_browser_day_pagination_and_row_bulk_vote_only_apply_to_visible_days(self) -> None:
        page = self.require_page()
        page.set_viewport_size({"width": 480, "height": 900})

        self.open_home_page()
        self.login(name="pagination-owner")
        self.create_poll(
            title="Paginated bulk poll",
            description="Used for day pagination and row bulk vote coverage.",
            identifier="paginated_bulk_poll",
            timezone="Europe/Helsinki",
            start_date="2026-04-13",
            end_date="2026-04-19",
            daily_start_hour=9,
            daily_end_hour=10,
            allowed_weekdays=[0, 1, 2, 3, 4, 5, 6],
        )

        nav_range = page.locator(".calendar-nav-range")
        nav_range.wait_for()
        visible_days = page.locator(".calendar-day-col").count()
        self.assertGreater(visible_days, 0)
        self.assertLess(visible_days, 7)
        self.assertEqual(nav_range.inner_text().strip(), f"Days 1-{visible_days}/7")

        first_time_row = page.locator(".calendar-time-row").first
        first_time_row.locator(".bulk-time-trigger").click()
        first_time_row.locator(".bulk-menu-item").filter(has_text="Yes").click()
        page.wait_for_function(
            """
            (expectedCount) => {
              const row = document.querySelector('.calendar-table tbody tr');
              if (!row) {
                return false;
              }
              const yesButtons = Array.from(row.querySelectorAll('.vote-switch-option-yes'));
              return yesButtons.length === expectedCount && yesButtons.every((button) => button.getAttribute('aria-checked') === 'true');
            }
            """,
            arg=visible_days,
        )

        next_button = page.get_by_role("button", name="Next days")
        while next_button.is_enabled():
            next_button.click()

        last_start = 7 - visible_days + 1
        page.wait_for_function(
            """
            ([startDay, endDay]) => {
              const range = document.querySelector('.calendar-nav-range');
              return Boolean(range) && range.textContent.trim() === `Days ${startDay}-${endDay}/7`;
            }
            """,
            arg=[last_start, 7],
        )
        page.wait_for_function(
            """
            (expectedCount) => {
              const row = document.querySelector('.calendar-table tbody tr');
              if (!row) {
                return false;
              }
              const yesButtons = Array.from(row.querySelectorAll('.vote-switch-option-yes'));
              return yesButtons.length === expectedCount && yesButtons.every((button) => button.getAttribute('aria-checked') === 'false');
            }
            """,
            arg=visible_days,
        )

        previous_button = page.get_by_role("button", name="Previous days")
        while previous_button.is_enabled():
            previous_button.click()

        page.wait_for_function(
            """
            (endDay) => {
              const range = document.querySelector('.calendar-nav-range');
              return Boolean(range) && range.textContent.trim() === `Days 1-${endDay}/7`;
            }
            """,
            arg=visible_days,
        )
        page.wait_for_function(
            """
            (expectedCount) => {
              const row = document.querySelector('.calendar-table tbody tr');
              if (!row) {
                return false;
              }
              const yesButtons = Array.from(row.querySelectorAll('.vote-switch-option-yes'));
              return yesButtons.length === expectedCount && yesButtons.every((button) => button.getAttribute('aria-checked') === 'true');
            }
            """,
            arg=visible_days,
        )

    def test_browser_logout_keeps_selected_poll_open_and_refreshes_to_anonymous_state(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="logout-owner")
        self.create_poll(
            title="Logout state poll",
            description="Used for logout selected poll coverage.",
            identifier="logout_state_poll",
            timezone="Europe/Helsinki",
            start_date="2026-04-20",
            end_date="2026-04-20",
        )

        first_yes_button = page.locator(".vote-switch-option-yes").first
        first_yes_button.click()
        self.wait_for_first_vote_state(".vote-switch-option-yes", True, page=page)

        page.get_by_role("button", name="Logout", exact=True).click()
        page.get_by_role("button", name="Login").wait_for()
        page.locator(".details-title").filter(has_text="Logout state poll").wait_for()
        page.get_by_text("Enter your name and PIN to continue.").wait_for()

        self.assertEqual(first_yes_button.get_attribute("aria-checked"), "false")

        first_yes_button.click()
        page.get_by_role("dialog").wait_for()

    def test_browser_create_success_feedback_remains_visible_after_opening_created_poll(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="create-success-feedback-owner")
        self.create_poll(
            title="Create success feedback poll",
            description="Used for create success feedback coverage.",
            identifier="create_success_feedback_poll",
            timezone="Europe/Helsinki",
            start_date="2026-04-22",
            end_date="2026-04-22",
        )

        page.get_by_role("status").filter(has_text="Poll created successfully.").wait_for()
        page.locator(".details-title").filter(has_text="Create success feedback poll").wait_for()

    def test_browser_login_success_feedback_remains_visible_after_refreshing_selected_poll(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="login-success-feedback-owner")
        self.create_poll(
            title="Login success feedback poll",
            description="Used for login success feedback coverage.",
            identifier="login_success_feedback_poll",
            timezone="Europe/Helsinki",
            start_date="2026-04-23",
            end_date="2026-04-23",
        )

        page.get_by_role("button", name="Logout", exact=True).click()
        page.get_by_role("button", name="Login").wait_for()
        page.get_by_role("button", name="Login").click()
        self.submit_auth_dialog(name="login-success-feedback-owner")

        page.get_by_role("status").filter(has_text="Logged in.").wait_for()
        page.locator(".details-title").filter(has_text="Login success feedback poll").wait_for()

    def test_browser_logout_success_feedback_remains_visible_after_refreshing_selected_poll(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="logout-success-feedback-owner")
        self.create_poll(
            title="Logout success feedback poll",
            description="Used for logout success feedback coverage.",
            identifier="logout_success_feedback_poll",
            timezone="Europe/Helsinki",
            start_date="2026-04-24",
            end_date="2026-04-24",
        )

        page.get_by_role("button", name="Logout", exact=True).click()
        page.get_by_role("button", name="Login").wait_for()
        page.get_by_role("status").filter(has_text="Logged out.").wait_for()
        page.locator(".details-title").filter(has_text="Logout success feedback poll").wait_for()

    def test_browser_login_from_create_view_does_not_reopen_stale_selected_poll(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="stale-selected-login-owner")
        self.create_poll(
            title="Stale selected login poll",
            description="Used for stale selected poll login coverage.",
            identifier="stale_selected_login_poll",
            timezone="Europe/Helsinki",
            start_date="2026-04-20",
            end_date="2026-04-20",
        )

        page.get_by_role("button", name="Logout", exact=True).click()
        page.get_by_role("button", name="Login").wait_for()
        page.locator(".title-home").click()
        page.get_by_role("heading", name="Polls").wait_for()
        page.get_by_role("button", name="Create new poll").click()
        page.locator("#section-panel-create").wait_for()
        self.assertNotIn("id=", page.url)

        page.get_by_role("button", name="Login").click()
        self.submit_auth_dialog(name="stale-selected-login-user")
        page.get_by_role("button", name="Logout", exact=True).wait_for()

        page.locator("#section-panel-create").wait_for()
        self.assertFalse(page.locator(".details-title").is_visible())
        self.assertNotIn("id=", page.url)

    def test_browser_logout_from_profile_view_does_not_reopen_stale_selected_poll(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="stale-selected-logout-owner")
        self.create_poll(
            title="Stale selected logout poll",
            description="Used for stale selected poll logout coverage.",
            identifier="stale_selected_logout_poll",
            timezone="Europe/Helsinki",
            start_date="2026-04-21",
            end_date="2026-04-21",
        )

        page.locator(".auth-name-link").click()
        page.get_by_role("heading", name="My data").wait_for()
        self.assertNotIn("id=", page.url)

        page.get_by_role("button", name="Logout", exact=True).click()
        page.get_by_role("button", name="Login").wait_for()

        page.get_by_role("heading", name="My data").wait_for()
        self.assertFalse(page.locator(".details-title").is_visible())
        self.assertNotIn("id=", page.url)

    def test_browser_partial_delete_own_data_shows_remaining_poll_summary(self) -> None:
        page = self.require_page()
        keep_identifier = "profile_keep_poll"
        delete_identifier = "profile_delete_poll"

        self.open_home_page()
        self.login(name="partial-delete-owner")
        self.create_poll(
            title="Profile keep poll",
            description="Poll that should remain after delete own data.",
            identifier=keep_identifier,
            timezone="Europe/Helsinki",
            start_date="2026-04-21",
            end_date="2026-04-21",
        )
        keep_yes_button = page.locator(".vote-switch-option-yes").first
        keep_yes_button.click()
        self.wait_for_first_vote_state(".vote-switch-option-yes", True, page=page)

        page.locator(".title-home").click()
        page.get_by_role("heading", name="Polls").wait_for()
        page.get_by_role("button", name="Create new poll").click()
        page.locator("#poll-title").fill("Profile delete poll")
        page.locator("#poll-description").fill("Poll that should be deleted.")
        page.locator("#poll-identifier").fill(delete_identifier)
        page.locator("#poll-timezone").fill("Europe/Helsinki")
        page.locator("#start-date").fill("2026-04-22")
        page.locator("#end-date").fill("2026-04-22")
        page.locator("#section-panel-create button[type='submit']").click()
        page.locator(".details-title").filter(has_text="Profile delete poll").wait_for()

        delete_yes_button = page.locator(".vote-switch-option-yes").first
        delete_yes_button.click()
        self.wait_for_first_vote_state(".vote-switch-option-yes", True, page=page)

        browser = self.browser
        if browser is None:
            raise unittest.SkipTest("Playwright browser is not available for this test run.")

        guest_context = browser.new_context(base_url=self.live_server_url)
        self.addCleanup(guest_context.close)
        guest_page = guest_context.new_page()
        guest_page.set_default_timeout(15000)

        self.open_home_page(guest_page, f"/?id={keep_identifier}")
        self.login(name="partial-delete-guest", page=guest_page)
        guest_page.locator(".vote-switch-option-no").first.click()
        self.wait_for_first_vote_state(".vote-switch-option-no", True, page=guest_page)

        page.locator(".auth-name-link").click()
        page.get_by_role("heading", name="My data").wait_for()
        page.get_by_text("Vote count: 2").wait_for()

        page.on("dialog", lambda dialog: dialog.accept())
        page.get_by_role("button", name="Delete own data").click()

        page.get_by_role("status").filter(has_text="Own data deleted where possible.").wait_for()
        page.get_by_text("Deleted votes: 2").wait_for()
        page.get_by_text("Deleted polls: 1").wait_for()
        page.get_by_text("Remaining created polls: 1").wait_for()
        page.get_by_text("Remaining polls with other users' votes: 1").wait_for()
        page.get_by_role("button", name="Logout").wait_for()
        page.get_by_role("button", name="Profile keep poll").wait_for()
        page.get_by_text("No votes.").wait_for()

    def test_browser_browser_timezone_preference_falls_back_to_poll_mode_when_option_unavailable(self) -> None:
        browser = self.browser
        if browser is None:
            raise unittest.SkipTest("Playwright browser is not available for this test run.")

        utc_context = browser.new_context(base_url=self.live_server_url, timezone_id="UTC")
        self.addCleanup(utc_context.close)
        utc_page = utc_context.new_page()
        utc_page.set_default_timeout(15000)

        self.open_home_page(utc_page)
        self.login(name="browser-tz-owner", page=utc_page)

        identity_id = utc_page.evaluate(
            """
            async () => {
              const response = await fetch('/api/auth/session/', { credentials: 'same-origin' });
              const payload = await response.json();
              return payload.identity.id;
            }
            """
        )
        utc_page.evaluate(
            """
            ([identityId, value]) => {
              window.localStorage.setItem(`timepoll-calendar-timezone:${identityId}`, value);
            }
            """,
            [identity_id, '{"mode":"browser","timezone":"UTC"}'],
        )

        self.create_poll(
            title="Browser timezone fallback poll",
            description="Used for browser timezone fallback coverage.",
            identifier="browser_timezone_fallback_poll",
            timezone="UTC",
            start_date="2026-04-23",
            end_date="2026-04-23",
            daily_start_hour=9,
            daily_end_hour=10,
            page=utc_page,
        )

        utc_page.locator(".details-title").filter(has_text="Browser timezone fallback poll").wait_for()
        self.assertFalse(
            utc_page.locator("input[name='calendar-timezone-mode'][value='browser']").is_visible()
        )
        self.assertTrue(
            utc_page.locator("input[name='calendar-timezone-mode'][value='poll']").is_checked()
        )
        self.assertEqual(utc_page.locator(".bulk-time-trigger").first.inner_text().strip(), "09:00")

    def test_browser_pending_vote_action_resumes_after_login(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="pending-vote-creator")
        self.create_poll(
            title="Pending vote poll",
            description="Used for pending vote action coverage.",
            identifier="pending_vote_poll",
            timezone="Europe/Helsinki",
            start_date="2026-04-24",
            end_date="2026-04-24",
        )

        page.get_by_role("button", name="Logout", exact=True).click()
        page.get_by_role("button", name="Login").wait_for()

        first_yes_button = page.locator(".vote-switch-option-yes").first
        first_yes_button.click()
        page.get_by_role("dialog").wait_for()

        self.submit_auth_dialog(name="pending-voter")
        page.get_by_role("button", name="Logout", exact=True).wait_for()
        page.get_by_role("dialog").wait_for(state="hidden")
        self.wait_for_first_vote_state(".vote-switch-option-yes", True, page=page)
        self.assertEqual(first_yes_button.get_attribute("aria-checked"), "true")

    def test_browser_cancelled_auth_dialog_discards_pending_vote_action(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="pending-vote-cancel-creator")
        self.create_poll(
            title="Pending vote cancel poll",
            description="Used for cancelled pending vote coverage.",
            identifier="pending_vote_cancel_poll",
            timezone="Europe/Helsinki",
            start_date="2026-04-24",
            end_date="2026-04-24",
        )

        page.get_by_role("button", name="Logout", exact=True).click()
        page.get_by_role("button", name="Login").wait_for()

        first_yes_button = page.locator(".vote-switch-option-yes").first
        self.assertEqual(first_yes_button.get_attribute("aria-checked"), "false")

        first_yes_button.click()
        page.get_by_role("dialog").wait_for()
        page.keyboard.press("Escape")
        page.get_by_role("dialog").wait_for(state="hidden")

        page.get_by_role("button", name="Login").click()
        self.submit_auth_dialog(name="pending-vote-cancel-user")
        page.get_by_role("button", name="Logout", exact=True).wait_for()
        page.wait_for_load_state("networkidle")

        self.assertEqual(first_yes_button.get_attribute("aria-checked"), "false")

    def test_browser_pending_create_action_resumes_after_login(self) -> None:
        page = self.require_page()

        self.open_home_page()
        page.get_by_role("button", name="Create new poll").click()
        page.locator("#poll-title").fill("Pending create poll")
        page.locator("#poll-description").fill("Used for pending create coverage.")
        page.locator("#poll-identifier").fill("pending_create_poll")
        page.locator("#poll-timezone").fill("Europe/Helsinki")
        page.locator("#start-date").fill("2026-04-24")
        page.locator("#end-date").fill("2026-04-24")
        page.locator("#section-panel-create button[type='submit']").click()
        page.get_by_role("dialog").wait_for()

        self.submit_auth_dialog(name="pending-creator")
        page.get_by_role("button", name="Logout", exact=True).wait_for()
        page.locator(".details-title").filter(has_text="Pending create poll").wait_for()
        self.assertIn("id=pending_create_poll", page.url)

    def test_browser_history_back_and_forward_restore_ui_state(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="history-owner")
        self.create_poll(
            title="History first poll",
            description="First history target.",
            identifier="history_first_poll",
            timezone="Europe/Helsinki",
            start_date="2026-04-27",
            end_date="2026-04-27",
        )

        page.locator(".title-home").click()
        page.get_by_role("heading", name="Polls").wait_for()
        self.create_poll(
            title="History second poll",
            description="Second history target.",
            identifier="history_second_poll",
            timezone="Europe/Helsinki",
            start_date="2026-04-28",
            end_date="2026-04-28",
        )

        page.locator(".title-home").click()
        page.get_by_role("heading", name="Polls").wait_for()
        page.locator(".poll-item").filter(has_text="History first poll").click()
        page.locator(".details-title").filter(has_text="History first poll").wait_for()
        self.assertIn("id=history_first_poll", page.url)

        page.locator(".title-home").click()
        page.get_by_role("heading", name="Polls").wait_for()
        self.assertNotIn("id=", page.url)

        page.locator(".poll-item").filter(has_text="History second poll").click()
        page.locator(".details-title").filter(has_text="History second poll").wait_for()
        self.assertIn("id=history_second_poll", page.url)

        page.go_back()
        page.get_by_role("heading", name="Polls").wait_for()
        page.wait_for_function("() => !window.location.search.includes('id=')")

        page.go_back()
        page.locator(".details-title").filter(has_text="History first poll").wait_for()
        page.wait_for_function(
            "() => window.location.search.includes('id=history_first_poll')"
        )

        page.go_forward()
        page.get_by_role("heading", name="Polls").wait_for()
        page.wait_for_function("() => !window.location.search.includes('id=')")

        page.go_forward()
        page.locator(".details-title").filter(has_text="History second poll").wait_for()
        page.wait_for_function(
            "() => window.location.search.includes('id=history_second_poll')"
        )

    def test_browser_resize_recalculates_visible_days_after_mount(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="resize-owner")
        self.create_poll(
            title="Resize poll",
            description="Used for resize coverage.",
            identifier="resize_poll",
            timezone="Europe/Helsinki",
            start_date="2026-04-13",
            end_date="2026-04-19",
            daily_start_hour=9,
            daily_end_hour=10,
            allowed_weekdays=[0, 1, 2, 3, 4, 5, 6],
        )

        initial_visible_days = page.locator(".calendar-day-col").count()
        self.assertGreater(initial_visible_days, 3)

        shrink_state = page.evaluate(
            """
            async () => {
              const tableWrap = document.querySelector('.details .table-wrap');
              if (tableWrap) {
                tableWrap.style.width = '320px';
              }
              window.dispatchEvent(new Event('resize'));
              await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
              return {
                wrapWidth: tableWrap ? tableWrap.clientWidth : null,
                renderedCount: document.querySelectorAll('.calendar-day-col').length,
                rangeText: document.querySelector('.calendar-nav-range')?.textContent?.trim() || ''
              };
            }
            """
        )
        shrunken_visible_days = int(shrink_state["renderedCount"])
        self.assertLess(shrunken_visible_days, initial_visible_days, shrink_state)
        self.assertTrue(bool(shrink_state["rangeText"]), shrink_state)

        expand_state = page.evaluate(
            """
            async () => {
              const tableWrap = document.querySelector('.details .table-wrap');
              if (tableWrap) {
                tableWrap.style.width = '1600px';
              }
              window.dispatchEvent(new Event('resize'));
              await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
              return {
                wrapWidth: tableWrap ? tableWrap.clientWidth : null,
                renderedCount: document.querySelectorAll('.calendar-day-col').length
              };
            }
            """
        )
        self.assertGreater(int(expand_state["renderedCount"]), shrunken_visible_days, expand_state)

    def test_browser_timezone_suggestion_dropdowns_select_and_hide(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="timezone-suggestion-owner")
        page.get_by_role("button", name="Create new poll").click()

        page.locator("#poll-timezone").fill("europe/hel")
        page.locator(".timezone-suggestions").wait_for()
        page.locator(".timezone-suggestion").filter(has_text="Europe/Helsinki").first.click()
        self.assertEqual(page.locator("#poll-timezone").input_value(), "Europe/Helsinki")
        page.locator(".timezone-suggestions").wait_for(state="hidden")

        page.locator("#poll-title").fill("Timezone suggestion poll")
        page.locator("#poll-description").fill("Used for timezone suggestion coverage.")
        page.locator("#poll-identifier").fill("timezone_suggestion_poll")
        page.locator("#start-date").fill("2026-04-29")
        page.locator("#end-date").fill("2026-04-29")
        page.locator("#section-panel-create button[type='submit']").click()
        page.locator(".details-title").filter(has_text="Timezone suggestion poll").wait_for()

        page.locator(".calendar-timezone-mode-item-custom").click()
        page.locator("#calendar-timezone").fill("pacific/hon")
        page.locator(".timezone-suggestions").wait_for()
        page.locator(".timezone-suggestion").filter(has_text="Pacific/Honolulu").first.click()
        self.assertEqual(page.locator("#calendar-timezone").input_value(), "Pacific/Honolulu")
        page.locator(".timezone-suggestions").wait_for(state="hidden")

    def test_browser_create_form_shows_client_side_validation_errors(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="validation-owner")
        page.get_by_role("button", name="Create new poll").click()

        page.locator("#poll-identifier").fill("bad-id")
        page.get_by_text("Identifier may contain only A-Z, a-z, 0-9 and underscore (_).").wait_for()
        self.assertIn("input-invalid", page.locator("#poll-identifier").get_attribute("class") or "")

        page.locator("#poll-timezone").fill("")
        weekday_inputs = page.locator("#section-panel-create .weekday-item input")
        for index in range(5):
            weekday_inputs.nth(index).set_checked(False)

        page.locator("#section-panel-create button[type='submit']").click()
        page.get_by_text("Title is required.").first.wait_for()
        page.get_by_text("Timezone is required.").first.wait_for()
        page.get_by_text("Start date is required.").first.wait_for()
        page.get_by_text("End date is required.").first.wait_for()
        page.get_by_text("Select at least one weekday.").first.wait_for()

    def test_browser_create_form_maps_backend_identifier_conflict_to_field(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="duplicate-owner")
        self.create_poll(
            title="Duplicate source poll",
            description="Original poll for duplicate identifier coverage.",
            identifier="duplicate_identifier_poll",
            timezone="Europe/Helsinki",
            start_date="2026-04-30",
            end_date="2026-04-30",
        )

        page.locator(".title-home").click()
        page.get_by_role("button", name="Create new poll").click()
        page.locator("#poll-title").fill("Duplicate target poll")
        page.locator("#poll-description").fill("Should fail with duplicate identifier.")
        page.locator("#poll-identifier").fill("duplicate_identifier_poll")
        page.locator("#poll-timezone").fill("Europe/Helsinki")
        page.locator("#start-date").fill("2026-05-01")
        page.locator("#end-date").fill("2026-05-01")
        page.locator("#section-panel-create button[type='submit']").click()

        page.get_by_role("alert").filter(has_text="This identifier is already in use.").wait_for()
        page.get_by_text("This identifier is already in use.").last.wait_for()
        self.assertIn("input-invalid", page.locator("#poll-identifier").get_attribute("class") or "")

    def test_browser_edit_form_shows_schedule_conflict_error_for_voted_slot(self) -> None:
        page = self.require_page()
        poll_identifier = "edit_conflict_poll"

        self.open_home_page()
        self.login(name="edit-conflict-owner")
        self.create_poll(
            title="Edit conflict poll",
            description="Used for edit conflict coverage.",
            identifier=poll_identifier,
            timezone="Europe/Helsinki",
            start_date="2026-05-04",
            end_date="2026-05-04",
        )

        browser = self.browser
        if browser is None:
            raise unittest.SkipTest("Playwright browser is not available for this test run.")

        voter_context = browser.new_context(base_url=self.live_server_url)
        self.addCleanup(voter_context.close)
        voter_page = voter_context.new_page()
        voter_page.set_default_timeout(15000)

        self.open_home_page(voter_page, f"/?id={poll_identifier}")
        self.login(name="edit-conflict-voter", page=voter_page)
        voter_page.locator(".vote-switch-option-yes").first.click()
        self.wait_for_first_vote_state(".vote-switch-option-yes", True, page=voter_page)

        page.reload(wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.locator(".details-title").filter(has_text="Edit conflict poll").wait_for()
        page.get_by_role("button", name="Edit poll").click()

        edit_weekdays = page.locator("#section-panel-selected .weekday-item input")
        edit_weekdays.nth(0).set_checked(False)
        edit_weekdays.nth(1).set_checked(True)
        page.get_by_role("button", name="Save changes").click()

        page.get_by_role("alert").filter(
            has_text="You cannot remove time slots that already have votes."
        ).wait_for()
        page.locator("#section-panel-selected .field-error").filter(
            has_text="You cannot remove time slots that already have votes."
        ).first.wait_for()
        page.get_by_role("button", name="Save changes").wait_for()

    def test_browser_open_poll_failure_shows_error_toast(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="open-error-owner")
        self.create_poll(
            title="Open error poll",
            description="Used for open error coverage.",
            identifier="open_error_poll",
            timezone="Europe/Helsinki",
            start_date="2026-05-05",
            end_date="2026-05-05",
        )

        page.locator(".title-home").click()
        page.get_by_role("heading", name="Polls").wait_for()
        self.mock_fetch_json(
            url_part="/api/polls/open_error_poll/",
            method="GET",
            status=500,
            body={"detail": "Temporarily unavailable."},
            page=page,
        )
        page.locator(".poll-item").filter(has_text="Open error poll").click()

        page.get_by_role("alert").filter(has_text="Temporarily unavailable.").wait_for()
        page.get_by_role("heading", name="Polls").wait_for()
        self.assertNotIn("id=open_error_poll", page.url)

    def test_browser_close_poll_failure_shows_error_toast(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="close-error-owner")
        self.create_poll(
            title="Close error poll",
            description="Used for close error coverage.",
            identifier="close_error_poll",
            timezone="Europe/Helsinki",
            start_date="2026-05-06",
            end_date="2026-05-06",
        )

        self.mock_fetch_json(
            url_part="/api/polls/close_error_poll/close/",
            method="POST",
            status=500,
            body={"detail": "Close failed from mock."},
            page=page,
        )
        page.get_by_role("button", name="Close poll").click()

        page.get_by_role("alert").filter(has_text="Close failed from mock.").wait_for()
        page.get_by_text("Poll is open").first.wait_for()
        page.get_by_role("button", name="Close poll").wait_for()

    def test_browser_logout_failure_shows_error_toast_and_keeps_session(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="logout-error-owner")
        self.mock_fetch_json(
            url_part="/api/auth/logout/",
            method="POST",
            status=500,
            body={"detail": "Logout failed from mock."},
            page=page,
        )

        page.get_by_role("button", name="Logout", exact=True).click()
        page.get_by_role("alert").filter(has_text="Logout failed from mock.").wait_for()
        page.get_by_role("button", name="Logout", exact=True).wait_for()
        page.get_by_role("button", name="Hello, logout-error-owner").wait_for()
