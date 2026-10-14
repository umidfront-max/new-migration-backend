"""Reyestr serializerlari."""
from collections.abc import Mapping

from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from apps.geography.models import Country, District, Region

from .models import Employer, Migrant, passport_validator
from .services import calculate_risk_score


class MigrantSerializer(serializers.ModelSerializer):
    """
    Davlat kodi, hudud va tuman nomi bo'yicha ishlaydi.

    Tuman nomi faqat viloyat ichida noyob, shuning uchun u tanlangan viloyat
    ichidan qidiriladi. Viloyat almashsa, eski viloyatdagi tuman tozalanadi.

    `employer` — matn: reyestrda shunday nomli tashkilot bo'lsa avtomatik
    bog'lanadi, bo'lmasa erkin matn sifatida saqlanadi.
    `score` bo'sh kelsa — model o'zi hisoblaydi.
    """

    name = serializers.CharField(source="full_name")
    passport = serializers.CharField(
        source="passport_number", required=False, allow_blank=True, allow_null=True,
        max_length=9,
        validators=[
            passport_validator,
            UniqueValidator(
                queryset=Migrant.objects.all(),
                message="Bu pasport seriya-raqami bilan migrant allaqachon mavjud",
            ),
        ],
    )
    countryCode = serializers.SlugRelatedField(
        source="country", slug_field="code", queryset=Country.objects.all(),
    )
    country = serializers.CharField(source="country.name", read_only=True)
    flag = serializers.CharField(source="country.flag", read_only=True)
    region = serializers.SlugRelatedField(slug_field="name", queryset=Region.objects.all())
    district = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    remit = serializers.CharField(source="remittance_band", required=False, allow_blank=True)
    marital = serializers.CharField(source="marital_status", required=False, allow_blank=True)
    health = serializers.CharField(source="health_status", required=False)
    convicted = serializers.BooleanField(source="is_convicted", required=False)
    employer = serializers.CharField(
        source="employer_name", required=False, allow_blank=True,
    )
    employerId = serializers.PrimaryKeyRelatedField(source="employer", read_only=True)
    risk = serializers.CharField(source="legal_status", required=False)
    score = serializers.IntegerField(source="risk_score", required=False, allow_null=True)
    exitDate = serializers.DateField(
        source="exit_date", required=False, allow_null=True, format="%d.%m.%Y",
        input_formats=["%d.%m.%Y", "%Y-%m-%d"],
    )

    class Meta:
        model = Migrant
        fields = [
            "id", "pinfl", "passport", "name", "nationality", "gender", "speciality",
            "countryCode", "country", "flag", "region", "district", "purpose",
            "remit", "marital", "health", "convicted",
            "employer", "employerId", "address", "phone",
            "risk", "score", "exitDate",
        ]

    def to_internal_value(self, data) -> dict:
        if isinstance(data, Mapping):
            data = data.copy()
            for key in ("pinfl", "passport"):
                if isinstance(data.get(key), str):
                    value = data[key].strip()
                    if key == "passport":
                        value = "".join(value.split()).upper()
                    data[key] = value or None
        return super().to_internal_value(data)

    def to_representation(self, migrant: Migrant) -> dict:
        data = super().to_representation(migrant)
        data["district"] = migrant.district.name if migrant.district_id else None
        return data

    def validate(self, attrs: dict) -> dict:
        pinfl = attrs.get("pinfl", getattr(self.instance, "pinfl", None))
        passport = attrs.get("passport_number", getattr(self.instance, "passport_number", None))
        if not pinfl and not passport:
            message = "PINFL yoki pasport seriya-raqamidan bittasini kiriting"
            raise serializers.ValidationError({"pinfl": message, "passport": message})
        if pinfl and passport:
            message = "Faqat bitta hujjatni kiriting: PINFL yoki pasport seriya-raqami"
            raise serializers.ValidationError({"pinfl": message, "passport": message})

        region = attrs["region"] if "region" in attrs else getattr(self.instance, "region", None)
        touched = self.instance is None or "region" in attrs or "district" in attrs

        if "district" in attrs:
            name = (attrs.pop("district") or "").strip()
            if not name:
                attrs["district"] = None
            elif region is None:
                raise serializers.ValidationError({"district": "Avval viloyatni tanlang"})
            else:
                district = District.objects.filter(region=region, name=name).first()
                if district is None:
                    raise serializers.ValidationError(
                        {"district": f"“{region.name}” da bunday tuman yo‘q"},
                    )
                attrs["district"] = district
        elif self.instance is not None and self.instance.district_id and "region" in attrs:
            # Viloyat almashdi, tuman yuborilmadi — eski tuman endi mos emas
            if self.instance.district.region_id != getattr(region, "id", None):
                attrs["district"] = None

        # Hududning tumanlari bor bo'lsa — chiqqan tuman ham ko'rsatilishi shart
        district = attrs["district"] if "district" in attrs else getattr(self.instance, "district", None)
        if touched and region is not None and district is None and region.districts.exists():
            raise serializers.ValidationError({"district": "Chiqqan tumanni tanlang"})

        return attrs

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
        migrant = super().create(self._apply_auto_score(validated_data))
        migrant.link_employer()
        migrant.save(update_fields=["employer"])
        return migrant

    def update(self, instance: Migrant, validated_data: dict) -> Migrant:
        migrant = super().update(instance, self._apply_auto_score(validated_data, instance))
        if "employer_name" in validated_data:
            migrant.employer = None
            migrant.link_employer()
            migrant.save(update_fields=["employer"])
        return migrant


class EmployerSerializer(serializers.ModelSerializer):
    """
    Davlatlar ro'yxatdan tanlanadi, `formal` tanlovdan kelib chiqadi.

    Yuborilgan migrantlar va jo'natma formada kiritilmaydi — faqat o'qiladi.
    """

    dir = serializers.CharField(source="direction")
    countries = serializers.SlugRelatedField(
        slug_field="name", queryset=Country.objects.all(), many=True,
    )
    employment = serializers.ChoiceField(
        source="employment_type", choices=Employer.Employment.choices, required=False,
    )
    sent = serializers.IntegerField(source="sent_count", read_only=True)
    remit = serializers.IntegerField(source="remittance_amount", read_only=True)
    formal = serializers.IntegerField(source="formal_share", read_only=True)
    migrantCount = serializers.IntegerField(source="migrants.count", read_only=True)

    class Meta:
        model = Employer
        fields = [
            "id", "name", "dir", "countries", "employment",
            "sent", "remit", "formal", "migrantCount", "status",
        ]

    def validate_countries(self, value: list) -> list:
        if not value:
            raise serializers.ValidationError("Kamida bitta davlat tanlanishi kerak")
        return value
