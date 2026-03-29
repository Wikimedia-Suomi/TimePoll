import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from django.contrib.sessions.models import Session
from django.db import IntegrityError
from django.http import Http404, HttpResponse
from django.test import Client, RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse

from timepoll.security import (
    CONTENT_SECURITY_POLICY,
    WIKIMEDIA_VUE_CDN_INTEGRITY,
    WIKIMEDIA_VUE_CDN_URL,
    ContentSecurityPolicyMiddleware,
)

from .models import Identity, Poll, PollVote
from .views import (
    SESSION_IDENTITY_KEY,
    generate_poll_options,
    index,
    parse_poll_payload,
    poll_close,
    poll_detail,
    poll_reopen,
    poll_start_end_dates,
    poll_vote_delete,
    poll_votes_upsert,
)


class SecurityHeaderTests(SimpleTestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()

    def test_index_sets_strict_content_security_policy_header(self):
        middleware = ContentSecurityPolicyMiddleware(lambda request: HttpResponse("ok"))
        response = middleware(self.factory.get(reverse("polls:index")))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("Content-Security-Policy"),
            CONTENT_SECURITY_POLICY,
        )

    def test_index_uses_sri_for_wikimedia_vue_cdn(self):
        request = self.factory.get(reverse("polls:index"))
        template_source = (
            Path(__file__).resolve().parent / "templates" / "polls" / "index.html"
        ).read_text(encoding="utf-8")

        with patch("polls.views.render", return_value=HttpResponse("ok")) as render_mock:
            response = index(request)

        self.assertEqual(response.status_code, 200)
        render_mock.assert_called_once()
        self.assertEqual(render_mock.call_args.args[1], "polls/index.html")
        self.assertEqual(
            render_mock.call_args.args[2],
            {
                "vue_cdn_url": WIKIMEDIA_VUE_CDN_URL,
                "vue_cdn_integrity": WIKIMEDIA_VUE_CDN_INTEGRITY,
            },
        )
        self.assertIn('src="{{ vue_cdn_url }}"', template_source)
        self.assertIn('integrity="{{ vue_cdn_integrity }}"', template_source)
        self.assertIn('crossorigin="anonymous"', template_source)


class PollScheduleLogicTests(SimpleTestCase):
    def make_schedule(self, **overrides: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "title": "Schedule logic poll",
            "description": "Used for pure schedule unit tests.",
            "start_date": "2026-05-03",
            "end_date": "2026-05-03",
            "daily_start_hour": 9,
            "daily_end_hour": 17,
            "allowed_weekdays": [6],
            "timezone": "Pacific/Honolulu",
        }
        payload.update(overrides)
        return parse_poll_payload(payload)

    def test_generate_poll_options_maps_local_honolulu_slot_to_expected_utc_slot(self) -> None:
        schedule = self.make_schedule(
            daily_start_hour=14,
            daily_end_hour=15,
        )

        options = generate_poll_options(schedule)

        self.assertEqual(len(options), 1)
        self.assertEqual(
            options[0]["starts_at"].astimezone(ZoneInfo("UTC")).isoformat(),
            "2026-05-04T00:00:00+00:00",
        )
        self.assertEqual(
            options[0]["ends_at"].astimezone(ZoneInfo("UTC")).isoformat(),
            "2026-05-04T01:00:00+00:00",
        )

    def test_generate_poll_options_keeps_full_honolulu_day_as_utc_span_across_two_dates(self) -> None:
        schedule = self.make_schedule(
            daily_start_hour=0,
            daily_end_hour=24,
        )

        options = generate_poll_options(schedule)

        self.assertEqual(len(options), 24)
        self.assertEqual(
            options[0]["starts_at"].astimezone(ZoneInfo("UTC")).isoformat(),
            "2026-05-03T10:00:00+00:00",
        )
        self.assertEqual(
            options[-1]["starts_at"].astimezone(ZoneInfo("UTC")).isoformat(),
            "2026-05-04T09:00:00+00:00",
        )

    def test_poll_start_end_dates_projects_utc_window_back_to_poll_timezone(self) -> None:
        poll = Poll(
            title="Projected timezone poll",
            window_starts_at=datetime(2026, 5, 4, 0, 0, tzinfo=ZoneInfo("UTC")),
            window_ends_at=datetime(2026, 5, 4, 1, 0, tzinfo=ZoneInfo("UTC")),
            timezone_name="Pacific/Honolulu",
        )

        self.assertEqual(
            poll_start_end_dates(poll),
            {"start_date": "2026-05-03", "end_date": "2026-05-03"},
        )

    def test_generate_poll_options_preserves_current_dst_spring_forward_sequence(self) -> None:
        schedule = self.make_schedule(
            start_date="2026-03-29",
            end_date="2026-03-29",
            daily_start_hour=2,
            daily_end_hour=5,
            timezone="Europe/Helsinki",
        )

        options = generate_poll_options(schedule)

        self.assertEqual(
            [(item["starts_at"].isoformat(), item["ends_at"].isoformat()) for item in options],
            [
                ("2026-03-29T02:00:00+02:00", "2026-03-29T03:00:00+02:00"),
                ("2026-03-29T03:00:00+02:00", "2026-03-29T04:00:00+03:00"),
                ("2026-03-29T04:00:00+03:00", "2026-03-29T05:00:00+03:00"),
            ],
        )

    def test_generate_poll_options_preserves_current_dst_fall_back_sequence(self) -> None:
        schedule = self.make_schedule(
            start_date="2026-10-25",
            end_date="2026-10-25",
            daily_start_hour=2,
            daily_end_hour=5,
            timezone="Europe/Helsinki",
        )

        options = generate_poll_options(schedule)

        self.assertEqual(
            [(item["starts_at"].isoformat(), item["ends_at"].isoformat()) for item in options],
            [
                ("2026-10-25T02:00:00+03:00", "2026-10-25T03:00:00+03:00"),
                ("2026-10-25T03:00:00+03:00", "2026-10-25T04:00:00+02:00"),
                ("2026-10-25T04:00:00+02:00", "2026-10-25T05:00:00+02:00"),
            ],
        )


class PollApiTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.other_client = Client()
        self.factory = RequestFactory()

    def login(self, client: Client, name: str, pin: str = "1234"):
        return client.post(
            reverse("polls:login_identity"),
            data=json.dumps({"name": name, "pin": pin}),
            content_type="application/json",
        )

    def create_poll(self, client: Client):
        return client.post(
            reverse("polls:polls_collection"),
            data=json.dumps(
                {
                    "title": "Sprint planning",
                    "description": "Pick a slot",
                    "start_date": "2026-03-10",
                    "end_date": "2026-03-10",
                    "daily_start_hour": 9,
                    "daily_end_hour": 17,
                    "allowed_weekdays": [0, 1, 2, 3, 4],
                    "timezone": "Europe/Helsinki",
                }
            ),
            content_type="application/json",
        )

    def create_poll_with_payload(self, client: Client, payload):
        return client.post(
            reverse("polls:polls_collection"),
            data=json.dumps(payload),
            content_type="application/json",
        )

    def update_poll_with_payload(self, client: Client, poll_id, payload):
        return client.put(
            reverse("polls:poll_detail", args=[poll_id]),
            data=json.dumps(payload),
            content_type="application/json",
        )

    def request_raw_json(self, client: Client, method: str, url_name: str, body: str, args=None):
        args = args or []
        return client.generic(
            method.upper(),
            reverse(url_name, args=args),
            data=body,
            content_type="application/json",
        )

    def make_request(self, method: str, path: str, *, body: str = "", identity: Identity | None = None):
        request = self.factory.generic(
            method.upper(),
            path,
            data=body,
            content_type="application/json",
        )
        request.session = {}
        if identity is not None:
            request.session[SESSION_IDENTITY_KEY] = identity.id
        return request

    def test_create_poll_requires_authentication(self):
        response = self.create_poll(self.client)
        self.assertEqual(response.status_code, 401)

    def test_login_creates_identity_if_missing(self):
        response = self.login(self.client, "alice", "1234")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["created"])

    def test_login_rotates_session_key_and_preserves_anonymous_session_data(self):
        session = self.client.session
        session["transient_key"] = "transient-value"
        session.save()
        old_session_key = session.session_key
        self.assertTrue(old_session_key)
        self.assertTrue(Session.objects.filter(session_key=old_session_key).exists())

        response = self.login(self.client, "alice", "1234")
        self.assertEqual(response.status_code, 201)

        refreshed_session = self.client.session
        self.assertNotEqual(refreshed_session.session_key, old_session_key)
        self.assertEqual(refreshed_session.get("transient_key"), "transient-value")
        self.assertEqual(refreshed_session.get(SESSION_IDENTITY_KEY), response.json()["identity"]["id"])
        self.assertFalse(Session.objects.filter(session_key=old_session_key).exists())

    def test_login_existing_user_with_wrong_pin_fails(self):
        create_response = self.login(self.client, "alice", "1234")
        self.assertEqual(create_response.status_code, 201)

        fail_response = self.login(self.client, "alice", "9999")
        self.assertEqual(fail_response.status_code, 401)

    def test_logout_destroys_session(self):
        login_response = self.login(self.client, "alice", "1234")
        self.assertEqual(login_response.status_code, 201)

        session = self.client.session
        session["transient_key"] = "transient-value"
        session.save()
        old_session_key = session.session_key
        self.assertTrue(Session.objects.filter(session_key=old_session_key).exists())

        logout_response = self.client.post(reverse("polls:logout_identity"))
        self.assertEqual(logout_response.status_code, 200)
        self.assertFalse(Session.objects.filter(session_key=old_session_key).exists())

        refreshed_session = self.client.session
        self.assertNotIn("transient_key", refreshed_session)
        self.assertNotIn("identity_id", refreshed_session)

        auth_session_response = self.client.get(reverse("polls:auth_session"))
        self.assertEqual(auth_session_response.status_code, 200)
        self.assertFalse(auth_session_response.json()["authenticated"])

    def test_auth_session_sets_csrf_cookie(self):
        csrf_client = Client(enforce_csrf_checks=True)

        response = csrf_client.get(reverse("polls:auth_session"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", response.cookies)
        self.assertTrue(response.cookies["csrftoken"].value)

    def test_login_and_logout_rotate_csrf_cookie(self):
        csrf_client = Client(enforce_csrf_checks=True)

        session_response = csrf_client.get(reverse("polls:auth_session"))
        self.assertEqual(session_response.status_code, 200)
        initial_token = csrf_client.cookies["csrftoken"].value
        self.assertTrue(initial_token)

        login_response = csrf_client.post(
            reverse("polls:login_identity"),
            data=json.dumps({"name": "csrf-user", "pin": "1234"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=initial_token,
        )
        self.assertEqual(login_response.status_code, 201)
        self.assertIn("csrftoken", login_response.cookies)
        login_token = login_response.cookies["csrftoken"].value
        self.assertTrue(login_token)
        self.assertNotEqual(login_token, initial_token)

        logout_response = csrf_client.post(
            reverse("polls:logout_identity"),
            HTTP_X_CSRFTOKEN=login_token,
        )
        self.assertEqual(logout_response.status_code, 200)
        self.assertIn("csrftoken", logout_response.cookies)
        logout_token = logout_response.cookies["csrftoken"].value
        self.assertTrue(logout_token)
        self.assertNotEqual(logout_token, login_token)

    def test_api_csrf_failure_returns_json_error_payload(self):
        csrf_client = Client(enforce_csrf_checks=True)

        session_response = csrf_client.get(reverse("polls:auth_session"))
        self.assertEqual(session_response.status_code, 200)

        response = csrf_client.post(
            reverse("polls:login_identity"),
            data=json.dumps({"name": "csrf-user", "pin": "1234"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN="x" * 32,
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.headers["Content-Type"].split(";")[0], "application/json")
        self.assertEqual(
            response.json(),
            {
                "error": "csrf_failed",
                "detail": "CSRF verification failed. Request aborted.",
            },
        )

    def test_login_matches_existing_identity_case_insensitively(self):
        create_response = self.login(self.client, "Alice", "1234")
        self.assertEqual(create_response.status_code, 201)
        created_identity_id = create_response.json()["identity"]["id"]

        login_response = self.login(self.client, "alice", "1234")
        self.assertEqual(login_response.status_code, 200)
        self.assertFalse(login_response.json()["created"])
        self.assertEqual(login_response.json()["identity"]["id"], created_identity_id)
        self.assertEqual(Identity.objects.count(), 1)

    def test_creator_can_close_then_delete(self):
        self.login(self.client, "alice")
        create = self.create_poll(self.client)
        self.assertEqual(create.status_code, 201)
        poll_id = create.json()["poll"]["id"]
        self.assertEqual(len(create.json()["poll"]["options"]), 8)
        self.assertEqual(create.json()["poll"]["timezone"], "Europe/Helsinki")

        delete_before_close = self.client.delete(reverse("polls:poll_detail", args=[poll_id]))
        self.assertEqual(delete_before_close.status_code, 409)

        close = self.client.post(reverse("polls:poll_close", args=[poll_id]))
        self.assertEqual(close.status_code, 200)

        delete_after_close = self.client.delete(reverse("polls:poll_detail", args=[poll_id]))
        self.assertEqual(delete_after_close.status_code, 200)
        self.assertFalse(Poll.objects.filter(id=poll_id).exists())

    def test_only_creator_can_close(self):
        self.login(self.client, "creator")
        create = self.create_poll(self.client)
        poll_id = create.json()["poll"]["id"]

        self.login(self.other_client, "bob")
        close = self.other_client.post(reverse("polls:poll_close", args=[poll_id]))
        self.assertEqual(close.status_code, 403)

    def test_creator_can_reopen_closed_poll(self):
        self.login(self.client, "creator")
        create = self.create_poll(self.client)
        poll_id = create.json()["poll"]["id"]

        close = self.client.post(reverse("polls:poll_close", args=[poll_id]))
        self.assertEqual(close.status_code, 200)

        reopen = self.client.post(reverse("polls:poll_reopen", args=[poll_id]))
        self.assertEqual(reopen.status_code, 200)
        poll_payload = reopen.json()["poll"]
        self.assertFalse(poll_payload["is_closed"])
        self.assertTrue(poll_payload["can_close"])
        self.assertFalse(poll_payload["can_reopen"])
        self.assertFalse(poll_payload["can_delete"])

        poll = Poll.objects.get(id=poll_id)
        self.assertFalse(poll.is_closed)
        self.assertIsNone(poll.closed_at)

        delete_while_open = self.client.delete(reverse("polls:poll_detail", args=[poll_id]))
        self.assertEqual(delete_while_open.status_code, 409)

    def test_only_creator_can_reopen(self):
        self.login(self.client, "creator")
        create = self.create_poll(self.client)
        poll_id = create.json()["poll"]["id"]

        close = self.client.post(reverse("polls:poll_close", args=[poll_id]))
        self.assertEqual(close.status_code, 200)

        self.login(self.other_client, "bob")
        reopen = self.other_client.post(reverse("polls:poll_reopen", args=[poll_id]))
        self.assertEqual(reopen.status_code, 403)

    def test_vote_edit_and_delete(self):
        self.login(self.client, "creator")
        create = self.create_poll(self.client)
        poll = create.json()["poll"]
        poll_id = poll["id"]
        option_id = poll["options"][0]["id"]

        self.login(self.other_client, "voter")

        vote = self.other_client.put(
            reverse("polls:poll_votes_upsert", args=[poll_id]),
            data=json.dumps({"votes": [{"option_id": option_id, "status": "yes"}]}),
            content_type="application/json",
        )
        self.assertEqual(vote.status_code, 200)
        self.assertTrue(PollVote.objects.filter(poll_option_id=option_id, voter__name="voter").exists())

        edit = self.other_client.put(
            reverse("polls:poll_votes_upsert", args=[poll_id]),
            data=json.dumps({"votes": [{"option_id": option_id, "status": "maybe"}]}),
            content_type="application/json",
        )
        self.assertEqual(edit.status_code, 200)
        self.assertEqual(
            PollVote.objects.get(poll_option_id=option_id, voter__name="voter").status,
            "maybe",
        )

        delete = self.other_client.delete(reverse("polls:poll_vote_delete", args=[poll_id, option_id]))
        self.assertEqual(delete.status_code, 200)
        self.assertFalse(PollVote.objects.filter(poll_option_id=option_id, voter__name="voter").exists())

    def test_vote_can_be_cleared_to_no_value(self):
        self.login(self.client, "creator")
        create = self.create_poll(self.client)
        poll = create.json()["poll"]
        poll_id = poll["id"]
        option_id = poll["options"][0]["id"]

        self.login(self.other_client, "voter")

        set_vote = self.other_client.put(
            reverse("polls:poll_votes_upsert", args=[poll_id]),
            data=json.dumps({"votes": [{"option_id": option_id, "status": "no"}]}),
            content_type="application/json",
        )
        self.assertEqual(set_vote.status_code, 200)
        self.assertTrue(PollVote.objects.filter(poll_option_id=option_id, voter__name="voter").exists())

        clear_vote = self.other_client.put(
            reverse("polls:poll_votes_upsert", args=[poll_id]),
            data=json.dumps({"votes": [{"option_id": option_id, "status": None}]}),
            content_type="application/json",
        )
        self.assertEqual(clear_vote.status_code, 200)
        self.assertFalse(PollVote.objects.filter(poll_option_id=option_id, voter__name="voter").exists())

    def test_poll_vote_delete_handles_missing_vote_and_foreign_option(self):
        self.login(self.client, "creator")
        first_create = self.create_poll(self.client)
        second_create = self.create_poll_with_payload(
            self.client,
            {
                "title": "Second delete poll",
                "description": "",
                "start_date": "2026-03-11",
                "end_date": "2026-03-11",
                "daily_start_hour": 9,
                "daily_end_hour": 17,
                "allowed_weekdays": [0, 1, 2, 3, 4],
                "timezone": "Europe/Helsinki",
            },
        )
        first_poll = first_create.json()["poll"]
        second_poll = second_create.json()["poll"]
        first_poll_id = first_poll["id"]
        first_option_id = first_poll["options"][0]["id"]
        foreign_option_id = second_poll["options"][0]["id"]

        self.login(self.other_client, "voter")

        missing_vote_delete = self.other_client.delete(
            reverse("polls:poll_vote_delete", args=[first_poll_id, first_option_id])
        )
        self.assertEqual(missing_vote_delete.status_code, 200)
        self.assertFalse(missing_vote_delete.json()["deleted"])

        voter = Identity.objects.get(name="voter")
        foreign_option_request = self.make_request(
            "DELETE",
            f"/api/polls/{first_poll_id}/votes/{foreign_option_id}/",
            identity=voter,
        )
        with self.assertRaises(Http404):
            poll_vote_delete(foreign_option_request, first_poll_id, foreign_option_id)

    def test_set_language_sets_cookie(self):
        response = self.client.post(
            reverse("polls:set_language"),
            data=json.dumps({"language": "fi"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["language"], "fi")
        self.assertEqual(response.cookies["django_language"].value, "fi")

    def test_set_language_supports_norwegian_and_estonian(self):
        for code in ("no", "et"):
            with self.subTest(code=code):
                response = self.client.post(
                    reverse("polls:set_language"),
                    data=json.dumps({"language": code}),
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["language"], code)
                self.assertEqual(response.cookies["django_language"].value, code)

    def test_auth_session_clears_stale_identity_from_session(self):
        login_response = self.login(self.client, "alice", "1234")
        self.assertEqual(login_response.status_code, 201)

        identity_id = login_response.json()["identity"]["id"]
        Identity.objects.filter(id=identity_id).delete()

        response = self.client.get(reverse("polls:auth_session"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["authenticated"])
        self.assertIsNone(response.json()["identity"])
        self.assertNotIn("identity_id", self.client.session)

    def test_set_language_rejects_invalid_language_code(self):
        cases: list[tuple[str, object]] = [
            ("unsupported-string", "de"),
            ("null", None),
            ("numeric", 123),
        ]

        for label, language in cases:
            with self.subTest(case=label):
                response = self.client.post(
                    reverse("polls:set_language"),
                    data=json.dumps({"language": language}),
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"], "invalid_language")
                self.assertNotIn("django_language", response.cookies)

    def test_polls_collection_summary_matrix_for_creator_voter_and_anonymous(self):
        anonymous_client = Client()

        self.login(self.client, "creator")
        self.login(self.other_client, "voter")

        open_response = self.create_poll_with_payload(
            self.client,
            {
                "identifier": "open_summary_poll",
                "title": "Open summary poll",
                "description": "Open poll for summary coverage",
                "start_date": "2026-03-10",
                "end_date": "2026-03-10",
                "daily_start_hour": 9,
                "daily_end_hour": 12,
                "allowed_weekdays": [0, 1, 2, 3, 4],
                "timezone": "Europe/Helsinki",
            },
        )
        self.assertEqual(open_response.status_code, 201)
        open_poll = open_response.json()["poll"]
        open_poll_id = open_poll["id"]
        open_option_ids = [option["id"] for option in open_poll["options"]]

        creator_open_vote = self.client.put(
            reverse("polls:poll_votes_upsert", args=[open_poll_id]),
            data=json.dumps({"votes": [{"option_id": open_option_ids[0], "status": "yes"}]}),
            content_type="application/json",
        )
        self.assertEqual(creator_open_vote.status_code, 200)

        voter_open_vote = self.other_client.put(
            reverse("polls:poll_votes_upsert", args=[open_poll_id]),
            data=json.dumps(
                {
                    "votes": [
                        {"option_id": open_option_ids[0], "status": "maybe"},
                        {"option_id": open_option_ids[1], "status": "yes"},
                    ]
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(voter_open_vote.status_code, 200)

        closed_response = self.create_poll_with_payload(
            self.client,
            {
                "identifier": "closed_summary_poll",
                "title": "Closed summary poll",
                "description": "Closed poll for summary coverage",
                "start_date": "2026-03-11",
                "end_date": "2026-03-11",
                "daily_start_hour": 9,
                "daily_end_hour": 11,
                "allowed_weekdays": [0, 1, 2, 3, 4],
                "timezone": "Europe/Helsinki",
            },
        )
        self.assertEqual(closed_response.status_code, 201)
        closed_poll = closed_response.json()["poll"]
        closed_poll_id = closed_poll["id"]
        closed_option_ids = [option["id"] for option in closed_poll["options"]]

        creator_closed_vote = self.client.put(
            reverse("polls:poll_votes_upsert", args=[closed_poll_id]),
            data=json.dumps({"votes": [{"option_id": closed_option_ids[0], "status": "no"}]}),
            content_type="application/json",
        )
        self.assertEqual(creator_closed_vote.status_code, 200)

        voter_closed_vote = self.other_client.put(
            reverse("polls:poll_votes_upsert", args=[closed_poll_id]),
            data=json.dumps({"votes": [{"option_id": closed_option_ids[1], "status": "yes"}]}),
            content_type="application/json",
        )
        self.assertEqual(voter_closed_vote.status_code, 200)

        close_response = self.client.post(reverse("polls:poll_close", args=[closed_poll_id]))
        self.assertEqual(close_response.status_code, 200)

        anonymous_response = anonymous_client.get(reverse("polls:polls_collection"))
        creator_response = self.client.get(reverse("polls:polls_collection"))
        voter_response = self.other_client.get(reverse("polls:polls_collection"))

        self.assertEqual(anonymous_response.status_code, 200)
        self.assertEqual(creator_response.status_code, 200)
        self.assertEqual(voter_response.status_code, 200)

        def summary_lookup(response, identifier):
            return next(
                poll for poll in response.json()["polls"] if poll["identifier"] == identifier
            )

        anonymous_open = summary_lookup(anonymous_response, "open_summary_poll")
        creator_open = summary_lookup(creator_response, "open_summary_poll")
        voter_open = summary_lookup(voter_response, "open_summary_poll")

        self.assertEqual(anonymous_open["participant_count"], 2)
        self.assertFalse(anonymous_open["can_close"])
        self.assertFalse(anonymous_open["can_reopen"])
        self.assertFalse(anonymous_open["can_delete"])
        self.assertFalse(anonymous_open["can_edit"])

        self.assertEqual(creator_open["participant_count"], 2)
        self.assertTrue(creator_open["can_close"])
        self.assertFalse(creator_open["can_reopen"])
        self.assertFalse(creator_open["can_delete"])
        self.assertTrue(creator_open["can_edit"])

        self.assertEqual(voter_open["participant_count"], 2)
        self.assertFalse(voter_open["can_close"])
        self.assertFalse(voter_open["can_reopen"])
        self.assertFalse(voter_open["can_delete"])
        self.assertFalse(voter_open["can_edit"])

        anonymous_closed = summary_lookup(anonymous_response, "closed_summary_poll")
        creator_closed = summary_lookup(creator_response, "closed_summary_poll")
        voter_closed = summary_lookup(voter_response, "closed_summary_poll")

        self.assertEqual(anonymous_closed["participant_count"], 2)
        self.assertFalse(anonymous_closed["can_close"])
        self.assertFalse(anonymous_closed["can_reopen"])
        self.assertFalse(anonymous_closed["can_delete"])
        self.assertFalse(anonymous_closed["can_edit"])

        self.assertEqual(creator_closed["participant_count"], 2)
        self.assertFalse(creator_closed["can_close"])
        self.assertTrue(creator_closed["can_reopen"])
        self.assertTrue(creator_closed["can_delete"])
        self.assertFalse(creator_closed["can_edit"])

        self.assertEqual(voter_closed["participant_count"], 2)
        self.assertFalse(voter_closed["can_close"])
        self.assertFalse(voter_closed["can_reopen"])
        self.assertFalse(voter_closed["can_delete"])
        self.assertFalse(voter_closed["can_edit"])

    def test_create_poll_forces_fixed_60_minute_slots(self):
        self.login(self.client, "alice")
        response = self.create_poll_with_payload(
            self.client,
            {
                "title": "Fixed slot",
                "description": "",
                "start_date": "2026-03-10",
                "end_date": "2026-03-10",
                "slot_minutes": 30,
                "daily_start_hour": 9,
                "daily_end_hour": 17,
                "allowed_weekdays": [0, 1, 2, 3, 4],
                "timezone": "Europe/Helsinki",
            },
        )
        self.assertEqual(response.status_code, 201)
        poll = response.json()["poll"]
        self.assertEqual(poll["slot_minutes"], 60)
        self.assertEqual(len(poll["options"]), 8)

    def test_create_poll_with_identifier_uses_identifier_as_public_id(self):
        self.login(self.client, "alice")
        response = self.create_poll_with_payload(
            self.client,
            {
                "identifier": "Poll_Name_2026",
                "title": "Identifier poll",
                "description": "Poll with custom id",
                "start_date": "2026-03-10",
                "end_date": "2026-03-10",
                "daily_start_hour": 9,
                "daily_end_hour": 17,
                "allowed_weekdays": [0, 1, 2, 3, 4],
                "timezone": "Europe/Helsinki",
            },
        )
        self.assertEqual(response.status_code, 201)
        poll = response.json()["poll"]
        self.assertEqual(poll["id"], "Poll_Name_2026")
        self.assertEqual(poll["identifier"], "Poll_Name_2026")
        self.assertTrue(Poll.objects.filter(identifier="Poll_Name_2026").exists())

    def test_poll_detail_supports_identifier_reference(self):
        self.login(self.client, "alice")
        create = self.create_poll_with_payload(
            self.client,
            {
                "identifier": "Poll_Name_2026",
                "title": "Identifier detail",
                "description": "",
                "start_date": "2026-03-10",
                "end_date": "2026-03-10",
                "daily_start_hour": 9,
                "daily_end_hour": 17,
                "allowed_weekdays": [0, 1, 2, 3, 4],
                "timezone": "Europe/Helsinki",
            },
        )
        self.assertEqual(create.status_code, 201)
        poll_ref = create.json()["poll"]["id"]
        detail = self.client.get(reverse("polls:poll_detail", args=[poll_ref]))
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["poll"]["id"], "Poll_Name_2026")

    def test_poll_reference_404_matrix_for_invalid_identifier_and_uuid(self):
        self.login(self.client, "alice")
        identity = Identity.objects.get(name="alice")

        missing_refs = [
            "missing_poll_2026",
            "11111111-1111-1111-1111-111111111111",
        ]
        cases: list[tuple[str, Any, list[int], str]] = [
            ("GET", poll_detail, [], ""),
            ("DELETE", poll_detail, [], ""),
            ("POST", poll_close, [], ""),
            ("POST", poll_reopen, [], ""),
            (
                "PUT",
                poll_votes_upsert,
                [],
                json.dumps({"votes": [{"option_id": 1, "status": "yes"}]}),
            ),
            ("DELETE", poll_vote_delete, [1], ""),
        ]

        for poll_ref in missing_refs:
            for case in cases:
                method = case[0]
                view_func = case[1]
                extra_args = case[2]
                body = case[3]
                with self.subTest(
                    poll_ref=poll_ref,
                    method=method,
                    view_name=getattr(view_func, "__name__", str(view_func)),
                ):
                    request = self.make_request(
                        method,
                        f"/api/polls/{poll_ref}/",
                        body=body,
                        identity=identity,
                    )
                    with self.assertRaises(Http404):
                        view_func(request, poll_ref, *extra_args)

    def test_create_poll_rejects_invalid_identifier(self):
        self.login(self.client, "alice")
        response = self.create_poll_with_payload(
            self.client,
            {
                "identifier": "Poll-Name-2026",
                "title": "Bad identifier",
                "description": "",
                "start_date": "2026-03-10",
                "end_date": "2026-03-10",
                "daily_start_hour": 9,
                "daily_end_hour": 17,
                "allowed_weekdays": [0, 1, 2, 3, 4],
                "timezone": "Europe/Helsinki",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "invalid_poll_identifier")

    def test_create_and_update_poll_identifier_edge_cases(self):
        self.login(self.client, "alice")

        invalid_identifier_cases = [
            ("non-string", 12345),
            ("too-long", "a" * 81),
        ]

        for label, identifier in invalid_identifier_cases:
            with self.subTest(case=f"create-{label}"):
                response = self.create_poll_with_payload(
                    self.client,
                    {
                        "identifier": identifier,
                        "title": "Invalid identifier",
                        "description": "",
                        "start_date": "2026-03-10",
                        "end_date": "2026-03-10",
                        "daily_start_hour": 9,
                        "daily_end_hour": 17,
                        "allowed_weekdays": [0, 1, 2, 3, 4],
                        "timezone": "Europe/Helsinki",
                    },
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"], "invalid_poll_identifier")

        create = self.create_poll_with_payload(
            self.client,
            {
                "identifier": "Poll_Name_2026",
                "title": "Identifier update",
                "description": "Original identifier",
                "start_date": "2026-03-10",
                "end_date": "2026-03-10",
                "daily_start_hour": 9,
                "daily_end_hour": 17,
                "allowed_weekdays": [0, 1, 2, 3, 4],
                "timezone": "Europe/Helsinki",
            },
        )
        self.assertEqual(create.status_code, 201)
        poll_id = create.json()["poll"]["id"]

        invalid_update = self.update_poll_with_payload(
            self.client,
            poll_id,
            {
                "identifier": 12345,
                "title": "Still invalid",
                "description": "",
                "start_date": "2026-03-10",
                "end_date": "2026-03-10",
                "daily_start_hour": 9,
                "daily_end_hour": 17,
                "allowed_weekdays": [0, 1, 2, 3, 4],
                "timezone": "Europe/Helsinki",
            },
        )
        self.assertEqual(invalid_update.status_code, 400)
        self.assertEqual(invalid_update.json()["error"], "invalid_poll_identifier")

        blank_identifier_update = self.update_poll_with_payload(
            self.client,
            poll_id,
            {
                "identifier": "   ",
                "title": "Identifier removed",
                "description": "Blank identifier clears custom id",
                "start_date": "2026-03-10",
                "end_date": "2026-03-10",
                "daily_start_hour": 9,
                "daily_end_hour": 17,
                "allowed_weekdays": [0, 1, 2, 3, 4],
                "timezone": "Europe/Helsinki",
            },
        )
        self.assertEqual(blank_identifier_update.status_code, 200)
        updated_poll = blank_identifier_update.json()["poll"]
        self.assertIsNone(updated_poll["identifier"])
        self.assertEqual(updated_poll["title"], "Identifier removed")
        self.assertNotEqual(updated_poll["id"], "Poll_Name_2026")

        poll = Poll.objects.get(title="Identifier removed")
        self.assertIsNone(poll.identifier)

        removed_identifier_request = self.make_request("GET", "/api/polls/Poll_Name_2026/")
        with self.assertRaises(Http404):
            poll_detail(removed_identifier_request, "Poll_Name_2026")

        new_reference_detail = self.client.get(reverse("polls:poll_detail", args=[updated_poll["id"]]))
        self.assertEqual(new_reference_detail.status_code, 200)
        self.assertEqual(new_reference_detail.json()["poll"]["title"], "Identifier removed")

    def test_create_poll_rejects_duplicate_identifier(self):
        self.login(self.client, "alice")
        first = self.create_poll_with_payload(
            self.client,
            {
                "identifier": "Poll_Name_2026",
                "title": "First poll",
                "description": "",
                "start_date": "2026-03-10",
                "end_date": "2026-03-10",
                "daily_start_hour": 9,
                "daily_end_hour": 17,
                "allowed_weekdays": [0, 1, 2, 3, 4],
                "timezone": "Europe/Helsinki",
            },
        )
        self.assertEqual(first.status_code, 201)

        duplicate = self.create_poll_with_payload(
            self.client,
            {
                "identifier": "Poll_Name_2026",
                "title": "Duplicate poll",
                "description": "",
                "start_date": "2026-03-11",
                "end_date": "2026-03-11",
                "daily_start_hour": 9,
                "daily_end_hour": 17,
                "allowed_weekdays": [0, 1, 2, 3, 4],
                "timezone": "Europe/Helsinki",
            },
        )
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(duplicate.json()["error"], "poll_identifier_taken")

    def test_create_poll_rejects_invalid_title_and_description_payloads(self):
        self.login(self.client, "alice")

        cases: list[tuple[str, dict[str, object], str]] = [
            ("title-not-string", {"title": 1234}, "invalid_title"),
            ("title-empty", {"title": "   "}, "invalid_title"),
            ("title-too-long", {"title": "a" * 161}, "invalid_title"),
            ("description-not-string", {"description": 1234}, "invalid_description"),
            ("description-too-long", {"description": "a" * 1201}, "invalid_description"),
        ]

        for label, overrides, expected_error in cases:
            with self.subTest(case=label):
                payload: dict[str, object] = {
                    "title": "Valid title",
                    "description": "Valid description",
                    "start_date": "2026-03-10",
                    "end_date": "2026-03-10",
                    "daily_start_hour": 9,
                    "daily_end_hour": 17,
                    "allowed_weekdays": [0, 1, 2, 3, 4],
                    "timezone": "Europe/Helsinki",
                }
                payload.update(overrides)
                response = self.create_poll_with_payload(self.client, payload)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"], expected_error)

    def test_create_poll_rejects_invalid_date_range(self):
        self.login(self.client, "alice")
        response = self.create_poll_with_payload(
            self.client,
            {
                "title": "Bad dates",
                "description": "",
                "start_date": "2026-03-12",
                "end_date": "2026-03-10",
                "daily_start_hour": 9,
                "daily_end_hour": 17,
                "allowed_weekdays": [0, 1, 2, 3, 4],
                "timezone": "Europe/Helsinki",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "invalid_date_range")

    def test_create_poll_rejects_invalid_daily_hours(self):
        self.login(self.client, "alice")
        response = self.create_poll_with_payload(
            self.client,
            {
                "title": "Bad hours",
                "description": "",
                "start_date": "2026-03-10",
                "end_date": "2026-03-10",
                "daily_start_hour": 18,
                "daily_end_hour": 9,
                "allowed_weekdays": [0, 1, 2, 3, 4],
                "timezone": "Europe/Helsinki",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "invalid_daily_hours")

    def test_create_poll_rejects_empty_weekdays(self):
        self.login(self.client, "alice")
        response = self.create_poll_with_payload(
            self.client,
            {
                "title": "Bad weekdays",
                "description": "",
                "start_date": "2026-03-10",
                "end_date": "2026-03-10",
                "daily_start_hour": 9,
                "daily_end_hour": 17,
                "allowed_weekdays": [],
                "timezone": "Europe/Helsinki",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "invalid_weekdays")

    def test_create_poll_filters_by_weekdays_and_daily_hours(self):
        self.login(self.client, "alice")
        response = self.create_poll_with_payload(
            self.client,
            {
                "title": "Filtered",
                "description": "",
                "start_date": "2026-03-09",
                "end_date": "2026-03-15",
                "daily_start_hour": 9,
                "daily_end_hour": 10,
                "allowed_weekdays": [0, 2],
                "timezone": "Europe/Helsinki",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.json()["poll"]["options"]), 2)

    def test_create_poll_rejects_invalid_timezone(self):
        self.login(self.client, "alice")
        response = self.create_poll_with_payload(
            self.client,
            {
                "title": "Bad timezone",
                "description": "",
                "start_date": "2026-03-10",
                "end_date": "2026-03-10",
                "daily_start_hour": 9,
                "daily_end_hour": 17,
                "allowed_weekdays": [0, 1, 2, 3, 4],
                "timezone": "Mars/Phobos",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "invalid_timezone")

    def test_generate_slots_supports_24_hour_end_and_string_hour_inputs(self):
        self.login(self.client, "alice")

        target_date = date(2026, 3, 10)
        response = self.create_poll_with_payload(
            self.client,
            {
                "title": "Late night slot",
                "description": "Covers the midnight boundary.",
                "start_date": target_date.isoformat(),
                "end_date": target_date.isoformat(),
                "daily_start_hour": "23",
                "daily_end_hour": "24",
                "allowed_weekdays": [target_date.weekday()],
                "timezone": "UTC",
            },
        )
        self.assertEqual(response.status_code, 201)
        poll = response.json()["poll"]
        self.assertEqual(poll["daily_start_hour"], 23)
        self.assertEqual(poll["daily_end_hour"], 24)
        self.assertEqual(len(poll["options"]), 1)
        self.assertEqual(poll["options"][0]["starts_at"], "2026-03-10T23:00:00+00:00")
        self.assertEqual(poll["options"][0]["ends_at"], "2026-03-11T00:00:00+00:00")

    def test_shared_invalid_json_returns_invalid_json(self):
        self.login(self.client, "alice")
        create = self.create_poll(self.client)
        poll_id = create.json()["poll"]["id"]

        cases: list[tuple[str, Client, str, str, list[str], str]] = [
            ("login", self.client, "POST", "polls:login_identity", [], "{"),
            ("language", self.client, "POST", "polls:set_language", [], "{"),
            ("poll-create", self.client, "POST", "polls:polls_collection", [], "{"),
            ("poll-votes", self.client, "PUT", "polls:poll_votes_upsert", [poll_id], "{"),
            ("non-object-json", self.client, "POST", "polls:polls_collection", [], "[]"),
        ]

        for label, client, method, url_name, args, body in cases:
            with self.subTest(case=label):
                response = self.request_raw_json(client, method, url_name, body, args=args)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"], "invalid_json")

    def test_login_rejects_invalid_name_and_pin_payloads(self):
        cases: list[tuple[str, dict[str, object], str]] = [
            ("name-not-string", {"name": 1234, "pin": "1234"}, "invalid_name"),
            ("name-too-short", {"name": "a", "pin": "1234"}, "invalid_name"),
            ("name-too-long", {"name": "a" * 81, "pin": "1234"}, "invalid_name"),
            ("pin-not-string", {"name": "alice", "pin": 1234}, "invalid_pin"),
            ("pin-non-digits", {"name": "alice", "pin": "12ab"}, "invalid_pin"),
            ("pin-too-short", {"name": "alice", "pin": "123"}, "invalid_pin"),
            ("pin-too-long", {"name": "alice", "pin": "1" * 13}, "invalid_pin"),
        ]

        for case_label, payload, expected_error in cases:
            with self.subTest(case=case_label):
                response = self.client.post(
                    reverse("polls:login_identity"),
                    data=json.dumps(payload),
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"], expected_error)

    def test_login_handles_integrity_race_path(self):

        first_lookup = MagicMock()
        first_lookup.first.return_value = None

        existing_identity = Identity(id=1, name="alice", name_key=Identity.build_name_key("alice"))
        existing_identity.set_pin("1234")

        second_lookup = MagicMock()
        second_lookup.first.return_value = existing_identity

        with patch("polls.views.Identity.objects.filter", side_effect=[first_lookup, second_lookup]):
            with patch("polls.views.Identity.save", side_effect=IntegrityError()):
                login_response = self.client.post(
                    reverse("polls:login_identity"),
                    data=json.dumps({"name": "alice", "pin": "1234"}),
                    content_type="application/json",
                )
        self.assertEqual(login_response.status_code, 200)
        self.assertFalse(login_response.json()["created"])
        self.assertTrue(login_response.json()["authenticated"])
        self.assertEqual(login_response.json()["identity"]["name"], "alice")

    def test_schedule_generation_rejects_no_slots_and_too_many_options(self):
        self.login(self.client, "alice")

        no_slots_date = date(2026, 3, 10)
        no_matching_weekday = (no_slots_date.weekday() + 1) % 7
        no_slots_response = self.create_poll_with_payload(
            self.client,
            {
                "title": "No slots",
                "description": "",
                "start_date": no_slots_date.isoformat(),
                "end_date": no_slots_date.isoformat(),
                "daily_start_hour": 9,
                "daily_end_hour": 17,
                "allowed_weekdays": [no_matching_weekday],
                "timezone": "Europe/Helsinki",
            },
        )
        self.assertEqual(no_slots_response.status_code, 400)
        self.assertEqual(no_slots_response.json()["error"], "invalid_options")

        start_date = date(2026, 1, 1)
        end_date = start_date + timedelta(days=90)
        too_many_response = self.create_poll_with_payload(
            self.client,
            {
                "title": "Too many slots",
                "description": "",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "daily_start_hour": 0,
                "daily_end_hour": 24,
                "allowed_weekdays": [0, 1, 2, 3, 4, 5, 6],
                "timezone": "UTC",
            },
        )
        self.assertEqual(too_many_response.status_code, 400)
        self.assertEqual(too_many_response.json()["error"], "too_many_options")

    def test_create_poll_rejects_invalid_weekday_values(self):
        self.login(self.client, "alice")

        invalid_cases = [
            ("not-a-list", "1"),
            ("bool-item", [True]),
            ("string-item", ["1"]),
            ("negative-item", [-1]),
            ("too-large-item", [7]),
        ]

        for label, weekdays in invalid_cases:
            with self.subTest(case=label):
                response = self.create_poll_with_payload(
                    self.client,
                    {
                        "title": "Bad weekdays",
                        "description": "",
                        "start_date": "2026-03-10",
                        "end_date": "2026-03-10",
                        "daily_start_hour": 9,
                        "daily_end_hour": 17,
                        "allowed_weekdays": weekdays,
                        "timezone": "Europe/Helsinki",
                    },
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"], "invalid_weekdays")

    def test_edit_poll_rejects_invalid_json_and_payload_matrix(self):
        self.login(self.client, "alice")
        create = self.create_poll(self.client)
        self.assertEqual(create.status_code, 201)
        poll_id = create.json()["poll"]["id"]

        json_cases = [
            ("broken-json", "{", "invalid_json"),
            ("non-object-json", "[]", "invalid_json"),
        ]
        for label, body, expected_error in json_cases:
            with self.subTest(case=label):
                response = self.request_raw_json(
                    self.client,
                    "PUT",
                    "polls:poll_detail",
                    body,
                    args=[poll_id],
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"], expected_error)

        payload_cases = [
            (
                "invalid-date-range",
                {
                    "title": "Bad dates",
                    "description": "",
                    "start_date": "2026-03-12",
                    "end_date": "2026-03-10",
                    "daily_start_hour": 9,
                    "daily_end_hour": 17,
                    "allowed_weekdays": [0, 1, 2, 3, 4],
                    "timezone": "Europe/Helsinki",
                },
                "invalid_date_range",
            ),
            (
                "invalid-daily-hours",
                {
                    "title": "Bad hours",
                    "description": "",
                    "start_date": "2026-03-10",
                    "end_date": "2026-03-10",
                    "daily_start_hour": 18,
                    "daily_end_hour": 9,
                    "allowed_weekdays": [0, 1, 2, 3, 4],
                    "timezone": "Europe/Helsinki",
                },
                "invalid_daily_hours",
            ),
            (
                "invalid-timezone",
                {
                    "title": "Bad timezone",
                    "description": "",
                    "start_date": "2026-03-10",
                    "end_date": "2026-03-10",
                    "daily_start_hour": 9,
                    "daily_end_hour": 17,
                    "allowed_weekdays": [0, 1, 2, 3, 4],
                    "timezone": "Mars/Phobos",
                },
                "invalid_timezone",
            ),
            (
                "invalid-weekdays",
                {
                    "title": "Bad weekdays",
                    "description": "",
                    "start_date": "2026-03-10",
                    "end_date": "2026-03-10",
                    "daily_start_hour": 9,
                    "daily_end_hour": 17,
                    "allowed_weekdays": [],
                    "timezone": "Europe/Helsinki",
                },
                "invalid_weekdays",
            ),
        ]

        for label, payload, expected_error in payload_cases:
            with self.subTest(case=label):
                response = self.update_poll_with_payload(self.client, poll_id, payload)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"], expected_error)

    def test_creator_can_edit_poll(self):
        self.login(self.client, "alice")
        create = self.create_poll(self.client)
        self.assertEqual(create.status_code, 201)
        poll_id = create.json()["poll"]["id"]

        response = self.update_poll_with_payload(
            self.client,
            poll_id,
            {
                "title": "Sprint planning updated",
                "description": "Updated description",
                "start_date": "2026-03-10",
                "end_date": "2026-03-11",
                "daily_start_hour": 9,
                "daily_end_hour": 17,
                "allowed_weekdays": [0, 1, 2, 3, 4],
                "timezone": "Europe/Helsinki",
            },
        )
        self.assertEqual(response.status_code, 200)
        poll = response.json()["poll"]
        self.assertEqual(poll["title"], "Sprint planning updated")
        self.assertEqual(poll["description"], "Updated description")
        self.assertEqual(poll["start_date"], "2026-03-10")
        self.assertEqual(poll["end_date"], "2026-03-11")
        self.assertEqual(len(poll["options"]), 16)

    def test_only_creator_can_edit_poll(self):
        self.login(self.client, "creator")
        create = self.create_poll(self.client)
        poll_id = create.json()["poll"]["id"]

        self.login(self.other_client, "bob")
        response = self.update_poll_with_payload(
            self.other_client,
            poll_id,
            {
                "title": "Not allowed",
                "description": "",
                "start_date": "2026-03-10",
                "end_date": "2026-03-10",
                "daily_start_hour": 9,
                "daily_end_hour": 17,
                "allowed_weekdays": [0, 1, 2, 3, 4],
                "timezone": "Europe/Helsinki",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_edit_poll_rejects_invalid_title_and_description_payloads(self):
        self.login(self.client, "creator")
        create = self.create_poll(self.client)
        self.assertEqual(create.status_code, 201)
        poll_id = create.json()["poll"]["id"]

        cases: list[tuple[str, dict[str, object], str]] = [
            ("title-not-string", {"title": 1234}, "invalid_title"),
            ("title-empty", {"title": "   "}, "invalid_title"),
            ("title-too-long", {"title": "a" * 161}, "invalid_title"),
            ("description-not-string", {"description": 1234}, "invalid_description"),
            ("description-too-long", {"description": "a" * 1201}, "invalid_description"),
        ]

        for label, overrides, expected_error in cases:
            with self.subTest(case=label):
                payload: dict[str, object] = {
                    "title": "Updated title",
                    "description": "Updated description",
                    "start_date": "2026-03-10",
                    "end_date": "2026-03-10",
                    "daily_start_hour": 9,
                    "daily_end_hour": 17,
                    "allowed_weekdays": [0, 1, 2, 3, 4],
                    "timezone": "Europe/Helsinki",
                }
                payload.update(overrides)
                response = self.update_poll_with_payload(self.client, poll_id, payload)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"], expected_error)

    def test_poll_detail_does_not_expose_participant_identity_names(self):
        self.login(self.client, "creator")
        create = self.create_poll(self.client)
        self.assertEqual(create.status_code, 201)
        poll = create.json()["poll"]
        poll_id = poll["id"]
        option_id = poll["options"][0]["id"]

        self.login(self.other_client, "guest")
        vote = self.other_client.put(
            reverse("polls:poll_votes_upsert", args=[poll_id]),
            data=json.dumps({"votes": [{"option_id": option_id, "status": "yes"}]}),
            content_type="application/json",
        )
        self.assertEqual(vote.status_code, 200)

        detail = self.client.get(reverse("polls:poll_detail", args=[poll_id]))
        self.assertEqual(detail.status_code, 200)
        poll_payload = detail.json()["poll"]
        self.assertNotIn("participants", poll_payload)
        self.assertEqual(poll_payload["participant_count"], 1)

        voted_option = next(option for option in poll_payload["options"] if option["id"] == option_id)
        self.assertNotIn("votes", voted_option)
        self.assertEqual(voted_option["counts"]["yes"], 1)

    def test_auth_me_created_polls_do_not_expose_participant_identity_names(self):
        self.login(self.client, "creator")
        create = self.create_poll(self.client)
        self.assertEqual(create.status_code, 201)
        poll = create.json()["poll"]
        poll_id = poll["id"]
        option_id = poll["options"][0]["id"]

        self.login(self.other_client, "guest")
        vote = self.other_client.put(
            reverse("polls:poll_votes_upsert", args=[poll_id]),
            data=json.dumps({"votes": [{"option_id": option_id, "status": "maybe"}]}),
            content_type="application/json",
        )
        self.assertEqual(vote.status_code, 200)

        export_response = self.client.get(reverse("polls:auth_me_data"))
        self.assertEqual(export_response.status_code, 200)
        created_poll = export_response.json()["created_polls"][0]
        self.assertNotIn("participants", created_poll)
        self.assertEqual(created_poll["participant_count"], 1)

        voted_option = next(option for option in created_poll["options"] if option["id"] == option_id)
        self.assertNotIn("votes", voted_option)
        self.assertEqual(voted_option["counts"]["maybe"], 1)

    def test_auth_me_data_requires_authentication(self):
        response = self.client.get(reverse("polls:auth_me_data"))
        self.assertEqual(response.status_code, 401)

    def test_auth_me_data_returns_full_identity_export(self):
        self.login(self.client, "alice")
        create = self.create_poll(self.client)
        poll = create.json()["poll"]
        option_id = poll["options"][0]["id"]
        poll_id = poll["id"]

        vote = self.client.put(
            reverse("polls:poll_votes_upsert", args=[poll_id]),
            data=json.dumps({"votes": [{"option_id": option_id, "status": "yes"}]}),
            content_type="application/json",
        )
        self.assertEqual(vote.status_code, 200)

        response = self.client.get(reverse("polls:auth_me_data"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("identity", payload)
        self.assertNotIn("pin_hash", payload["identity"])
        self.assertEqual(payload["identity"]["name"], "alice")
        self.assertEqual(payload["stats"]["created_poll_count"], 1)
        self.assertEqual(payload["stats"]["vote_count"], 1)
        self.assertEqual(len(payload["created_polls"]), 1)
        self.assertEqual(len(payload["votes"]), 1)
        self.assertIn("poll_is_closed", payload["votes"][0])

    def test_delete_own_data_removes_votes_and_only_polls_without_other_votes(self):
        self.login(self.client, "owner")
        first_create = self.create_poll(self.client)
        second_create = self.create_poll_with_payload(
            self.client,
            {
                "title": "Second poll",
                "description": "",
                "start_date": "2026-03-11",
                "end_date": "2026-03-11",
                "daily_start_hour": 9,
                "daily_end_hour": 17,
                "allowed_weekdays": [0, 1, 2, 3, 4],
                "timezone": "Europe/Helsinki",
            },
        )
        first_poll = first_create.json()["poll"]
        second_poll = second_create.json()["poll"]
        first_poll_id = first_poll["id"]
        second_poll_id = second_poll["id"]
        first_option_id = first_poll["options"][0]["id"]
        second_option_id = second_poll["options"][0]["id"]

        owner_vote_first = self.client.put(
            reverse("polls:poll_votes_upsert", args=[first_poll_id]),
            data=json.dumps({"votes": [{"option_id": first_option_id, "status": "yes"}]}),
            content_type="application/json",
        )
        self.assertEqual(owner_vote_first.status_code, 200)
        owner_vote_second = self.client.put(
            reverse("polls:poll_votes_upsert", args=[second_poll_id]),
            data=json.dumps({"votes": [{"option_id": second_option_id, "status": "maybe"}]}),
            content_type="application/json",
        )
        self.assertEqual(owner_vote_second.status_code, 200)

        self.login(self.other_client, "guest")
        guest_vote = self.other_client.put(
            reverse("polls:poll_votes_upsert", args=[first_poll_id]),
            data=json.dumps({"votes": [{"option_id": first_option_id, "status": "no"}]}),
            content_type="application/json",
        )
        self.assertEqual(guest_vote.status_code, 200)

        delete_response = self.client.delete(reverse("polls:auth_me_data"))
        self.assertEqual(delete_response.status_code, 200)
        delete_payload = delete_response.json()
        self.assertFalse(delete_payload["deleted_identity"])
        self.assertEqual(delete_payload["deleted_polls_count"], 1)
        self.assertEqual(delete_payload["remaining_created_polls_count"], 1)

        self.assertFalse(Poll.objects.filter(id=second_poll_id).exists())
        self.assertTrue(Poll.objects.filter(id=first_poll_id).exists())
        self.assertFalse(PollVote.objects.filter(voter__name="owner").exists())
        self.assertTrue(PollVote.objects.filter(voter__name="guest").exists())

        session_response = self.client.get(reverse("polls:auth_session"))
        self.assertEqual(session_response.status_code, 200)
        self.assertTrue(session_response.json()["authenticated"])

    def test_delete_own_data_removes_identity_when_no_data_left(self):
        self.login(self.client, "solo")
        create = self.create_poll(self.client)
        poll = create.json()["poll"]
        poll_id = poll["id"]
        option_id = poll["options"][0]["id"]
        vote = self.client.put(
            reverse("polls:poll_votes_upsert", args=[poll_id]),
            data=json.dumps({"votes": [{"option_id": option_id, "status": "yes"}]}),
            content_type="application/json",
        )
        self.assertEqual(vote.status_code, 200)

        response = self.client.delete(reverse("polls:auth_me_data"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["deleted_identity"])
        self.assertFalse(Poll.objects.filter(id=poll_id).exists())
        self.assertFalse(Identity.objects.filter(name__iexact="solo").exists())

        session_response = self.client.get(reverse("polls:auth_session"))
        self.assertEqual(session_response.status_code, 200)
        self.assertFalse(session_response.json()["authenticated"])

    def test_vote_api_rejects_invalid_payload_and_closed_poll(self):
        self.login(self.client, "creator")
        create = self.create_poll(self.client)
        poll = create.json()["poll"]
        poll_id = poll["id"]
        option_id = poll["options"][0]["id"]

        self.login(self.other_client, "voter")

        invalid_cases = [
            ("votes-empty", {"votes": []}),
            ("votes-not-list", {"votes": "yes"}),
            ("vote-item-not-object", {"votes": [None]}),
            ("wrong-option-id", {"votes": [{"option_id": 999999, "status": "yes"}]}),
            ("wrong-option-type", {"votes": [{"option_id": "bad", "status": "yes"}]}),
            ("wrong-status", {"votes": [{"option_id": option_id, "status": "later"}]}),
        ]

        for label, payload in invalid_cases:
            with self.subTest(case=label):
                response = self.other_client.put(
                    reverse("polls:poll_votes_upsert", args=[poll_id]),
                    data=json.dumps(payload),
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"], "invalid_votes")

        close = self.client.post(reverse("polls:poll_close", args=[poll_id]))
        self.assertEqual(close.status_code, 200)

        closed_vote = self.other_client.put(
            reverse("polls:poll_votes_upsert", args=[poll_id]),
            data=json.dumps({"votes": [{"option_id": option_id, "status": "yes"}]}),
            content_type="application/json",
        )
        self.assertEqual(closed_vote.status_code, 409)
        self.assertEqual(closed_vote.json()["error"], "poll_closed")

        closed_delete = self.other_client.delete(
            reverse("polls:poll_vote_delete", args=[poll_id, option_id])
        )
        self.assertEqual(closed_delete.status_code, 409)
        self.assertEqual(closed_delete.json()["error"], "poll_closed")

    def test_poll_detail_put_delete_cover_401_403_409_matrix(self):
        self.login(self.client, "creator")
        create = self.create_poll(self.client)
        self.assertEqual(create.status_code, 201)
        poll_id = create.json()["poll"]["id"]

        unauth_put = self.update_poll_with_payload(
            Client(),
            poll_id,
            {
                "title": "Unauthorized update",
                "description": "",
                "start_date": "2026-03-10",
                "end_date": "2026-03-10",
                "daily_start_hour": 9,
                "daily_end_hour": 17,
                "allowed_weekdays": [0, 1, 2, 3, 4],
                "timezone": "Europe/Helsinki",
            },
        )
        self.assertEqual(unauth_put.status_code, 401)
        self.assertEqual(unauth_put.json()["error"], "authentication_required")

        unauth_delete = Client().delete(reverse("polls:poll_detail", args=[poll_id]))
        self.assertEqual(unauth_delete.status_code, 401)
        self.assertEqual(unauth_delete.json()["error"], "authentication_required")

        self.login(self.other_client, "bob")
        forbidden_delete = self.other_client.delete(reverse("polls:poll_detail", args=[poll_id]))
        self.assertEqual(forbidden_delete.status_code, 403)
        self.assertEqual(forbidden_delete.json()["error"], "forbidden")

        open_delete = self.client.delete(reverse("polls:poll_detail", args=[poll_id]))
        self.assertEqual(open_delete.status_code, 409)
        self.assertEqual(open_delete.json()["error"], "poll_not_closed")

        close = self.client.post(reverse("polls:poll_close", args=[poll_id]))
        self.assertEqual(close.status_code, 200)

        closed_put = self.update_poll_with_payload(
            self.client,
            poll_id,
            {
                "title": "Closed update",
                "description": "",
                "start_date": "2026-03-10",
                "end_date": "2026-03-10",
                "daily_start_hour": 9,
                "daily_end_hour": 17,
                "allowed_weekdays": [0, 1, 2, 3, 4],
                "timezone": "Europe/Helsinki",
            },
        )
        self.assertEqual(closed_put.status_code, 409)
        self.assertEqual(closed_put.json()["error"], "poll_closed")
