"""Autentifikatsiya va foydalanuvchilarni boshqarish."""
from django.contrib.auth import authenticate
from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsAdministrator
from core.viewsets import AuditedModelViewSet, client_ip

from .models import AuditLogEntry, Role, SystemSetting, User
from .serializers import (
    AuditLogEntrySerializer,
    CurrentUserSerializer,
    LoginSerializer,
    RoleSerializer,
    SystemSettingSerializer,
    UserSerializer,
)


def record_sign_in_attempt(login: str, ip: str, is_success: bool, reason: str = "") -> None:
    """Kirish urinishini jurnalga yozadi — muvaffaqiyatlisi ham, rad etilgani ham."""
    AuditLogEntry.objects.create(
        actor_login=login,
        role_name="—",
        action="Tizimga kirdi" if is_success else f"Kirish rad etildi: {reason}",
        ip_address=ip,
        is_success=is_success,
    )


class LoginView(APIView):
    """Login va parol bo'yicha token beradi."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        login = serializer.validated_data["login"].strip().lower()
        password = serializer.validated_data["password"]
        ip = client_ip(request)

        user = User.objects.filter(login=login).first()
        if user is None:
            record_sign_in_attempt(login, ip, False, "hisob topilmadi")
            return Response(
                {"error": "Bunday foydalanuvchi topilmadi"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if user.is_blocked:
            record_sign_in_attempt(login, ip, False, "hisob bloklangan")
            return Response(
                {"error": "Hisob bloklangan — administratorga murojaat qiling"},
                status=status.HTTP_403_FORBIDDEN,
            )

        authenticated = authenticate(request, username=login, password=password)
        if authenticated is None:
            record_sign_in_attempt(login, ip, False, "parol noto‘g‘ri")
            return Response(
                {"error": "Parol noto‘g‘ri"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        token, _ = Token.objects.get_or_create(user=authenticated)
        record_sign_in_attempt(login, ip, True)
        return Response({
            "token": token.key,
            "user": CurrentUserSerializer(authenticated).data,
        })


class LogoutView(APIView):
    """Joriy tokenni bekor qiladi."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CurrentUserView(APIView):
    """Kirgan foydalanuvchi haqidagi ma'lumot."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(CurrentUserSerializer(request.user).data)


class RoleViewSet(AuditedModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAdministrator]
    audit_label = "Rol"
    search_fields = ["name", "scope"]
    ordering_fields = ["name", "capacity"]


class UserViewSet(AuditedModelViewSet):
    queryset = User.objects.select_related("role").all()
    serializer_class = UserSerializer
    permission_classes = [IsAdministrator]
    audit_label = "Foydalanuvchi"
    filterset_fields = ["status", "role__name"]
    search_fields = ["login", "full_name", "unit"]
    ordering_fields = ["full_name", "login", "date_joined"]


class SystemSettingViewSet(AuditedModelViewSet):
    queryset = SystemSetting.objects.all()
    serializer_class = SystemSettingSerializer
    permission_classes = [IsAdministrator]
    audit_label = "Sozlama"
    lookup_field = "key"


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Jurnal faqat o'qish uchun.

    Yozuvlar tizim tomonidan qo'shiladi — API orqali tahrirlab bo'lmaydi.
    """

    queryset = AuditLogEntry.objects.select_related("user").all()
    serializer_class = AuditLogEntrySerializer
    filterset_fields = ["is_success", "actor_login"]
    search_fields = ["action", "actor_login", "role_name"]
    ordering_fields = ["created_at"]
