# Generated manually for initial project setup.

import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Identity",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=80, unique=True)),
                ("pin_hash", models.CharField(max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ("name",),
            },
        ),
        migrations.CreateModel(
            name="Poll",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=160)),
                ("description", models.TextField(blank=True)),
                ("is_closed", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("closed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "creator",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="created_polls", to="polls.identity"),
                ),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
        migrations.CreateModel(
            name="PollOption",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("starts_at", models.DateTimeField()),
                ("ends_at", models.DateTimeField(blank=True, null=True)),
                ("label", models.CharField(blank=True, max_length=120)),
                (
                    "poll",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="options", to="polls.poll"),
                ),
            ],
            options={
                "ordering": ("starts_at",),
            },
        ),
        migrations.CreateModel(
            name="PollVote",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("available", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "poll_option",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="votes", to="polls.polloption"),
                ),
                (
                    "voter",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="votes", to="polls.identity"),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="pollvote",
            constraint=models.UniqueConstraint(fields=("poll_option", "voter"), name="unique_vote_per_option_voter"),
        ),
    ]
