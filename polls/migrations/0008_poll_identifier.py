from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("polls", "0007_identity_name_key"),
    ]

    operations = [
        migrations.AddField(
            model_name="poll",
            name="identifier",
            field=models.CharField(blank=True, max_length=80, null=True, unique=True),
        ),
    ]
