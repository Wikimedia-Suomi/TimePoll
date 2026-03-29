from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any, TypedDict, cast
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase
from hypothesis import given
from hypothesis import settings as hypothesis_settings
from hypothesis import strategies as st

from .models import Poll
from .views import FIXED_SLOT_MINUTES, generate_poll_options, poll_start_end_dates

PROPERTY_TEST_SETTINGS = hypothesis_settings(deadline=None, max_examples=60)
CURATED_TIMEZONES = (
    "UTC",
    "Europe/Helsinki",
    "America/New_York",
    "Pacific/Honolulu",
    "Asia/Kathmandu",
    "Australia/Sydney",
)


class TimezoneAwareSchedule(TypedDict):
    start_date: date
    end_date: date
    daily_start_hour: int
    daily_end_hour: int
    allowed_weekdays: list[int]
    timezone_name: str


@st.composite
def timezone_aware_schedule_payloads(draw: st.DrawFn) -> TimezoneAwareSchedule:
    start_date = draw(st.dates(min_value=date(2026, 1, 1), max_value=date(2026, 12, 10)))
    day_span = draw(st.integers(min_value=0, max_value=21))
    daily_start_hour = draw(st.integers(min_value=0, max_value=23))
    daily_end_hour = draw(st.integers(min_value=daily_start_hour + 1, max_value=24))
    guaranteed_offset = draw(st.integers(min_value=0, max_value=day_span))
    guaranteed_weekday = (start_date + timedelta(days=guaranteed_offset)).weekday()
    extra_weekdays = draw(st.sets(st.integers(min_value=0, max_value=6), max_size=6))
    allowed_weekdays = sorted(set(extra_weekdays) | {guaranteed_weekday})
    timezone_name = draw(st.sampled_from(CURATED_TIMEZONES))
    return {
        "start_date": start_date,
        "end_date": start_date + timedelta(days=day_span),
        "daily_start_hour": daily_start_hour,
        "daily_end_hour": daily_end_hour,
        "allowed_weekdays": allowed_weekdays,
        "timezone_name": timezone_name,
    }


class TimezonePropertyTests(SimpleTestCase):
    @PROPERTY_TEST_SETTINGS
    @given(timezone_aware_schedule_payloads())
    def test_generate_poll_options_preserves_invariants_across_curated_timezones(
        self,
        schedule: TimezoneAwareSchedule,
    ) -> None:
        options = generate_poll_options(cast(dict[str, Any], schedule))
        timezone_info = ZoneInfo(schedule["timezone_name"])
        start_date = schedule["start_date"]
        end_date = schedule["end_date"]
        daily_start_hour = schedule["daily_start_hour"]
        daily_end_hour = schedule["daily_end_hour"]
        allowed_weekdays = schedule["allowed_weekdays"]

        matching_days = sum(
            1
            for offset in range((end_date - start_date).days + 1)
            if (start_date + timedelta(days=offset)).weekday() in allowed_weekdays
        )
        self.assertEqual(len(options), matching_days * (daily_end_hour - daily_start_hour))

        previous_start = None
        seen_starts: set[datetime] = set()
        for option in options:
            starts_at = option["starts_at"]
            ends_at = option["ends_at"]

            local_start = starts_at.astimezone(timezone_info)
            local_end = ends_at.astimezone(timezone_info)

            self.assertEqual(ends_at - starts_at, timedelta(minutes=FIXED_SLOT_MINUTES))
            self.assertEqual(local_start.minute, 0)
            self.assertEqual(local_end.minute, 0)
            self.assertEqual(local_start.second, 0)
            self.assertEqual(local_end.second, 0)
            self.assertGreaterEqual(local_start.date(), start_date)
            self.assertLessEqual(local_start.date(), end_date)
            self.assertIn(local_start.weekday(), allowed_weekdays)
            self.assertGreaterEqual(local_start.hour, daily_start_hour)

            if daily_end_hour == 24 and local_end.date() > local_start.date():
                self.assertEqual(local_start.hour, 23)
                self.assertEqual(local_end.hour, 0)
            else:
                self.assertEqual(local_start.date(), local_end.date())
                self.assertLessEqual(local_end.hour, daily_end_hour)

            if previous_start is not None:
                self.assertGreaterEqual(starts_at, previous_start)
            self.assertNotIn(starts_at, seen_starts)
            seen_starts.add(starts_at)
            previous_start = starts_at

    @PROPERTY_TEST_SETTINGS
    @given(timezone_aware_schedule_payloads())
    def test_poll_start_end_dates_round_trip_schedule_window_across_curated_timezones(
        self,
        schedule: TimezoneAwareSchedule,
    ) -> None:
        timezone_info = ZoneInfo(schedule["timezone_name"])
        poll = Poll(
            title="Round-trip timezone poll",
            window_starts_at=datetime.combine(schedule["start_date"], time.min, tzinfo=timezone_info),
            window_ends_at=datetime.combine(
                schedule["end_date"] + timedelta(days=1),
                time.min,
                tzinfo=timezone_info,
            ),
            timezone_name=schedule["timezone_name"],
        )

        self.assertEqual(
            poll_start_end_dates(poll),
            {
                "start_date": schedule["start_date"].isoformat(),
                "end_date": schedule["end_date"].isoformat(),
            },
        )
