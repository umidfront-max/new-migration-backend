"""Kirish huquqlari."""
from rest_framework.permissions import SAFE_METHODS, BasePermission

ADMINISTRATOR_ROLES = {
    "Super administrator",
    "Respublika administratori",
}


class IsAdministrator(BasePermission):
    """Faqat administrator rolidagi foydalanuvchi o'zgartira oladi."""

    message = "Bu amal uchun administrator huquqi kerak."

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        if user.is_superuser:
            return True
        role_name = getattr(getattr(user, "role", None), "name", "")
        return role_name in ADMINISTRATOR_ROLES


class ReadOnly(BasePermission):
    """Faqat o'qish — audit jurnali kabi o'zgarmas ma'lumot uchun."""

    def has_permission(self, request, view) -> bool:
        return request.method in SAFE_METHODS
