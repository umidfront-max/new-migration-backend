"""Barcha ilovalar uchun umumiy abstrakt modellar."""
from django.db import models


class TimeStampedModel(models.Model):
    """Yaratilgan va o'zgartirilgan vaqtni saqlaydi."""

    created_at = models.DateTimeField("yaratilgan", auto_now_add=True)
    updated_at = models.DateTimeField("o'zgartirilgan", auto_now=True)

    class Meta:
        abstract = True


class OrderedModel(TimeStampedModel):
    """Ko'rsatish tartibi muhim bo'lgan yozuvlar uchun."""

    position = models.PositiveIntegerField("tartib", default=0, db_index=True)

    class Meta:
        abstract = True
        ordering = ["position", "id"]
