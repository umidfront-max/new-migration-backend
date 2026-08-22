"""
Audit jurnaliga yozadigan asosiy ViewSet.

Frontenddagi `db.js` dagi `trace()` bilan bir xil mantiq: har bir qo'shish,
o'zgartirish va o'chirish jurnalga tushadi.
"""
from rest_framework import viewsets

from apps.accounts.models import AuditLogEntry


def client_ip(request) -> str:
    """So'rov kelgan IP manzil (proksi orqasida ham to'g'ri ishlaydi)."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "") or "0.0.0.0"


class AuditedModelViewSet(viewsets.ModelViewSet):
    """
    Yozuv ustidagi amallarni audit jurnaliga qaydlaydi.

    Merosxo'r sinf `audit_label` ni belgilaydi — jurnalda shu nom ko'rinadi.
    """

    audit_label: str = "Yozuv"

    def write_audit(self, verb: str) -> None:
        user = self.request.user if self.request.user.is_authenticated else None
        AuditLogEntry.objects.create(
            user=user,
            actor_login=getattr(user, "login", "mehmon"),
            role_name=getattr(getattr(user, "role", None), "name", "—"),
            action=f"{self.audit_label} {verb}",
            ip_address=client_ip(self.request),
            is_success=True,
        )

    def perform_create(self, serializer) -> None:
        serializer.save()
        self.write_audit("qo‘shildi")

    def perform_update(self, serializer) -> None:
        serializer.save()
        self.write_audit("o‘zgartirildi")

    def perform_destroy(self, instance) -> None:
        instance.delete()
        self.write_audit("o‘chirildi")
