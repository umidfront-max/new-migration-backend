"""
"Yuborilgan migrantlar" endi qo'lda kiritilmaydi — reyestrdagi bog'langan
migrantlar sonidan hisoblanadi. Mavjud qiymatlar shu songa tenglashtiriladi.
"""
from django.db import migrations
from django.db.models import Count


def recount(apps, schema_editor) -> None:
    Employer = apps.get_model("registry", "Employer")
    for employer in Employer.objects.annotate(total=Count("migrants")):
        if employer.sent_count != employer.total:
            Employer.objects.filter(pk=employer.pk).update(sent_count=employer.total)


class Migration(migrations.Migration):

    dependencies = [
        ("registry", "0003_migrant_district"),
    ]

    operations = [
        migrations.RunPython(recount, migrations.RunPython.noop),
    ]
