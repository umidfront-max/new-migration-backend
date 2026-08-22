"""Reyestr API'si."""
from django_filters import rest_framework as filters

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


class MigrantViewSet(AuditedModelViewSet):
    queryset = Migrant.objects.select_related("country", "region").all()
    serializer_class = MigrantSerializer
    filterset_class = MigrantFilter
    audit_label = "Reyestr yozuvi"
    search_fields = ["full_name", "pinfl", "phone"]
    ordering_fields = ["full_name", "risk_score", "exit_date", "created_at"]


class EmployerViewSet(AuditedModelViewSet):
    queryset = Employer.objects.prefetch_related("countries").all()
    serializer_class = EmployerSerializer
    audit_label = "Ish beruvchi"
    filterset_fields = ["status", "employment_type", "direction"]
    search_fields = ["name", "direction"]
    ordering_fields = ["sent_count", "remittance_amount", "name"]
