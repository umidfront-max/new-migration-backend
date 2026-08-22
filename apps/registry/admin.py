"""Django admin — reyestr."""
from django.contrib import admin

from .models import Employer, Migrant


@admin.register(Migrant)
class MigrantAdmin(admin.ModelAdmin):
    list_display = ("full_name", "pinfl", "gender", "country", "region",
                    "legal_status", "risk_score")
    list_filter = ("gender", "legal_status", "purpose", "country")
    search_fields = ("full_name", "pinfl", "phone")
    autocomplete_fields = ("country", "region")


@admin.register(Employer)
class EmployerAdmin(admin.ModelAdmin):
    list_display = ("name", "direction", "employment_type", "sent_count", "status")
    list_filter = ("status", "employment_type", "direction")
    search_fields = ("name",)
    filter_horizontal = ("countries",)
