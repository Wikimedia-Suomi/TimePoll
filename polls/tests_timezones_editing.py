from __future__ import annotations

import json

from django.test import Client, TestCase
from django.urls import reverse


class TimezoneEditingContractTests(TestCase):
    def setUp(self) -> None:
        self.owner_client = Client()
        self.voter_client = Client()

    def login(self, client: Client, name: str, pin: str = "1234"):
        return client.post(
            reverse("polls:login_identity"),
            data=json.dumps({"name": name, "pin": pin}),
            content_type="application/json",
        )

    def create_poll(self, client: Client, **overrides):
        payload = {
            "title": "Timezone editing contract poll",
            "description": "Used for backend schedule/vote contract coverage.",
            "start_date": "2026-03-10",
            "end_date": "2026-03-10",
            "daily_start_hour": 9,
            "daily_end_hour": 17,
            "allowed_weekdays": [0, 1, 2, 3, 4],
            "timezone": "Europe/Helsinki",
        }
        payload.update(overrides)
        return client.post(
            reverse("polls:polls_collection"),
            data=json.dumps(payload),
            content_type="application/json",
        )

    def update_poll(self, client: Client, poll_ref: str, **overrides):
        payload = {
            "title": "Timezone editing contract poll updated",
            "description": "",
            "start_date": "2026-03-10",
            "end_date": "2026-03-10",
            "daily_start_hour": 9,
            "daily_end_hour": 17,
            "allowed_weekdays": [0, 1, 2, 3, 4],
            "timezone": "Europe/Helsinki",
        }
        payload.update(overrides)
        return client.put(
            reverse("polls:poll_detail", args=[poll_ref]),
            data=json.dumps(payload),
            content_type="application/json",
        )

    def cast_vote(self, client: Client, poll_ref: str, option_id: str, status: str = "yes"):
        return client.put(
            reverse("polls:poll_votes_upsert", args=[poll_ref]),
            data=json.dumps({"votes": [{"option_id": option_id, "status": status}]}),
            content_type="application/json",
        )

    def test_edit_contract_rejects_removing_voted_slot(self) -> None:
        self.login(self.owner_client, "contract-creator")
        create = self.create_poll(self.owner_client)
        self.assertEqual(create.status_code, 201)
        poll = create.json()["poll"]
        poll_id = poll["id"]
        option_id = poll["options"][0]["id"]

        self.login(self.voter_client, "contract-voter")
        vote = self.cast_vote(self.voter_client, poll_id, option_id, status="yes")
        self.assertEqual(vote.status_code, 200)

        response = self.update_poll(
            self.owner_client,
            poll_id,
            daily_start_hour=10,
            daily_end_hour=17,
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"], "schedule_conflicts_with_votes")

    def test_edit_contract_allows_removing_only_unvoted_slots(self) -> None:
        self.login(self.owner_client, "safe-shrink-creator")
        create = self.create_poll(self.owner_client)
        self.assertEqual(create.status_code, 201)
        poll = create.json()["poll"]
        poll_id = poll["id"]
        remaining_option_id = poll["options"][2]["id"]

        self.login(self.voter_client, "safe-shrink-voter")
        vote = self.cast_vote(self.voter_client, poll_id, remaining_option_id, status="maybe")
        self.assertEqual(vote.status_code, 200)

        response = self.update_poll(
            self.owner_client,
            poll_id,
            daily_start_hour=10,
            daily_end_hour=17,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["poll"]["options"]), 7)

    def test_edit_contract_timezone_change_rejects_excluding_voted_slot(self) -> None:
        self.login(self.owner_client, "timezone-conflict-creator")
        create = self.create_poll(
            self.owner_client,
            title="Timezone conflict poll",
            start_date="2026-05-04",
            end_date="2026-05-04",
            daily_start_hour=0,
            daily_end_hour=24,
            allowed_weekdays=[0, 1, 2, 3, 4, 5, 6],
            timezone="UTC",
        )
        self.assertEqual(create.status_code, 201)
        poll = create.json()["poll"]
        poll_id = poll["id"]
        option_id = poll["options"][0]["id"]

        self.login(self.voter_client, "timezone-conflict-voter")
        vote = self.cast_vote(self.voter_client, poll_id, option_id, status="yes")
        self.assertEqual(vote.status_code, 200)

        response = self.update_poll(
            self.owner_client,
            poll_id,
            title="Timezone conflict poll updated",
            start_date="2026-05-03",
            end_date="2026-05-03",
            daily_start_hour=15,
            daily_end_hour=16,
            allowed_weekdays=[6],
            timezone="Pacific/Honolulu",
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"], "schedule_conflicts_with_votes")

    def test_edit_contract_timezone_change_preserves_voted_slot_and_schedule_projection(self) -> None:
        self.login(self.owner_client, "timezone-preserve-creator")
        create = self.create_poll(
            self.owner_client,
            title="Timezone preserve poll",
            description="Covers timezone-aware edit save contract.",
            start_date="2026-05-04",
            end_date="2026-05-04",
            daily_start_hour=0,
            daily_end_hour=24,
            allowed_weekdays=[0, 1, 2, 3, 4, 5, 6],
            timezone="UTC",
        )
        self.assertEqual(create.status_code, 201)
        poll = create.json()["poll"]
        poll_id = poll["id"]
        original_option = poll["options"][0]
        original_option_id = original_option["id"]
        original_starts_at = original_option["starts_at"]
        original_ends_at = original_option["ends_at"]

        self.login(self.voter_client, "timezone-preserve-voter")
        vote = self.cast_vote(self.voter_client, poll_id, original_option_id, status="yes")
        self.assertEqual(vote.status_code, 200)

        response = self.update_poll(
            self.owner_client,
            poll_id,
            title="Timezone preserve poll updated",
            description="Saved after timezone shift.",
            start_date="2026-05-03",
            end_date="2026-05-03",
            daily_start_hour=14,
            daily_end_hour=15,
            allowed_weekdays=[6],
            timezone="Pacific/Honolulu",
        )
        self.assertEqual(response.status_code, 200)

        updated_poll = response.json()["poll"]
        self.assertEqual(updated_poll["timezone"], "Pacific/Honolulu")
        self.assertEqual(updated_poll["start_date"], "2026-05-03")
        self.assertEqual(updated_poll["end_date"], "2026-05-03")
        self.assertEqual(updated_poll["daily_start_hour"], 14)
        self.assertEqual(updated_poll["daily_end_hour"], 15)
        self.assertEqual(updated_poll["allowed_weekdays"], [6])
        self.assertEqual(len(updated_poll["options"]), 1)

        updated_option = updated_poll["options"][0]
        self.assertEqual(updated_option["id"], original_option_id)
        self.assertEqual(updated_option["starts_at"], original_starts_at)
        self.assertEqual(updated_option["ends_at"], original_ends_at)
        self.assertEqual(updated_option["counts"]["yes"], 1)
