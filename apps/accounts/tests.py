"""Autentifikatsiya, parol va huquqlar testlari."""
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .models import AuditLogEntry, Role, User


class AuthenticationTests(APITestCase):
    def setUp(self) -> None:
        self.role = Role.objects.create(name="Super administrator", scope="Butun tizim")
        self.user = User.objects.create_user(
            "admin.root", "kuchli-parol-123", full_name="A. Karimov", role=self.role,
        )
        self.blocked = User.objects.create_user(
            "bloklangan", "kuchli-parol-123", full_name="M. Yusupova",
            role=self.role, status=User.Status.BLOCKED,
        )

    def test_login_returns_token(self) -> None:
        response = self.client.post(reverse("auth:login"), {
            "login": "admin.root", "password": "kuchli-parol-123",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(response.data["token"])
        self.assertEqual(response.data["user"]["name"], "A. Karimov")
        self.assertEqual(response.data["user"]["role"], "Super administrator")

    def test_login_is_case_insensitive(self) -> None:
        response = self.client.post(reverse("auth:login"), {
            "login": "  ADMIN.ROOT  ", "password": "kuchli-parol-123",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_wrong_password_is_rejected(self) -> None:
        response = self.client.post(reverse("auth:login"), {
            "login": "admin.root", "password": "xato",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["error"], "Parol noto‘g‘ri")

    def test_unknown_login_is_rejected(self) -> None:
        response = self.client.post(reverse("auth:login"), {
            "login": "yo-q", "password": "xato",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["error"], "Bunday foydalanuvchi topilmadi")

    def test_blocked_user_cannot_sign_in(self) -> None:
        response = self.client.post(reverse("auth:login"), {
            "login": "bloklangan", "password": "kuchli-parol-123",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("bloklangan", response.data["error"].lower())

    def test_every_attempt_is_logged(self) -> None:
        self.client.post(reverse("auth:login"), {
            "login": "admin.root", "password": "xato",
        }, format="json")
        self.client.post(reverse("auth:login"), {
            "login": "admin.root", "password": "kuchli-parol-123",
        }, format="json")
        self.assertEqual(AuditLogEntry.objects.count(), 2)
        self.assertEqual(AuditLogEntry.objects.filter(is_success=False).count(), 1)

    def test_logout_removes_token(self) -> None:
        self.client.force_authenticate(self.user)
        Token.objects.create(user=self.user)
        response = self.client.post(reverse("auth:logout"))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Token.objects.filter(user=self.user).exists())

    def test_anonymous_access_is_denied(self) -> None:
        self.assertEqual(
            self.client.get(reverse("migrant-list")).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


class UserManagementTests(APITestCase):
    def setUp(self) -> None:
        self.admin_role = Role.objects.create(name="Super administrator")
        self.operator_role = Role.objects.create(name="Viloyat operatori")
        self.admin = User.objects.create_user(
            "admin.root", "kuchli-parol-123", full_name="A. Karimov", role=self.admin_role,
        )
        self.operator = User.objects.create_user(
            "operator", "kuchli-parol-123", full_name="D. Ergasheva", role=self.operator_role,
        )

    def test_admin_creates_user_with_password(self) -> None:
        self.client.force_authenticate(self.admin)
        response = self.client.post(reverse("user-list"), {
            "login": "Yangi.Xodim", "name": "Y. Xodimov",
            "role": "Viloyat operatori", "password": "yangi-parol-456",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["login"], "yangi.xodim")
        self.assertTrue(response.data["hasPassword"])
        self.assertNotIn("password", response.data)

        created = User.objects.get(login="yangi.xodim")
        self.assertTrue(created.check_password("yangi-parol-456"))

    def test_created_user_can_sign_in(self) -> None:
        self.client.force_authenticate(self.admin)
        self.client.post(reverse("user-list"), {
            "login": "yangi.xodim", "name": "Y. Xodimov",
            "role": "Viloyat operatori", "password": "yangi-parol-456",
        }, format="json")
        self.client.force_authenticate(None)

        response = self.client.post(reverse("auth:login"), {
            "login": "yangi.xodim", "password": "yangi-parol-456",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_short_password_is_rejected(self) -> None:
        self.client.force_authenticate(self.admin)
        response = self.client.post(reverse("user-list"), {
            "login": "qisqa", "name": "Q. Parol", "password": "123",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_empty_password_on_update_keeps_old_one(self) -> None:
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            reverse("user-detail", args=[self.operator.pk]),
            {"unit": "Farg‘ona viloyati", "password": ""}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.operator.refresh_from_db()
        self.assertEqual(self.operator.unit, "Farg‘ona viloyati")
        self.assertTrue(self.operator.check_password("kuchli-parol-123"))

    def test_operator_cannot_create_users(self) -> None:
        self.client.force_authenticate(self.operator)
        response = self.client.post(reverse("user-list"), {
            "login": "boshqa", "name": "B. Boshqa", "password": "kuchli-parol-123",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_operator_can_read_users(self) -> None:
        self.client.force_authenticate(self.operator)
        self.assertEqual(
            self.client.get(reverse("user-list")).status_code, status.HTTP_200_OK,
        )


class AuditLogTests(APITestCase):
    def setUp(self) -> None:
        role = Role.objects.create(name="Super administrator")
        self.admin = User.objects.create_user(
            "admin.root", "kuchli-parol-123", full_name="A. Karimov", role=role,
        )
        self.client.force_authenticate(self.admin)

    def test_audit_log_is_read_only(self) -> None:
        response = self.client.post(reverse("audit-log-list"), {
            "action": "Qo‘lda yozildi",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
