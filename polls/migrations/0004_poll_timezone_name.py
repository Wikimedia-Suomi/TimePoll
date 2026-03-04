from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("polls", "0003_poll_allowed_weekdays_poll_daily_end_hour_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="poll",
            name="timezone_name",
            field=models.CharField(default="UTC", max_length=64),
        ),
    ]
