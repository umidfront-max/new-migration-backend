"""Django admin — monitoring."""
from django.contrib import admin

from .models import ConsulateService, ReturnProgram, SosChannel, SosEvent, ViolationType


@admin.register(ViolationType)
class ViolationTypeAdmin(admin.ModelAdmin):
    list_display = ("label", "key", "value", "delta")


@admin.register(SosEvent)
class SosEventAdmin(admin.ModelAdmin):
    list_display = ("code", "applicant_name", "country", "city", "severity", "is_resolved")
    list_filter = ("severity", "is_resolved", "country")
    search_fields = ("code", "applicant_name", "city", "event_type")


@admin.register(SosChannel)
class SosChannelAdmin(admin.ModelAdmin):
    list_display = ("name", "share", "icon")


@admin.register(ConsulateService)
class ConsulateServiceAdmin(admin.ModelAdmin):
    list_display = ("label", "value", "tone")


@admin.register(ReturnProgram)
class ReturnProgramAdmin(admin.ModelAdmin):
    list_display = ("name", "completed", "target", "completion_percent")
