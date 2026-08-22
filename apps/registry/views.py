"""Reyestr API'si."""
from django_filters import rest_framework as filters

from core.export import CsvExportMixin
from core.viewsets import AuditedModelViewSet

from .models import Employer, Migrant
from .serializers import EmployerSerializer, MigrantSerializer


class MigrantFilter(filters.FilterSet):
    """Frontenddagi filtrlar bilan bir xil: davlat, jins, xavf holati."""

    country = filters.CharFilter(field_name="country__code", lookup_expr="iexact")
    region = filters.CharFilter(field_name="region__name", lookup_expr="iexact")
    risky = filters.BooleanFilter(method="filter_risky")

    class Meta:
        model = Migrant
        fields = ["country", "region", "gender", "purpose", "legal_status"]

    def filter_risky(self, queryset, name, value):
        """`?risky=true` — huquqiy holati toza bo'lmaganlar."""
        if value is None:
            return queryset
        clear = Migrant.LegalStatus.CLEAR
        return queryset.exclude(legal_status=clear) if value else queryset.filter(legal_status=clear)


class MigrantViewSet(CsvExportMixin, AuditedModelViewSet):
    queryset = Migrant.objects.select_related("country", "region", "employer").all()
    serializer_class = MigrantSerializer
    filterset_class = MigrantFilter
    audit_label = "Reyestr yozuvi"
    search_fields = ["full_name", "pinfl", "phone"]
    ordering_fields = ["full_name", "risk_score", "exit_date", "created_at"]

    export_filename = "migrantlar"
    export_headers = [
        "PINFL", "F.I.Sh", "Jinsi", "Millati", "Mutaxassisligi",
        "Davlat", "Hudud", "Maqsad", "Ish beruvchi",
        "Holati", "Risk ball", "Chiqish sanasi", "Telefon",
    ]

    def export_row(self, migrant: Migrant) -> list:
        return [
            migrant.pinfl, migrant.full_name, migrant.gender, migrant.nationality,
            migrant.speciality, migrant.country.name, migrant.region.name,
            migrant.purpose, migrant.employer_label, migrant.legal_status,
            migrant.risk_score,
            migrant.exit_date.strftime("%d.%m.%Y") if migrant.exit_date else "",
            migrant.phone,
        ]


class EmployerViewSet(CsvExportMixin, AuditedModelViewSet):
    queryset = Employer.objects.prefetch_related("countries").all()
    serializer_class = EmployerSerializer
    audit_label = "Ish beruvchi"
    filterset_fields = ["status", "employment_type", "direction"]
    search_fields = ["name", "direction"]
    ordering_fields = ["sent_count", "remittance_amount", "name"]

    export_filename = "ish-beruvchilar"
    export_headers = [
        "Kompaniya", "Yo‘nalishi", "Davlatlar", "Shartnoma",
        "Yuborilgan", "Jo‘natma (mln $)", "Holati",
    ]

    def export_row(self, employer: Employer) -> list:
        return [
            employer.name, employer.direction,
            ", ".join(country.name for country in employer.countries.all()),
            employer.employment_type, employer.sent_count,
            employer.remittance_amount, employer.status,
        ]
