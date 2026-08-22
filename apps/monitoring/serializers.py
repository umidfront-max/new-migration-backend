"""Monitoring serializerlari."""
from rest_framework import serializers

from apps.geography.models import Country

from .models import ConsulateService, ReturnProgram, SosChannel, SosEvent, ViolationType


class ViolationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ViolationType
        fields = ["id", "key", "label", "value", "delta", "tone", "position"]


class SosEventSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="applicant_name")
    countryCode = serializers.SlugRelatedField(
        source="country", slug_field="code", queryset=Country.objects.all(),
    )
    country = serializers.CharField(source="country.name", read_only=True)
    flag = serializers.CharField(source="country.flag", read_only=True)
    lat = serializers.FloatField(source="latitude", required=False, allow_null=True)
    lng = serializers.FloatField(source="longitude", required=False, allow_null=True)
    type = serializers.CharField(source="event_type")
    minutesAgo = serializers.IntegerField(source="minutes_ago", required=False)
    resolved = serializers.BooleanField(source="is_resolved", required=False)

    class Meta:
        model = SosEvent
        fields = [
            "id", "code", "name", "countryCode", "country", "flag", "city",
            "lat", "lng", "type", "severity", "minutesAgo", "phone", "resolved",
        ]

    def create(self, validated_data: dict) -> SosEvent:
        """Kod berilmasa avtomatik raqamlanadi; koordinata davlat markazidan olinadi."""
        country = validated_data.get("country")
        if not validated_data.get("code"):
            validated_data["code"] = f"SOS-{SosEvent.objects.count() + 1001}"
        if validated_data.get("latitude") is None and country:
            validated_data["latitude"] = country.latitude
        if validated_data.get("longitude") is None and country:
            validated_data["longitude"] = country.longitude
        return super().create(validated_data)


class SosChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = SosChannel
        fields = ["id", "name", "share", "icon", "position"]


class ConsulateServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsulateService
        fields = ["id", "label", "value", "tone", "position"]


class ReturnProgramSerializer(serializers.ModelSerializer):
    done = serializers.IntegerField(source="completed", required=False)
    percent = serializers.IntegerField(source="completion_percent", read_only=True)

    class Meta:
        model = ReturnProgram
        fields = ["id", "name", "done", "target", "tone", "percent", "position"]
