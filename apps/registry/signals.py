"""Migrant o'zgarganda ish beruvchining "yuborilgan migrantlar" sonini yangilaydi."""
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .models import Employer, Migrant


@receiver(pre_save, sender=Migrant)
def remember_previous_employer(sender, instance: Migrant, **kwargs) -> None:
    """Ish beruvchi almashsa, eskisining soni ham kamayishi kerak."""
    instance._previous_employer_id = (
        Migrant.objects.filter(pk=instance.pk).values_list("employer_id", flat=True).first()
        if instance.pk else None
    )


@receiver(post_save, sender=Migrant)
def recount_after_save(sender, instance: Migrant, raw: bool = False, **kwargs) -> None:
    if raw:
        return
    previous = getattr(instance, "_previous_employer_id", None)
    if previous != instance.employer_id or kwargs.get("created"):
        Employer.recount_sent([previous, instance.employer_id])


@receiver(post_delete, sender=Migrant)
def recount_after_delete(sender, instance: Migrant, **kwargs) -> None:
    Employer.recount_sent([instance.employer_id])
