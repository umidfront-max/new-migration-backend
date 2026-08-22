"""Reyestr testlari: risk ball, ish beruvchi, filtrlar."""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import AuditLogEntry, Role, User
from apps.geography.models import Country, Region

from .models import Employer, Migrant
from .services import calculate_risk_score


class RiskScoreTests(APITestCase):
    """`calculate_risk_score` frontenddagi mantiq bilan bir xil bo'lishi kerak."""

    def test_clean_profile_scores_low(self) -> None:
        score = calculate_risk_score(
            country_risk=24, purpose="Ishlash (rasmiy)",
            legal_status="Xavf yo‘q", employer_name="Hanwha Corp.",
        )
        self.assertEqual(score, 16)

    def test_informal_work_adds_points(self) -> None:
        formal = calculate_risk_score(country_risk=62, purpose="Ishlash (rasmiy)",
                                      employer_name="Ozon Logistics")
        informal = calculate_risk_score(country_risk=62, purpose="Ishlash (norasmiy)",
                                        employer_name="Ozon Logistics")
        self.assertEqual(informal - formal, 16)

    def test_wanted_status_raises_score(self) -> None:
        score = calculate_risk_score(
            country_risk=62, purpose="Ishlash (norasmiy)", legal_status="Qidiruvda",
            is_convicted=True, employer_name="Ro‘yxatdan o‘tmagan",
        )
        self.assertGreaterEqual(score, 90)

    def test_score_never_leaves_bounds(self) -> None:
        lowest = calculate_risk_score(country_risk=0, employer_name="Rasmiy MChJ")
        highest = calculate_risk_score(
            country_risk=100, purpose="Ishlash (norasmiy)",
            legal_status="Bedarak yo‘qolgan", is_convicted=True,
            employer_name="", health_status="Nogironlik",
        )
        self.assertGreaterEqual(lowest, 4)
        self.assertLessEqual(highest, 96)


class MigrantApiTests(APITestCase):
    """Migrant qo'shishda ball bo'sh qolsa avtomatik hisoblanishi kerak."""

    def setUp(self) -> None:
        self.role = Role.objects.create(name="Super administrator", scope="Butun tizim")
        self.user = User.objects.create_user(
            "admin.test", "demo-parol-123", full_name="Test Admin", role=self.role,
        )
        self.country = Country.objects.create(
            code="RU", name="Rossiya", latitude=55.75, longitude=37.62, risk_score=62,
        )
        self.region = Region.objects.create(
            name="Toshkent viloyati", latitude=40.9, longitude=69.9,
        )
        self.client.force_authenticate(self.user)

    def payload(self, **overrides) -> dict:
        data = {
            "pinfl": "12345678901234",
            "name": "Karimov Jasur",
            "countryCode": "RU",
            "region": "Toshkent viloyati",
            "purpose": "Ishlash (norasmiy)",
            "employer": "Ro‘yxatdan o‘tmagan",
        }
        data.update(overrides)
        return data

    def test_score_is_calculated_when_omitted(self) -> None:
        response = self.client.post(reverse("migrant-list"), self.payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["score"], 57)

    def test_explicit_score_is_kept(self) -> None:
        response = self.client.post(
            reverse("migrant-list"), self.payload(score=12), format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["score"], 12)

    def test_pinfl_must_be_fourteen_digits(self) -> None:
        response = self.client.post(
            reverse("migrant-list"), self.payload(pinfl="123"), format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("pinfl", response.data)

    def test_create_writes_audit_entry(self) -> None:
        self.client.post(reverse("migrant-list"), self.payload(), format="json")
        entry = AuditLogEntry.objects.first()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.actor_login, "admin.test")
        self.assertIn("qo‘shildi", entry.action)

    def test_risky_filter(self) -> None:
        Migrant.objects.create(
            pinfl="11111111111111", full_name="Toza", country=self.country,
            region=self.region, legal_status=Migrant.LegalStatus.CLEAR,
        )
        Migrant.objects.create(
            pinfl="22222222222222", full_name="Qidiruvda", country=self.country,
            region=self.region, legal_status=Migrant.LegalStatus.WANTED,
        )
        response = self.client.get(reverse("migrant-list"), {"risky": "true"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Qidiruvda")


class EmployerApiTests(APITestCase):
    """Ish beruvchida davlatlar tanlovi va shartnoma turi."""

    def setUp(self) -> None:
        self.role = Role.objects.create(name="Super administrator")
        self.user = User.objects.create_user(
            "admin.test", "demo-parol-123", full_name="Test Admin", role=self.role,
        )
        Country.objects.create(code="RU", name="Rossiya", latitude=55.7, longitude=37.6)
        Country.objects.create(code="KZ", name="Qozog‘iston", latitude=43.2, longitude=76.8)
        self.client.force_authenticate(self.user)

    def test_countries_are_required(self) -> None:
        response = self.client.post(reverse("employer-list"), {
            "name": "Bo‘sh MChJ", "dir": "IT", "countries": [],
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("countries", response.data)

    def test_formal_share_follows_employment_type(self) -> None:
        response = self.client.post(reverse("employer-list"), {
            "name": "Norasmiy MChJ", "dir": "Qurilish",
            "countries": ["Rossiya"], "employment": "Norasmiy bandlik",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["formal"], 0)

        employer = Employer.objects.get(name="Norasmiy MChJ")
        self.assertTrue(employer.is_informal)
        self.assertEqual([c.name for c in employer.countries.all()], ["Rossiya"])

    def test_multiple_countries_are_linked(self) -> None:
        response = self.client.post(reverse("employer-list"), {
            "name": "Ikki yo‘nalish", "dir": "Logistika",
            "countries": ["Rossiya", "Qozog‘iston"], "employment": "Rasmiy shartnoma",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(sorted(response.data["countries"]), ["Qozog‘iston", "Rossiya"])
        self.assertEqual(response.data["formal"], 100)
