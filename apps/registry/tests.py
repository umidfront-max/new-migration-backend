"""Reyestr testlari: risk ball, ish beruvchi, filtrlar."""
from django.db import IntegrityError, transaction
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import AuditLogEntry, Role, User
from apps.geography.models import Country, District, Region

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

    def test_passport_only_migrants_can_be_created(self) -> None:
        for passport in ("AA1234567", "AB7654321"):
            with self.subTest(passport=passport):
                payload = self.payload(passport=passport)
                payload.pop("pinfl")
                response = self.client.post(reverse("migrant-list"), payload, format="json")
                self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
                self.assertIsNone(response.data["pinfl"])
                self.assertEqual(response.data["passport"], passport)
                self.assertEqual(Migrant.objects.get(pk=response.data["id"]).passport_number, passport)
        self.assertEqual(Migrant.objects.filter(pinfl__isnull=True).count(), 2)

    def test_passport_is_normalized_before_uniqueness_check(self) -> None:
        response = self.client.post(
            reverse("migrant-list"), self.payload(pinfl="", passport=" ab 1234567 "), format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["passport"], "AB1234567")
        self.assertIsNone(response.data["pinfl"])
        duplicate = self.client.post(
            reverse("migrant-list"), self.payload(pinfl=None, passport="ab1234567"), format="json",
        )
        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("passport", duplicate.data)

    def test_passport_format_is_validated(self) -> None:
        for passport in ("123456789", "A12345678", "ABC123456", "AA123456", "AA12345678", "AA123456X"):
            with self.subTest(passport=passport):
                response = self.client.post(
                    reverse("migrant-list"), self.payload(pinfl=None, passport=passport), format="json",
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("passport", response.data)

    def test_exactly_one_identifier_is_required(self) -> None:
        for identifiers in ({}, {"pinfl": None, "passport": None}, {"pinfl": "", "passport": ""},
                            {"pinfl": "12345678901234", "passport": "AA1234567"}):
            with self.subTest(identifiers=identifiers):
                payload = self.payload()
                payload.pop("pinfl")
                payload.update(identifiers)
                response = self.client.post(reverse("migrant-list"), payload, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("pinfl", response.data)
                self.assertIn("passport", response.data)

    def test_pinfl_remains_unique(self) -> None:
        first = self.client.post(reverse("migrant-list"), self.payload(), format="json")
        self.assertEqual(first.status_code, status.HTTP_201_CREATED, first.data)
        duplicate = self.client.post(reverse("migrant-list"), self.payload(), format="json")
        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("pinfl", duplicate.data)

    def test_identifier_can_be_switched_and_preserved_on_partial_update(self) -> None:
        created = self.client.post(reverse("migrant-list"), self.payload(), format="json")
        detail = reverse("migrant-detail", args=[created.data["id"]])
        switched = self.client.patch(detail, {"pinfl": None, "passport": "AA1234567"}, format="json")
        self.assertEqual(switched.status_code, status.HTTP_200_OK, switched.data)
        self.assertIsNone(switched.data["pinfl"])
        self.assertEqual(switched.data["passport"], "AA1234567")
        renamed = self.client.patch(detail, {"name": "Yangilangan"}, format="json")
        self.assertEqual(renamed.status_code, status.HTTP_200_OK, renamed.data)
        self.assertEqual(renamed.data["passport"], "AA1234567")
        cleared = self.client.patch(detail, {"passport": ""}, format="json")
        self.assertEqual(cleared.status_code, status.HTTP_400_BAD_REQUEST)
        restored = self.client.patch(detail, {"pinfl": "12345678901234", "passport": None}, format="json")
        self.assertEqual(restored.status_code, status.HTTP_200_OK, restored.data)
        self.assertEqual(restored.data["pinfl"], "12345678901234")
        self.assertIsNone(restored.data["passport"])

    def test_passport_is_searchable_and_exported(self) -> None:
        created = self.client.post(
            reverse("migrant-list"), self.payload(pinfl=None, passport="AA1234567"), format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        searched = self.client.get(reverse("migrant-list"), {"search": "aa1234567"})
        self.assertEqual(searched.status_code, status.HTTP_200_OK, searched.data)
        self.assertEqual(searched.data["count"], 1)
        self.assertEqual(searched.data["results"][0]["id"], created.data["id"])
        exported = self.client.get(reverse("migrant-export"), {"search": "AA1234567"})
        self.assertEqual(exported.status_code, status.HTTP_200_OK)
        self.assertIn("Pasport seriya-raqami", exported.content.decode("utf-8-sig"))
        self.assertIn("AA1234567", exported.content.decode("utf-8-sig"))

    def test_database_requires_exactly_one_nonempty_identifier(self) -> None:
        for identifiers in ({}, {"pinfl": ""}, {"passport_number": ""},
                            {"pinfl": "12345678901234", "passport_number": "AA1234567"}):
            with self.subTest(identifiers=identifiers):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    Migrant.objects.create(
                        full_name="Hujjatsiz", country=self.country, region=self.region, **identifiers,
                    )

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

    def test_district_is_saved_within_region(self) -> None:
        District.objects.create(region=self.region, name="Zangiota")
        response = self.client.post(
            reverse("migrant-list"), self.payload(district="Zangiota"), format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["district"], "Zangiota")
        self.assertEqual(Migrant.objects.get().district.name, "Zangiota")

    def test_district_of_other_region_is_rejected(self) -> None:
        other = Region.objects.create(name="Samarqand", latitude=39.6, longitude=66.9)
        District.objects.create(region=other, name="Urgut")
        response = self.client.post(
            reverse("migrant-list"), self.payload(district="Urgut"), format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("district", response.data)

    def test_region_change_clears_district(self) -> None:
        district = District.objects.create(region=self.region, name="Zangiota")
        Region.objects.create(name="Samarqand", latitude=39.6, longitude=66.9)
        migrant = Migrant.objects.create(
            pinfl="44444444444444", full_name="Ko‘chgan", country=self.country,
            region=self.region, district=district,
        )
        response = self.client.patch(
            reverse("migrant-detail", args=[migrant.pk]), {"region": "Samarqand"}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertIsNone(response.data["district"])

    def test_district_required_when_region_has_districts(self) -> None:
        District.objects.create(region=self.region, name="Zangiota")
        response = self.client.post(reverse("migrant-list"), self.payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("district", response.data)

    def test_sent_count_follows_linked_migrants(self) -> None:
        first = Employer.objects.create(name="Birinchi MChJ", direction="IT", sent_count=999)
        second = Employer.objects.create(name="Ikkinchi MChJ", direction="IT")
        response = self.client.post(
            reverse("migrant-list"), self.payload(employer="Birinchi MChJ"), format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        first.refresh_from_db()
        self.assertEqual(first.sent_count, 1)

        migrant_id = response.data["id"]
        self.client.patch(
            reverse("migrant-detail", args=[migrant_id]), {"employer": "Ikkinchi MChJ"},
            format="json",
        )
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual((first.sent_count, second.sent_count), (0, 1))

        self.client.delete(reverse("migrant-detail", args=[migrant_id]))
        second.refresh_from_db()
        self.assertEqual(second.sent_count, 0)

    def test_district_filter(self) -> None:
        zangiota = District.objects.create(region=self.region, name="Zangiota")
        Migrant.objects.create(
            pinfl="55555555555555", full_name="Zangiotalik", country=self.country,
            region=self.region, district=zangiota,
        )
        Migrant.objects.create(
            pinfl="66666666666666", full_name="Tumansiz", country=self.country,
            region=self.region,
        )
        response = self.client.get(reverse("migrant-list"), {"district": "Zangiota"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Zangiotalik")


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

    def test_export_returns_csv_with_related_countries(self) -> None:
        """`prefetch_related` bilan eksport — chunk_size bo'lmasa 500 beradi."""
        employer = Employer.objects.create(
            name="Eksport MChJ", direction="Logistika", sent_count=120,
        )
        employer.countries.set(Country.objects.all())

        response = self.client.get(reverse("employer-export"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("text/csv", response["Content-Type"])

        body = response.content.decode("utf-8-sig")
        self.assertIn("Eksport MChJ", body)
        # Davlatlar Country.Meta.ordering bo'yicha chiqadi — tartibga bog'lanmaymiz
        self.assertIn("Rossiya", body)
        self.assertIn("Qozog‘iston", body)

    def test_migrant_export_includes_employer_label(self) -> None:
        region = Region.objects.create(name="Samarqand", latitude=39.6, longitude=66.9)
        country = Country.objects.get(code="RU")
        employer = Employer.objects.create(name="Ozon Logistics", direction="Logistika")
        Migrant.objects.create(
            pinfl="33333333333333", full_name="Eksport Migrant",
            country=country, region=region, employer=employer,
        )
        response = self.client.get(reverse("migrant-export"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Ozon Logistics", response.content.decode("utf-8-sig"))

    def test_multiple_countries_are_linked(self) -> None:
        response = self.client.post(reverse("employer-list"), {
            "name": "Ikki yo‘nalish", "dir": "Logistika",
            "countries": ["Rossiya", "Qozog‘iston"], "employment": "Rasmiy shartnoma",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(sorted(response.data["countries"]), ["Qozog‘iston", "Rossiya"])
        self.assertEqual(response.data["formal"], 100)

    def test_sent_and_remit_are_read_only(self) -> None:
        """Yuborilganlar va jo'natma formada kiritilmaydi — kelgan qiymat e'tiborsiz."""
        response = self.client.post(reverse("employer-list"), {
            "name": "Statistika MChJ", "dir": "IT", "countries": ["Rossiya"],
            "sent": 500, "remit": 40,
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        employer = Employer.objects.get(name="Statistika MChJ")
        self.assertEqual((employer.sent_count, employer.remittance_amount), (0, 0))
