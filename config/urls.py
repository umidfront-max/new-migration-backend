"""
API yo'nalishlari.

Endpoint nomlari frontenddagi to'plam nomlari bilan mos keladi, shuning uchun
`src/stores/db.js` ni API chaqiruvlariga o'tkazish oson.
"""
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import (
    AuditLogViewSet,
    CurrentUserView,
    LoginView,
    LogoutView,
    RoleViewSet,
    SystemSettingViewSet,
    UserViewSet,
)
from apps.analytics.views import (
    AiInsightViewSet,
    AiSuggestionViewSet,
    DashboardSummaryView,
    IntegrationViewSet,
    MetricTileViewSet,
    ReportArchiveViewSet,
    ReportTemplateViewSet,
    RiskWeightViewSet,
    ShareSliceViewSet,
    TimeSeriesViewSet,
)
from apps.geography.views import (
    BorderPointViewSet,
    BorderSourceViewSet,
    CountryViewSet,
    DistrictViewSet,
    RegionViewSet,
)
from apps.monitoring.views import (
    ConsulateServiceViewSet,
    ReturnProgramViewSet,
    SosChannelViewSet,
    SosEventViewSet,
    ViolationTypeViewSet,
)
from apps.registry.views import EmployerViewSet, MigrantViewSet

router = DefaultRouter()

# foydalanuvchilar va tizim
router.register("users", UserViewSet, basename="user")
router.register("roles", RoleViewSet, basename="role")
router.register("settings", SystemSettingViewSet, basename="setting")
router.register("audit-log", AuditLogViewSet, basename="audit-log")

# geografiya
router.register("countries", CountryViewSet, basename="country")
router.register("regions", RegionViewSet, basename="region")
router.register("districts", DistrictViewSet, basename="district")
router.register("border-points", BorderPointViewSet, basename="border-point")
router.register("border-sources", BorderSourceViewSet, basename="border-source")

# reyestr
router.register("migrants", MigrantViewSet, basename="migrant")
router.register("employers", EmployerViewSet, basename="employer")

# monitoring
router.register("violations", ViolationTypeViewSet, basename="violation")
router.register("sos-events", SosEventViewSet, basename="sos-event")
router.register("sos-channels", SosChannelViewSet, basename="sos-channel")
router.register("consulate-services", ConsulateServiceViewSet, basename="consulate-service")
router.register("return-programs", ReturnProgramViewSet, basename="return-program")

# analitika
router.register("metrics", MetricTileViewSet, basename="metric")
router.register("shares", ShareSliceViewSet, basename="share")
router.register("series", TimeSeriesViewSet, basename="series")
router.register("ai-insights", AiInsightViewSet, basename="ai-insight")
router.register("ai-suggestions", AiSuggestionViewSet, basename="ai-suggestion")
router.register("integrations", IntegrationViewSet, basename="integration")
router.register("risk-weights", RiskWeightViewSet, basename="risk-weight")
router.register("report-templates", ReportTemplateViewSet, basename="report-template")
router.register("report-archive", ReportArchiveViewSet, basename="report-archive")

auth_patterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", CurrentUserView.as_view(), name="current-user"),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include((auth_patterns, "auth"))),
    path("api/dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("api/", include(router.urls)),
]
