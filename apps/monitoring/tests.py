"""Monitoring testlari: SOS oqimi, eksport, dasturlar."""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import AuditLogEntry, Role, User
from apps.geography.models import Country

from .models import ReturnProgram, SosEvent, ViolationType


class SosEventTests(APITestCase):
    def setUp(self) -> None:
        role = Role.objects.create(name="Super administrator")
        self.user = User.objects.create_user(
            "operator.test", "kuchli-parol-123", full_name="Operator", role=role,
        )
        self.client.force_authenticate(self.user)
        self.country = Country.objects.create(
            code="RU", name="Rossiya", flag="🇷🇺",
            latitude=55.75, longitude=37.62,
        )

    def test_code_and_coordinates_are_filled_in(self) -> None:
        """Kod berilmasa avtomatik, koordinata bo'sh bo'lsa davlat markazi."""
        response = self.client.post(reverse("sos-event-list"), {
            "name": "Karimov Jasur", "countryCode": "RU", "city": "Moskva",
            "type": "Ish haqi to‘lanmagan", "severity": "high",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(response.data["code"].startswith("SOS-"))
        self.assertEqual(response.data["lat"], 55.75)
        self.assertEqual(response.data["lng"], 37.62)
        self.assertEqual(response.data["country"], "Rossiya")

    def test_resolve_closes_the_event(self) -> None:
        event = SosEvent.objects.create(
            code="SOS-1", applicant_name="A", country=self.country,
            city="Moskva", event_type="Qamoqqa olingan", severity="critical",
        )
        response = self.client.post(reverse("sos-event-resolve", args=[event.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(response.data["resolved"])
        event.refresh_from_db()
        self.assertTrue(event.is_resolved)

    def test_resolving_twice_is_rejected(self) -> None:
        event = SosEvent.objects.create(
            code="SOS-2", applicant_name="B", country=self.country,
            city="Kazan", event_type="Bog‘lanish uzilgan", is_resolved=True,
        )
        response = self.client.post(reverse("sos-event-resolve", args=[event.pk]))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_reopen_restores_the_event(self) -> None:
        event = SosEvent.objects.create(
            code="SOS-3", applicant_name="C", country=self.country,
            city="Ostona", event_type="Tibbiy yordam kerak", is_resolved=True,
        )
        response = self.client.post(reverse("sos-event-reopen", args=[event.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["resolved"])

    def test_resolve_is_written_to_audit_log(self) -> None:
        event = SosEvent.objects.create(
            code="SOS-4", applicant_name="D", country=self.country,
            city="Dubay", event_type="Hujjat musodara qilingan",
        )
        self.client.post(reverse("sos-event-resolve", args=[event.pk]))
        entry = AuditLogEntry.objects.first()
        self.assertIn("yopildi", entry.action)
        self.assertEqual(entry.actor_login, "operator.test")

    def test_urgent_property(self) -> None:
        critical = SosEvent(severity=SosEvent.Severity.CRITICAL)
        low = SosEvent(severity=SosEvent.Severity.LOW)
        self.assertTrue(critical.is_urgent)
        self.assertFalse(low.is_urgent)

    def test_export_returns_csv(self) -> None:
        SosEvent.objects.create(
            code="SOS-5", applicant_name="Eksport", country=self.country,
            city="Seul", event_type="Majburiy mehnat belgilari",
        )
        response = self.client.get(reverse("sos-event-export"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn("attachment", response["Content-Disposition"])

        body = response.content.decode("utf-8-sig")
        self.assertIn("Murojaatchi", body)
        self.assertIn("Eksport", body)

    def test_export_respects_filters(self) -> None:
        SosEvent.objects.create(
            code="SOS-6", applicant_name="Kritik", country=self.country,
            city="Moskva", event_type="Qamoqqa olingan", severity="critical",
        )
        SosEvent.objects.create(
            code="SOS-7", applicant_name="Past", country=self.country,
            city="Moskva", event_type="Yo‘lkira yo‘q", severity="low",
        )
        response = self.client.get(reverse("sos-event-export"), {"severity": "critical"})
        body = response.content.decode("utf-8-sig")
        self.assertIn("Kritik", body)
        self.assertNotIn("Past", body)


class MonitoringModelTests(APITestCase):
    def setUp(self) -> None:
        role = Role.objects.create(name="Super administrator")
        self.client.force_authenticate(
            User.objects.create_user("a.test", "kuchli-parol-123",
                                     full_name="A", role=role),
        )

    def test_return_program_percent_is_capped(self) -> None:
        program = ReturnProgram.objects.create(name="Dastur", completed=250, target=100)
        self.assertEqual(program.completion_percent, 100)

    def test_return_program_percent_handles_zero_target(self) -> None:
        program = ReturnProgram.objects.create(name="Nol", completed=10, target=0)
        self.assertEqual(program.completion_percent, 0)

    def test_violation_growth_flag(self) -> None:
        growing = ViolationType.objects.create(key="a", label="O‘smoqda", delta=4.2)
        falling = ViolationType.objects.create(key="b", label="Pasaymoqda", delta=-2.1)
        self.assertTrue(growing.is_growing)
        self.assertFalse(falling.is_growing)

    def test_violation_key_is_unique(self) -> None:
        ViolationType.objects.create(key="deport", label="Deportatsiya")
        response = self.client.post(reverse("violation-list"), {
            "key": "deport", "label": "Takror",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
