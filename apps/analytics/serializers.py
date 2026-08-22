"""Analitika serializerlari."""
from rest_framework import serializers

from .models import (
    AiInsight,
    AiSuggestion,
    Integration,
    MetricTile,
    ReportArchiveEntry,
    ReportTemplate,
    RiskWeight,
    ShareSlice,
    TimeSeries,
)


class MetricTileSerializer(serializers.ModelSerializer):
    sub = serializers.CharField(source="subtitle", required=False, allow_blank=True)

    class Meta:
        model = MetricTile
        fields = ["id", "group", "key", "label", "value", "delta", "sub", "tone", "position"]


class ShareSliceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShareSlice
        fields = ["id", "group", "key", "label", "value", "tone", "position"]


class TimeSeriesSerializer(serializers.ModelSerializer):
    values = serializers.ListField(
        source="monthly_values", child=serializers.IntegerField(), min_length=12, max_length=12,
    )
    total = serializers.IntegerField(read_only=True)

    class Meta:
        model = TimeSeries
        fields = ["id", "key", "name", "color", "values", "total"]


class AiInsightSerializer(serializers.ModelSerializer):
    action = serializers.CharField(
        source="recommended_action", required=False, allow_blank=True,
    )

    class Meta:
        model = AiInsight
        fields = ["id", "tag", "title", "body", "action", "confidence", "tone", "position"]


class AiSuggestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AiSuggestion
        fields = ["id", "text", "position"]


class IntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Integration
        fields = ["id", "name", "status"]


class RiskWeightSerializer(serializers.ModelSerializer):
    w = serializers.IntegerField(source="weight", required=False)

    class Meta:
        model = RiskWeight
        fields = ["id", "key", "label", "w", "position"]


class ReportTemplateSerializer(serializers.ModelSerializer):
    desc = serializers.CharField(source="description", required=False, allow_blank=True)
    fmt = serializers.CharField(source="formats", required=False)
    formatList = serializers.ListField(source="format_list", read_only=True)

    class Meta:
        model = ReportTemplate
        fields = ["id", "name", "desc", "period", "fmt", "formatList", "tone", "position"]


class ReportArchiveEntrySerializer(serializers.ModelSerializer):
    at = serializers.DateField(
        source="generated_on", required=False, allow_null=True,
        format="%d.%m.%Y", input_formats=["%d.%m.%Y", "%Y-%m-%d"],
    )
    by = serializers.CharField(source="generated_by", required=False, allow_blank=True)

    class Meta:
        model = ReportArchiveEntry
        fields = ["id", "name", "size", "at", "by"]
