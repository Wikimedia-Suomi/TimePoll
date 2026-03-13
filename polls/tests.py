import json

from django.contrib.sessions.models import Session
from django.test import Client, TestCase
from django.urls import reverse

from .models import Identity, Poll, PollVote


class PollApiTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.other_client = Client()

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

    def test_create_poll_requires_authentication(self):
        response = self.create_poll(self.client)
        self.assertEqual(response.status_code, 401)

    def test_login_creates_identity_if_missing(self):
        response = self.login(self.client, "alice", "1234")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["created"])

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

    def test_login_matches_existing_identity_case_insensitively(self):
        create_response = self.login(self.client, "Alice", "1234")
        self.assertEqual(create_response.status_code, 201)
        created_identity_id = create_response.json()["identity"]["id"]

        login_response = self.login(self.client, "alice", "1234")
        self.assertEqual(login_response.status_code, 200)
        self.assertFalse(login_response.json()["created"])
        self.assertEqual(login_response.json()["identity"]["id"], created_identity_id)
        self.assertEqual(Identity.objects.count(), 1)

    def test_register_rejects_case_insensitive_duplicate_name(self):
        first = self.client.post(
            reverse("polls:register_identity"),
            data=json.dumps({"name": "Alice", "pin": "1234"}),
            content_type="application/json",
        )
        self.assertEqual(first.status_code, 201)

        duplicate = self.other_client.post(
            reverse("polls:register_identity"),
            data=json.dumps({"name": "alice", "pin": "4321"}),
            content_type="application/json",
        )
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(duplicate.json()["error"], "name_taken")

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

    def test_edit_poll_rejects_removing_slot_with_votes(self):
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

        response = self.update_poll_with_payload(
            self.client,
            poll_id,
            {
                "title": "Shrink window",
                "description": "",
                "start_date": "2026-03-10",
                "end_date": "2026-03-10",
                "daily_start_hour": 10,
                "daily_end_hour": 17,
                "allowed_weekdays": [0, 1, 2, 3, 4],
                "timezone": "Europe/Helsinki",
            },
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"], "schedule_conflicts_with_votes")

    def test_edit_poll_allows_removing_unvoted_slots(self):
        self.login(self.client, "creator")
        create = self.create_poll(self.client)
        poll = create.json()["poll"]
        poll_id = poll["id"]
        option_id = poll["options"][2]["id"]  # 11:00-12:00 remains after shrinking to 10-17

        self.login(self.other_client, "voter")
        vote = self.other_client.put(
            reverse("polls:poll_votes_upsert", args=[poll_id]),
            data=json.dumps({"votes": [{"option_id": option_id, "status": "maybe"}]}),
            content_type="application/json",
        )
        self.assertEqual(vote.status_code, 200)

        response = self.update_poll_with_payload(
            self.client,
            poll_id,
            {
                "title": "Shrink safely",
                "description": "",
                "start_date": "2026-03-10",
                "end_date": "2026-03-10",
                "daily_start_hour": 10,
                "daily_end_hour": 17,
                "allowed_weekdays": [0, 1, 2, 3, 4],
                "timezone": "Europe/Helsinki",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["poll"]["options"]), 7)

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
