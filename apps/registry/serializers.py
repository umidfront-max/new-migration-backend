"""Reyestr serializerlari."""
from rest_framework import serializers

from apps.geography.models import Country, Region

from .models import Employer, Migrant
from .services import calculate_risk_score


class MigrantSerializer(serializers.ModelSerializer):
    """
    Davlat kodi va hudud nomi bo'yicha ishlaydi.
    `score` bo'sh kelsa — model o'zi hisoblaydi.
    """

    name = serializers.CharField(source="full_name")
    countryCode = serializers.SlugRelatedField(
        source="country", slug_field="code", queryset=Country.objects.all(),
    )
    country = serializers.CharField(source="country.name", read_only=True)
    flag = serializers.CharField(source="country.flag", read_only=True)
    region = serializers.SlugRelatedField(slug_field="name", queryset=Region.objects.all())

    remit = serializers.CharField(source="remittance_band", required=False, allow_blank=True)
    marital = serializers.CharField(source="marital_status", required=False, allow_blank=True)
    health = serializers.CharField(source="health_status", required=False)
    convicted = serializers.BooleanField(source="is_convicted", required=False)
    employer = serializers.CharField(source="employer_name", required=False, allow_blank=True)
    risk = serializers.CharField(source="legal_status", required=False)
    score = serializers.IntegerField(source="risk_score", required=False, allow_null=True)
    exitDate = serializers.DateField(
        source="exit_date", required=False, allow_null=True, format="%d.%m.%Y",
        input_formats=["%d.%m.%Y", "%Y-%m-%d"],
    )

    class Meta:
        model = Migrant
        fields = [
            "id", "pinfl", "name", "nationality", "gender", "speciality",
            "countryCode", "country", "flag", "region", "purpose",
            "remit", "marital", "health", "convicted",
            "employer", "address", "phone",
            "risk", "score", "exitDate",
        ]

    def _apply_auto_score(self, validated: dict, instance: Migrant | None = None) -> dict:
        """Ball berilmagan bo'lsa modeldan hisoblab qo'yadi."""
        if validated.get("risk_score") is not None:
            return validated

        country = validated.get("country") or getattr(instance, "country", None)
        validated["risk_score"] = calculate_risk_score(
            country_risk=getattr(country, "risk_score", 30),
            purpose=validated.get("purpose") or getattr(instance, "purpose", ""),
            legal_status=validated.get("legal_status") or getattr(instance, "legal_status", ""),
            is_convicted=validated.get("is_convicted", getattr(instance, "is_convicted", False)),
            employer_name=validated.get("employer_name", getattr(instance, "employer_name", "")),
            health_status=validated.get("health_status", getattr(instance, "health_status", "")),
        )
        return validated

    def create(self, validated_data: dict) -> Migrant:
        return super().create(self._apply_auto_score(validated_data))

    def update(self, instance: Migrant, validated_data: dict) -> Migrant:
        return super().update(instance, self._apply_auto_score(validated_data, instance))


class EmployerSerializer(serializers.ModelSerializer):
    """Davlatlar ro'yxatdan tanlanadi, `formal` tanlovdan kelib chiqadi."""

    dir = serializers.CharField(source="direction")
    countries = serializers.SlugRelatedField(
        slug_field="name", queryset=Country.objects.all(), many=True,
    )
    employment = serializers.ChoiceField(
        source="employment_type", choices=Employer.Employment.choices, required=False,
    )
    sent = serializers.IntegerField(source="sent_count", required=False)
    remit = serializers.IntegerField(source="remittance_amount", required=False)
    formal = serializers.IntegerField(source="formal_share", read_only=True)

    class Meta:
        model = Employer
        fields = [
            "id", "name", "dir", "countries", "employment",
            "sent", "remit", "formal", "status",
        ]

    def validate_countries(self, value: list) -> list:
        if not value:
            raise serializers.ValidationError("Kamida bitta davlat tanlanishi kerak")
        return value
