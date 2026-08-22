"""Django admin — geografiya."""
from django.contrib import admin

from .models import BorderPoint, BorderSource, Country, District, Region


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "hub", "total", "risk_score", "remittance_amount")
    search_fields = ("code", "name", "hub")
    list_filter = ("risk_score",)


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("name", "departed", "returned", "risk_score")
    search_fields = ("name",)


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ("name", "region", "departed", "returned", "risk_score")
    list_filter = ("region",)
    search_fields = ("name",)


@admin.register(BorderPoint)
class BorderPointAdmin(admin.ModelAdmin):
    list_display = ("name", "region", "outbound", "inbound", "load_percent")
    list_filter = ("region",)
    search_fields = ("name",)


@admin.register(BorderSource)
class BorderSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "status")
    list_filter = ("status",)
