"""Migrantlar reyestri va ish beruvchilar."""
from django.core.validators import RegexValidator
from django.db import models

from apps.geography.models import Country, Region
from core.models import TimeStampedModel

pinfl_validator = RegexValidator(r"^\d{14}$", "PINFL 14 ta raqamdan iborat bo‘lishi kerak")


class Migrant(TimeStampedModel):
    """Reyestrdagi shaxs."""

    class Gender(models.TextChoices):
        MALE = "Erkak", "Erkak"
        FEMALE = "Ayol", "Ayol"
        MINOR = "Voyaga yetmagan", "Voyaga yetmagan"

    class Purpose(models.TextChoices):
        FORMAL_WORK = "Ishlash (rasmiy)", "Ishlash (rasmiy)"
        INFORMAL_WORK = "Ishlash (norasmiy)", "Ishlash (norasmiy)"
        STUDY = "O‘qish", "O‘qish"
        MEDICAL = "Davolanish", "Davolanish"
        TRAVEL = "Sayohat", "Sayohat"
        RESIDENCE = "Doimiy yashash", "Doimiy yashash"

    class LegalStatus(models.TextChoices):
        CLEAR = "Xavf yo‘q", "Xavf yo‘q"
        WANTED = "Qidiruvda", "Qidiruvda"
        SERVING = "Jazoni o‘tamoqda", "Jazoni o‘tamoqda"
        MISSING = "Bedarak yo‘qolgan", "Bedarak yo‘qolgan"

    class Health(models.TextChoices):
        HEALTHY = "Sog‘lom", "Sog‘lom"
        CHRONIC = "Surunkali kasallik", "Surunkali kasallik"
        DISABILITY = "Nogironlik", "Nogironlik"

    pinfl = models.CharField(
        "PINFL", max_length=14, unique=True, validators=[pinfl_validator], db_index=True,
    )
    full_name = models.CharField("F.I.Sh", max_length=180, db_index=True)
    nationality = models.CharField("millati", max_length=60, blank=True)
    gender = models.CharField("jinsi", max_length=24, choices=Gender.choices, default=Gender.MALE)
    speciality = models.CharField("mutaxassisligi", max_length=90, blank=True)

    country = models.ForeignKey(
        Country, verbose_name="qabul qiluvchi davlat",
        on_delete=models.PROTECT, related_name="migrants",
    )
    region = models.ForeignKey(
        Region, verbose_name="chiqqan hududi",
        on_delete=models.PROTECT, related_name="migrants",
    )

    purpose = models.CharField(
        "chiqish maqsadi", max_length=32, choices=Purpose.choices, default=Purpose.FORMAL_WORK,
    )
    remittance_band = models.CharField("pul jo‘natmalari", max_length=32, blank=True)
    marital_status = models.CharField("oilaviy ahvoli", max_length=40, blank=True)
    health_status = models.CharField(
        "sog‘lig‘i", max_length=32, choices=Health.choices, default=Health.HEALTHY,
    )
    is_convicted = models.BooleanField("sudlangan", default=False)

    employer_name = models.CharField("ish beruvchi", max_length=180, blank=True)
    address = models.CharField("xorijdagi manzil", max_length=250, blank=True)
    phone = models.CharField("telefon", max_length=32, blank=True)

    legal_status = models.CharField(
        "holati", max_length=32, choices=LegalStatus.choices, default=LegalStatus.CLEAR,
    )
    risk_score = models.PositiveSmallIntegerField("risk ball", default=0)
    exit_date = models.DateField("chiqish sanasi", null=True, blank=True)

    class Meta:
        verbose_name = "migrant"
        verbose_name_plural = "migrantlar"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["legal_status"]),
            models.Index(fields=["gender"]),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} — {self.pinfl}"

    @property
    def is_at_risk(self) -> bool:
        return self.legal_status != self.LegalStatus.CLEAR


class Employer(TimeStampedModel):
    """Migrant yuboruvchi tashkilot."""

    class Employment(models.TextChoices):
        FORMAL = "Rasmiy shartnoma", "Rasmiy shartnoma"
        INFORMAL = "Norasmiy bandlik", "Norasmiy bandlik"

    class Status(models.TextChoices):
        APPROVED = "Tasdiqlangan", "Tasdiqlangan"
        WATCHED = "Kuzatuvda", "Kuzatuvda"
        RESTRICTED = "Cheklangan", "Cheklangan"

    name = models.CharField("kompaniya nomi", max_length=180, unique=True)
    direction = models.CharField("yo‘nalishi", max_length=90)
    countries = models.ManyToManyField(
        Country, verbose_name="qaysi davlatlarga yuboradi", related_name="employers", blank=True,
    )
    employment_type = models.CharField(
        "shartnoma", max_length=24, choices=Employment.choices, default=Employment.FORMAL,
    )
    sent_count = models.PositiveIntegerField("yuborilgan migrantlar", default=0)
    remittance_amount = models.PositiveIntegerField("jo‘natma, mln $", default=0)
    status = models.CharField(
        "holati", max_length=16, choices=Status.choices, default=Status.WATCHED,
    )

    class Meta:
        verbose_name = "ish beruvchi"
        verbose_name_plural = "ish beruvchilar"
        ordering = ["-sent_count", "name"]

    def __str__(self) -> str:
        return self.name

    @property
    def formal_share(self) -> int:
        """Ko'rsatkichlar uchun foiz ko'rinishi — tanlovdan kelib chiqadi."""
        return 100 if self.employment_type == self.Employment.FORMAL else 0

    @property
    def is_informal(self) -> bool:
        return self.employment_type == self.Employment.INFORMAL
