from __future__ import annotations

from datetime import datetime
from typing import Any, TypedDict
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase

from .models import Poll
from .views import generate_poll_options, parse_poll_payload, poll_start_end_dates


class ScheduleGoldenCase(TypedDict):
    name: str
    overrides: dict[str, Any]
    expected_pairs: list[tuple[str, str]]


class ProjectionGoldenCase(TypedDict):
    name: str
    window_starts_at: datetime
    window_ends_at: datetime
    timezone_name: str
    expected_dates: dict[str, str]


class TimezoneGoldenCaseTests(SimpleTestCase):
    def make_schedule(self, **overrides: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "title": "Timezone golden case poll",
            "description": "Locks current backend timezone behavior.",
            "start_date": "2026-05-03",
            "end_date": "2026-05-03",
            "daily_start_hour": 9,
            "daily_end_hour": 17,
            "allowed_weekdays": [6],
            "timezone": "UTC",
        }
        payload.update(overrides)
        return parse_poll_payload(payload)

    def assert_option_pairs(
        self,
        schedule: dict[str, Any],
        expected_pairs: list[tuple[str, str]],
    ) -> None:
        options = generate_poll_options(schedule)
        actual_pairs = [
            (option["starts_at"].isoformat(), option["ends_at"].isoformat())
            for option in options
        ]
        self.assertEqual(actual_pairs, expected_pairs)

    def test_generate_poll_options_matches_current_golden_cases(self) -> None:
        cases: list[ScheduleGoldenCase] = [
            {
                "name": "utc_simple_workday",
                "overrides": {
                    "daily_start_hour": 9,
                    "daily_end_hour": 12,
                },
                "expected_pairs": [
                    ("2026-05-03T09:00:00+00:00", "2026-05-03T10:00:00+00:00"),
                    ("2026-05-03T10:00:00+00:00", "2026-05-03T11:00:00+00:00"),
                    ("2026-05-03T11:00:00+00:00", "2026-05-03T12:00:00+00:00"),
                ],
            },
            {
                "name": "honolulu_crosses_utc_date_boundary",
                "overrides": {
                    "timezone": "Pacific/Honolulu",
                    "daily_start_hour": 14,
                    "daily_end_hour": 15,
                },
                "expected_pairs": [
                    ("2026-05-03T14:00:00-10:00", "2026-05-03T15:00:00-10:00"),
                ],
            },
            {
                "name": "helsinki_spring_forward_preserves_current_sequence",
                "overrides": {
                    "start_date": "2026-03-29",
                    "end_date": "2026-03-29",
                    "daily_start_hour": 2,
                    "daily_end_hour": 5,
                    "timezone": "Europe/Helsinki",
                },
                "expected_pairs": [
                    ("2026-03-29T02:00:00+02:00", "2026-03-29T03:00:00+02:00"),
                    ("2026-03-29T03:00:00+02:00", "2026-03-29T04:00:00+03:00"),
                    ("2026-03-29T04:00:00+03:00", "2026-03-29T05:00:00+03:00"),
                ],
            },
            {
                "name": "helsinki_fall_back_preserves_current_sequence",
                "overrides": {
                    "start_date": "2026-10-25",
                    "end_date": "2026-10-25",
                    "daily_start_hour": 2,
                    "daily_end_hour": 5,
                    "allowed_weekdays": [6],
                    "timezone": "Europe/Helsinki",
                },
                "expected_pairs": [
                    ("2026-10-25T02:00:00+03:00", "2026-10-25T03:00:00+03:00"),
                    ("2026-10-25T03:00:00+03:00", "2026-10-25T04:00:00+02:00"),
                    ("2026-10-25T04:00:00+02:00", "2026-10-25T05:00:00+02:00"),
                ],
            },
            {
                "name": "kathmandu_preserves_45_minute_offset",
                "overrides": {
                    "timezone": "Asia/Kathmandu",
                    "daily_start_hour": 9,
                    "daily_end_hour": 11,
                },
                "expected_pairs": [
                    ("2026-05-03T09:00:00+05:45", "2026-05-03T10:00:00+05:45"),
                    ("2026-05-03T10:00:00+05:45", "2026-05-03T11:00:00+05:45"),
                ],
            },
        ]

        for case in cases:
            with self.subTest(case=case["name"]):
                schedule = self.make_schedule(**case["overrides"])
                self.assert_option_pairs(schedule, case["expected_pairs"])

    def test_generate_poll_options_keeps_full_honolulu_day_contract(self) -> None:
        schedule = self.make_schedule(
            timezone="Pacific/Honolulu",
            daily_start_hour=0,
            daily_end_hour=24,
        )

        options = generate_poll_options(schedule)

        self.assertEqual(len(options), 24)
        self.assertEqual(
            options[0]["starts_at"].isoformat(),
            "2026-05-03T00:00:00-10:00",
        )
        self.assertEqual(
            options[0]["ends_at"].isoformat(),
            "2026-05-03T01:00:00-10:00",
        )
        self.assertEqual(
            options[-1]["starts_at"].isoformat(),
            "2026-05-03T23:00:00-10:00",
        )
        self.assertEqual(
            options[-1]["ends_at"].isoformat(),
            "2026-05-04T00:00:00-10:00",
        )

    def test_poll_start_end_dates_match_current_projection_cases(self) -> None:
        cases: list[ProjectionGoldenCase] = [
            {
                "name": "utc_same_day",
                "window_starts_at": datetime(2026, 5, 3, 0, 0, tzinfo=ZoneInfo("UTC")),
                "window_ends_at": datetime(2026, 5, 4, 0, 0, tzinfo=ZoneInfo("UTC")),
                "timezone_name": "UTC",
                "expected_dates": {"start_date": "2026-05-03", "end_date": "2026-05-03"},
            },
            {
                "name": "honolulu_projects_back_to_previous_local_day",
                "window_starts_at": datetime(2026, 5, 4, 0, 0, tzinfo=ZoneInfo("UTC")),
                "window_ends_at": datetime(2026, 5, 4, 1, 0, tzinfo=ZoneInfo("UTC")),
                "timezone_name": "Pacific/Honolulu",
                "expected_dates": {"start_date": "2026-05-03", "end_date": "2026-05-03"},
            },
            {
                "name": "kathmandu_keeps_local_day_boundaries",
                "window_starts_at": datetime(2026, 5, 3, 18, 15, tzinfo=ZoneInfo("UTC")),
                "window_ends_at": datetime(2026, 5, 4, 18, 15, tzinfo=ZoneInfo("UTC")),
                "timezone_name": "Asia/Kathmandu",
                "expected_dates": {"start_date": "2026-05-04", "end_date": "2026-05-04"},
            },
            {
                "name": "helsinki_spring_forward_day_projects_back_correctly",
                "window_starts_at": datetime(2026, 3, 28, 22, 0, tzinfo=ZoneInfo("UTC")),
                "window_ends_at": datetime(2026, 3, 29, 21, 0, tzinfo=ZoneInfo("UTC")),
                "timezone_name": "Europe/Helsinki",
                "expected_dates": {"start_date": "2026-03-29", "end_date": "2026-03-29"},
            },
        ]

        for case in cases:
            with self.subTest(case=case["name"]):
                poll = Poll(
                    title=case["name"],
                    window_starts_at=case["window_starts_at"],
                    window_ends_at=case["window_ends_at"],
                    timezone_name=case["timezone_name"],
                )
                self.assertEqual(poll_start_end_dates(poll), case["expected_dates"])
