from __future__ import annotations

import string
from datetime import date, timedelta
from typing import NoReturn
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase
from hypothesis import given
from hypothesis import settings as hypothesis_settings
from hypothesis import strategies as st

from .views import (
    FIXED_SLOT_MINUTES,
    IDENTIFIER_MAX_LENGTH,
    APIError,
    generate_poll_options,
    parse_allowed_weekdays,
    validate_poll_identifier,
)

PROPERTY_TEST_SETTINGS = hypothesis_settings(deadline=None, max_examples=60)
IDENTIFIER_ALPHABET = string.ascii_letters + string.digits + "_"
WHITESPACE_ALPHABET = " \t\n\r"


def fail_type_expectation(name: str, value: object, expected: str) -> NoReturn:
    raise AssertionError(f"{name} should be {expected}, got {type(value).__name__}")


@st.composite
def valid_schedule_payloads(draw: st.DrawFn) -> dict[str, object]:
    start_date = draw(st.dates(min_value=date(2026, 1, 1), max_value=date(2026, 12, 10)))
    day_span = draw(st.integers(min_value=0, max_value=21))
    daily_start_hour = draw(st.integers(min_value=0, max_value=23))
    daily_end_hour = draw(st.integers(min_value=daily_start_hour + 1, max_value=24))
    guaranteed_offset = draw(st.integers(min_value=0, max_value=day_span))
    guaranteed_weekday = (start_date + timedelta(days=guaranteed_offset)).weekday()
    extra_weekdays = draw(st.sets(st.integers(min_value=0, max_value=6), max_size=6))
    allowed_weekdays = sorted(set(extra_weekdays) | {guaranteed_weekday})
    return {
        "start_date": start_date,
        "end_date": start_date + timedelta(days=day_span),
        "daily_start_hour": daily_start_hour,
        "daily_end_hour": daily_end_hour,
        "allowed_weekdays": allowed_weekdays,
        "timezone_name": "UTC",
    }


@st.composite
def invalid_identifier_values(draw: st.DrawFn) -> str:
    prefix = draw(st.text(alphabet=IDENTIFIER_ALPHABET, max_size=20))
    suffix = draw(st.text(alphabet=IDENTIFIER_ALPHABET, max_size=20))
    bad_character = draw(st.sampled_from(["-", ".", "!", "/", ":", "@"]))
    left_padding = draw(st.text(alphabet=WHITESPACE_ALPHABET, max_size=2))
    right_padding = draw(st.text(alphabet=WHITESPACE_ALPHABET, max_size=2))
    return f"{left_padding}{prefix}{bad_character}{suffix}{right_padding}"


class PollPropertyTests(SimpleTestCase):
    @PROPERTY_TEST_SETTINGS
    @given(st.lists(st.integers(min_value=0, max_value=6), min_size=1, max_size=21))
    def test_parse_allowed_weekdays_sorts_and_deduplicates(self, weekdays: list[int]) -> None:
        parsed = parse_allowed_weekdays(weekdays)
        self.assertEqual(parsed, sorted(set(weekdays)))

    @PROPERTY_TEST_SETTINGS
    @given(st.one_of(st.booleans(), st.integers(max_value=-1), st.integers(min_value=7), st.text(), st.none()))
    def test_parse_allowed_weekdays_rejects_invalid_items(self, bad_item: object) -> None:
        with self.assertRaises(APIError) as exc_context:
            parse_allowed_weekdays([bad_item])
        self.assertEqual(exc_context.exception.code, "invalid_weekdays")

    @PROPERTY_TEST_SETTINGS
    @given(
        identifier=st.text(
            alphabet=IDENTIFIER_ALPHABET,
            min_size=1,
            max_size=IDENTIFIER_MAX_LENGTH,
        ),
        left_padding=st.text(alphabet=WHITESPACE_ALPHABET, max_size=3),
        right_padding=st.text(alphabet=WHITESPACE_ALPHABET, max_size=3),
    )
    def test_validate_poll_identifier_accepts_allowed_values(
        self,
        identifier: str,
        left_padding: str,
        right_padding: str,
    ) -> None:
        parsed = validate_poll_identifier(f"{left_padding}{identifier}{right_padding}")
        self.assertEqual(parsed, identifier)

    @PROPERTY_TEST_SETTINGS
    @given(st.text(alphabet=WHITESPACE_ALPHABET, min_size=1, max_size=20))
    def test_validate_poll_identifier_treats_blank_strings_as_missing(self, raw_value: str) -> None:
        self.assertIsNone(validate_poll_identifier(raw_value))

    @PROPERTY_TEST_SETTINGS
    @given(invalid_identifier_values())
    def test_validate_poll_identifier_rejects_disallowed_characters(self, raw_value: str) -> None:
        with self.assertRaises(APIError) as exc_context:
            validate_poll_identifier(raw_value)
        self.assertEqual(exc_context.exception.code, "invalid_poll_identifier")

    @PROPERTY_TEST_SETTINGS
    @given(st.text(alphabet=IDENTIFIER_ALPHABET, min_size=IDENTIFIER_MAX_LENGTH + 1, max_size=120))
    def test_validate_poll_identifier_rejects_too_long_values(self, raw_value: str) -> None:
        with self.assertRaises(APIError) as exc_context:
            validate_poll_identifier(raw_value)
        self.assertEqual(exc_context.exception.code, "invalid_poll_identifier")

    @PROPERTY_TEST_SETTINGS
    @given(valid_schedule_payloads())
    def test_generate_poll_options_preserves_schedule_invariants(
        self,
        schedule: dict[str, object],
    ) -> None:
        options = generate_poll_options(schedule)
        timezone_info = ZoneInfo("UTC")
        start_date = schedule["start_date"]
        end_date = schedule["end_date"]
        daily_start_hour = schedule["daily_start_hour"]
        daily_end_hour = schedule["daily_end_hour"]
        allowed_weekdays = schedule["allowed_weekdays"]

        if not isinstance(start_date, date):
            fail_type_expectation("start_date", start_date, "date")
        if not isinstance(end_date, date):
            fail_type_expectation("end_date", end_date, "date")
        if not isinstance(daily_start_hour, int):
            fail_type_expectation("daily_start_hour", daily_start_hour, "int")
        if not isinstance(daily_end_hour, int):
            fail_type_expectation("daily_end_hour", daily_end_hour, "int")
        if not isinstance(allowed_weekdays, list):
            fail_type_expectation("allowed_weekdays", allowed_weekdays, "list")

        matching_days = sum(
            1
            for offset in range((end_date - start_date).days + 1)
            if (start_date + timedelta(days=offset)).weekday() in allowed_weekdays
        )
        self.assertEqual(len(options), matching_days * (daily_end_hour - daily_start_hour))

        previous_start = None
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
            previous_start = starts_at
