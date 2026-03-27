from __future__ import annotations

import unittest
from typing import TYPE_CHECKING, Optional

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings, tag

from .tests_browser import (
    PLAYWRIGHT_TESTS_AVAILABLE,
    REQUIRE_BROWSER_TESTS,
    axe_runner_factory,
    sync_playwright_fn,
)

if TYPE_CHECKING:
    from playwright.sync_api import Browser, BrowserContext, Page, Playwright


@tag("browser_storyboard")
@override_settings(ALLOWED_HOSTS=["127.0.0.1", "localhost", "testserver", "[::1]"])
class PollStoryboardBrowserTests(StaticLiveServerTestCase):
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

    def require_browser(self) -> "Browser":
        if self.browser is None:
            raise unittest.SkipTest("Playwright browser is not available for this test run.")
        return self.browser

    def create_context_page(self, *, timezone_id: Optional[str] = None) -> "Page":
        browser = self.require_browser()
        kwargs = {"base_url": self.live_server_url}
        if timezone_id:
            kwargs["timezone_id"] = timezone_id
        context = browser.new_context(**kwargs)
        self.addCleanup(context.close)
        page = context.new_page()
        page.set_default_timeout(15000)
        page.set_viewport_size({"width": 1400, "height": 1200})
        return page

    def open_home_page(self, page: "Page", path: str = "/") -> None:
        page.goto(path, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.locator("#app").wait_for(state="visible")
        page.get_by_role("heading", name="TimePoll").wait_for()

    def submit_auth_dialog(self, page: "Page", *, name: str, pin: str) -> None:
        dialog = page.get_by_role("dialog")
        dialog.wait_for()
        page.locator("#auth-name").fill(name)
        page.locator("#auth-pin").fill(pin)
        dialog.locator("button[type='submit']").click()

    def login(
        self,
        page: "Page",
        *,
        name: str,
        pin: str,
        login_button_name: str = "Login",
        logout_button_name: str = "Logout",
    ) -> None:
        page.get_by_role("button", name=login_button_name).click()
        self.submit_auth_dialog(page, name=name, pin=pin)
        page.get_by_role("button", name=logout_button_name, exact=True).wait_for()

    def create_poll(
        self,
        page: "Page",
        *,
        open_button_name: str,
        title: str,
        description: str,
        identifier: str,
        timezone_input: str,
        timezone_selection: Optional[str],
        start_date: str,
        end_date: str,
        daily_start_hour: int,
        daily_end_hour: int,
        allowed_weekdays: list[int],
    ) -> None:
        page.get_by_role("button", name=open_button_name).click()
        page.locator("#poll-title").fill(title)
        page.locator("#poll-description").fill(description)
        page.locator("#poll-identifier").fill(identifier)
        page.locator("#poll-timezone").fill(timezone_input)
        if timezone_selection:
            page.locator("#create-timezone-suggestions").wait_for()
            page.locator("#create-timezone-suggestions .timezone-suggestion").filter(
                has_text=timezone_selection
            ).first.click()
            page.locator("#create-timezone-suggestions").wait_for(state="hidden")
        page.locator("#start-date").fill(start_date)
        page.locator("#end-date").fill(end_date)
        page.locator("#daily-start-hour").select_option(str(daily_start_hour))
        page.locator("#daily-end-hour").select_option(str(daily_end_hour))
        weekday_inputs = page.locator("#section-panel-create .weekday-item input")
        normalized_weekdays = {value for value in allowed_weekdays if isinstance(value, int) and 0 <= value <= 6}
        for index in range(7):
            weekday_inputs.nth(index).set_checked(index in normalized_weekdays)
        page.locator("#section-panel-create button[type='submit']").click()
        page.locator(".details-title").filter(has_text=title).wait_for()

    def edit_poll(
        self,
        page: "Page",
        *,
        edit_button_name: str,
        save_button_name: str,
        description: str,
        daily_end_hour: int,
    ) -> None:
        page.get_by_role("button", name=edit_button_name).click()
        page.locator("#edit-description").fill(description)
        page.locator("#edit-daily-end-hour").select_option(str(daily_end_hour))
        page.get_by_role("button", name=save_button_name).click()

    def row_locator(self, page: "Page", time_label: str):
        return page.locator(".calendar-time-row").filter(has_text=time_label).first.locator("xpath=..")

    def bulk_vote_day(self, page: "Page", day_index: int, label: str) -> None:
        day_header = page.locator(".calendar-day-col").nth(day_index)
        day_header.locator(".bulk-day-trigger").click()
        day_header.locator(".bulk-menu-item").filter(has_text=label).first.click()

    def bulk_vote_row(self, page: "Page", time_label: str, label: str) -> None:
        row = self.row_locator(page, time_label)
        row.locator(".bulk-time-trigger").click()
        row.locator(".bulk-menu-item").filter(has_text=label).first.click()

    def click_vote(self, page: "Page", day_index: int, time_label: str, status: str) -> None:
        row = self.row_locator(page, time_label)
        row.locator("td.calendar-cell").nth(day_index).locator(f".vote-switch-option-{status}").click()

    def wait_for_cell_vote_state(
        self,
        page: "Page",
        *,
        day_index: int,
        time_label: str,
        status: str,
        checked: bool,
    ) -> None:
        expected = "true" if checked else "false"
        page.wait_for_function(
            """
            ([targetDayIndex, targetTimeLabel, targetStatus, expectedState]) => {
              const rows = Array.from(document.querySelectorAll('.calendar-table tbody tr')).filter((row) => {
                const header = row.querySelector('th.calendar-time-row');
                return Boolean(header) && header.textContent.trim() === targetTimeLabel;
              });
              if (!rows.length) {
                return false;
              }
              const cells = rows[0].querySelectorAll('td.calendar-cell');
              const cell = cells[targetDayIndex];
              if (!cell) {
                return false;
              }
              const button = cell.querySelector(`.vote-switch-option-${targetStatus}`);
              return Boolean(button) && button.getAttribute('aria-checked') === expectedState;
            }
            """,
            arg=[day_index, time_label, status, expected],
        )

    def get_cell_option_id(self, page: "Page", *, day_index: int, time_label: str) -> str:
        option_id = page.evaluate(
            """
            ([targetDayIndex, targetTimeLabel]) => {
              const rows = Array.from(document.querySelectorAll('.calendar-table tbody tr')).filter((row) => {
                const header = row.querySelector('th.calendar-time-row');
                return Boolean(header) && header.textContent.trim() === targetTimeLabel;
              });
              if (!rows.length) {
                return '';
              }
              const cell = rows[0].querySelectorAll('td.calendar-cell')[targetDayIndex];
              const button = cell ? cell.querySelector('.vote-switch-option') : null;
              return button ? (button.getAttribute('data-vote-option-id') || '') : '';
            }
            """,
            [day_index, time_label],
        )
        return str(option_id or "")

    def get_cell_group_label(self, page: "Page", *, day_index: int, time_label: str) -> str:
        value = page.evaluate(
            """
            ([targetDayIndex, targetTimeLabel]) => {
              const rows = Array.from(document.querySelectorAll('.calendar-table tbody tr')).filter((row) => {
                const header = row.querySelector('th.calendar-time-row');
                return Boolean(header) && header.textContent.trim() === targetTimeLabel;
              });
              if (!rows.length) {
                return '';
              }
              const cell = rows[0].querySelectorAll('td.calendar-cell')[targetDayIndex];
              const group = cell ? cell.querySelector('.vote-switch') : null;
              return group ? (group.getAttribute('aria-label') || '') : '';
            }
            """,
            [day_index, time_label],
        )
        return str(value or "")

    def active_element_snapshot(self, page: "Page") -> dict[str, str]:
        return page.evaluate(
            """
            () => {
              const element = document.activeElement;
              return {
                id: element?.id || '',
                text: (element?.textContent || '').trim(),
                className: typeof element?.className === 'string' ? element.className : '',
                role: element?.getAttribute?.('role') || '',
                status: element?.getAttribute?.('data-vote-status') || '',
                optionId: element?.getAttribute?.('data-vote-option-id') || ''
              };
            }
            """
        )

    def tab_until(
        self,
        page: "Page",
        *,
        text: str = "",
        element_id: str = "",
        option_id: str = "",
        status: str = "",
        max_steps: int = 200,
    ) -> dict[str, str]:
        for _ in range(max_steps):
            snapshot = self.active_element_snapshot(page)
            if text and snapshot["text"] != text:
                page.keyboard.press("Tab")
                continue
            if element_id and snapshot["id"] != element_id:
                page.keyboard.press("Tab")
                continue
            if option_id and snapshot["optionId"] != option_id:
                page.keyboard.press("Tab")
                continue
            if status and snapshot["status"] != status:
                page.keyboard.press("Tab")
                continue
            if text or element_id or option_id or status:
                return snapshot
            page.keyboard.press("Tab")
        raise AssertionError(
            "Did not reach the requested focus target with keyboard navigation. "
            f"text={text!r} element_id={element_id!r} option_id={option_id!r} status={status!r}"
        )

    def wait_for_vote_switch_count(self, page: "Page", expected_count: int) -> None:
        page.wait_for_function(
            """
            (count) => document.querySelectorAll('.calendar-table tbody .vote-switch').length === count
            """,
            arg=expected_count,
        )

    def wait_for_active_vote_button(self, page: "Page", *, option_id: str, status: str) -> None:
        page.wait_for_function(
            """
            ([targetOptionId, targetStatus]) => {
              const active = document.activeElement;
              return Boolean(active)
                && active.getAttribute('data-vote-option-id') === targetOptionId
                && active.getAttribute('data-vote-status') === targetStatus;
            }
            """,
            arg=[option_id, status],
        )

    def test_storyboard_multitimezone_video_call_flow_can_be_completed_end_to_end(self) -> None:
        title = "Maailmanlaajuinen tiimipuhelu"
        identifier = "global_video_sync"

        aino_page = self.create_context_page(timezone_id="Europe/Helsinki")
        maya_page = self.create_context_page(timezone_id="America/New_York")
        kenji_page = self.create_context_page(timezone_id="Asia/Tokyo")
        leila_page = self.create_context_page(timezone_id="Africa/Nairobi")

        self.open_home_page(aino_page)
        aino_page.locator("#language-select").select_option("fi")
        aino_page.get_by_role("button", name="Kirjaudu").wait_for()
        self.login(
            aino_page,
            name="Aino",
            pin="4826",
            login_button_name="Kirjaudu",
            logout_button_name="Kirjaudu ulos",
        )
        self.create_poll(
            aino_page,
            open_button_name="Luo uusi kysely",
            title=title,
            description="Sovitaan ensi viikon videopuhelu. Valitse kaikki ajat, jotka sopivat varmasti tai ehka.",
            identifier=identifier,
            timezone_input="europe/hel",
            timezone_selection="Europe/Helsinki",
            start_date="2026-03-30",
            end_date="2026-04-05",
            daily_start_hour=15,
            daily_end_hour=20,
            allowed_weekdays=[0, 1, 2, 3, 4],
        )
        self.assertIn("id=global_video_sync", aino_page.url)

        self.edit_poll(
            aino_page,
            edit_button_name="Muokkaa kyselyä",
            save_button_name="Tallenna muutokset",
            description=(
                "Sovitaan ensi viikon videopuhelu. Merkitse kaikki varmasti sopivat ajat "
                "Kyllä-vastauksella ja epävarmat Ehkä-vastauksella."
            ),
            daily_end_hour=21,
        )
        aino_page.get_by_role("status").filter(has_text="Kysely päivitetty.").wait_for()
        self.assertEqual(aino_page.get_by_role("button", name="Poista kysely").count(), 0)

        self.bulk_vote_day(aino_page, 3, "Ehkä")
        self.bulk_vote_row(aino_page, "16:00", "Kyllä")
        self.click_vote(aino_page, 0, "16:00", "no")
        self.wait_for_cell_vote_state(aino_page, day_index=0, time_label="16:00", status="no", checked=True)
        self.click_vote(aino_page, 3, "18:00", "maybe")
        self.wait_for_cell_vote_state(aino_page, day_index=3, time_label="18:00", status="maybe", checked=False)
        self.wait_for_cell_vote_state(aino_page, day_index=3, time_label="16:00", status="yes", checked=True)

        self.open_home_page(maya_page, f"/?id={identifier}")
        self.login(maya_page, name="Maya", pin="9035")
        maya_page.locator(".details-title").filter(has_text=title).wait_for()
        maya_page.locator(".calendar-timezone-mode-item").filter(has_text="Browser timezone").click()
        maya_page.locator(".calendar-time-row").filter(has_text="09:00").first.wait_for()
        self.click_vote(maya_page, 3, "09:00", "yes")
        self.wait_for_cell_vote_state(maya_page, day_index=3, time_label="09:00", status="yes", checked=True)
        self.bulk_vote_row(maya_page, "10:00", "Maybe")
        self.click_vote(maya_page, 2, "10:00", "no")
        self.wait_for_cell_vote_state(maya_page, day_index=2, time_label="10:00", status="no", checked=True)
        self.click_vote(maya_page, 3, "11:00", "maybe")
        self.wait_for_cell_vote_state(maya_page, day_index=3, time_label="11:00", status="maybe", checked=True)
        maya_page.locator(".auth-name-link").click()
        maya_page.get_by_role("heading", name="My data").wait_for()
        yes_vote_item = maya_page.locator("#section-panel-profile .profile-item").filter(has_text="My vote: Yes").first
        yes_vote_item.wait_for()
        yes_vote_item.get_by_role("button", name="Delete vote").click()
        maya_page.get_by_role("status").filter(has_text="Vote deleted.").wait_for()
        maya_page.get_by_role("button", name="Open poll").first.click()
        maya_page.locator(".details-title").filter(has_text=title).wait_for()
        self.click_vote(maya_page, 3, "09:00", "yes")
        self.wait_for_cell_vote_state(maya_page, day_index=3, time_label="09:00", status="yes", checked=True)

        self.open_home_page(kenji_page, f"/?id={identifier}")
        self.login(kenji_page, name="Kenji", pin="1174")
        kenji_page.locator(".details-title").filter(has_text=title).wait_for()
        kenji_page.locator(".calendar-timezone-mode-item-custom").click()
        kenji_page.locator("#calendar-timezone").fill("asia/tok")
        kenji_page.locator("#calendar-timezone-suggestions").wait_for()
        kenji_page.locator("#calendar-timezone-suggestions .timezone-suggestion").filter(
            has_text="Asia/Tokyo"
        ).first.click()
        kenji_page.locator(".calendar-time-row").filter(has_text="22:00").first.wait_for()
        self.bulk_vote_day(kenji_page, 3, "No")
        self.click_vote(kenji_page, 3, "22:00", "yes")
        self.wait_for_cell_vote_state(kenji_page, day_index=3, time_label="22:00", status="yes", checked=True)
        self.click_vote(kenji_page, 3, "23:00", "maybe")
        self.wait_for_cell_vote_state(kenji_page, day_index=3, time_label="23:00", status="maybe", checked=True)

        self.open_home_page(leila_page, f"/?id={identifier}")
        self.tab_until(leila_page, text="Login")
        leila_page.keyboard.press("Enter")
        leila_page.get_by_role("dialog").wait_for()
        self.assertEqual(self.active_element_snapshot(leila_page)["id"], "auth-name")
        leila_page.locator("#auth-name").fill("Leila")
        leila_page.locator("#auth-pin").fill("5512")
        leila_page.keyboard.press("Enter")
        leila_page.get_by_role("dialog").wait_for(state="hidden")
        leila_page.locator(".details-title").filter(has_text=title).wait_for()
        group_label = self.get_cell_group_label(leila_page, day_index=3, time_label="16:00")
        self.assertTrue(group_label)
        self.assertIn("16:00", group_label)

        thursday_trigger_id = leila_page.locator(".bulk-day-trigger").nth(3).get_attribute("id")
        self.assertTrue(thursday_trigger_id)
        self.tab_until(leila_page, element_id=thursday_trigger_id or "")
        leila_page.keyboard.press("Enter")
        self.assertEqual(self.active_element_snapshot(leila_page)["text"], "No vote")
        leila_page.keyboard.press("ArrowDown")
        leila_page.keyboard.press("ArrowDown")
        leila_page.keyboard.press("ArrowDown")
        self.assertEqual(self.active_element_snapshot(leila_page)["text"], "Maybe")
        leila_page.keyboard.press("Enter")
        self.assertEqual(self.active_element_snapshot(leila_page)["id"], thursday_trigger_id)

        leila_1600_option_id = self.get_cell_option_id(leila_page, day_index=3, time_label="16:00")
        self.assertTrue(leila_1600_option_id)
        self.tab_until(leila_page, option_id=leila_1600_option_id, status="maybe")
        leila_page.keyboard.press("ArrowLeft")
        self.wait_for_cell_vote_state(leila_page, day_index=3, time_label="16:00", status="yes", checked=True)
        self.wait_for_active_vote_button(leila_page, option_id=leila_1600_option_id, status="yes")
        self.assertEqual(self.active_element_snapshot(leila_page)["status"], "yes")

        leila_1800_option_id = self.get_cell_option_id(leila_page, day_index=3, time_label="18:00")
        self.assertTrue(leila_1800_option_id)
        self.tab_until(leila_page, option_id=leila_1800_option_id, status="maybe")
        leila_page.keyboard.press("ArrowRight")
        self.wait_for_cell_vote_state(leila_page, day_index=3, time_label="18:00", status="no", checked=True)
        self.wait_for_active_vote_button(leila_page, option_id=leila_1800_option_id, status="no")

        aino_page.reload(wait_until="domcontentloaded")
        aino_page.wait_for_load_state("networkidle")
        aino_page.locator(".details-title").filter(has_text=title).wait_for()
        aino_page.locator(".calendar-vote-mode-item").filter(has_text="Tulostila").click()
        aino_page.locator("#min-yes-filter").select_option("4")
        self.wait_for_vote_switch_count(aino_page, 1)
        self.assertEqual(aino_page.locator(".bulk-time-trigger").first.inner_text().strip(), "16:00")
        self.assertEqual(aino_page.locator(".vote-switch-option-yes .vote-switch-count").first.inner_text(), "4")
        self.assertEqual(aino_page.get_by_role("button", name="Poista kysely").count(), 0)

        aino_page.get_by_role("button", name="Sulje kysely").click()
        aino_page.get_by_text("Kysely on suljettu").first.wait_for()
        self.assertEqual(aino_page.get_by_role("button", name="Poista kysely").count(), 1)

        maya_page.reload(wait_until="domcontentloaded")
        maya_page.wait_for_load_state("networkidle")
        maya_page.get_by_text("Poll is closed").first.wait_for()
        self.assertTrue(maya_page.locator(".vote-switch-option-yes").first.is_disabled())

        aino_page.on("dialog", lambda dialog: dialog.accept())
        aino_page.get_by_role("button", name="Poista kysely").click()
        aino_page.get_by_role("heading", name="Kyselyt").wait_for()
        self.assertEqual(aino_page.locator(".poll-item").filter(has_text=title).count(), 0)

        maya_page.goto(f"/?id={identifier}", wait_until="domcontentloaded")
        maya_page.wait_for_load_state("networkidle")
        maya_page.wait_for_function("() => !window.location.search.includes('id=')")
        maya_page.get_by_role("heading", name="Polls").wait_for()

    def test_storyboard_keyboard_and_screen_reader_user_can_vote_with_keyboard_only(self) -> None:
        title = "Accessible storyboard poll"
        identifier = "accessible_storyboard_poll"

        owner_page = self.create_context_page(timezone_id="Europe/Helsinki")
        leila_page = self.create_context_page(timezone_id="Africa/Nairobi")

        self.open_home_page(owner_page)
        self.login(owner_page, name="Owner", pin="4826")
        self.create_poll(
            owner_page,
            open_button_name="Create new poll",
            title=title,
            description="Created to verify the storyboard keyboard and screen reader path.",
            identifier=identifier,
            timezone_input="europe/hel",
            timezone_selection="Europe/Helsinki",
            start_date="2026-03-30",
            end_date="2026-04-05",
            daily_start_hour=15,
            daily_end_hour=20,
            allowed_weekdays=[0, 1, 2, 3, 4],
        )

        self.open_home_page(leila_page, f"/?id={identifier}")
        self.tab_until(leila_page, text="Login")
        leila_page.keyboard.press("Enter")
        leila_page.get_by_role("dialog").wait_for()
        self.assertEqual(self.active_element_snapshot(leila_page)["id"], "auth-name")
        leila_page.locator("#auth-name").fill("LeilaKeyboard")
        leila_page.locator("#auth-pin").fill("5512")
        leila_page.keyboard.press("Enter")
        leila_page.get_by_role("dialog").wait_for(state="hidden")
        leila_page.locator(".details-title").filter(has_text=title).wait_for()

        group_label = self.get_cell_group_label(leila_page, day_index=3, time_label="16:00")
        self.assertTrue(group_label)
        self.assertIn("16:00", group_label)

        thursday_trigger_id = leila_page.locator(".bulk-day-trigger").nth(3).get_attribute("id")
        self.assertTrue(thursday_trigger_id)
        self.tab_until(leila_page, element_id=thursday_trigger_id or "")
        leila_page.keyboard.press("Enter")
        self.assertEqual(self.active_element_snapshot(leila_page)["text"], "No vote")
        leila_page.keyboard.press("ArrowDown")
        leila_page.keyboard.press("ArrowDown")
        leila_page.keyboard.press("ArrowDown")
        self.assertEqual(self.active_element_snapshot(leila_page)["text"], "Maybe")
        leila_page.keyboard.press("Enter")
        self.assertEqual(self.active_element_snapshot(leila_page)["id"], thursday_trigger_id)

        leila_1600_option_id = self.get_cell_option_id(leila_page, day_index=3, time_label="16:00")
        self.assertTrue(leila_1600_option_id)
        self.tab_until(leila_page, option_id=leila_1600_option_id, status="maybe")
        leila_page.keyboard.press("ArrowLeft")
        self.wait_for_cell_vote_state(leila_page, day_index=3, time_label="16:00", status="yes", checked=True)
        self.wait_for_active_vote_button(leila_page, option_id=leila_1600_option_id, status="yes")
        self.assertEqual(self.active_element_snapshot(leila_page)["status"], "yes")

        leila_1800_option_id = self.get_cell_option_id(leila_page, day_index=3, time_label="18:00")
        self.assertTrue(leila_1800_option_id)
        self.tab_until(leila_page, option_id=leila_1800_option_id, status="maybe")
        leila_page.keyboard.press("ArrowRight")
        self.wait_for_cell_vote_state(leila_page, day_index=3, time_label="18:00", status="no", checked=True)
        self.wait_for_active_vote_button(leila_page, option_id=leila_1800_option_id, status="no")
