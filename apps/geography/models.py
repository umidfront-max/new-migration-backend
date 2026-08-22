"""Davlatlar, hududlar, tumanlar va chegara o'tkazish punktlari."""
from django.db import models

from core.models import TimeStampedModel


class Country(TimeStampedModel):
    """Qabul qiluvchi davlat va u bo'yicha migratsiya ko'rsatkichlari."""

    code = models.CharField("kodi", max_length=2, unique=True)
    name = models.CharField("nomi", max_length=120)
    flag = models.CharField("bayrog‘i", max_length=8, blank=True)
    hub = models.CharField("asosiy shahri", max_length=120, blank=True)

    latitude = models.FloatField("kengligi")
    longitude = models.FloatField("uzunligi")
    azimuth = models.PositiveSmallIntegerField("yo‘nalish burchagi", default=0)
    distance_km = models.PositiveIntegerField("masofa, km", default=0)

    total = models.PositiveIntegerField("jami migrantlar", default=0)
    departed = models.PositiveIntegerField("chiqqanlar", default=0)
    returned = models.PositiveIntegerField("qaytganlar", default=0)

    # chiqish maqsadi kesimi
    work = models.PositiveIntegerField("ishlash", default=0)
    study = models.PositiveIntegerField("o‘qish", default=0)
    medical = models.PositiveIntegerField("davolanish", default=0)
    residence = models.PositiveIntegerField("doimiy yashash", default=0)
    travel = models.PositiveIntegerField("sayohat", default=0)

    # alohida nazorat
    wanted = models.PositiveIntegerField("qidiruvdagilar", default=0)
    jailed = models.PositiveIntegerField("jazoni o‘tayotganlar", default=0)
    missing = models.PositiveIntegerField("bedarak yo‘qolganlar", default=0)

    remittance_amount = models.PositiveIntegerField("jo‘natma, mln $", default=0)
    remittance_count = models.PositiveIntegerField("jo‘natmalar soni, ming", default=0)
    risk_score = models.PositiveSmallIntegerField("xavf indeksi", default=0)

    class Meta:
        verbose_name = "davlat"
        verbose_name_plural = "davlatlar"
        ordering = ["-total", "name"]

    def __str__(self) -> str:
        return f"{self.flag} {self.name}".strip()

    @property
    def purpose_total(self) -> int:
        """Maqsadlar bo'yicha yig'indi — nomuvofiqlikni tekshirish uchun."""
        return self.work + self.study + self.medical + self.residence + self.travel


class Region(TimeStampedModel):
    """Chiqish hududi (viloyat)."""

    name = models.CharField("nomi", max_length=120, unique=True)
    latitude = models.FloatField("kengligi")
    longitude = models.FloatField("uzunligi")
    departed = models.PositiveIntegerField("chiqqanlar", default=0)
    returned = models.PositiveIntegerField("qaytganlar", default=0)
    risk_score = models.PositiveSmallIntegerField("xavf darajasi", default=0)

    class Meta:
        verbose_name = "hudud"
        verbose_name_plural = "hududlar"
        ordering = ["-departed", "name"]

    def __str__(self) -> str:
        return self.name


class District(TimeStampedModel):
    """Viloyat tumani."""

    region = models.ForeignKey(
        Region, verbose_name="viloyat", on_delete=models.CASCADE, related_name="districts",
    )
    name = models.CharField("nomi", max_length=120)
    departed = models.PositiveIntegerField("chiqqanlar", default=0)
    returned = models.PositiveIntegerField("qaytganlar", default=0)
    risk_score = models.PositiveSmallIntegerField("xavf darajasi", default=0)

    class Meta:
        verbose_name = "tuman"
        verbose_name_plural = "tumanlar"
        ordering = ["-departed", "name"]
        constraints = [
            models.UniqueConstraint(fields=["region", "name"], name="unique_district_per_region"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.region.name})"


class BorderPoint(TimeStampedModel):
    """Chegaradan o'tkazish punkti."""

    region = models.ForeignKey(
        Region, verbose_name="viloyat", on_delete=models.PROTECT, related_name="border_points",
    )
    name = models.CharField("punkt nomi", max_length=180)
    outbound = models.PositiveIntegerField("chiqish", default=0)
    inbound = models.PositiveIntegerField("kirish", default=0)
    load_percent = models.PositiveSmallIntegerField("yuklama, %", default=0)

    class Meta:
        verbose_name = "o‘tkazish punkti"
        verbose_name_plural = "o‘tkazish punktlari"
        ordering = ["-load_percent", "name"]

    def __str__(self) -> str:
        return self.name

    @property
    def is_overloaded(self) -> bool:
        """Yuklama 85% dan oshsa navbat rejimi yoqiladi."""
        return self.load_percent >= 85


class BorderSource(TimeStampedModel):
    """Chegara moduliga ulangan tashqi ma'lumot manbai."""

    class Status(models.TextChoices):
        CONNECTED = "ulangan", "Ulangan"
        TESTING = "sinovda", "Sinovda"
        PLANNED = "rejada", "Rejada"

    name = models.CharField("manba nomi", max_length=180, unique=True)
    status = models.CharField(
        "holati", max_length=16, choices=Status.choices, default=Status.CONNECTED,
    )

    class Meta:
        verbose_name = "ma’lumot manbai"
        verbose_name_plural = "ma’lumot manbalari"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
