"""Django admin — foydalanuvchilar va jurnal."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import AuditLogEntry, Role, SystemSetting, User


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "scope", "capacity", "tone")
    search_fields = ("name", "scope")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("full_name",)
    list_display = ("login", "full_name", "role", "unit", "status", "is_staff")
    list_filter = ("status", "role", "is_staff", "is_superuser")
    search_fields = ("login", "full_name", "unit")
    fieldsets = (
        (None, {"fields": ("login", "password")}),
        ("Shaxsiy ma’lumot", {"fields": ("full_name", "unit", "phone")}),
        ("Huquqlar", {"fields": ("role", "status", "is_active", "is_staff",
                                 "is_superuser", "groups", "user_permissions")}),
        ("Sanalar", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("login", "full_name", "role", "password1", "password2"),
        }),
    )
    readonly_fields = ("last_login", "date_joined")


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ("label", "key", "kind", "number_value", "is_enabled")
    list_filter = ("kind",)


@admin.register(AuditLogEntry)
class AuditLogEntryAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor_login", "role_name", "action", "ip_address", "is_success")
    list_filter = ("is_success", "role_name")
    search_fields = ("actor_login", "action")
    readonly_fields = [field.name for field in AuditLogEntry._meta.fields]

    def has_add_permission(self, request) -> bool:
        """Jurnal o'zgarmas — qo'lda yozuv qo'shilmaydi."""
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False
