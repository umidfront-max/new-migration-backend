"""
Ko'rsatkichlar, grafik qatorlari va panel ro'yxatlari.

Bir-biriga o'xshash KPI to'plamlari (dashboard, konsullik, qaytish, chegara,
SOS, audit) bitta `MetricTile` modelida `group` maydoni bilan saqlanadi —
shu sababli olti xil model o'rniga bitta jadval yetarli.
"""
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models import OrderedModel, TimeStampedModel

TONE_CHOICES = [
    ("turk", "Firuza"),
    ("lapis", "Ko‘k"),
    ("saffron", "Sariq"),
    ("coral", "Marjon"),
    ("violet", "Binafsha"),
    ("mist", "Kulrang"),
]


class MetricTile(OrderedModel):
    """Sahifa yuqorisidagi raqamli ko'rsatkich."""

    class Group(models.TextChoices):
        DASHBOARD = "dashboard", "Boshqaruv paneli"
        CONSULATE = "consulate", "Konsullik"
        RETURN = "return", "Qaytish"
        BORDER = "border", "Chegara"
        SOS = "sos", "SOS xizmati"
        AUDIT = "audit", "Audit"

    group = models.CharField("guruh", max_length=16, choices=Group.choices, db_index=True)
    key = models.SlugField("kalit", max_length=40, blank=True)
    label = models.CharField("ko‘rsatkich nomi", max_length=180)
    value = models.BigIntegerField("qiymati", default=0)
    delta = models.FloatField("o‘zgarish, %", default=0)
    subtitle = models.CharField("izoh", max_length=180, blank=True)
    tone = models.CharField("rangi", max_length=16, choices=TONE_CHOICES, default="lapis")

    class Meta(OrderedModel.Meta):
        verbose_name = "ko‘rsatkich"
        verbose_name_plural = "ko‘rsatkichlar"

    def __str__(self) -> str:
        return f"{self.get_group_display()}: {self.label}"


class ShareSlice(OrderedModel):
    """Doiraviy diagramma bo'lagi — tarkib, maqsad, xavf taqsimoti."""

    class Group(models.TextChoices):
        COMPOSITION = "composition", "Migrantlar tarkibi"
        PURPOSE = "purpose", "Chiqish maqsadi"
        RISK = "risk", "Xavf taqsimoti"

    group = models.CharField("guruh", max_length=16, choices=Group.choices, db_index=True)
    key = models.SlugField("kalit", max_length=40, blank=True)
    label = models.CharField("nomi", max_length=180)
    value = models.BigIntegerField("qiymati", default=0)
    tone = models.CharField("rangi", max_length=16, choices=TONE_CHOICES, default="lapis")

    class Meta(OrderedModel.Meta):
        verbose_name = "taqsimot bo‘lagi"
        verbose_name_plural = "taqsimot bo‘laklari"

    def __str__(self) -> str:
        return f"{self.get_group_display()}: {self.label}"


class TimeSeries(TimeStampedModel):
    """12 oylik grafik qatori."""

    MONTHS = 12

    key = models.SlugField("kalit", max_length=32, unique=True)
    name = models.CharField("qator nomi", max_length=120)
    color = models.CharField("rangi", max_length=32, default="var(--turk)")
    monthly_values = models.JSONField("oylik qiymatlar", default=list)

    class Meta:
        verbose_name = "grafik qatori"
        verbose_name_plural = "grafik qatorlari"
        ordering = ["key"]

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        from django.core.exceptions import ValidationError

        if len(self.monthly_values) != self.MONTHS:
            raise ValidationError({"monthly_values": f"{self.MONTHS} ta qiymat bo‘lishi kerak"})

    @property
    def total(self) -> int:
        return sum(int(v or 0) for v in self.monthly_values)


