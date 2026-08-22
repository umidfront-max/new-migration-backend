"""Geografiya serializerlari — maydon nomlari frontend bilan bir xil."""
from rest_framework import serializers

from .models import BorderPoint, BorderSource, Country, District, Region


class CountrySerializer(serializers.ModelSerializer):
    lat = serializers.FloatField(source="latitude")
    lng = serializers.FloatField(source="longitude")
    angle = serializers.IntegerField(source="azimuth", required=False)
    dist = serializers.IntegerField(source="distance_km", required=False)
    out = serializers.IntegerField(source="departed", required=False)
    back = serializers.IntegerField(source="returned", required=False)
    remit = serializers.IntegerField(source="remittance_amount", required=False)
    remitCount = serializers.IntegerField(source="remittance_count", required=False)
    risk = serializers.IntegerField(source="risk_score", required=False)

    class Meta:
        model = Country
        fields = [
            "id", "code", "name", "flag", "hub", "lat", "lng", "angle", "dist",
            "total", "out", "back",
            "work", "study", "medical", "residence", "travel",
            "wanted", "jailed", "missing",
            "remit", "remitCount", "risk",
        ]

    def validate_code(self, value: str) -> str:
        return value.strip().upper()


class RegionSerializer(serializers.ModelSerializer):
    lat = serializers.FloatField(source="latitude")
    lng = serializers.FloatField(source="longitude")
    out = serializers.IntegerField(source="departed", required=False)
    back = serializers.IntegerField(source="returned", required=False)
    risk = serializers.IntegerField(source="risk_score", required=False)
    districtCount = serializers.IntegerField(source="districts.count", read_only=True)

    class Meta:
        model = Region
        fields = ["id", "name", "lat", "lng", "out", "back", "risk", "districtCount"]


class DistrictSerializer(serializers.ModelSerializer):
    region = serializers.SlugRelatedField(slug_field="name", queryset=Region.objects.all())
    out = serializers.IntegerField(source="departed", required=False)
    back = serializers.IntegerField(source="returned", required=False)
    risk = serializers.IntegerField(source="risk_score", required=False)

    class Meta:
        model = District
        fields = ["id", "region", "name", "out", "back", "risk"]


class BorderPointSerializer(serializers.ModelSerializer):
    region = serializers.SlugRelatedField(slug_field="name", queryset=Region.objects.all())
    out = serializers.IntegerField(source="outbound", required=False)
    # `in` — Python'da kalit so'z, shuning uchun manba `inbound` deb nomlangan
    load = serializers.IntegerField(source="load_percent", required=False)
    isOverloaded = serializers.BooleanField(source="is_overloaded", read_only=True)

    class Meta:
        model = BorderPoint
        fields = ["id", "region", "name", "out", "load", "isOverloaded"]

    def to_representation(self, instance: BorderPoint) -> dict:
        data = super().to_representation(instance)
        data["in"] = instance.inbound
        return data

    def to_internal_value(self, data):
        payload = data.copy()
        if "in" in payload:
            payload["inbound"] = payload.pop("in")
        validated = super().to_internal_value(payload)
        if "inbound" in payload:
            validated["inbound"] = int(payload["inbound"] or 0)
        return validated


class BorderSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = BorderSource
        fields = ["id", "name", "status"]
