"""Monitoring API'si."""
from rest_framework.decorators import action
from rest_framework.response import Response

from core.export import CsvExportMixin
from core.viewsets import AuditedModelViewSet

from .models import (
    ConsulateCase,
    ConsulateService,
    ReturnProgram,
    SosChannel,
    SosEvent,
    ViolationType,
)
from .serializers import (
    ConsulateCaseSerializer,
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


class SosEventViewSet(CsvExportMixin, AuditedModelViewSet):
    queryset = SosEvent.objects.select_related("country").all()
    serializer_class = SosEventSerializer
    audit_label = "SOS murojaat"
    filterset_fields = ["severity", "is_resolved", "country__code"]
    search_fields = ["applicant_name", "city", "event_type", "code"]
    ordering_fields = ["minutes_ago", "created_at"]

    export_filename = "sos-murojaatlar"
    export_headers = [
        "Raqami", "Murojaatchi", "Davlat", "Shahar", "Turi",
        "Jiddiyligi", "Necha daqiqa oldin", "Telefon", "Hal etilgan",
    ]

    def export_row(self, event: SosEvent) -> list:
        return [
            event.code, event.applicant_name, event.country.name, event.city,
            event.event_type, event.get_severity_display(), event.minutes_ago,
            event.phone, "ha" if event.is_resolved else "yo‘q",
        ]

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        """Murojaatni hal etilgan deb belgilaydi."""
        event = self.get_object()
        if event.is_resolved:
            return Response({"detail": "Murojaat allaqachon yopilgan"}, status=409)
        event.is_resolved = True
        event.save(update_fields=["is_resolved"])
        self.write_audit("yopildi")
        return Response(self.get_serializer(event).data)

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        """Yopilgan murojaatni qayta ochadi."""
        event = self.get_object()
        event.is_resolved = False
        event.save(update_fields=["is_resolved"])
        self.write_audit("qayta ochildi")
        return Response(self.get_serializer(event).data)


class SosChannelViewSet(AuditedModelViewSet):
    queryset = SosChannel.objects.all()
    serializer_class = SosChannelSerializer
    audit_label = "SOS kanali"


class ConsulateCaseViewSet(AuditedModelViewSet):
    queryset = ConsulateCase.objects.select_related("country").all()
    serializer_class = ConsulateCaseSerializer
    audit_label = "Konsullik ishi"
    filterset_fields = ["stage", "country__code"]
    search_fields = ["code", "applicant_name", "subject"]
    ordering_fields = ["created_at", "stage"]


class ConsulateServiceViewSet(AuditedModelViewSet):
    queryset = ConsulateService.objects.all()
    serializer_class = ConsulateServiceSerializer
    audit_label = "Konsullik xizmati"


class ReturnProgramViewSet(AuditedModelViewSet):
    queryset = ReturnProgram.objects.all()
    serializer_class = ReturnProgramSerializer
    audit_label = "Reintegratsiya dasturi"