class AiInsight(OrderedModel):
    """Model aniqlagan tendensiya yoki anomaliya."""

    class Tag(models.TextChoices):
        GROWTH = "O‘SISH", "O‘sish"
        ANOMALY = "ANOMALIYA", "Anomaliya"
        FORECAST = "PROGNOZ", "Prognoz"
        POSITIVE = "IJOBIY", "Ijobiy"
        WARNING = "OGOHLANTIRISH", "Ogohlantirish"

    tag = models.CharField("belgi", max_length=24, choices=Tag.choices, default=Tag.FORECAST)
    title = models.CharField("sarlavha", max_length=250)
    body = models.TextField("tavsif")
    recommended_action = models.CharField("tavsiya etilgan chora", max_length=250, blank=True)
    confidence = models.PositiveSmallIntegerField(
        "ishonch, %", default=80,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    tone = models.CharField("rangi", max_length=16, choices=TONE_CHOICES, default="lapis")

    class Meta(OrderedModel.Meta):
        verbose_name = "AI insayt"
        verbose_name_plural = "AI insaytlar"

    def __str__(self) -> str:
        return self.title


class AiSuggestion(OrderedModel):
    """Tabiiy tildagi tayyor savol."""

    text = models.CharField("savol matni", max_length=250, unique=True)

    class Meta(OrderedModel.Meta):
        verbose_name = "AI savoli"
        verbose_name_plural = "AI savollari"

    def __str__(self) -> str:
        return self.text


class Integration(TimeStampedModel):
    """Ulangan yoki rejadagi tashqi tizim."""

    class Status(models.TextChoices):
        CONNECTED = "Ulangan", "Ulangan"
        TESTING = "Sinovda", "Sinovda"
        PLANNED = "Rejada", "Rejada"

    name = models.CharField("tizim nomi", max_length=180, unique=True)
    status = models.CharField(
        "holati", max_length=16, choices=Status.choices, default=Status.PLANNED,
    )

    class Meta:
        verbose_name = "integratsiya"
        verbose_name_plural = "integratsiyalar"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class RiskWeight(OrderedModel):
    """AI xavf modelidagi omil vazni."""

    key = models.SlugField("kalit", max_length=32, unique=True)
    label = models.CharField("omil nomi", max_length=180)
    weight = models.PositiveSmallIntegerField(
        "vazni, %", default=10,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    class Meta(OrderedModel.Meta):
        verbose_name = "model omili"
        verbose_name_plural = "model omillari"

    def __str__(self) -> str:
        return f"{self.label} — {self.weight}%"


class ReportTemplate(OrderedModel):
    """Hisobot shabloni."""

    class Period(models.TextChoices):
        DAILY = "Kunlik", "Kunlik"
        WEEKLY = "Haftalik", "Haftalik"
        MONTHLY = "Oylik", "Oylik"
        QUARTERLY = "Choraklik", "Choraklik"
        YEARLY = "Yillik", "Yillik"

    name = models.CharField("shablon nomi", max_length=180, unique=True)
    description = models.TextField("tavsifi", blank=True)
    period = models.CharField(
        "davriyligi", max_length=16, choices=Period.choices, default=Period.MONTHLY,
    )
    formats = models.CharField("formatlar", max_length=90, default="XLSX, PDF")
    tone = models.CharField("rangi", max_length=16, choices=TONE_CHOICES, default="lapis")

    class Meta(OrderedModel.Meta):
        verbose_name = "hisobot shabloni"
        verbose_name_plural = "hisobot shablonlari"

    def __str__(self) -> str:
        return self.name

    @property
    def format_list(self) -> list[str]:
        return [item.strip() for item in self.formats.split(",") if item.strip()]


class ReportArchiveEntry(TimeStampedModel):
    """Shakllantirilgan hisobot arxivi."""

    name = models.CharField("hisobot nomi", max_length=250)
    size = models.CharField("hajmi", max_length=32, blank=True)
    generated_on = models.DateField("sanasi", null=True, blank=True)
    generated_by = models.CharField("kim shakllantirgan", max_length=64, blank=True)

    class Meta:
        verbose_name = "arxiv yozuvi"
        verbose_name_plural = "hisobot arxivi"
        ordering = ["-generated_on", "-id"]

    def __str__(self) -> str:
        return self.name
