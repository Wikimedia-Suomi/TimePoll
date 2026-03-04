from django.db import migrations, models
from django.utils import timezone


def copy_available_to_status(apps, schema_editor):
    PollVote = apps.get_model("polls", "PollVote")
    for vote in PollVote.objects.all():
        vote.status = "yes" if vote.available else "no"
        vote.save(update_fields=["status"])


class Migration(migrations.Migration):
    dependencies = [
        ("polls", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="poll",
            name="slot_minutes",
            field=models.PositiveIntegerField(default=60),
        ),
        migrations.AddField(
            model_name="poll",
            name="window_ends_at",
            field=models.DateTimeField(default=timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="poll",
            name="window_starts_at",
            field=models.DateTimeField(default=timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="pollvote",
            name="status",
            field=models.CharField(
                choices=[("yes", "Yes"), ("no", "No"), ("maybe", "Maybe")],
                default="yes",
                max_length=5,
            ),
        ),
        migrations.RunPython(copy_available_to_status, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="pollvote",
            name="available",
        ),
    ]
