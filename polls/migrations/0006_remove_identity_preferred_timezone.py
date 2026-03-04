from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("polls", "0005_identity_preferred_timezone"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="identity",
            name="preferred_timezone",
        ),
    ]
