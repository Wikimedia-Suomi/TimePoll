import unicodedata

from django.db import migrations, models


def build_name_key(raw_name):
    normalized = unicodedata.normalize("NFKC", str(raw_name or "").strip())
    return normalized.casefold()


def populate_identity_name_key(apps, schema_editor):
    Identity = apps.get_model("polls", "Identity")
    existing_keys = {}
    updates = []

    for identity in Identity.objects.all().order_by("id"):
        key = build_name_key(identity.name)
        if not key:
            raise RuntimeError(f"Identity {identity.id} has empty name and cannot be migrated.")
        if key in existing_keys:
            previous_id = existing_keys[key]
            raise RuntimeError(
                "Case-insensitive duplicate identity names found during migration: "
                f"{previous_id} and {identity.id} (name={identity.name!r}). "
                "Resolve duplicates first and rerun migrations."
            )
        existing_keys[key] = identity.id
        updates.append((identity.id, key))

    for identity_id, key in updates:
        Identity.objects.filter(id=identity_id).update(name_key=key)


class Migration(migrations.Migration):

    dependencies = [
        ("polls", "0006_remove_identity_preferred_timezone"),
    ]

    operations = [
        migrations.AddField(
            model_name="identity",
            name="name_key",
            field=models.CharField(max_length=160, null=True),
        ),
        migrations.RunPython(populate_identity_name_key, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="identity",
            name="name_key",
            field=models.CharField(max_length=160, unique=True),
        ),
    ]
