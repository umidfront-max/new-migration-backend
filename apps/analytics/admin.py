"""Django admin — analitika."""
from django.contrib import admin

from .models import (
    AiInsight, AiSuggestion, Integration, MetricTile,
    ReportArchiveEntry, ReportTemplate, RiskWeight, ShareSlice, TimeSeries,
)


@admin.register(MetricTile)
class MetricTileAdmin(admin.ModelAdmin):
    list_display = ("label", "group", "value", "delta", "tone", "position")
    list_filter = ("group",)


@admin.register(ShareSlice)
class ShareSliceAdmin(admin.ModelAdmin):
    list_display = ("label", "group", "value", "tone", "position")
    list_filter = ("group",)


@admin.register(TimeSeries)
class TimeSeriesAdmin(admin.ModelAdmin):
    list_display = ("name", "key", "total")


@admin.register(AiInsight)
class AiInsightAdmin(admin.ModelAdmin):
    list_display = ("title", "tag", "confidence", "tone")
    list_filter = ("tag",)


admin.site.register([AiSuggestion, Integration, RiskWeight, ReportTemplate, ReportArchiveEntry])

admin.site.site_header = "Migratsiya monitoringi"
admin.site.site_title = "Migratsiya monitoringi"
admin.site.index_title = "Boshqaruv"
