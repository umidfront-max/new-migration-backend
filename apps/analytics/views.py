"""Analitika API'si va umumlashtirilgan dashboard endpointi."""
from datetime import date

from django.db.models import Count, Sum
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.geography.models import BorderPoint, Country, Region
from apps.monitoring.models import SosEvent, ViolationType
from apps.registry.models import Employer, Migrant

DATASET_MODELS = {
    "migrants": Migrant,
    "employers": Employer,
    "sos-events": SosEvent,
}
from core.pagination import LargePagination
from core.reports import build_dataset_csv
from core.viewsets import AuditedModelViewSet

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
from .serializers import (
    AiInsightSerializer,
    DashboardSummarySerializer,
    AiSuggestionSerializer,
    IntegrationSerializer,
    MetricTileSerializer,
    ReportArchiveEntrySerializer,
    ReportTemplateSerializer,
    RiskWeightSerializer,
    ShareSliceSerializer,
    TimeSeriesSerializer,
)


class MetricTileViewSet(AuditedModelViewSet):
    """`?group=dashboard` bilan kerakli to'plam olinadi."""

    queryset = MetricTile.objects.all()
    serializer_class = MetricTileSerializer
    pagination_class = LargePagination
    audit_label = "Ko‘rsatkich"
    filterset_fields = ["group"]
    ordering_fields = ["position", "value"]


class ShareSliceViewSet(AuditedModelViewSet):
    queryset = ShareSlice.objects.all()
    serializer_class = ShareSliceSerializer
    pagination_class = LargePagination
    audit_label = "Taqsimot bo‘lagi"
    filterset_fields = ["group"]
    ordering_fields = ["position", "value"]


class TimeSeriesViewSet(AuditedModelViewSet):
    queryset = TimeSeries.objects.all()
    serializer_class = TimeSeriesSerializer
    audit_label = "Grafik qatori"
    lookup_field = "key"


class AiInsightViewSet(AuditedModelViewSet):
    queryset = AiInsight.objects.all()
    serializer_class = AiInsightSerializer
    audit_label = "AI insayt"
    filterset_fields = ["tag"]
    search_fields = ["title", "body"]
    ordering_fields = ["confidence", "position"]


class AiSuggestionViewSet(AuditedModelViewSet):
    queryset = AiSuggestion.objects.all()
    serializer_class = AiSuggestionSerializer
    audit_label = "AI savoli"


class IntegrationViewSet(AuditedModelViewSet):
    queryset = Integration.objects.all()
    serializer_class = IntegrationSerializer
    pagination_class = LargePagination
    audit_label = "Integratsiya"
    filterset_fields = ["status"]
    search_fields = ["name"]


class RiskWeightViewSet(AuditedModelViewSet):
    queryset = RiskWeight.objects.all()
    serializer_class = RiskWeightSerializer
    audit_label = "Model omili"


class ReportTemplateViewSet(AuditedModelViewSet):
    queryset = ReportTemplate.objects.all()
    serializer_class = ReportTemplateSerializer
    audit_label = "Hisobot shabloni"
    filterset_fields = ["period"]
    search_fields = ["name", "description"]

    @action(detail=True, methods=["post"])
    def generate(self, request, pk=None):
        """
        Shablon bo'yicha hisobot shakllantiradi.

        Arxivga yozuv qo'shiladi va uning `dataset` maydoni orqali faylni
        `/api/report-archive/{id}/download/` dan olish mumkin.
        """
        template = self.get_object()
        today = date.today()
        model = DATASET_MODELS.get(template.dataset, Migrant)
        row_count = model.objects.count()

        entry = ReportArchiveEntry.objects.create(
            name=f"{template.name} — {today.strftime('%Y-%m-%d')}",
            dataset=template.dataset,
            row_count=row_count,
            size=f"{row_count} qator",
            generated_on=today,
            generated_by=getattr(request.user, "login", "tizim"),
        )
        self.write_audit("shakllantirildi")
        return Response(
            {
                "template": ReportTemplateSerializer(template).data,
                "archive": ReportArchiveEntrySerializer(entry).data,
                "detail": f"Hisobot shakllantirildi — {row_count} qator",
            },
            status=201,
        )


class ReportArchiveViewSet(AuditedModelViewSet):
    queryset = ReportArchiveEntry.objects.all()
    serializer_class = ReportArchiveEntrySerializer
    audit_label = "Arxiv yozuvi"
    filterset_fields = ["dataset"]
    search_fields = ["name", "generated_by"]

    @action(detail=True, methods=["get"], throttle_classes=[ScopedRateThrottle])
    def download(self, request, pk=None):
        """Arxiv yozuvining ma'lumotini CSV ko'rinishida beradi."""
        entry = self.get_object()
        response = build_dataset_csv(entry.dataset, entry.name)
        if response is None:
            return Response({"detail": "Bu to‘plam uchun eksport yo‘q"}, status=400)

        self.write_audit("yuklab olindi")
        return response

    download.throttle_scope = "export"


class DashboardSummaryView(APIView):
    """
    Boshqaruv paneli uchun yig'ma ko'rsatkichlar.

    Bir so'rovda hisoblanadi — frontend har bir jadvalni alohida
    so'ramasligi uchun.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = DashboardSummarySerializer

    @extend_schema(
        summary="Boshqaruv paneli uchun yig‘ma ko‘rsatkichlar",
        responses={200: DashboardSummarySerializer},
    )
    def get(self, request):
        countries = Country.objects.aggregate(
            total=Sum("total"),
            departed=Sum("departed"),
            returned=Sum("returned"),
            wanted=Sum("wanted"),
            jailed=Sum("jailed"),
            missing=Sum("missing"),
            remittance=Sum("remittance_amount"),
        )
        border = BorderPoint.objects.aggregate(
            outbound=Sum("outbound"), inbound=Sum("inbound"),
        )
        employers = Employer.objects.aggregate(
            sent=Sum("sent_count"), count=Count("id"),
        )
        formal_sent = (
            Employer.objects
            .filter(employment_type=Employer.Employment.FORMAL)
            .aggregate(sent=Sum("sent_count"))["sent"] or 0
        )
        total_sent = employers["sent"] or 0

        return Response({
            "countries": {**{k: v or 0 for k, v in countries.items()},
                          "count": Country.objects.count()},
            "regions": {"count": Region.objects.count()},
            "border": {k: v or 0 for k, v in border.items()},
            "registry": {
                "count": Migrant.objects.count(),
                "atRisk": Migrant.objects.exclude(
                    legal_status=Migrant.LegalStatus.CLEAR,
                ).count(),
            },
            "employers": {
                "count": employers["count"] or 0,
                "sent": total_sent,
                "formalShare": round(formal_sent / total_sent * 100) if total_sent else 0,
            },
            "sos": {
                "open": SosEvent.objects.filter(is_resolved=False).count(),
                "urgent": SosEvent.objects.filter(
                    severity__in=[SosEvent.Severity.CRITICAL, SosEvent.Severity.HIGH],
                    is_resolved=False,
                ).count(),
            },
            "violations": {
                "total": ViolationType.objects.aggregate(t=Sum("value"))["t"] or 0,
            },
        })
