from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("polls", "0004_poll_timezone_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="identity",
            name="preferred_timezone",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
    ]
