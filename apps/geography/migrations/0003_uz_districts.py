"""Barcha hududlarga tumanlar va viloyatga bo'ysunuvchi shaharlarni qo'shadi."""
from django.db import migrations

from apps.geography.uz_districts import ensure_districts


def add_districts(apps, schema_editor) -> None:
    ensure_districts(apps.get_model("geography", "Region"), apps.get_model("geography", "District"))


class Migration(migrations.Migration):

    dependencies = [
        ("geography", "0002_country_consulate_helped_country_consulate_requests_and_more"),
    ]

    operations = [
        migrations.RunPython(add_districts, migrations.RunPython.noop),
    ]
