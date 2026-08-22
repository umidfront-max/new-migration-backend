"""Monitoring API'si."""
from core.viewsets import AuditedModelViewSet

from .models import ConsulateService, ReturnProgram, SosChannel, SosEvent, ViolationType
from .serializers import (
    ConsulateServiceSerializer,
    ReturnProgramSerializer,
    SosChannelSerializer,
    SosEventSerializer,
    ViolationTypeSerializer,
)


class ViolationTypeViewSet(AuditedModelViewSet):
    queryset = ViolationType.objects.all()
    serializer_class = ViolationTypeSerializer
    audit_label = "Qonunbuzilish turi"
    search_fields = ["label", "key"]
    ordering_fields = ["value", "delta", "label"]


class SosEventViewSet(AuditedModelViewSet):
    queryset = SosEvent.objects.select_related("country").all()
    serializer_class = SosEventSerializer
    audit_label = "SOS murojaat"
    filterset_fields = ["severity", "is_resolved", "country__code"]
    search_fields = ["applicant_name", "city", "event_type", "code"]
    ordering_fields = ["minutes_ago", "created_at"]


class SosChannelViewSet(AuditedModelViewSet):
    queryset = SosChannel.objects.all()
    serializer_class = SosChannelSerializer
    audit_label = "SOS kanali"


class ConsulateServiceViewSet(AuditedModelViewSet):
    queryset = ConsulateService.objects.all()
    serializer_class = ConsulateServiceSerializer
    audit_label = "Konsullik xizmati"


class ReturnProgramViewSet(AuditedModelViewSet):
    queryset = ReturnProgram.objects.all()
    serializer_class = ReturnProgramSerializer
    audit_label = "Reintegratsiya dasturi"
