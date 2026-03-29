from __future__ import annotations

import unittest
from typing import TYPE_CHECKING, Any, Optional

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings, tag

from .tests_browser import (
    PLAYWRIGHT_TESTS_AVAILABLE,
    REQUIRE_BROWSER_TESTS,
    axe_runner_factory,
    playwright_timeout_error_cls,
    sync_playwright_fn,
)

if TYPE_CHECKING:
    from playwright.sync_api import Browser, BrowserContext, Page, Playwright


@tag("browser", "timezone_contract")
@override_settings(ALLOWED_HOSTS=["127.0.0.1", "localhost", "testserver", "[::1]"])
class PollTimezoneContractBrowserTests(StaticLiveServerTestCase):
    playwright: Optional["Playwright"] = None
    browser: Optional["Browser"] = None
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

    def open_home_page(self, page: Optional["Page"] = None, path: str = "/") -> None:
        page = page or self.require_page()
        for attempt in range(2):
            try:
                page.goto(path, wait_until="commit", timeout=30000)
                break
            except playwright_timeout_error_cls:
                if attempt == 1:
                    raise
                try:
                    page.goto("about:blank", wait_until="load", timeout=5000)
                except playwright_timeout_error_cls:
                    pass
                page.wait_for_timeout(250)
        page.locator("#app").wait_for(state="attached", timeout=30000)
        page.wait_for_function("window.__timePollAppMounted === true", timeout=30000)
        page.get_by_role("heading", name="TimePoll").wait_for(timeout=30000)

    def login(
        self,
        *,
        name: str,
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
            normalized_weekdays = {
                value for value in allowed_weekdays if isinstance(value, int) and 0 <= value <= 6
            }
            weekday_inputs = page.locator("#section-panel-create .weekday-item input")
            for index in range(7):
                weekday_inputs.nth(index).set_checked(index in normalized_weekdays)
        page.locator("#section-panel-create button[type='submit']").click()
        page.locator(".details-title").filter(has_text=title).wait_for()

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
        voter_page.locator(".calendar-table tbody tr").first.locator(".vote-switch-option-yes").nth(
            vote_option_index
        ).click()
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

    def normalized_aria_snapshot(self, locator: Any) -> str:
        snapshot = locator.aria_snapshot()
        return "\n".join(line.rstrip() for line in snapshot.strip().splitlines())

    def assert_aria_snapshot_contains(self, locator: Any, *expected_fragments: str) -> str:
        snapshot = self.normalized_aria_snapshot(locator)
        for fragment in expected_fragments:
            self.assertIn(fragment, snapshot, snapshot)
        return snapshot

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
        page.wait_for_function("() => document.querySelectorAll('.bulk-time-trigger').length === 3")

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
                return (
                  poll.start_date === '2026-05-03'
                  && poll.end_date === '2026-05-04'
                  && poll.daily_start_hour === 0
                  && poll.daily_end_hour === 15
                  && Array.isArray(poll.allowed_weekdays)
                  && poll.allowed_weekdays.includes(0)
                  && poll.allowed_weekdays.includes(6)
                  && Array.isArray(poll.options)
                  && poll.options.length === 2
                  && poll.options[0].starts_at === '2026-05-04T00:00:00+00:00'
                  && poll.options[1].starts_at === '2026-05-05T00:00:00+00:00'
                );
              } catch (error) {
                return false;
              }
            }
            """,
            arg=poll_identifier,
        )
