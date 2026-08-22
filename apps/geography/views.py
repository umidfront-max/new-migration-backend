"""Geografiya API'si."""
from core.pagination import LargePagination
from core.viewsets import AuditedModelViewSet

from .models import BorderPoint, BorderSource, Country, District, Region
from .serializers import (
    BorderPointSerializer,
    BorderSourceSerializer,
    CountrySerializer,
    DistrictSerializer,
    RegionSerializer,
)


class CountryViewSet(AuditedModelViewSet):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    pagination_class = LargePagination
    audit_label = "Davlat"
    lookup_field = "code"
    search_fields = ["name", "code", "hub"]
    ordering_fields = ["total", "risk_score", "remittance_amount", "name"]


class RegionViewSet(AuditedModelViewSet):
    queryset = Region.objects.all()
    serializer_class = RegionSerializer
    pagination_class = LargePagination
    audit_label = "Hudud"
    search_fields = ["name"]
    ordering_fields = ["departed", "returned", "risk_score", "name"]


class DistrictViewSet(AuditedModelViewSet):
    queryset = District.objects.select_related("region").all()
    serializer_class = DistrictSerializer
    pagination_class = LargePagination
    audit_label = "Tuman"
    filterset_fields = ["region__name"]
    search_fields = ["name"]
    ordering_fields = ["departed", "returned", "risk_score", "name"]


class BorderPointViewSet(AuditedModelViewSet):
    queryset = BorderPoint.objects.select_related("region").all()
    serializer_class = BorderPointSerializer
    audit_label = "O‘tkazish punkti"
    filterset_fields = ["region__name"]
    search_fields = ["name"]
    ordering_fields = ["load_percent", "outbound", "inbound", "name"]


class BorderSourceViewSet(AuditedModelViewSet):
    queryset = BorderSource.objects.all()
    serializer_class = BorderSourceSerializer
    audit_label = "Ma’lumot manbai"
    filterset_fields = ["status"]
    search_fields = ["name"]
