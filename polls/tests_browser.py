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
    from playwright.sync_api import Browser, BrowserContext, Dialog, Page, Playwright

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

    def enable_csp_violation_tracking(self, *, page: Optional["Page"] = None) -> None:
        page = page or self.require_page()
        page.add_init_script(
            """
            (() => {
              window.__timePollCspViolations = [];
              document.addEventListener("securitypolicyviolation", (event) => {
                window.__timePollCspViolations.push({
                  blockedURI: event.blockedURI,
                  disposition: event.disposition,
                  effectiveDirective: event.effectiveDirective,
                  violatedDirective: event.violatedDirective,
                });
              });
            })();
            """
        )

    def get_csp_violations(self, *, page: Optional["Page"] = None) -> list[dict[str, Any]]:
        page = page or self.require_page()
        violations = page.evaluate("window.__timePollCspViolations || []")
        return violations if isinstance(violations, list) else []

    def assert_no_csp_violations(
        self,
        *,
        page: Optional["Page"] = None,
        page_name: str,
    ) -> None:
        violations = self.get_csp_violations(page=page)
        self.assertEqual(
            [],
            violations,
            f"Unexpected CSP violations on {page_name}:\n{json.dumps(violations, indent=2)}",
        )

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

    def test_home_page_loads_without_csp_violations(self):
        page = self.require_page()
        self.enable_csp_violation_tracking(page=page)

        self.open_home_page(page)
        page.wait_for_timeout(250)

        self.assert_no_csp_violations(page=page, page_name="home page load")

    def test_csp_blocks_cross_origin_fetch_and_image_requests(self):
        page = self.require_page()
        self.enable_csp_violation_tracking(page=page)

        self.open_home_page(page)

        fetch_result = page.evaluate(
            """
            async () => {
              try {
                await fetch("https://example.com/");
                return { allowed: true };
              } catch (error) {
                return {
                  allowed: false,
                  message: error instanceof Error ? error.message : String(error),
                };
              }
            }
            """
        )
        image_result = page.evaluate(
            """
            () => new Promise((resolve) => {
              const image = document.createElement("img");
              image.onload = () => resolve({ loaded: true });
              image.onerror = () => resolve({ loaded: false });
              image.src = "https://example.com/tracker.png";
              document.body.appendChild(image);
            })
            """
        )

        page.wait_for_function("window.__timePollCspViolations.length >= 2", timeout=5000)
        violations = self.get_csp_violations(page=page)
        directives = {item.get("effectiveDirective") for item in violations}

        self.assertFalse(fetch_result["allowed"], fetch_result.get("message"))
        self.assertFalse(image_result["loaded"])
        self.assertIn("connect-src", directives)
        self.assertIn("img-src", directives)

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

    def open_profile_panel(self, *, page: Optional["Page"] = None) -> None:
        page = page or self.require_page()
        page.wait_for_load_state("networkidle")
        page.locator(".auth-name-link").click()
        page.get_by_role("heading", name="My data").wait_for()

    def open_edit_timezone_confirmation_dialog(
        self,
        *,
        timezone: str = "Pacific/Honolulu",
        page: Optional["Page"] = None,
    ) -> Any:
        page = page or self.require_page()
        timezone_input = page.locator("#edit-timezone")
        timezone_input.fill(timezone)
        timezone_input.press("Tab")
        dialog = page.get_by_role("dialog").filter(has_text="Confirm timezone change")
        try:
            dialog.wait_for(timeout=2000)
        except Exception:
            timezone_input.focus()
            timezone_input.blur()
            dialog.wait_for()
        return dialog

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
              return Boolean(element) && element.getAttribute("data-selected") === expectedState;
            }
            """,
            arg=[selector, expected],
        )

    def select_option_disabled_map(
        self,
        selector: str,
        *,
        page: Optional["Page"] = None,
    ) -> dict[str, bool]:
        page = page or self.require_page()
        options = page.locator(selector).evaluate(
            """
            (select) => Array.from(select.options).map((option) => ({
              value: option.value,
              disabled: option.disabled,
            }))
            """
        )
        disabled_map: dict[str, bool] = {}
        if not isinstance(options, list):
            return disabled_map
        for item in options:
            if not isinstance(item, dict):
                continue
            value = item.get("value")
            if value is None:
                continue
            disabled_map[str(value)] = bool(item.get("disabled"))
        return disabled_map

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

    def week_blocks_locator(
        self,
        *,
        week_index: int = 0,
        page: Optional["Page"] = None,
    ) -> Any:
        page = page or self.require_page()
        return page.locator(".calendar-week").nth(week_index).locator(".calendar-week-block")

    def week_block_locator(
        self,
        *,
        week_index: int = 0,
        block_index: int = 0,
        page: Optional["Page"] = None,
    ) -> Any:
        return self.week_blocks_locator(week_index=week_index, page=page).nth(block_index)

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

    def open_edit_form_for_utc_vote_that_shifts_in_honolulu(
        self,
        *,
        poll_identifier: str,
        title: str,
        owner_name: str,
        voter_name: str,
        daily_start_hour: int = 0,
        daily_end_hour: int = 24,
        allowed_weekdays: Optional[list[int]] = None,
        vote_option_index: int = 0,
    ) -> None:
        page = self.require_page()
        self.open_home_page()
        self.login(name=owner_name)
        self.create_poll(
            title=title,
            description="Used for timezone-aware edit regression coverage.",
            identifier=poll_identifier,
            timezone="UTC",
            start_date="2026-05-04",
            end_date="2026-05-04",
            daily_start_hour=daily_start_hour,
            daily_end_hour=daily_end_hour,
            allowed_weekdays=allowed_weekdays if allowed_weekdays is not None else [0, 1, 2, 3, 4, 5, 6],
        )

        voter_page = self.open_logged_in_poll_page(poll_identifier=poll_identifier, name=voter_name)
        voter_page.locator(".calendar-table tbody tr").first.locator(".vote-switch-option-yes").nth(vote_option_index).click()
        self.wait_for_first_vote_state(".vote-switch-option-yes", True, page=voter_page)
        page.wait_for_function(
            """
            async (pollIdentifier) => {
              try {
                const response = await fetch(`/api/polls/${pollIdentifier}/`, {
                  credentials: 'same-origin',
                  headers: { Accept: 'application/json' },
                });
                if (!response.ok) {
                  return false;
                }
                const contentType = response.headers.get('content-type') || '';
                if (!contentType.includes('application/json')) {
                  return false;
                }
                const poll = await response.json();
                const firstOption = Array.isArray(poll.options) ? poll.options[0] : null;
                const counts = firstOption && typeof firstOption.counts === 'object' ? firstOption.counts : null;
                return Boolean(
                  firstOption
                  && firstOption.starts_at === '2026-05-04T00:00:00+00:00'
                  && counts
                  && counts.yes === 1
                );
              } catch (error) {
                return false;
              }
            }
            """,
            arg=poll_identifier,
        )

        page.reload(wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.locator(".details-title").filter(has_text=title).wait_for()
        page.get_by_role("button", name="Edit poll").click()
        page.locator("#edit-timezone").wait_for()

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

    def normalized_aria_snapshot(self, locator: Any) -> str:
        snapshot = locator.aria_snapshot()
        return "\n".join(line.rstrip() for line in snapshot.strip().splitlines())

    def assert_aria_snapshot_contains(
        self,
        locator: Any,
        *expected_fragments: str,
    ) -> str:
        snapshot = self.normalized_aria_snapshot(locator)
        for fragment in expected_fragments:
            self.assertIn(fragment, snapshot, snapshot)
        return snapshot

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
        self.open_profile_panel(page=page)

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

        self.mock_fetch_json(
            url_part="/api/polls/",
            method="PUT",
            status=409,
            body={
                "error": "schedule_conflicts_with_votes",
                "detail": "Cannot remove or shrink time slots that already have votes.",
            },
            page=page,
        )
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
        self.assertTrue(voter_page.locator(".vote-switch").first.is_disabled())

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

    def test_vote_cell_menu_open_state_has_no_accessibility_violations(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="vote-cell-menu-a11y-owner")
        self.create_poll(
            title="Vote cell menu accessibility poll",
            description="Used for vote cell menu accessibility coverage.",
            identifier="vote_cell_menu_accessibility_poll",
            timezone="Europe/Helsinki",
            start_date="2026-06-15",
            end_date="2026-06-15",
        )

        first_vote_cell = page.locator(".vote-switch").first
        first_vote_cell.focus()
        page.keyboard.press("Enter")
        vote_menu = page.locator(".vote-cell-menu").first
        vote_menu.wait_for()
        page.keyboard.press("ArrowRight")
        page.wait_for_function(
            """
            () => {
              const active = document.activeElement;
              return Boolean(active)
                && active.getAttribute('role') === 'menuitemradio'
                && active.textContent.trim() === 'Yes'
                && active.getAttribute('aria-checked') === 'true';
            }
            """
        )

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="vote cell menu state")

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

    def test_calendar_timezone_combobox_exposes_named_combobox_contract(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="calendar-timezone-contract-owner")
        self.create_poll(
            title="Calendar timezone contract poll",
            description="Used for calendar timezone ARIA contract coverage.",
            identifier="calendar_timezone_contract_poll",
            timezone="UTC",
            start_date="2026-05-15",
            end_date="2026-05-15",
            daily_start_hour=23,
            daily_end_hour=24,
        )

        page.locator(".calendar-timezone-mode-item-custom").click()
        timezone_input = page.locator("#calendar-timezone")
        timezone_input.fill("pacific/hon")
        page.locator("#calendar-timezone-suggestions").wait_for()

        self.assertEqual(timezone_input.get_attribute("aria-label"), "Calendar timezone")
        self.assertEqual(timezone_input.get_attribute("role"), "combobox")
        self.assertEqual(timezone_input.get_attribute("aria-expanded"), "true")
        self.assert_aria_snapshot_contains(
            timezone_input,
            'combobox "Calendar timezone"',
        )
        self.assert_aria_snapshot_contains(
            page.locator("#calendar-timezone-suggestions"),
            'listbox "Timezone suggestions"',
            'option "Pacific/Honolulu',
        )

    def test_calendar_day_bulk_menu_exposes_menu_contract(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="calendar-bulk-contract-owner")
        self.create_poll(
            title="Calendar bulk contract poll",
            description="Used for calendar bulk menu ARIA contract coverage.",
            identifier="calendar_bulk_contract_poll",
            timezone="Europe/Helsinki",
            start_date="2026-06-11",
            end_date="2026-06-12",
            daily_start_hour=9,
            daily_end_hour=11,
        )

        first_day_trigger = page.locator(".bulk-day-trigger").first
        first_day_trigger.click()
        day_menu = page.locator(".bulk-menu").first
        day_menu.wait_for()

        self.assert_aria_snapshot_contains(
            day_menu,
            "- menu",
            'menuitem "No vote"',
            'menuitem "Yes"',
            'menuitem "Maybe"',
            'menuitem "No"',
        )

    def test_calendar_vote_switch_exposes_button_and_menu_contract(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="calendar-vote-menu-contract-owner")
        self.create_poll(
            title="Calendar vote menu contract poll",
            description="Used for vote switch ARIA contract coverage.",
            identifier="calendar_vote_menu_contract_poll",
            timezone="Europe/Helsinki",
            start_date="2026-06-15",
            end_date="2026-06-15",
        )

        first_yes_button = page.locator(".vote-switch-option-yes").first
        first_yes_button.click()
        self.wait_for_first_vote_state(".vote-switch-option-yes", True, page=page)

        vote_group = page.locator(".vote-switch").first
        group_label = vote_group.get_attribute("aria-label") or ""
        self.assertIn("Mon", group_label)
        self.assertIn("09:00", group_label)
        self.assert_aria_snapshot_contains(
            vote_group,
            'button "',
            "My vote: Yes",
            "Yes votes: 1",
            "Maybe votes: 0",
            "No votes: 0",
        )
        self.assertEqual(first_yes_button.get_attribute("data-selected"), "true")

        vote_group.focus()
        vote_group.press("Enter")
        vote_menu = page.locator(".vote-cell-menu").first
        vote_menu.wait_for()
        self.assert_aria_snapshot_contains(
            vote_menu,
            "- menu",
            'menuitemradio "No vote"',
            'menuitemradio "Yes" [checked]',
            'menuitemradio "Maybe"',
            'menuitemradio "No"',
        )

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

        week_blocks = self.week_blocks_locator(page=page)
        self.assertGreater(week_blocks.count(), 1)

        first_block = self.week_block_locator(block_index=0, page=page)
        scroll_before = float(page.evaluate("() => window.scrollY"))
        first_block.locator('[data-nav-direction="next"]').click()
        page.wait_for_function("(previousY) => window.scrollY > previousY + 5", arg=scroll_before)
        page.wait_for_function(
            """
            (blockIndex) => {
              const targetBlock = document.querySelectorAll('.calendar-week .calendar-week-block')[blockIndex];
              const active = document.activeElement;
              return Boolean(targetBlock) && Boolean(active) && targetBlock.contains(active);
            }
            """,
            arg=1,
        )

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

        self.open_profile_panel(page=page)
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

        self.open_profile_panel(page=page)
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
        self.open_profile_panel(page=page)
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
        self.open_profile_panel(page=page)
        page.get_by_role("button", name="Delete vote").click()
        page.get_by_role("status").filter(has_text="Vote deleted.").wait_for()
        page.get_by_text("No votes.").wait_for()

        page.get_by_role("button", name="Profile vote delete details accessibility poll").click()
        page.locator(".details-title").filter(
            has_text="Profile vote delete details accessibility poll"
        ).wait_for()
        self.assertEqual(page.locator(".vote-switch-option-yes").first.get_attribute("data-selected"), "false")

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

        first_block = self.week_block_locator(block_index=0, page=page)
        nav_range = first_block.locator(".calendar-nav-range")
        nav_range.wait_for()
        visible_days = first_block.locator(".calendar-day-col").count()
        self.assertGreater(visible_days, 0)
        self.assertLess(visible_days, 7)
        self.assertEqual(nav_range.inner_text().strip(), f"Days 1-{visible_days}/7")

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

        week_blocks = self.week_blocks_locator(page=page)
        first_block_day_count = self.week_block_locator(block_index=0, page=page).locator(
            ".calendar-day-col"
        ).count()
        block_count = week_blocks.count()
        self.assertGreater(block_count, 1)

        last_block = self.week_block_locator(block_index=block_count - 1, page=page)
        last_block.scroll_into_view_if_needed()
        nav_range = last_block.locator(".calendar-nav-range")
        nav_range.wait_for()
        last_visible_days = last_block.locator(".calendar-day-col").count()
        self.assertGreater(last_visible_days, 0)

        last_start = ((block_count - 1) * first_block_day_count) + 1
        self.assertEqual(nav_range.inner_text().strip(), f"Days {last_start}-7/7")

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="mobile last page calendar state")

    def test_profile_empty_state_has_no_accessibility_violations(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="profile-empty-a11y-user")
        self.open_profile_panel(page=page)
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
        self.assertEqual(self.active_element_snapshot(page)["text"], "Cancel")
        self.assertTrue(self.active_element_has_visible_focus(page))

        page.keyboard.press("Tab")
        self.assertEqual(self.active_element_snapshot(page)["id"], "auth-name")

        page.keyboard.press("Shift+Tab")
        self.assertEqual(self.active_element_snapshot(page)["text"], "Cancel")

        page.keyboard.press("Shift+Tab")
        self.assertEqual(self.active_element_snapshot(page)["text"], "Login")

        page.keyboard.press("Escape")
        page.get_by_role("dialog").wait_for(state="hidden")
        self.assertTrue(login_button.evaluate("element => document.activeElement === element"))

    def test_browser_auth_dialog_login_moves_focus_to_authenticated_control(self) -> None:
        page = self.require_page()

        self.open_home_page()
        page.get_by_role("button", name="Login").first.click()
        dialog = page.get_by_role("dialog")
        dialog.wait_for()

        page.get_by_label("Name").fill("focus-after-login-user")
        page.get_by_label("PIN code").fill("1234")
        dialog.get_by_role("button", name="Login").click()

        dialog.wait_for(state="hidden")
        auth_name_link = page.locator(".auth-name-link")
        auth_name_link.wait_for()
        self.assertTrue(auth_name_link.evaluate("element => document.activeElement === element"))

    def test_browser_create_poll_button_moves_focus_to_create_form(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="create-focus-owner")
        page.get_by_role("button", name="Create new poll").click()
        page.locator("#section-panel-create").wait_for()
        page.wait_for_function("() => document.activeElement?.id === 'poll-title'")

        self.assertEqual(self.active_element_snapshot(page)["id"], "poll-title")
        self.assertTrue(self.active_element_has_visible_focus(page))

    def test_browser_open_poll_moves_focus_to_details_heading(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="open-poll-focus-owner")
        self.create_poll(
            title="Open poll focus target",
            description="Used for selected section focus coverage.",
            identifier="open_poll_focus_target",
            timezone="Europe/Helsinki",
            start_date="2026-06-12",
            end_date="2026-06-12",
        )

        page.locator(".title-home").click()
        page.locator("#section-panel-list").wait_for()

        page.locator(".poll-item").filter(has_text="Open poll focus target").click()
        page.locator("#section-panel-selected").wait_for()
        page.wait_for_function("() => document.activeElement?.id === 'details-heading'")

        self.assertEqual(self.active_element_snapshot(page)["id"], "details-heading")
        self.assertTrue(self.active_element_has_visible_focus(page))

    def test_browser_home_link_moves_focus_to_poll_list_heading(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="list-focus-owner")
        self.create_poll(
            title="List focus target poll",
            description="Used for list section focus coverage.",
            identifier="list_focus_target_poll",
            timezone="Europe/Helsinki",
            start_date="2026-06-15",
            end_date="2026-06-15",
        )

        page.locator(".title-home").click()
        page.locator("#section-panel-list").wait_for()
        page.wait_for_function("() => document.activeElement?.id === 'poll-list-heading'")

        self.assertEqual(self.active_element_snapshot(page)["id"], "poll-list-heading")
        self.assertTrue(self.active_element_has_visible_focus(page))

    def test_browser_home_page_initial_focus_moves_to_poll_list_heading(self) -> None:
        page = self.require_page()

        self.open_home_page()
        page.wait_for_function("() => document.activeElement?.id === 'poll-list-heading'")

        self.assertEqual(self.active_element_snapshot(page)["id"], "poll-list-heading")
        self.assertTrue(self.active_element_has_visible_focus(page))

    def test_browser_poll_list_supports_arrow_key_navigation(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="poll-list-keyboard-owner")
        self.create_poll(
            title="Poll list keyboard first poll",
            description="Used for poll list keyboard coverage.",
            identifier="poll_list_keyboard_first_poll",
            timezone="Europe/Helsinki",
            start_date="2026-06-17",
            end_date="2026-06-17",
        )
        page.locator(".title-home").click()
        page.locator("#section-panel-list").wait_for()
        self.create_poll(
            title="Poll list keyboard second poll",
            description="Used for poll list keyboard coverage.",
            identifier="poll_list_keyboard_second_poll",
            timezone="Europe/Helsinki",
            start_date="2026-06-18",
            end_date="2026-06-18",
        )

        page.locator(".title-home").click()
        page.locator("#section-panel-list").wait_for()
        page.wait_for_function("() => document.activeElement?.id === 'poll-list-heading'")
        poll_buttons = page.locator("#section-panel-list .poll-item")
        first_button_id = poll_buttons.nth(0).get_attribute("id")
        second_button_id = poll_buttons.nth(1).get_attribute("id")
        self.assertIsNotNone(first_button_id)
        self.assertIsNotNone(second_button_id)

        page.keyboard.press("ArrowDown")
        self.assertEqual(
            self.active_element_snapshot(page)["id"],
            first_button_id,
        )

        page.keyboard.press("ArrowDown")
        self.assertEqual(
            self.active_element_snapshot(page)["id"],
            second_button_id,
        )

        page.keyboard.press("ArrowUp")
        self.assertEqual(
            self.active_element_snapshot(page)["id"],
            first_button_id,
        )

        page.keyboard.press("ArrowUp")
        self.assertEqual(self.active_element_snapshot(page)["id"], "poll-list-heading")

        page.keyboard.press("End")
        self.assertEqual(
            self.active_element_snapshot(page)["id"],
            second_button_id,
        )

        page.keyboard.press("Home")
        self.assertEqual(
            self.active_element_snapshot(page)["id"],
            first_button_id,
        )
        self.assertTrue(self.active_element_has_visible_focus(page))

    def test_browser_selected_back_button_returns_focus_to_poll_list_item(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="selected-back-list-owner")
        self.create_poll(
            title="Selected back list poll",
            description="Used for selected-to-list return coverage.",
            identifier="selected_back_list_poll",
            timezone="Europe/Helsinki",
            start_date="2026-06-16",
            end_date="2026-06-16",
        )

        page.locator(".title-home").click()
        page.locator("#section-panel-list").wait_for()

        poll_button = page.locator(".poll-item").filter(has_text="Selected back list poll")
        poll_button.click()
        page.locator("#section-panel-selected").wait_for()

        back_button = page.locator("#selected-back-button")
        self.assertEqual(back_button.inner_text().strip(), "Back to poll list")
        back_button.click()
        page.locator("#section-panel-list").wait_for()

        self.assertTrue(poll_button.evaluate("element => document.activeElement === element"))
        self.assertTrue(self.active_element_has_visible_focus(page))

    def test_browser_edit_poll_button_moves_focus_to_edit_form(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="edit-focus-owner")
        self.create_poll(
            title="Edit focus poll",
            description="Used for edit focus coverage.",
            identifier="edit_focus_poll",
            timezone="Europe/Helsinki",
            start_date="2026-06-12",
            end_date="2026-06-12",
        )

        page.get_by_role("button", name="Edit poll").click()
        page.locator("#edit-title").wait_for()
        page.wait_for_function("() => document.activeElement?.id === 'edit-title'")

        self.assertEqual(self.active_element_snapshot(page)["id"], "edit-title")
        self.assertTrue(self.active_element_has_visible_focus(page))

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

    def test_browser_edit_timezone_listbox_supports_keyboard_navigation(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="edit-timezone-keyboard-a11y-owner")
        self.create_poll(
            title="Edit timezone keyboard accessibility poll",
            description="Used for edit timezone keyboard coverage.",
            identifier="edit_timezone_keyboard_a11y_poll",
            timezone="UTC",
            start_date="2026-06-10",
            end_date="2026-06-10",
        )

        page.get_by_role("button", name="Edit poll").click()
        timezone_input = page.locator("#edit-timezone")
        timezone_input.fill("europe/hel")
        page.locator("#edit-timezone-suggestions").wait_for()

        page.keyboard.press("ArrowDown")
        self.assertEqual(timezone_input.get_attribute("aria-activedescendant"), "edit-timezone-suggestion-0")
        self.assertTrue(page.locator("#edit-timezone-suggestions .timezone-suggestion.is-active").is_visible())

        page.keyboard.press("Escape")
        page.locator("#edit-timezone-suggestions").wait_for(state="hidden")

        timezone_input.fill("europe/hel")
        page.locator("#edit-timezone-suggestions").wait_for()
        page.keyboard.press("ArrowDown")
        page.keyboard.press("Enter")

        page.locator("#edit-timezone-suggestions").wait_for(state="hidden")
        self.assertEqual(timezone_input.input_value(), "Europe/Helsinki")

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
                return Boolean(button) && button.getAttribute('data-selected') === 'true';
              });
            }
            """
        )

    def test_browser_vote_cell_keyboard_navigation_and_menu_selection_work(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="vote-menu-keyboard-a11y-owner")
        self.create_poll(
            title="Vote menu keyboard accessibility poll",
            description="Used for vote menu keyboard coverage.",
            identifier="vote_menu_keyboard_a11y_poll",
            timezone="Europe/Helsinki",
            start_date="2026-06-15",
            end_date="2026-06-16",
        )

        first_vote_cell = page.locator(".vote-switch").first
        first_vote_cell.focus()
        self.assertEqual(self.active_element_snapshot(page)["optionId"], first_vote_cell.get_attribute("data-vote-option-id"))
        self.assertTrue(self.active_element_has_visible_focus(page))

        page.keyboard.press("ArrowRight")
        page.wait_for_function(
            """
            () => {
              const active = document.activeElement;
              const firstCell = document.querySelector('.vote-switch');
              const nextCell = document.querySelectorAll('.vote-switch')[1];
              return Boolean(active)
                && Boolean(firstCell)
                && Boolean(nextCell)
                && active === nextCell
                && active !== firstCell;
            }
            """
        )
        self.assertEqual(self.active_element_snapshot(page)["status"], "")
        self.assertTrue(self.active_element_has_visible_focus(page))

        page.keyboard.press("Enter")
        menu = page.locator(".vote-cell-menu").first
        menu.wait_for()
        self.assertEqual(self.active_element_snapshot(page)["text"], "No vote")

        page.keyboard.press("ArrowRight")
        page.wait_for_function(
            """
            () => {
              const button = document.activeElement;
              const trigger = document.querySelectorAll('.vote-switch')[1];
              const yesSegment = trigger
                ? trigger.querySelector('.vote-switch-option-yes')
                : null;
              return Boolean(button)
                && Boolean(trigger)
                && Boolean(yesSegment)
                && button.getAttribute('role') === 'menuitemradio'
                && button.textContent.trim() === 'Yes'
                && button.getAttribute('aria-checked') === 'true'
                && trigger.getAttribute('data-vote-status') === 'yes'
                && yesSegment.getAttribute('data-selected') === 'true';
            }
            """
        )
        self.assertEqual(self.active_element_snapshot(page)["text"], "Yes")

        page.keyboard.press("Enter")
        page.wait_for_function(
            """
            () => {
              const active = document.activeElement;
              const optionId = active?.getAttribute?.('data-vote-option-id') || '';
              const yesSegment = optionId
                ? document.querySelector(`.vote-switch-option-yes[data-vote-option-id="${optionId}"]`)
                : null;
              return Boolean(active)
                && Boolean(yesSegment)
                && active.classList.contains('vote-switch')
                && active.getAttribute('data-vote-status') === 'yes'
                && yesSegment.getAttribute('data-selected') === 'true'
                && document.querySelectorAll('.vote-cell-menu').length === 0;
            }
            """
        )
        self.assertEqual(self.active_element_snapshot(page)["status"], "yes")
        page.wait_for_function(
            """
            () => {
              const statusRegion = document.querySelector('p.sr-only[role="status"][aria-live="polite"]');
              return Boolean(statusRegion) && statusRegion.textContent.trim() === 'Vote saved: Yes.';
            }
            """
        )

        page.keyboard.press("Home")
        page.wait_for_function(
            """
            () => {
              const active = document.activeElement;
              const firstButton = document.querySelector('.vote-switch');
              return Boolean(active)
                && Boolean(firstButton)
                && active === firstButton;
            }
            """
        )

        page.keyboard.press(" ")
        page.locator(".vote-cell-menu").first.wait_for()
        page.keyboard.press("ArrowRight")
        page.wait_for_function(
            """
            () => {
              const button = document.activeElement;
              const firstButton = document.querySelector('.vote-switch');
              const yesSegment = firstButton
                ? firstButton.querySelector('.vote-switch-option-yes')
                : null;
              return Boolean(button)
                && Boolean(firstButton)
                && Boolean(yesSegment)
                && button.getAttribute('role') === 'menuitemradio'
                && button.textContent.trim() === 'Yes'
                && firstButton.getAttribute('data-vote-status') === 'yes'
                && yesSegment.getAttribute('data-selected') === 'true';
            }
            """
        )
        page.keyboard.press("Escape")
        page.wait_for_function(
            """
            () => {
              const active = document.activeElement;
              const firstButton = document.querySelector('.vote-switch');
              const yesSegment = firstButton
                ? firstButton.querySelector('.vote-switch-option-yes')
                : null;
              return Boolean(active)
                && Boolean(firstButton)
                && Boolean(yesSegment)
                && active === firstButton
                && firstButton.getAttribute('data-vote-status') === ''
                && yesSegment.getAttribute('data-selected') === 'false'
                && document.querySelectorAll('.vote-cell-menu').length === 0;
            }
            """
        )
        self.assertTrue(self.active_element_has_visible_focus(page))

    def test_browser_vote_cell_hover_only_highlights_hovered_segment(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="vote-hover-owner")
        self.create_poll(
            title="Vote hover poll",
            description="Used to verify hovered vote segments highlight independently.",
            identifier="vote_hover_poll",
            timezone="Europe/Helsinki",
            start_date="2026-06-15",
            end_date="2026-06-15",
        )

        page.locator(".vote-switch-option-yes").first.hover()
        styles = page.evaluate(
            """
            () => {
              const readBackground = (selector) => {
                const element = document.querySelector(selector);
                return element ? window.getComputedStyle(element).backgroundColor : '';
              };
              return {
                yes: readBackground('.vote-switch-option-yes'),
                maybe: readBackground('.vote-switch-option-maybe'),
                no: readBackground('.vote-switch-option-no'),
              };
            }
            """
        )

        self.assertNotEqual(styles["yes"], styles["maybe"])
        self.assertEqual(styles["maybe"], styles["no"])

    def test_browser_vote_cell_keyboard_synthetic_click_does_not_close_menu(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="vote-keyboard-click-owner")
        self.create_poll(
            title="Vote keyboard click poll",
            description="Used to verify synthetic keyboard clicks do not close vote menus.",
            identifier="vote_keyboard_click_poll",
            timezone="Europe/Helsinki",
            start_date="2026-06-15",
            end_date="2026-06-15",
        )

        first_vote_cell = page.locator(".vote-switch").first
        first_vote_cell.focus()

        page.evaluate(
            """
            () => {
              const trigger = document.querySelector('.vote-switch');
              if (!trigger) {
                return;
              }
              trigger.dispatchEvent(new KeyboardEvent('keydown', {
                key: 'Enter',
                bubbles: true,
                cancelable: true,
              }));
              trigger.dispatchEvent(new MouseEvent('click', {
                detail: 0,
                bubbles: true,
                cancelable: true,
              }));
            }
            """
        )

        menu = page.locator(".vote-cell-menu").first
        menu.wait_for()
        self.assertEqual(self.active_element_snapshot(page)["text"], "No vote")

    def test_browser_vote_cell_keyboard_menu_is_visibly_rendered(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="vote-keyboard-visible-menu-owner")
        self.create_poll(
            title="Vote keyboard visible menu poll",
            description="Used to verify the keyboard-opened vote menu is visibly rendered.",
            identifier="vote_keyboard_visible_menu_poll",
            timezone="Europe/Helsinki",
            start_date="2026-06-15",
            end_date="2026-06-15",
        )

        first_vote_cell = page.locator(".vote-switch").first
        first_vote_cell.focus()
        page.keyboard.press("Enter")

        page.wait_for_function(
            """
            () => {
              const cell = document.querySelector('.vote-cell.menu-open');
              const menu = cell ? cell.querySelector('.vote-cell-menu') : null;
              const firstItem = menu ? menu.querySelector('.bulk-menu-item') : null;
              if (!cell || !menu || !firstItem) {
                return false;
              }
              const cellRect = cell.getBoundingClientRect();
              const itemRect = firstItem.getBoundingClientRect();
              const probeX = itemRect.left + Math.min(12, Math.max(1, itemRect.width - 1));
              const probeY = itemRect.top + Math.min(12, Math.max(1, itemRect.height - 1));
              if (probeX >= window.innerWidth || probeY >= window.innerHeight) {
                return false;
              }
              const hit = document.elementFromPoint(probeX, probeY);
              return itemRect.top > cellRect.bottom
                && Boolean(hit)
                && (hit === firstItem || firstItem.contains(hit));
            }
            """
        )

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

        week_blocks = self.week_blocks_locator(page=page)
        self.assertGreater(week_blocks.count(), 1)

        first_block = self.week_block_locator(block_index=0, page=page)
        nav_range = first_block.locator(".calendar-nav-range")
        nav_range.wait_for()
        visible_days = first_block.locator(".calendar-day-col").count()
        self.assertGreater(visible_days, 0)
        self.assertLess(visible_days, 7)

        next_button = first_block.locator('[data-nav-direction="next"]')
        self.assertEqual(next_button.get_attribute("aria-label"), f"Next days, Days 1-{visible_days}/7")
        next_button.focus()
        self.assertTrue(next_button.evaluate("element => document.activeElement === element"))

        scroll_before = float(page.evaluate("() => window.scrollY"))
        page.keyboard.press("Enter")
        page.wait_for_function("(previousY) => window.scrollY > previousY + 5", arg=scroll_before)

        second_block = self.week_block_locator(block_index=1, page=page)
        second_block.locator(".calendar-nav-range").wait_for()
        second_visible_days = second_block.locator(".calendar-day-col").count()
        self.assertEqual(
            second_block.locator(".calendar-nav-range").inner_text().strip(),
            f"Days {visible_days + 1}-{visible_days + second_visible_days}/7",
        )

        previous_button = second_block.locator('[data-nav-direction="prev"]')
        self.assertEqual(
            previous_button.get_attribute("aria-label"),
            f"Previous days, Days {visible_days + 1}-{visible_days + second_visible_days}/7",
        )
        previous_button.focus()
        self.assertTrue(previous_button.evaluate("element => document.activeElement === element"))

        page.keyboard.press("Space")
        page.wait_for_function(
            """
            (blockIndex) => {
              const targetBlock = document.querySelectorAll('.calendar-week .calendar-week-block')[blockIndex];
              const active = document.activeElement;
              return Boolean(targetBlock) && Boolean(active) && targetBlock.contains(active);
            }
            """,
            arg=0,
        )
        self.assertEqual(nav_range.inner_text().strip(), f"Days 1-{visible_days}/7")

    def test_browser_calendar_block_navigation_crosses_week_boundaries(self) -> None:
        page = self.require_page()
        page.set_viewport_size({"width": 480, "height": 900})

        self.open_home_page()
        self.login(name="cross-week-pagination-owner")
        self.create_poll(
            title="Cross-week pagination poll",
            description="Used for cross-week calendar block navigation coverage.",
            identifier="cross_week_pagination_poll",
            timezone="Europe/Helsinki",
            start_date="2026-04-13",
            end_date="2026-04-21",
            daily_start_hour=9,
            daily_end_hour=10,
            allowed_weekdays=[0, 1, 2, 3, 4, 5, 6],
        )

        first_week_blocks = self.week_blocks_locator(week_index=0, page=page)
        last_block_index = first_week_blocks.count() - 1
        self.assertGreaterEqual(last_block_index, 1)

        last_block_first_week = self.week_block_locator(
            week_index=0,
            block_index=last_block_index,
            page=page,
        )
        last_block_first_week.scroll_into_view_if_needed()
        nav_range = last_block_first_week.locator(".calendar-nav-range")
        nav_range.wait_for()
        last_block_range = nav_range.inner_text().strip()
        self.assertTrue(last_block_range.startswith("Days "), last_block_range)
        self.assertTrue(last_block_range.endswith("/7"), last_block_range)

        next_button = last_block_first_week.locator('[data-nav-direction="next"]')
        self.assertTrue(next_button.is_enabled())
        next_button.click()

        first_block_second_week = self.week_block_locator(week_index=1, block_index=0, page=page)
        page.wait_for_function(
            """
            () => {
              const weeks = document.querySelectorAll('.calendar-week');
              const targetBlock = weeks[1]?.querySelector('.calendar-week-block');
              const active = document.activeElement;
              return Boolean(targetBlock) && Boolean(active) && targetBlock.contains(active);
            }
            """
        )
        second_week_range = first_block_second_week.locator(".calendar-nav-range")
        second_week_range.wait_for()
        self.assertEqual(second_week_range.inner_text().strip(), "Days 1-2/2")

        previous_button = first_block_second_week.locator('[data-nav-direction="prev"]')
        self.assertTrue(previous_button.is_enabled())
        previous_button.click()

        page.wait_for_function(
            """
            () => {
              const weeks = document.querySelectorAll('.calendar-week');
              const blocks = weeks[0]?.querySelectorAll('.calendar-week-block');
              const targetBlock = blocks ? blocks[blocks.length - 1] : null;
              const active = document.activeElement;
              return Boolean(targetBlock) && Boolean(active) && targetBlock.contains(active);
            }
            """
        )
        self.assertEqual(nav_range.inner_text().strip(), last_block_range)

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

        self.open_profile_panel(page=page)

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

    def test_browser_profile_button_moves_focus_to_profile_heading(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="profile-focus-owner")
        page.locator(".auth-name-link").click()
        page.locator("#section-panel-profile").wait_for()
        page.wait_for_function("() => document.activeElement?.id === 'profile-heading'")

        self.assertEqual(self.active_element_snapshot(page)["id"], "profile-heading")
        self.assertTrue(self.active_element_has_visible_focus(page))

    def test_browser_profile_back_button_returns_to_selected_poll(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="profile-back-selected-owner")
        self.create_poll(
            title="Profile back selected poll",
            description="Used for profile return to selected poll coverage.",
            identifier="profile_back_selected_poll",
            timezone="Europe/Helsinki",
            start_date="2026-06-18",
            end_date="2026-06-18",
        )

        page.locator(".auth-name-link").click()
        page.locator("#section-panel-profile").wait_for()

        back_button = page.locator("#profile-back-button")
        self.assertEqual(back_button.inner_text().strip(), "Back to poll")
        back_button.click()

        page.locator("#section-panel-selected").wait_for()
        page.wait_for_function("() => document.activeElement?.id === 'details-heading'")
        self.assertEqual(self.active_element_snapshot(page)["id"], "details-heading")
        self.assertTrue(self.active_element_has_visible_focus(page))

    def test_browser_profile_back_button_returns_to_create_form_and_preserves_draft(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="profile-back-create-owner")
        page.locator("#open-create-poll").click()
        page.locator("#section-panel-create").wait_for()
        page.locator("#poll-title").fill("Profile return draft")

        page.locator(".auth-name-link").click()
        page.locator("#section-panel-profile").wait_for()

        back_button = page.locator("#profile-back-button")
        self.assertEqual(back_button.inner_text().strip(), "Back to create poll")
        back_button.click()

        page.locator("#section-panel-create").wait_for()
        page.wait_for_function("() => document.activeElement?.id === 'poll-title'")
        self.assertEqual(page.locator("#poll-title").input_value(), "Profile return draft")
        self.assertEqual(self.active_element_snapshot(page)["id"], "poll-title")
        self.assertTrue(self.active_element_has_visible_focus(page))

    def test_browser_selected_back_button_returns_focus_to_profile_open_control(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="selected-back-profile-owner")
        self.create_poll(
            title="Selected back profile poll",
            description="Used for selected-to-profile return coverage.",
            identifier="selected_back_profile_poll",
            timezone="Europe/Helsinki",
            start_date="2026-06-17",
            end_date="2026-06-17",
        )

        page.locator(".auth-name-link").click()
        page.locator("#section-panel-profile").wait_for()

        profile_open_button = page.locator("#section-panel-profile .profile-open-poll-btn").filter(
            has_text="Selected back profile poll"
        )
        profile_open_button.click()
        page.locator("#section-panel-selected").wait_for()

        back_button = page.locator("#selected-back-button")
        self.assertEqual(back_button.inner_text().strip(), "Back to my data")
        back_button.click()
        page.locator("#section-panel-profile").wait_for()

        self.assertTrue(profile_open_button.evaluate("element => document.activeElement === element"))
        self.assertTrue(self.active_element_has_visible_focus(page))

    def test_browser_create_cancel_accepts_discard_and_returns_focus_to_create_button(self) -> None:
        page = self.require_page()
        dialog_messages: list[str] = []

        self.open_home_page()
        self.login(name="create-cancel-accept-owner")

        create_button = page.locator("#open-create-poll")
        create_button.click()
        page.locator("#section-panel-create").wait_for()
        page.locator("#poll-title").fill("Draft to discard")

        def handle_accept_dialog(dialog: "Dialog") -> None:
            dialog_messages.append(dialog.message)
            dialog.accept()

        page.on("dialog", handle_accept_dialog)
        page.locator("#create-cancel").click()

        page.locator("#section-panel-list").wait_for()
        self.assertEqual(dialog_messages, ["Discard this draft and return to the poll list?"])
        self.assertTrue(create_button.evaluate("element => document.activeElement === element"))
        self.assertTrue(self.active_element_has_visible_focus(page))

    def test_browser_create_cancel_dismiss_keeps_dirty_draft_open(self) -> None:
        page = self.require_page()
        dialog_messages: list[str] = []

        self.open_home_page()
        self.login(name="create-cancel-dismiss-owner")
        page.locator("#open-create-poll").click()
        page.locator("#section-panel-create").wait_for()
        page.locator("#poll-title").fill("Draft to keep")

        def handle_dismiss_dialog(dialog: "Dialog") -> None:
            dialog_messages.append(dialog.message)
            dialog.dismiss()

        page.on("dialog", handle_dismiss_dialog)
        page.locator("#create-cancel").click()

        page.locator("#section-panel-create").wait_for()
        self.assertEqual(dialog_messages, ["Discard this draft and return to the poll list?"])
        self.assertEqual(page.locator("#poll-title").input_value(), "Draft to keep")

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

    def test_success_toast_auto_closes_after_login(self) -> None:
        self.open_home_page()
        self.login(name="toast-user")
        page = self.require_page()

        success_toast = page.locator(".feedback.success")
        success_toast.wait_for()
        success_toast.wait_for(state="hidden", timeout=5000)
        self.assertEqual(page.locator(".feedback.success").count(), 0)

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

        self.assertFalse(voter_page.locator(".vote-switch").first.is_disabled())

        creator_page.get_by_role("button", name="Close poll").click()
        creator_page.get_by_text("Poll is closed").first.wait_for()

        voter_page.reload(wait_until="domcontentloaded")
        voter_page.wait_for_load_state("networkidle")
        voter_page.get_by_text("Poll is closed").first.wait_for()
        self.assertTrue(voter_page.locator(".vote-switch").first.is_disabled())

        creator_page.get_by_role("button", name="Reopen poll").click()
        creator_page.get_by_text("Poll is open").first.wait_for()

        voter_page.reload(wait_until="domcontentloaded")
        voter_page.wait_for_load_state("networkidle")
        voter_page.get_by_text("Poll is open").first.wait_for()
        self.assertFalse(voter_page.locator(".vote-switch").first.is_disabled())

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

        self.open_profile_panel(page=page)
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
        self.assertEqual(first_yes_button.get_attribute("data-selected"), "true")

        first_maybe_button.click()
        self.wait_for_first_vote_state(".vote-switch-option-maybe", True, page=page)
        self.assertEqual(first_maybe_button.get_attribute("data-selected"), "true")
        self.assertEqual(first_yes_button.get_attribute("data-selected"), "false")

        first_maybe_button.click()
        self.wait_for_first_vote_state(".vote-switch-option-maybe", False, page=page)
        self.wait_for_first_vote_state(".vote-switch-option-yes", False, page=page)
        self.assertEqual(first_maybe_button.get_attribute("data-selected"), "false")
        self.assertEqual(first_yes_button.get_attribute("data-selected"), "false")

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
        self.assertEqual(first_maybe_button.get_attribute("data-selected"), "false")
        self.assertEqual(first_yes_button.get_attribute("data-selected"), "false")

    def test_browser_rapid_vote_clicks_coalesce_pending_changes_and_queue_follow_up_sync(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="rapid-vote-owner")
        self.create_poll(
            title="Rapid vote serialization poll",
            description="Used for rapid vote request serialization coverage.",
            identifier="rapid_vote_serialization_poll",
            timezone="Europe/Helsinki",
            start_date="2026-04-07",
            end_date="2026-04-07",
            daily_start_hour=9,
            daily_end_hour=11,
        )

        page.wait_for_function(
            """
            () => document.querySelectorAll('.vote-switch-option-yes').length >= 2
            """
        )
        page.evaluate(
            """
            () => {
              if (window.__timepollVoteRequestStats) {
                return;
              }
              const originalFetch = window.fetch.bind(window);
              const voteUrlPattern = /\\/api\\/polls\\/[^/]+\\/votes\\/$/;
              window.__timepollVoteRequestStats = {
                active: 0,
                maxActive: 0,
                requestCount: 0,
                requests: [],
                responses: []
              };
              window.fetch = async (input, init = {}) => {
                const requestUrl = typeof input === 'string' ? input : input.url;
                const requestMethod = String(
                  (init && init.method)
                  || (typeof input === 'object' && input && input.method)
                  || 'GET'
                ).toUpperCase();
                if (requestMethod === 'PUT' && voteUrlPattern.test(requestUrl)) {
                  const stats = window.__timepollVoteRequestStats;
                  const headers = new Headers(init.headers || {});
                  const requestIndex = stats.requestCount + 1;
                  stats.requestCount = requestIndex;
                  stats.active += 1;
                  stats.maxActive = Math.max(stats.maxActive, stats.active);
                  stats.requests.push({
                    index: requestIndex,
                    csrfToken: headers.get('X-CSRFToken') || '',
                    bodyText: typeof init.body === 'string' ? init.body : ''
                  });
                  try {
                    if (requestIndex === 1) {
                      await new Promise((resolve) => window.setTimeout(resolve, 250));
                    }
                    const response = await originalFetch(input, init);
                    stats.responses.push({
                      index: requestIndex,
                      status: response.status
                    });
                    return response;
                  } finally {
                    stats.active -= 1;
                  }
                }
                return originalFetch(input, init);
              };
            }
            """
        )

        yes_buttons = page.locator(".vote-switch-option-yes")
        first_yes_button = yes_buttons.nth(0)
        second_yes_button = yes_buttons.nth(1)
        first_maybe_button = page.locator(".vote-switch-option-maybe").nth(0)
        first_option_id = first_yes_button.get_attribute("data-vote-option-id")
        second_option_id = second_yes_button.get_attribute("data-vote-option-id")
        if first_option_id is None or second_option_id is None:
            raise AssertionError("Vote buttons should expose option ids for request inspection.")

        first_yes_button.click()
        second_yes_button.click()

        page.wait_for_function(
            """
            () => {
              const selectedYesCount = document.querySelectorAll(
                '.vote-switch-option-yes[data-selected="true"]'
              ).length;
              return selectedYesCount >= 2;
            }
            """
        )
        page.wait_for_function(
            """
            () => {
              const stats = window.__timepollVoteRequestStats;
              return Boolean(stats) && stats.requestCount === 1 && stats.active === 1;
            }
            """
        )

        self.assertFalse(page.locator(".vote-switch").first.is_disabled())
        first_maybe_button.click()
        self.wait_for_first_vote_state(".vote-switch-option-maybe", True, page=page)
        self.assertEqual(first_maybe_button.get_attribute("data-selected"), "true")

        page.wait_for_function(
            """
            () => {
              const stats = window.__timepollVoteRequestStats;
              return Boolean(stats)
                && Array.isArray(stats.responses)
                && stats.responses.length >= 2
                && stats.requestCount === 2
                && stats.active === 0;
            }
            """
        )

        stats = page.evaluate("() => window.__timepollVoteRequestStats")
        self.assertEqual(stats["requestCount"], 2, stats)
        self.assertEqual(stats["maxActive"], 1, stats)
        self.assertEqual([item["status"] for item in stats["responses"]], [200, 200], stats)
        self.assertTrue(all(item["csrfToken"] for item in stats["requests"]), stats)
        first_request = json.loads(stats["requests"][0]["bodyText"])
        second_request = json.loads(stats["requests"][1]["bodyText"])
        first_request_votes = sorted((item["option_id"], item["status"]) for item in first_request["votes"])
        second_request_votes = sorted((item["option_id"], item["status"]) for item in second_request["votes"])
        expected_first_only = [(int(first_option_id), "yes")]
        expected_batched_first = sorted(
            [
                (int(first_option_id), "yes"),
                (int(second_option_id), "yes"),
            ]
        )
        expected_follow_up_only = [(int(first_option_id), "maybe")]
        expected_follow_up_with_second = sorted(
            [
                (int(first_option_id), "maybe"),
                (int(second_option_id), "yes"),
            ]
        )
        self.assertIn(first_request_votes, [expected_first_only, expected_batched_first], stats)
        self.assertIn(second_request_votes, [expected_follow_up_only, expected_follow_up_with_second], stats)
        self.assertEqual(first_maybe_button.get_attribute("data-selected"), "true")
        self.assertEqual(second_yes_button.get_attribute("data-selected"), "true")
        self.assertEqual(page.locator(".feedback.error").count(), 0)

    def test_browser_vote_request_recovers_from_csrf_retry(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="csrf-retry-owner")
        self.create_poll(
            title="CSRF retry vote poll",
            description="Used to verify automatic CSRF recovery for vote writes.",
            identifier="csrf_retry_vote_poll",
            timezone="Europe/Helsinki",
            start_date="2026-04-13",
            end_date="2026-04-13",
        )

        page.evaluate(
            """
            () => {
              if (window.__timepollCsrfRetryStats) {
                return;
              }
              const originalFetch = window.fetch.bind(window);
              const voteUrlPattern = /\\/api\\/polls\\/[^/]+\\/votes\\/$/;
              const sessionUrlPattern = /\\/api\\/auth\\/session\\/$/;
              window.__timepollCsrfRetryStats = {
                sessionRefreshCount: 0,
                voteStatuses: [],
                voteAttemptCount: 0
              };
              window.fetch = async (input, init = {}) => {
                const requestUrl = typeof input === 'string' ? input : input.url;
                const requestMethod = String(
                  (init && init.method)
                  || (typeof input === 'object' && input && input.method)
                  || 'GET'
                ).toUpperCase();
                if (requestMethod === 'GET' && sessionUrlPattern.test(requestUrl)) {
                  window.__timepollCsrfRetryStats.sessionRefreshCount += 1;
                  return originalFetch(input, init);
                }
                if (requestMethod === 'PUT' && voteUrlPattern.test(requestUrl)) {
                  const stats = window.__timepollCsrfRetryStats;
                  stats.voteAttemptCount += 1;
                  const nextInit = { ...init, headers: new Headers(init.headers || {}) };
                  if (stats.voteAttemptCount === 1) {
                    nextInit.headers.set('X-CSRFToken', 'x'.repeat(32));
                  }
                  const response = await originalFetch(input, nextInit);
                  stats.voteStatuses.push(response.status);
                  return response;
                }
                return originalFetch(input, init);
              };
            }
            """
        )

        first_yes_button = page.locator(".vote-switch-option-yes").first
        first_yes_button.click()
        self.wait_for_first_vote_state(".vote-switch-option-yes", True, page=page)
        page.wait_for_function(
            """
            () => {
              const stats = window.__timepollCsrfRetryStats;
              return Boolean(stats)
                && Array.isArray(stats.voteStatuses)
                && stats.voteStatuses.length >= 2
                && stats.voteStatuses[0] === 403
                && stats.voteStatuses[1] === 200
                && stats.sessionRefreshCount >= 1;
            }
            """
        )

        stats = page.evaluate("() => window.__timepollCsrfRetryStats")
        self.assertEqual(stats["voteStatuses"][:2], [403, 200], stats)
        self.assertGreaterEqual(stats["sessionRefreshCount"], 1, stats)
        self.assertEqual(first_yes_button.get_attribute("data-selected"), "true")
        self.assertEqual(page.locator(".feedback.error").count(), 0)

    def test_browser_vote_sync_updates_local_poll_summary_and_defers_poll_list_refresh_until_home(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="poll-list-refresh-owner")
        self.create_poll(
            title="Poll list refresh vote poll",
            description="Used to verify vote sync avoids eager poll list refetches.",
            identifier="poll_list_refresh_vote_poll",
            timezone="Europe/Helsinki",
            start_date="2026-04-13",
            end_date="2026-04-13",
        )

        page.evaluate(
            """
            () => {
              const originalFetch = window.fetch.bind(window);
              const voteUrlPattern = /\\/api\\/polls\\/[^/]+\\/votes\\/$/;
              const pollsListUrlPattern = /\\/api\\/polls\\/$/;
              window.__timepollPollListRefreshStats = {
                listFetchCount: 0,
                votePutCount: 0
              };
              window.fetch = async (input, init = {}) => {
                const requestUrl = typeof input === 'string' ? input : input.url;
                const requestMethod = String(
                  (init && init.method)
                  || (typeof input === 'object' && input && input.method)
                  || 'GET'
                ).toUpperCase();
                if (requestMethod === 'PUT' && voteUrlPattern.test(requestUrl)) {
                  window.__timepollPollListRefreshStats.votePutCount += 1;
                }
                if (requestMethod === 'GET' && pollsListUrlPattern.test(requestUrl)) {
                  window.__timepollPollListRefreshStats.listFetchCount += 1;
                }
                return originalFetch(input, init);
              };
            }
            """
        )

        first_yes_button = page.locator(".vote-switch-option-yes").first
        first_yes_button.click()
        self.wait_for_first_vote_state(".vote-switch-option-yes", True, page=page)
        page.wait_for_function(
            """
            () => {
              const stats = window.__timepollPollListRefreshStats;
              return Boolean(stats) && stats.votePutCount >= 1;
            }
            """
        )
        page.wait_for_timeout(300)

        stats_before_home = page.evaluate("() => window.__timepollPollListRefreshStats")
        self.assertEqual(stats_before_home["listFetchCount"], 0, stats_before_home)

        page.locator(".title-home").click()
        page.get_by_role("heading", name="Polls").wait_for()
        page.wait_for_function(
            """
            () => {
              const stats = window.__timepollPollListRefreshStats;
              return Boolean(stats) && stats.listFetchCount >= 1;
            }
            """
        )

        stats_after_home = page.evaluate("() => window.__timepollPollListRefreshStats")
        self.assertGreaterEqual(stats_after_home["listFetchCount"], 1, stats_after_home)

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
                return Boolean(button) && button.getAttribute('data-selected') === 'true';
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
                return Boolean(maybeButton) && maybeButton.getAttribute('data-selected') === 'true';
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
              return Boolean(yesButton) && yesButton.getAttribute('data-selected') === 'true';
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

        self.open_profile_panel(page=page)
        page.get_by_text("My vote: Yes").wait_for()
        page.get_by_role("button", name="Delete vote").click()
        page.get_by_role("status").filter(has_text="Vote deleted.").wait_for()
        page.get_by_text("No votes.").wait_for()

        page.get_by_role("button", name="Profile vote delete poll").click()
        page.locator(".details-title").filter(has_text="Profile vote delete poll").wait_for()
        self.assertEqual(page.locator(".vote-switch-option-yes").first.get_attribute("data-selected"), "false")

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

        week_blocks = self.week_blocks_locator(page=page)
        self.assertGreater(week_blocks.count(), 1)

        first_block = self.week_block_locator(block_index=0, page=page)
        nav_range = first_block.locator(".calendar-nav-range")
        nav_range.wait_for()
        visible_days = first_block.locator(".calendar-day-col").count()
        self.assertGreater(visible_days, 0)
        self.assertLess(visible_days, 7)
        self.assertEqual(nav_range.inner_text().strip(), f"Days 1-{visible_days}/7")
        fit_state = page.evaluate(
            """
            () => {
              const rootPx = Number.parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
              const firstBlock = document.querySelector('.calendar-week .calendar-week-block');
              const wrap = firstBlock ? firstBlock.querySelector('.table-wrap') : null;
              const table = firstBlock ? firstBlock.querySelector('.calendar-table') : null;
              const dayHeaders = Array.from(firstBlock?.querySelectorAll('.calendar-day-col') || []);
              const overflowing = Array.from(document.querySelectorAll('body *'))
                .map((element) => {
                  const rect = element.getBoundingClientRect();
                  return {
                    tag: element.tagName.toLowerCase(),
                    className: typeof element.className === 'string' ? element.className : '',
                    right: rect.right,
                    width: rect.width
                  };
                })
                .filter((item) => item.right > document.documentElement.clientWidth + 1)
                .slice(0, 8);
              return {
                documentClientWidthPx: document.documentElement.clientWidth,
                documentScrollWidthPx: document.documentElement.scrollWidth,
                wrapWidthPx: wrap ? wrap.getBoundingClientRect().width : 0,
                wrapScrollWidthPx: wrap ? wrap.scrollWidth : 0,
                tableWidthPx: table ? table.getBoundingClientRect().width : 0,
                widthsInRem: dayHeaders.map((header) => header.getBoundingClientRect().width / rootPx),
                overflowing
              };
            }
            """
        )
        self.assertTrue(fit_state["widthsInRem"], fit_state)
        for width_in_rem in fit_state["widthsInRem"]:
            self.assertGreaterEqual(float(width_in_rem), 7.9, fit_state)
        self.assertLessEqual(
            float(fit_state["documentScrollWidthPx"]),
            float(fit_state["documentClientWidthPx"]) + 2.0,
            fit_state,
        )
        self.assertLessEqual(
            float(fit_state["wrapScrollWidthPx"]),
            float(fit_state["wrapWidthPx"]) + 2.0,
            fit_state,
        )
        self.assertLessEqual(float(fit_state["tableWidthPx"]), float(fit_state["wrapWidthPx"]) + 2.0, fit_state)

        first_time_row = first_block.locator(".calendar-time-row").first
        first_time_row.locator(".bulk-time-trigger").click()
        first_time_row.locator(".bulk-menu-item").filter(has_text="Yes").click()
        page.wait_for_function(
            """
            (expectedCount) => {
              const block = document.querySelector('.calendar-week .calendar-week-block');
              const row = block ? block.querySelector('.calendar-table tbody tr') : null;
              if (!row) {
                return false;
              }
              const yesButtons = Array.from(row.querySelectorAll('.vote-switch-option-yes'));
              return yesButtons.length === expectedCount && yesButtons.every((button) => button.getAttribute('data-selected') === 'true');
            }
            """,
            arg=visible_days,
        )

        second_block = self.week_block_locator(block_index=1, page=page)
        second_visible_days = second_block.locator(".calendar-day-col").count()
        scroll_before = float(page.evaluate("() => window.scrollY"))
        first_block.locator('[data-nav-direction="next"]').click()
        page.wait_for_function("(previousY) => window.scrollY > previousY + 5", arg=scroll_before)
        page.wait_for_function(
            """
            ([startDay, endDay]) => {
              const block = document.querySelectorAll('.calendar-week .calendar-week-block')[1];
              const range = block ? block.querySelector('.calendar-nav-range') : null;
              return Boolean(range) && range.textContent.trim() === `Days ${startDay}-${endDay}/7`;
            }
            """,
            arg=[visible_days + 1, visible_days + second_visible_days],
        )
        page.wait_for_function(
            """
            (expectedCount) => {
              const block = document.querySelectorAll('.calendar-week .calendar-week-block')[1];
              const row = block ? block.querySelector('.calendar-table tbody tr') : null;
              if (!row) {
                return false;
              }
              const yesButtons = Array.from(row.querySelectorAll('.vote-switch-option-yes'));
              return yesButtons.length === expectedCount && yesButtons.every((button) => button.getAttribute('data-selected') === 'false');
            }
            """,
            arg=second_visible_days,
        )

        second_block.locator('[data-nav-direction="prev"]').click()
        page.wait_for_function(
            """
            (blockIndex) => {
              const targetBlock = document.querySelectorAll('.calendar-week .calendar-week-block')[blockIndex];
              const active = document.activeElement;
              return Boolean(targetBlock) && Boolean(active) && targetBlock.contains(active);
            }
            """,
            arg=0,
        )
        self.assertEqual(nav_range.inner_text().strip(), f"Days 1-{visible_days}/7")
        page.wait_for_function(
            """
            (expectedCount) => {
              const block = document.querySelector('.calendar-week .calendar-week-block');
              const row = block ? block.querySelector('.calendar-table tbody tr') : null;
              if (!row) {
                return false;
              }
              const yesButtons = Array.from(row.querySelectorAll('.vote-switch-option-yes'));
              return yesButtons.length === expectedCount && yesButtons.every((button) => button.getAttribute('data-selected') === 'true');
            }
            """,
            arg=visible_days,
        )

    def test_browser_result_mode_yes_filter_hides_empty_rows_in_paginated_blocks(self) -> None:
        page = self.require_page()
        page.set_viewport_size({"width": 480, "height": 900})
        poll_identifier = "paginated_yes_filter_block_poll"

        self.open_home_page()
        self.login(name="paginated-filter-owner")
        self.create_poll(
            title="Paginated yes filter block poll",
            description="Used for paginated yes filter block coverage.",
            identifier=poll_identifier,
            timezone="Europe/Helsinki",
            start_date="2026-06-08",
            end_date="2026-06-14",
            daily_start_hour=9,
            daily_end_hour=10,
            allowed_weekdays=[0, 1, 2, 3, 4, 5, 6],
        )

        page.locator(".vote-switch-option-yes").first.click()
        self.wait_for_first_vote_state(".vote-switch-option-yes", True, page=page)

        voter_page = self.open_logged_in_poll_page(
            poll_identifier=poll_identifier,
            name="paginated-filter-voter",
        )
        voter_page.locator(".vote-switch-option-yes").first.click()
        self.wait_for_first_vote_state(".vote-switch-option-yes", True, page=voter_page)

        page.reload(wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.locator(".details-title").filter(has_text="Paginated yes filter block poll").wait_for()
        page.locator(".calendar-vote-mode-item").filter(has_text="Result mode").click()
        page.locator("#min-yes-filter").select_option("2")

        week_blocks = self.week_blocks_locator(page=page)
        self.assertGreater(week_blocks.count(), 1)

        first_block = self.week_block_locator(block_index=0, page=page)
        first_block.locator(".vote-switch").first.wait_for()
        first_block.locator('[data-nav-direction="next"]').click()

        page.wait_for_function(
            """
            (blockIndex) => {
              const block = document.querySelectorAll('.calendar-week .calendar-week-block')[blockIndex];
              if (!block) {
                return false;
              }
              const emptyRow = block.querySelector('.calendar-empty-row');
              const voteSwitches = block.querySelectorAll('.vote-switch');
              const timeTriggers = block.querySelectorAll('.bulk-time-trigger');
              return Boolean(emptyRow)
                && emptyRow.textContent.includes('No options match the current Yes filter.')
                && voteSwitches.length === 0
                && timeTriggers.length === 0;
            }
            """,
            arg=1,
        )

        second_block = self.week_block_locator(block_index=1, page=page)
        self.assertEqual(second_block.locator(".vote-switch").count(), 0)
        self.assertEqual(second_block.locator(".bulk-time-trigger").count(), 0)
        second_block.locator(".calendar-empty-row").filter(
            has_text="No options match the current Yes filter."
        ).wait_for()

    def test_browser_calendar_custom_timezone_preserves_duplicate_dst_hour_rows(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="calendar-dst-duplicate-owner")
        self.create_poll(
            title="Calendar DST duplicate hour poll",
            description="Used for duplicate DST hour calendar coverage.",
            identifier="calendar_dst_duplicate_hour_poll",
            timezone="UTC",
            start_date="2026-10-25",
            end_date="2026-10-25",
            daily_start_hour=0,
            daily_end_hour=3,
            allowed_weekdays=[6],
        )

        page.locator(".calendar-timezone-mode-item-custom").click()
        page.locator("#calendar-timezone").fill("Europe/Helsinki")
        page.locator("#calendar-timezone").blur()
        page.wait_for_function(
            """
            () => {
              const rowLabels = Array.from(
                document.querySelectorAll('.calendar-time-row .bulk-time-trigger, .calendar-time-row .bulk-time-label')
              ).map((element) => element.textContent.trim());
              const optionIds = Array.from(document.querySelectorAll('.vote-switch-option-yes'))
                .map((element) => element.getAttribute('data-vote-option-id'))
                .filter((value) => Boolean(value));
              return rowLabels.length === 3
                && rowLabels[0] === '03:00'
                && rowLabels[1] === '03:00'
                && rowLabels[2] === '04:00'
                && optionIds.length === 3
                && new Set(optionIds).size === 3;
            }
            """
        )

        calendar_state = page.evaluate(
            """
            () => ({
              rowLabels: Array.from(
                document.querySelectorAll('.calendar-time-row .bulk-time-trigger, .calendar-time-row .bulk-time-label')
              ).map((element) => element.textContent.trim()),
              optionIds: Array.from(document.querySelectorAll('.vote-switch-option-yes'))
                .map((element) => element.getAttribute('data-vote-option-id'))
                .filter((value) => Boolean(value))
            })
            """
        )

        self.assertEqual(calendar_state["rowLabels"], ["03:00", "03:00", "04:00"], calendar_state)
        self.assertEqual(len(calendar_state["optionIds"]), 3, calendar_state)
        self.assertEqual(len(set(calendar_state["optionIds"])), 3, calendar_state)

    def test_browser_calendar_pagination_buttons_expose_range_in_accessible_name(self) -> None:
        page = self.require_page()
        page.set_viewport_size({"width": 480, "height": 900})

        self.open_home_page()
        self.login(name="pagination-contract-owner")
        self.create_poll(
            title="Pagination contract poll",
            description="Used for pagination ARIA contract coverage.",
            identifier="pagination_contract_poll",
            timezone="Europe/Helsinki",
            start_date="2026-06-22",
            end_date="2026-06-28",
            daily_start_hour=9,
            daily_end_hour=10,
            allowed_weekdays=[0, 1, 2, 3, 4, 5, 6],
        )

        first_block = self.week_block_locator(block_index=0, page=page)
        nav_range = first_block.locator(".calendar-nav-range")
        nav_range.wait_for()
        current_range = nav_range.inner_text().strip()
        next_button = first_block.locator('[data-nav-direction="next"]')

        self.assertEqual(next_button.get_attribute("aria-label"), f"Next days, {current_range}")
        self.assertEqual(next_button.get_attribute("aria-describedby"), nav_range.get_attribute("id"))
        self.assert_aria_snapshot_contains(
            next_button,
            f'button "Next days, {current_range}"',
        )

    def test_browser_duplicate_dst_rows_expose_distinct_accessible_labels(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="calendar-dst-contract-owner")
        self.create_poll(
            title="Calendar DST accessibility contract poll",
            description="Used for duplicate DST hour accessibility contract coverage.",
            identifier="calendar_dst_accessibility_contract_poll",
            timezone="UTC",
            start_date="2026-10-25",
            end_date="2026-10-25",
            daily_start_hour=0,
            daily_end_hour=3,
            allowed_weekdays=[6],
        )

        page.locator(".calendar-timezone-mode-item-custom").click()
        page.locator("#calendar-timezone").fill("Europe/Helsinki")
        page.locator("#calendar-timezone").blur()
        page.wait_for_function(
            """
            () => document.querySelectorAll('.bulk-time-trigger').length === 3
            """
        )

        first_row_trigger = page.locator(".bulk-time-trigger").nth(0)
        second_row_trigger = page.locator(".bulk-time-trigger").nth(1)
        self.assertEqual(first_row_trigger.inner_text().strip(), "03:00")
        self.assertEqual(second_row_trigger.inner_text().strip(), "03:00")
        self.assertEqual(first_row_trigger.get_attribute("aria-label"), "03:00 [1/2]")
        self.assertEqual(second_row_trigger.get_attribute("aria-label"), "03:00 [2/2]")
        self.assertNotEqual(
            first_row_trigger.get_attribute("aria-label"),
            second_row_trigger.get_attribute("aria-label"),
        )

        first_group = page.locator(".vote-switch").nth(0)
        second_group = page.locator(".vote-switch").nth(1)
        self.assertIn("[1/2]", first_group.get_attribute("aria-label") or "")
        self.assertIn("[2/2]", second_group.get_attribute("aria-label") or "")
        self.assert_aria_snapshot_contains(first_row_trigger, 'button "03:00 [1/2]"')
        self.assert_aria_snapshot_contains(second_row_trigger, 'button "03:00 [2/2]"')

    def test_browser_calendar_gap_indicator_marks_missing_days_between_columns(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="gap-indicator-owner")
        self.create_poll(
            title="Gap indicator poll",
            description="Used for missing-day calendar gap indicator coverage.",
            identifier="gap_indicator_poll",
            timezone="Europe/Helsinki",
            start_date="2026-04-13",
            end_date="2026-04-17",
            daily_start_hour=9,
            daily_end_hour=10,
            allowed_weekdays=[0, 1, 3, 4],
        )

        gap_state = page.evaluate(
            """
            () => {
              const headers = Array.from(document.querySelectorAll('.calendar-week .calendar-day-col'));
              const firstRow = document.querySelector('.calendar-week .calendar-table tbody tr');
              const cells = firstRow ? Array.from(firstRow.querySelectorAll('td.calendar-cell')) : [];
              return {
                headerGapFlags: headers.map((header) => header.classList.contains('calendar-day-gap-before')),
                cellGapFlags: cells.map((cell) => cell.classList.contains('calendar-day-gap-before')),
              };
            }
            """
        )

        self.assertEqual(gap_state["headerGapFlags"], [False, False, True, False], gap_state)
        self.assertEqual(gap_state["cellGapFlags"], [False, False, True, False], gap_state)

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

        self.assertEqual(first_yes_button.get_attribute("data-selected"), "false")

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

        self.open_profile_panel(page=page)
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

        self.open_profile_panel(page=page)
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
        self.assertEqual(first_yes_button.get_attribute("data-selected"), "true")

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
        self.assertEqual(first_yes_button.get_attribute("data-selected"), "false")

        first_yes_button.click()
        page.get_by_role("dialog").wait_for()
        page.keyboard.press("Escape")
        page.get_by_role("dialog").wait_for(state="hidden")

        page.get_by_role("button", name="Login").click()
        self.submit_auth_dialog(name="pending-vote-cancel-user")
        page.get_by_role("button", name="Logout", exact=True).wait_for()
        page.wait_for_load_state("networkidle")

        self.assertEqual(first_yes_button.get_attribute("data-selected"), "false")

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

        initial_state = page.evaluate(
            """
            () => {
              const blocks = Array.from(document.querySelectorAll('.calendar-week .calendar-week-block'));
              return {
                blockCount: blocks.length,
                firstBlockDayCount: blocks[0]?.querySelectorAll('.calendar-day-col').length || 0,
              };
            }
            """
        )
        initial_visible_days = int(initial_state["firstBlockDayCount"])
        self.assertGreater(initial_visible_days, 3, initial_state)

        shrink_state = page.evaluate(
            """
            async () => {
              const tableWrap = document.querySelector('.details .calendar-week-block .table-wrap');
              if (tableWrap) {
                tableWrap.style.width = '320px';
              }
              window.dispatchEvent(new Event('resize'));
              await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
              const blocks = Array.from(document.querySelectorAll('.calendar-week .calendar-week-block'));
              return {
                wrapWidth: tableWrap ? tableWrap.clientWidth : null,
                blockCount: blocks.length,
                firstBlockDayCount: blocks[0]?.querySelectorAll('.calendar-day-col').length || 0,
                rangeTexts: blocks
                  .map((block) => block.querySelector('.calendar-nav-range')?.textContent?.trim() || '')
                  .filter((text) => Boolean(text))
              };
            }
            """
        )
        shrunken_visible_days = int(shrink_state["firstBlockDayCount"])
        self.assertLess(shrunken_visible_days, initial_visible_days, shrink_state)
        self.assertGreaterEqual(int(shrink_state["blockCount"]), int(initial_state["blockCount"]), shrink_state)
        self.assertTrue(bool(shrink_state["rangeTexts"]), shrink_state)

        expand_state = page.evaluate(
            """
            async () => {
              const tableWrap = document.querySelector('.details .calendar-week-block .table-wrap');
              if (tableWrap) {
                tableWrap.style.width = '1600px';
              }
              window.dispatchEvent(new Event('resize'));
              await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
              const blocks = Array.from(document.querySelectorAll('.calendar-week .calendar-week-block'));
              return {
                wrapWidth: tableWrap ? tableWrap.clientWidth : null,
                blockCount: blocks.length,
                firstBlockDayCount: blocks[0]?.querySelectorAll('.calendar-day-col').length || 0
              };
            }
            """
        )
        self.assertGreater(int(expand_state["firstBlockDayCount"]), shrunken_visible_days, expand_state)
        self.assertLessEqual(int(expand_state["blockCount"]), int(shrink_state["blockCount"]), expand_state)

    def test_browser_partial_week_calendar_columns_expand_to_max_width_when_space_is_available(self) -> None:
        page = self.require_page()
        page.set_viewport_size({"width": 1600, "height": 1000})

        self.open_home_page()
        self.login(name="column-cap-owner")
        self.create_poll(
            title="Mixed week width expansion poll",
            description="Used for partial-week calendar width expansion coverage.",
            identifier="mixed_week_width_expansion_poll",
            timezone="Europe/Helsinki",
            start_date="2026-04-13",
            end_date="2026-04-21",
            allowed_weekdays=[0, 1, 2, 3, 4, 5, 6],
        )

        width_state = page.evaluate(
            """
            () => {
              const rootPx = Number.parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
              const weeks = Array.from(document.querySelectorAll('.calendar-week'));
              const widthsInRemByWeek = weeks.map((week) =>
                Array.from(week.querySelectorAll('.calendar-day-col'))
                  .map((header) => header.getBoundingClientRect().width / rootPx)
              );
              const secondWeek = weeks[1];
              const secondWrap = secondWeek ? secondWeek.querySelector('.table-wrap') : null;
              const secondTable = secondWeek ? secondWeek.querySelector('.calendar-table') : null;
              const secondWrapRect = secondWrap ? secondWrap.getBoundingClientRect() : null;
              const secondTableRect = secondTable ? secondTable.getBoundingClientRect() : null;
              return {
                weekCounts: widthsInRemByWeek.map((widths) => widths.length),
                widthsInRemByWeek,
                partialWeekLeftGapPx: secondWrapRect && secondTableRect ? secondTableRect.left - secondWrapRect.left : null,
                partialWeekRightGapPx: secondWrapRect && secondTableRect
                  ? secondWrapRect.right - secondTableRect.right
                  : null
              };
            }
            """
        )

        self.assertEqual(width_state["weekCounts"], [7, 2], width_state)
        full_week_widths = width_state["widthsInRemByWeek"][0]
        partial_week_widths = width_state["widthsInRemByWeek"][1]
        self.assertTrue(full_week_widths, width_state)
        self.assertTrue(partial_week_widths, width_state)
        full_week_reference = float(full_week_widths[0])
        self.assertGreater(full_week_reference, 0, width_state)
        for width_in_rem in partial_week_widths:
            self.assertGreater(float(width_in_rem), full_week_reference + 1.0, width_state)
            self.assertAlmostEqual(float(width_in_rem), 18.0, delta=0.2)
            self.assertLessEqual(float(width_in_rem), 18.2, width_state)
        self.assertIsNotNone(width_state["partialWeekLeftGapPx"], width_state)
        self.assertLessEqual(float(width_state["partialWeekLeftGapPx"]), 4.0, width_state)

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

        page.get_by_role("button", name="Edit poll").click()
        page.locator("#edit-timezone").fill("pacific/hon")
        page.locator("#edit-timezone-suggestions").wait_for()
        page.locator("#edit-timezone-suggestions .timezone-suggestion").filter(has_text="Pacific/Honolulu").first.click()
        self.assertEqual(page.locator("#edit-timezone").input_value(), "Pacific/Honolulu")
        page.locator("#edit-timezone-suggestions").wait_for(state="hidden")

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
        self.assertEqual(self.active_element_snapshot(page)["id"], "poll-title")

        title_input = page.locator("#poll-title")
        self.assertEqual(title_input.get_attribute("aria-invalid"), "true")
        self.assertEqual(title_input.get_attribute("aria-describedby"), "create-title-error")
        self.assertEqual(title_input.get_attribute("aria-errormessage"), "create-title-error")

        identifier_input = page.locator("#poll-identifier")
        identifier_describedby = identifier_input.get_attribute("aria-describedby") or ""
        self.assertEqual(identifier_input.get_attribute("aria-invalid"), "true")
        self.assertIn("poll-identifier-help", identifier_describedby)
        self.assertIn("create-identifier-error", identifier_describedby)
        self.assertEqual(identifier_input.get_attribute("aria-errormessage"), "create-identifier-error")

        weekday_fieldset = page.locator("#section-panel-create fieldset").first
        weekday_checkbox = page.locator("#section-panel-create .weekday-item input").first
        weekday_describedby = weekday_checkbox.get_attribute("aria-describedby") or ""
        self.assertEqual(weekday_fieldset.get_attribute("aria-invalid"), "true")
        self.assertIn("create-allowed-weekdays-error", weekday_describedby)
        self.assertEqual(weekday_checkbox.get_attribute("aria-errormessage"), "create-allowed-weekdays-error")

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
        self.assertEqual(self.active_element_snapshot(page)["id"], "poll-identifier")
        self.assertIn("input-invalid", page.locator("#poll-identifier").get_attribute("class") or "")
        identifier_describedby = page.locator("#poll-identifier").get_attribute("aria-describedby") or ""
        self.assertEqual(page.locator("#poll-identifier").get_attribute("aria-invalid"), "true")
        self.assertIn("poll-identifier-help", identifier_describedby)
        self.assertIn("create-identifier-error", identifier_describedby)
        self.assertEqual(page.locator("#poll-identifier").get_attribute("aria-errormessage"), "create-identifier-error")

    def test_browser_edit_form_maps_backend_identifier_conflict_to_field(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="edit-duplicate-owner")
        self.create_poll(
            title="Edit duplicate source poll",
            description="Original poll for edit duplicate coverage.",
            identifier="edit_duplicate_source_poll",
            timezone="Europe/Helsinki",
            start_date="2026-04-30",
            end_date="2026-04-30",
        )

        page.locator(".title-home").click()
        self.create_poll(
            title="Edit duplicate target poll",
            description="Poll whose identifier will be edited.",
            identifier="edit_duplicate_target_poll",
            timezone="Europe/Helsinki",
            start_date="2026-05-01",
            end_date="2026-05-01",
        )

        page.get_by_role("button", name="Edit poll").click()
        page.locator("#edit-identifier").fill("edit_duplicate_source_poll")
        page.get_by_role("button", name="Save changes").click()

        page.get_by_role("alert").filter(has_text="This identifier is already in use.").wait_for()
        page.locator("#edit-identifier-error").filter(has_text="This identifier is already in use.").wait_for()
        self.assertEqual(self.active_element_snapshot(page)["id"], "edit-identifier")
        self.assertIn("input-invalid", page.locator("#edit-identifier").get_attribute("class") or "")
        identifier_describedby = page.locator("#edit-identifier").get_attribute("aria-describedby") or ""
        self.assertEqual(page.locator("#edit-identifier").get_attribute("aria-invalid"), "true")
        self.assertIn("edit-poll-identifier-help", identifier_describedby)
        self.assertIn("edit-identifier-error", identifier_describedby)
        self.assertEqual(page.locator("#edit-identifier").get_attribute("aria-errormessage"), "edit-identifier-error")

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

        self.mock_fetch_json(
            url_part="/api/polls/",
            method="PUT",
            status=409,
            body={
                "error": "schedule_conflicts_with_votes",
                "detail": "Cannot remove or shrink time slots that already have votes.",
            },
            page=page,
        )
        page.get_by_role("button", name="Save changes").click()

        page.get_by_role("alert").filter(
            has_text="You cannot remove time slots that already have votes."
        ).wait_for()
        page.locator("#section-panel-selected .field-error").filter(
            has_text="You cannot remove time slots that already have votes."
        ).first.wait_for()
        page.get_by_role("button", name="Save changes").wait_for()
        self.assertEqual(self.active_element_snapshot(page)["id"], "edit-timezone")
        self.assertEqual(page.locator("#edit-timezone").get_attribute("aria-invalid"), "true")
        self.assertEqual(
            page.locator("#edit-timezone").get_attribute("aria-describedby"),
            "edit-timezone-help edit-timezone-error",
        )
        self.assertEqual(page.locator("#edit-timezone").get_attribute("aria-errormessage"), "edit-timezone-error")

    def test_browser_edit_form_weekday_inputs_disable_days_with_votes(self) -> None:
        page = self.require_page()
        poll_identifier = "edit_weekday_lock_poll"

        self.open_home_page()
        self.login(name="edit-weekday-lock-owner")
        self.create_poll(
            title="Edit weekday lock poll",
            description="Used for edit weekday lock coverage.",
            identifier=poll_identifier,
            timezone="Europe/Helsinki",
            start_date="2026-05-04",
            end_date="2026-05-05",
        )

        browser = self.browser
        if browser is None:
            raise unittest.SkipTest("Playwright browser is not available for this test run.")

        voter_context = browser.new_context(base_url=self.live_server_url)
        self.addCleanup(voter_context.close)
        voter_page = voter_context.new_page()
        voter_page.set_default_timeout(15000)

        self.open_home_page(voter_page, f"/?id={poll_identifier}")
        self.login(name="edit-weekday-lock-voter", page=voter_page)
        voter_page.locator(".calendar-table tbody tr").first.locator(".vote-switch-option-yes").first.click()
        page.wait_for_function(
            """
            async () => {
              try {
                const response = await fetch('/api/polls/edit_weekday_lock_poll/', {
                  credentials: 'same-origin',
                  headers: { Accept: 'application/json' },
                });
                if (!response.ok) {
                  return false;
                }
                const contentType = response.headers.get('content-type') || '';
                if (!contentType.includes('application/json')) {
                  return false;
                }
                const poll = await response.json();
                return (poll.options || []).some((item) => {
                  const counts = item.counts || {};
                  return counts.yes === 1;
                });
              } catch (error) {
                return false;
              }
            }
            """
        )

        page.reload(wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.locator(".details-title").filter(has_text="Edit weekday lock poll").wait_for()
        page.get_by_role("button", name="Edit poll").click()

        monday_checkbox = page.locator("#section-panel-selected .weekday-item input").nth(0)
        tuesday_checkbox = page.locator("#section-panel-selected .weekday-item input").nth(1)

        self.assertTrue(monday_checkbox.is_checked())
        self.assertTrue(monday_checkbox.is_disabled())
        self.assertTrue(tuesday_checkbox.is_checked())
        self.assertFalse(tuesday_checkbox.is_disabled())

        page.get_by_text("Existing votes require these weekdays to remain selected: Mon.").wait_for()
        describedby = monday_checkbox.get_attribute("aria-describedby") or ""
        self.assertIn("edit-allowed-weekdays-hints", describedby)

        tuesday_checkbox.set_checked(False)
        self.assertFalse(tuesday_checkbox.is_checked())

    def test_browser_edit_form_date_inputs_follow_start_end_bounds_without_votes(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="edit-date-bounds-owner")
        self.create_poll(
            title="Edit date bounds poll",
            description="Used for edit date min/max without votes.",
            identifier="edit_date_bounds_poll",
            timezone="Europe/Helsinki",
            start_date="2026-05-10",
            end_date="2026-05-12",
        )

        page.get_by_role("button", name="Edit poll").click()
        page.locator("#edit-start-date").wait_for()

        self.assertEqual(page.locator("#edit-start-date").get_attribute("max"), "2026-05-12")
        self.assertEqual(page.locator("#edit-end-date").get_attribute("min"), "2026-05-10")
        page.get_by_text("Start date cannot be later than the selected end date.").wait_for()
        page.get_by_text("End date cannot be earlier than the selected start date.").wait_for()

        page.locator("#edit-end-date").fill("2026-05-11")
        page.wait_for_function(
            """
            () => document.querySelector('#edit-start-date')?.getAttribute('max') === '2026-05-11'
            """
        )

        page.locator("#edit-start-date").fill("2026-05-11")
        page.wait_for_function(
            """
            () => document.querySelector('#edit-end-date')?.getAttribute('min') === '2026-05-11'
            """
        )

    def test_browser_edit_form_date_inputs_reflect_existing_vote_bounds(self) -> None:
        page = self.require_page()
        poll_identifier = "edit_date_vote_bounds_poll"

        self.open_home_page()
        self.login(name="edit-date-vote-bounds-owner")
        self.create_poll(
            title="Edit date vote bounds poll",
            description="Used for edit date min/max with votes.",
            identifier=poll_identifier,
            timezone="Europe/Helsinki",
            start_date="2026-05-04",
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
        self.login(name="edit-date-vote-bounds-voter", page=voter_page)
        middle_yes_button = voter_page.locator(".calendar-table tbody tr").first.locator(
            ".vote-switch-option-yes"
        ).nth(1)
        middle_yes_button.click()
        page.wait_for_function(
            """
            async () => {
              try {
                const response = await fetch('/api/polls/edit_date_vote_bounds_poll/', {
                  credentials: 'same-origin',
                  headers: { Accept: 'application/json' },
                });
                if (!response.ok) {
                  return false;
                }
                const contentType = response.headers.get('content-type') || '';
                if (!contentType.includes('application/json')) {
                  return false;
                }
                const poll = await response.json();
                const option = (poll.options || []).find((item) => {
                  const counts = item.counts || {};
                  return counts.yes === 1;
                });
                if (!option) {
                  return false;
                }
                const counts = option.counts || {};
                return counts.yes === 1;
              } catch (error) {
                return false;
              }
            }
            """
        )

        page.reload(wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.locator(".details-title").filter(has_text="Edit date vote bounds poll").wait_for()
        page.get_by_role("button", name="Edit poll").click()
        page.locator("#edit-start-date").wait_for()

        self.assertEqual(page.locator("#edit-start-date").get_attribute("max"), "2026-05-05")
        self.assertEqual(page.locator("#edit-end-date").get_attribute("min"), "2026-05-05")
        page.get_by_text("Existing votes require the start date to be on or before").wait_for()
        page.get_by_text("Existing votes require the end date to be on or after").wait_for()
        self.assertEqual(
            page.get_by_text("Start date cannot be later than the selected end date.").count(),
            0,
        )
        self.assertEqual(
            page.get_by_text("End date cannot be earlier than the selected start date.").count(),
            0,
        )

        start_describedby = page.locator("#edit-start-date").get_attribute("aria-describedby") or ""
        end_describedby = page.locator("#edit-end-date").get_attribute("aria-describedby") or ""
        self.assertIn("edit-start-date-hints", start_describedby)
        self.assertIn("edit-end-date-hints", end_describedby)

    def test_browser_edit_form_timezone_change_updates_date_vote_bounds(self) -> None:
        page = self.require_page()
        poll_identifier = "edit_timezone_date_bounds_poll"

        self.open_edit_form_for_utc_vote_that_shifts_in_honolulu(
            poll_identifier=poll_identifier,
            title="Edit timezone date bounds poll",
            owner_name="edit-timezone-date-owner",
            voter_name="edit-timezone-date-voter",
        )

        self.assertEqual(page.locator("#edit-start-date").get_attribute("max"), "2026-05-04")
        self.assertEqual(page.locator("#edit-end-date").get_attribute("min"), "2026-05-04")

        dialog = self.open_edit_timezone_confirmation_dialog(page=page)
        dialog.get_by_role("button", name="Apply timezone change").click()
        page.wait_for_function(
            """
            () => document.querySelector('#edit-start-date')?.getAttribute('max') === '2026-05-03'
            """
        )

        self.assertEqual(page.locator("#edit-start-date").get_attribute("max"), "2026-05-03")
        page.locator("#edit-start-date").fill("2026-05-03")
        page.wait_for_function(
            """
            () => document.querySelector('#edit-end-date')?.getAttribute('min') === '2026-05-03'
            """
        )
        self.assertEqual(page.locator("#edit-end-date").get_attribute("min"), "2026-05-03")

    def test_browser_edit_form_hour_selects_follow_start_end_bounds_without_votes(self) -> None:
        page = self.require_page()

        self.open_home_page()
        self.login(name="edit-hour-bounds-owner")
        self.create_poll(
            title="Edit hour bounds poll",
            description="Used for edit hour bounds without votes.",
            identifier="edit_hour_bounds_poll",
            timezone="Europe/Helsinki",
            start_date="2026-05-11",
            end_date="2026-05-11",
            daily_start_hour=9,
            daily_end_hour=12,
        )

        page.get_by_role("button", name="Edit poll").click()
        page.locator("#edit-daily-start-hour").wait_for()

        start_options = self.select_option_disabled_map("#edit-daily-start-hour", page=page)
        end_options = self.select_option_disabled_map("#edit-daily-end-hour", page=page)
        self.assertFalse(start_options["11"])
        self.assertTrue(start_options["12"])
        self.assertFalse(end_options["10"])
        self.assertTrue(end_options["9"])
        page.get_by_text("Day start hour must be earlier than the selected end hour.").wait_for()
        page.get_by_text("Day end hour must be later than the selected start hour.").wait_for()

        start_describedby = page.locator("#edit-daily-start-hour").get_attribute("aria-describedby") or ""
        end_describedby = page.locator("#edit-daily-end-hour").get_attribute("aria-describedby") or ""
        self.assertIn("edit-start-hour-hints", start_describedby)
        self.assertIn("edit-end-hour-hints", end_describedby)

        page.locator("#edit-daily-end-hour").select_option("10")
        page.wait_for_function(
            """
            () => {
              const startSelect = document.querySelector('#edit-daily-start-hour');
              const optionNine = startSelect?.querySelector('option[value="9"]');
              const optionTen = startSelect?.querySelector('option[value="10"]');
              return Boolean(optionNine && optionTen)
                && optionNine.disabled === false
                && optionTen.disabled === true;
            }
            """
        )

        page.locator("#edit-daily-start-hour").select_option("8")
        page.wait_for_function(
            """
            () => {
              const endSelect = document.querySelector('#edit-daily-end-hour');
              const optionEight = endSelect?.querySelector('option[value="8"]');
              const optionNine = endSelect?.querySelector('option[value="9"]');
              return Boolean(optionEight && optionNine)
                && optionEight.disabled === true
                && optionNine.disabled === false;
            }
            """
        )

    def test_browser_edit_form_timezone_change_updates_hour_vote_bounds(self) -> None:
        page = self.require_page()
        poll_identifier = "edit_timezone_hour_bounds_poll"

        self.open_edit_form_for_utc_vote_that_shifts_in_honolulu(
            poll_identifier=poll_identifier,
            title="Edit timezone hour bounds poll",
            owner_name="edit-timezone-hour-owner",
            voter_name="edit-timezone-hour-voter",
        )

        start_options = self.select_option_disabled_map("#edit-daily-start-hour", page=page)
        end_options = self.select_option_disabled_map("#edit-daily-end-hour", page=page)
        self.assertFalse(start_options["0"])
        self.assertTrue(start_options["14"])
        self.assertFalse(end_options["14"])
        self.assertFalse(end_options["15"])

        self.open_edit_timezone_confirmation_dialog(page=page).get_by_role(
            "button",
            name="Apply timezone change",
        ).click()
        page.wait_for_function(
            """
            () => {
              const startSelect = document.querySelector('#edit-daily-start-hour');
              const endSelect = document.querySelector('#edit-daily-end-hour');
              const startFourteen = startSelect?.querySelector('option[value="14"]');
              const startFifteen = startSelect?.querySelector('option[value="15"]');
              const endFourteen = endSelect?.querySelector('option[value="14"]');
              const endFifteen = endSelect?.querySelector('option[value="15"]');
              return Boolean(startFourteen && startFifteen && endFourteen && endFifteen)
                && startFourteen.disabled === false
                && startFifteen.disabled === true
                && endFourteen.disabled === true
                && endFifteen.disabled === false;
            }
            """
        )

        start_options = self.select_option_disabled_map("#edit-daily-start-hour", page=page)
        end_options = self.select_option_disabled_map("#edit-daily-end-hour", page=page)
        self.assertFalse(start_options["14"])
        self.assertTrue(start_options["15"])
        self.assertTrue(end_options["14"])
        self.assertFalse(end_options["15"])

    def test_browser_edit_form_hour_selects_reflect_existing_vote_bounds(self) -> None:
        page = self.require_page()
        poll_identifier = "edit_hour_vote_bounds_poll"

        self.open_home_page()
        self.login(name="edit-hour-vote-bounds-owner")
        self.create_poll(
            title="Edit hour vote bounds poll",
            description="Used for edit hour bounds with votes.",
            identifier=poll_identifier,
            timezone="Europe/Helsinki",
            start_date="2026-05-04",
            end_date="2026-05-04",
            daily_start_hour=9,
            daily_end_hour=12,
        )

        browser = self.browser
        if browser is None:
            raise unittest.SkipTest("Playwright browser is not available for this test run.")

        voter_context = browser.new_context(base_url=self.live_server_url)
        self.addCleanup(voter_context.close)
        voter_page = voter_context.new_page()
        voter_page.set_default_timeout(15000)

        self.open_home_page(voter_page, f"/?id={poll_identifier}")
        self.login(name="edit-hour-vote-bounds-voter", page=voter_page)
        voter_page.locator(".calendar-table tbody tr").nth(1).locator(".vote-switch-option-yes").first.click()
        page.wait_for_function(
            """
            async () => {
              try {
                const response = await fetch('/api/polls/edit_hour_vote_bounds_poll/', {
                  credentials: 'same-origin',
                  headers: { Accept: 'application/json' },
                });
                if (!response.ok) {
                  return false;
                }
                const contentType = response.headers.get('content-type') || '';
                if (!contentType.includes('application/json')) {
                  return false;
                }
                const poll = await response.json();
                return (poll.options || []).some((item) => {
                  const counts = item.counts || {};
                  return counts.yes === 1;
                });
              } catch (error) {
                return false;
              }
            }
            """
        )

        page.reload(wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.locator(".details-title").filter(has_text="Edit hour vote bounds poll").wait_for()
        page.get_by_role("button", name="Edit poll").click()
        page.locator("#edit-daily-start-hour").wait_for()

        start_options = self.select_option_disabled_map("#edit-daily-start-hour", page=page)
        end_options = self.select_option_disabled_map("#edit-daily-end-hour", page=page)
        self.assertFalse(start_options["10"])
        self.assertTrue(start_options["11"])
        self.assertTrue(end_options["10"])
        self.assertFalse(end_options["11"])
        page.get_by_text("Existing votes require the day start hour to be at or before 10:00.").wait_for()
        page.get_by_text("Existing votes require the day end hour to be at or after 11:00.").wait_for()
        self.assertEqual(
            page.get_by_text("Day start hour must be earlier than the selected end hour.").count(),
            0,
        )
        self.assertEqual(
            page.get_by_text("Day end hour must be later than the selected start hour.").count(),
            0,
        )

        start_describedby = page.locator("#edit-daily-start-hour").get_attribute("aria-describedby") or ""
        end_describedby = page.locator("#edit-daily-end-hour").get_attribute("aria-describedby") or ""
        self.assertIn("edit-start-hour-hints", start_describedby)
        self.assertIn("edit-end-hour-hints", end_describedby)

    def test_browser_edit_form_timezone_change_updates_locked_weekday(self) -> None:
        page = self.require_page()
        poll_identifier = "edit_timezone_weekday_bounds_poll"

        self.open_edit_form_for_utc_vote_that_shifts_in_honolulu(
            poll_identifier=poll_identifier,
            title="Edit timezone weekday bounds poll",
            owner_name="edit-timezone-weekday-owner",
            voter_name="edit-timezone-weekday-voter",
        )

        monday_checkbox = page.locator("#section-panel-selected .weekday-item input").nth(0)
        sunday_checkbox = page.locator("#section-panel-selected .weekday-item input").nth(6)
        self.assertTrue(monday_checkbox.is_checked())
        self.assertTrue(monday_checkbox.is_disabled())
        self.assertTrue(sunday_checkbox.is_checked())
        self.assertFalse(sunday_checkbox.is_disabled())

        self.open_edit_timezone_confirmation_dialog(page=page).get_by_role(
            "button",
            name="Apply timezone change",
        ).click()
        page.wait_for_function(
            """
            () => {
              const inputs = document.querySelectorAll('#section-panel-selected .weekday-item input');
              const monday = inputs[0];
              const sunday = inputs[6];
              return Boolean(monday && sunday)
                && monday.disabled === false
                && sunday.disabled === true;
            }
            """
        )

        self.assertFalse(monday_checkbox.is_disabled())
        self.assertTrue(sunday_checkbox.is_disabled())
        page.get_by_text("Existing votes require these weekdays to remain selected: Sun.").wait_for()

        monday_checkbox.set_checked(False)
        self.assertFalse(monday_checkbox.is_checked())

    def test_browser_edit_form_timezone_change_can_save_valid_shifted_schedule(self) -> None:
        page = self.require_page()
        poll_identifier = "edit_timezone_save_success_poll"

        self.open_edit_form_for_utc_vote_that_shifts_in_honolulu(
            poll_identifier=poll_identifier,
            title="Edit timezone save success poll",
            owner_name="edit-timezone-save-owner",
            voter_name="edit-timezone-save-voter",
            daily_start_hour=0,
            daily_end_hour=1,
            allowed_weekdays=[0],
        )

        dialog = self.open_edit_timezone_confirmation_dialog(page=page)
        description_text = dialog.locator("#edit-timezone-confirm-description").text_content() or ""
        self.assertIn("UTC", description_text)
        self.assertIn("Pacific/Honolulu", description_text)
        self.assertIn("expands the schedule", description_text)
        summary_text = dialog.locator(".dialog-summary-list").text_content() or ""
        self.assertIn("Start date:", summary_text)
        self.assertIn("04/05/2026", summary_text)
        self.assertIn("03/05/2026", summary_text)
        self.assertIn("Daily end hour: 01:00 -> 15:00", summary_text)
        self.assertIn("Allowed weekdays: Mon -> Mon", summary_text)
        self.assertIn("Sun", summary_text)
        dialog.get_by_role("button", name="Apply timezone change").click()
        page.wait_for_function(
            """
            () => {
              const startDate = document.querySelector('#edit-start-date');
              const endDate = document.querySelector('#edit-end-date');
              const startHour = document.querySelector('#edit-daily-start-hour');
              const endHour = document.querySelector('#edit-daily-end-hour');
              const weekdayInputs = document.querySelectorAll('#section-panel-selected .weekday-item input');
              return Boolean(startDate && endDate && startHour && endHour && weekdayInputs.length >= 7)
                && startDate.value === '2026-05-03'
                && endDate.value === '2026-05-04'
                && startHour.value === '0'
                && endHour.value === '15'
                && weekdayInputs[0].checked === true
                && weekdayInputs[0].disabled === false
                && weekdayInputs[6].checked === true
                && weekdayInputs[6].disabled === true;
            }
            """
        )

        self.assertEqual(page.locator("#edit-start-date").input_value(), "2026-05-03")
        self.assertEqual(page.locator("#edit-end-date").input_value(), "2026-05-04")
        self.assertEqual(page.locator("#edit-daily-start-hour").input_value(), "0")
        self.assertEqual(page.locator("#edit-daily-end-hour").input_value(), "15")

        page.get_by_role("button", name="Save changes").click()
        page.get_by_role("status").filter(has_text="Poll updated successfully.").wait_for()
        page.get_by_role("button", name="Edit poll").wait_for()

        page.wait_for_function(
            """
            async (pollIdentifier) => {
              try {
                const response = await fetch(`/api/polls/${pollIdentifier}/`, {
                  credentials: 'same-origin',
                  headers: { Accept: 'application/json' },
                });
                if (!response.ok) {
                  return false;
                }
                const contentType = response.headers.get('content-type') || '';
                if (!contentType.includes('application/json')) {
                  return false;
                }
                const poll = await response.json();
                if (!poll || poll.timezone !== 'Pacific/Honolulu') {
                  return false;
                }
                if (poll.start_date !== '2026-05-03' || poll.end_date !== '2026-05-04') {
                  return false;
                }
                if (poll.daily_start_hour !== 0 || poll.daily_end_hour !== 15) {
                  return false;
                }
                if (!Array.isArray(poll.allowed_weekdays) || poll.allowed_weekdays.join(',') !== '0,6') {
                  return false;
                }
                if (!Array.isArray(poll.options) || poll.options.length < 2) {
                  return false;
                }
                const option = poll.options.find((item) => item.starts_at === '2026-05-04T00:00:00+00:00');
                const counts = option && typeof option.counts === 'object' ? option.counts : null;
                return Boolean(
                  option
                  && counts
                  && counts.yes === 1
                );
              } catch (error) {
                return false;
              }
            }
            """,
            arg=poll_identifier,
        )

    def test_browser_edit_form_timezone_change_confirmation_can_be_cancelled(self) -> None:
        page = self.require_page()
        poll_identifier = "edit_timezone_cancel_confirm_poll"

        self.open_edit_form_for_utc_vote_that_shifts_in_honolulu(
            poll_identifier=poll_identifier,
            title="Edit timezone cancel confirmation poll",
            owner_name="edit-timezone-cancel-owner",
            voter_name="edit-timezone-cancel-voter",
            daily_start_hour=0,
            daily_end_hour=1,
            allowed_weekdays=[0],
        )

        dialog = self.open_edit_timezone_confirmation_dialog(page=page)
        dialog.get_by_role("button", name="Cancel").click()
        dialog.wait_for(state="hidden")

        self.assertEqual(page.locator("#edit-timezone").input_value(), "UTC")
        self.assertEqual(page.locator("#edit-start-date").input_value(), "2026-05-04")
        self.assertEqual(page.locator("#edit-end-date").input_value(), "2026-05-04")
        self.assertEqual(page.locator("#edit-daily-start-hour").input_value(), "0")
        self.assertEqual(page.locator("#edit-daily-end-hour").input_value(), "1")

        monday_checkbox = page.locator("#section-panel-selected .weekday-item input").nth(0)
        sunday_checkbox = page.locator("#section-panel-selected .weekday-item input").nth(6)
        self.assertTrue(monday_checkbox.is_checked())
        self.assertFalse(sunday_checkbox.is_checked())

    def test_browser_edit_timezone_confirmation_dialog_focus_is_trapped_and_restored_on_escape(self) -> None:
        page = self.require_page()

        self.open_edit_form_for_utc_vote_that_shifts_in_honolulu(
            poll_identifier="edit_timezone_focus_trap_poll",
            title="Edit timezone focus trap poll",
            owner_name="edit-timezone-focus-owner",
            voter_name="edit-timezone-focus-voter",
            daily_start_hour=0,
            daily_end_hour=1,
            allowed_weekdays=[0],
        )

        timezone_input = page.locator("#edit-timezone")
        dialog = self.open_edit_timezone_confirmation_dialog(page=page)

        self.assertEqual(self.active_element_snapshot(page)["text"], "Apply timezone change")

        page.keyboard.press("Tab")
        self.assertEqual(self.active_element_snapshot(page)["text"], "Cancel")

        page.keyboard.press("Tab")
        self.assertEqual(self.active_element_snapshot(page)["text"], "Apply timezone change")

        page.keyboard.press("Shift+Tab")
        self.assertEqual(self.active_element_snapshot(page)["text"], "Cancel")

        page.keyboard.press("Escape")
        dialog.wait_for(state="hidden")
        self.assertTrue(timezone_input.evaluate("element => document.activeElement === element"))

    def test_edit_timezone_confirmation_dialog_has_no_accessibility_violations(self) -> None:
        page = self.require_page()

        self.open_edit_form_for_utc_vote_that_shifts_in_honolulu(
            poll_identifier="edit_timezone_dialog_a11y_poll",
            title="Edit timezone dialog accessibility poll",
            owner_name="edit-timezone-dialog-a11y-owner",
            voter_name="edit-timezone-dialog-a11y-voter",
            daily_start_hour=0,
            daily_end_hour=1,
            allowed_weekdays=[0],
        )

        self.open_edit_timezone_confirmation_dialog(page=page)

        results = self.run_accessibility_audit(page=page)
        self.assert_no_axe_violations(results, page_name="edit timezone confirmation dialog")

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
