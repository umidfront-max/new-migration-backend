"""Qonunbuzilishlar, SOS murojaatlar, konsullik va qaytish dasturlari."""
from django.db import models

from apps.geography.models import Country
from core.models import OrderedModel, TimeStampedModel

TONE_CHOICES = [
    ("turk", "Firuza"),
    ("lapis", "Ko‘k"),
    ("saffron", "Sariq"),
    ("coral", "Marjon"),
    ("violet", "Binafsha"),
    ("mist", "Kulrang"),
]


class ViolationType(OrderedModel):
    """Qonunbuzilish turi va u bo'yicha holatlar soni."""

    key = models.SlugField("kalit", max_length=32, unique=True)
    label = models.CharField("turi", max_length=120)
    value = models.PositiveIntegerField("holatlar soni", default=0)
    delta = models.FloatField("o‘zgarish, %", default=0)
    tone = models.CharField("rangi", max_length=16, choices=TONE_CHOICES, default="coral")

    class Meta(OrderedModel.Meta):
        verbose_name = "qonunbuzilish turi"
        verbose_name_plural = "qonunbuzilish turlari"

    def __str__(self) -> str:
        return self.label

    @property
    def is_growing(self) -> bool:
        return self.delta > 0


class SosEvent(TimeStampedModel):
    """Migrantdan kelgan shoshilinch murojaat."""

    class Severity(models.TextChoices):
        CRITICAL = "critical", "Kritik"
        HIGH = "high", "Shoshilinch"
        MID = "mid", "O‘rta"
        LOW = "low", "Past"

    code = models.CharField("murojaat raqami", max_length=24, unique=True)
    applicant_name = models.CharField("murojaatchi", max_length=180)
    country = models.ForeignKey(
        Country, verbose_name="davlat", on_delete=models.PROTECT, related_name="sos_events",
    )
    city = models.CharField("shahar", max_length=120)
    latitude = models.FloatField("kengligi", null=True, blank=True)
    longitude = models.FloatField("uzunligi", null=True, blank=True)
    event_type = models.CharField("murojaat turi", max_length=180)
    severity = models.CharField(
        "jiddiyligi", max_length=16, choices=Severity.choices, default=Severity.HIGH,
    )
    minutes_ago = models.PositiveIntegerField("necha daqiqa oldin", default=0)
    phone = models.CharField("telefon", max_length=32, blank=True)
    is_resolved = models.BooleanField("hal etilgan", default=False)

    class Meta:
        verbose_name = "SOS murojaat"
        verbose_name_plural = "SOS murojaatlar"
        ordering = ["minutes_ago", "-created_at"]
        indexes = [models.Index(fields=["severity"])]

    def __str__(self) -> str:
        return f"{self.code} — {self.event_type}"

    @property
    def is_urgent(self) -> bool:
        return self.severity in {self.Severity.CRITICAL, self.Severity.HIGH}


class SosChannel(OrderedModel):
    """Murojaat kelgan kanal va uning ulushi."""

    name = models.CharField("kanal nomi", max_length=120, unique=True)
    share = models.PositiveSmallIntegerField("ulushi, %", default=0)
    icon = models.CharField("belgisi", max_length=24, default="phone")

    class Meta(OrderedModel.Meta):
        verbose_name = "SOS kanali"
        verbose_name_plural = "SOS kanallari"

    def __str__(self) -> str:
        return self.name


class ConsulateService(OrderedModel):
    """Konsullik ko'rsatadigan xizmat turi."""

    label = models.CharField("xizmat turi", max_length=180, unique=True)
    value = models.PositiveIntegerField("murojaatlar soni", default=0)
    tone = models.CharField("rangi", max_length=16, choices=TONE_CHOICES, default="lapis")

    class Meta(OrderedModel.Meta):
        verbose_name = "konsullik xizmati"
        verbose_name_plural = "konsullik xizmatlari"

    def __str__(self) -> str:
        return self.label


class ReturnProgram(OrderedModel):
    """Qaytgan migrantlar uchun reintegratsiya dasturi."""

    name = models.CharField("dastur nomi", max_length=180, unique=True)
    completed = models.PositiveIntegerField("bajarildi", default=0)
    target = models.PositiveIntegerField("maqsad", default=1)
    tone = models.CharField("rangi", max_length=16, choices=TONE_CHOICES, default="lapis")

    class Meta(OrderedModel.Meta):
        verbose_name = "reintegratsiya dasturi"
        verbose_name_plural = "reintegratsiya dasturlari"

    def __str__(self) -> str:
        return self.name

    @property
    def completion_percent(self) -> int:
        """Bajarilish foizi — nol maqsadda ham xato bermaydi."""
        if not self.target:
            return 0
        return min(100, round(self.completed / self.target * 100))
