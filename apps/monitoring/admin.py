"""Django admin — monitoring."""
from django.contrib import admin

from .models import (
    ConsulateCase,
    ConsulateService,
    ReturnProgram,
    SosChannel,
    SosEvent,
    ViolationType,
)


@admin.register(ConsulateCase)
class ConsulateCaseAdmin(admin.ModelAdmin):
    list_display = ("code", "subject", "country", "stage", "created_at")
    list_filter = ("stage", "country")
    search_fields = ("code", "applicant_name", "subject")


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
