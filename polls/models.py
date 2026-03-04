import uuid
import unicodedata

from django.contrib.auth.hashers import check_password, make_password
from django.db import models


class Identity(models.Model):
    name = models.CharField(max_length=80, unique=True)
    name_key = models.CharField(max_length=160, unique=True)
    pin_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name

    @staticmethod
    def build_name_key(raw_name: str) -> str:
        normalized = unicodedata.normalize("NFKC", str(raw_name or "").strip())
        return normalized.casefold()

    def set_pin(self, raw_pin: str) -> None:
        self.pin_hash = make_password(raw_pin)

    def check_pin(self, raw_pin: str) -> bool:
        return check_password(raw_pin, self.pin_hash)

    def save(self, *args, **kwargs):
        self.name = str(self.name or "").strip()
        self.name_key = self.build_name_key(self.name)
        super().save(*args, **kwargs)


class Poll(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creator = models.ForeignKey(Identity, on_delete=models.CASCADE, related_name="created_polls")
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    window_starts_at = models.DateTimeField()
    window_ends_at = models.DateTimeField()
    slot_minutes = models.PositiveIntegerField(default=60)
    daily_start_hour = models.PositiveSmallIntegerField(default=9)
    daily_end_hour = models.PositiveSmallIntegerField(default=17)
    allowed_weekdays = models.JSONField(default=list)
    timezone_name = models.CharField(max_length=64, default="UTC")
    is_closed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return self.title


class PollOption(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="options")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    label = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ("starts_at",)

    def __str__(self) -> str:
        return f"{self.poll.title} - {self.starts_at.isoformat()}"


class PollVote(models.Model):
    STATUS_YES = "yes"
    STATUS_NO = "no"
    STATUS_MAYBE = "maybe"
    STATUS_CHOICES = (
        (STATUS_YES, "Yes"),
        (STATUS_NO, "No"),
        (STATUS_MAYBE, "Maybe"),
    )

    poll_option = models.ForeignKey(PollOption, on_delete=models.CASCADE, related_name="votes")
    voter = models.ForeignKey(Identity, on_delete=models.CASCADE, related_name="votes")
    status = models.CharField(max_length=5, choices=STATUS_CHOICES, default=STATUS_YES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["poll_option", "voter"], name="unique_vote_per_option_voter")
        ]

    def __str__(self) -> str:
        return f"{self.voter.name} -> {self.poll_option_id} ({self.status})"
