"""Analitika testlari: guruhlar, grafik qatorlari, yig'ma, hisobot."""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.geography.models import BorderPoint, Country, Region
from apps.monitoring.models import SosEvent, ViolationType
from apps.registry.models import Employer, Migrant

from .models import MetricTile, ReportArchiveEntry, ReportTemplate, ShareSlice, TimeSeries


class MetricAndShareTests(APITestCase):
    def setUp(self) -> None:
        role = Role.objects.create(name="Super administrator")
        self.client.force_authenticate(
            User.objects.create_user("a.test", "kuchli-parol-123",
                                     full_name="A", role=role),
        )
        MetricTile.objects.create(group="dashboard", label="Jami migrantlar", value=2148630)
        MetricTile.objects.create(group="dashboard", label="Chiqqanlar", value=486210)
        MetricTile.objects.create(group="sos", label="Jami chaqiruvlar", value=1247)
        ShareSlice.objects.create(group="purpose", label="Ishlash", value=214800)
        ShareSlice.objects.create(group="composition", label="Erkaklar", value=1712904)

    def test_metrics_are_filtered_by_group(self) -> None:
        response = self.client.get(reverse("metric-list"), {"group": "dashboard"})
        self.assertEqual(response.data["count"], 2)
        response = self.client.get(reverse("metric-list"), {"group": "sos"})
        self.assertEqual(response.data["count"], 1)

    def test_shares_are_filtered_by_group(self) -> None:
        response = self.client.get(reverse("share-list"), {"group": "purpose"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["label"], "Ishlash")

    def test_subtitle_is_exposed_as_sub(self) -> None:
        response = self.client.post(reverse("metric-list"), {
            "group": "dashboard", "label": "Yangi", "value": 10,
            "sub": "izoh matni", "tone": "turk",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["sub"], "izoh matni")


class TimeSeriesTests(APITestCase):
    def setUp(self) -> None:
        role = Role.objects.create(name="Super administrator")
        self.client.force_authenticate(
            User.objects.create_user("a.test", "kuchli-parol-123",
                                     full_name="A", role=role),
        )

    def test_series_requires_twelve_values(self) -> None:
        response = self.client.post(reverse("series-list"), {
            "key": "out", "name": "Chiqqanlar", "values": [1, 2, 3],
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("values", response.data)

    def test_series_accepts_twelve_values_and_totals_them(self) -> None:
        response = self.client.post(reverse("series-list"), {
            "key": "out", "name": "Chiqqanlar", "values": list(range(1, 13)),
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["total"], 78)

    def test_series_lookup_is_by_key(self) -> None:
        TimeSeries.objects.create(
            key="remit", name="Jo‘natmalar", monthly_values=[10] * 12,
        )
        response = self.client.get(reverse("series-detail", args=["remit"]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Jo‘natmalar")


class ReportTests(APITestCase):
    def setUp(self) -> None:
        role = Role.objects.create(name="Super administrator")
        self.user = User.objects.create_user(
            "a.test", "kuchli-parol-123", full_name="A", role=role,
        )
        self.client.force_authenticate(self.user)
        self.template = ReportTemplate.objects.create(
            name="Umumiy migratsiya holati", period="Oylik", formats="XLSX, PDF",
        )

    def test_format_list_is_split(self) -> None:
        self.assertEqual(self.template.format_list, ["XLSX", "PDF"])

    def test_generate_records_dataset_and_row_count(self) -> None:
        """Shakllantirilgan hisobot qaysi to'plamdan olinganini eslab qoladi."""
        Country.objects.create(code="RU", name="Rossiya", latitude=55.7, longitude=37.6)
        region = Region.objects.create(name="Samarqand", latitude=39.6, longitude=66.9)
        Migrant.objects.create(
            pinfl="11111111111111", full_name="A",
            country=Country.objects.first(), region=region,
        )
        response = self.client.post(
            reverse("report-template-generate", args=[self.template.pk]),
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        entry = ReportArchiveEntry.objects.first()
        self.assertEqual(entry.dataset, "migrants")
        self.assertEqual(entry.row_count, 1)
        self.assertEqual(entry.size, "1 qator")

    def test_archive_download_returns_csv(self) -> None:
        Country.objects.create(code="RU", name="Rossiya", latitude=55.7, longitude=37.6)
        region = Region.objects.create(name="Samarqand", latitude=39.6, longitude=66.9)
        Migrant.objects.create(
            pinfl="22222222222222", full_name="Yuklab olinadi",
            country=Country.objects.first(), region=region,
        )
        entry = ReportArchiveEntry.objects.create(
            name="Sinov hisoboti — 2026", dataset="migrants", row_count=1,
        )
        response = self.client.get(reverse("report-archive-download", args=[entry.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn("Yuklab olinadi", response.content.decode("utf-8-sig"))

    def test_download_filename_header_is_ascii_safe(self) -> None:
        """Lotin bo'lmagan belgi sarlavhani MIME-kodlanishiga olib kelmasligi kerak."""
        entry = ReportArchiveEntry.objects.create(
            name="Umumiy migratsiya holati — 2026-iyul", dataset="migrants",
        )
        response = self.client.get(reverse("report-archive-download", args=[entry.pk]))
        disposition = response["Content-Disposition"]
        self.assertFalse(disposition.startswith("=?"), disposition)
        self.assertIn("filename=\"umumiy-migratsiya-holati", disposition)
        self.assertIn("filename*=UTF-8''", disposition)

    def test_generate_adds_archive_entry(self) -> None:
        response = self.client.post(
            reverse("report-template-generate", args=[self.template.pk]),
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(ReportArchiveEntry.objects.count(), 1)

        entry = ReportArchiveEntry.objects.first()
        self.assertIn("Umumiy migratsiya holati", entry.name)
        self.assertEqual(entry.generated_by, "a.test")


class DashboardSummaryTests(APITestCase):
    def setUp(self) -> None:
        role = Role.objects.create(name="Super administrator")
        self.client.force_authenticate(
            User.objects.create_user("a.test", "kuchli-parol-123",
                                     full_name="A", role=role),
        )
        country = Country.objects.create(
            code="RU", name="Rossiya", latitude=55.7, longitude=37.6,
            total=1000, departed=400, returned=300, wanted=20,
            jailed=10, missing=5, remittance_amount=800, risk_score=62,
        )
        region = Region.objects.create(name="Toshkent viloyati", latitude=40.9, longitude=69.9)
        BorderPoint.objects.create(region=region, name="Punkt", outbound=100, inbound=80)

        Migrant.objects.create(
            pinfl="11111111111111", full_name="Toza", country=country, region=region,
        )
        Migrant.objects.create(
            pinfl="22222222222222", full_name="Qidiruvda", country=country, region=region,
            legal_status=Migrant.LegalStatus.WANTED,
        )
        formal = Employer.objects.create(
            name="Rasmiy", direction="IT", sent_count=600,
            employment_type=Employer.Employment.FORMAL,
        )
        informal = Employer.objects.create(
            name="Norasmiy", direction="Qurilish", sent_count=400,
            employment_type=Employer.Employment.INFORMAL,
        )
        formal.countries.add(country)
        informal.countries.add(country)

        SosEvent.objects.create(
            code="SOS-1", applicant_name="A", country=country, city="Moskva",
            event_type="Qamoqqa olingan", severity="critical",
        )
        SosEvent.objects.create(
            code="SOS-2", applicant_name="B", country=country, city="Kazan",
            event_type="Yopilgan", severity="low", is_resolved=True,
        )
        ViolationType.objects.create(key="deport", label="Deportatsiya", value=8412)

    def test_summary_aggregates_everything(self) -> None:
        response = self.client.get(reverse("dashboard-summary"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        self.assertEqual(data["countries"]["total"], 1000)
        self.assertEqual(data["countries"]["jailed"], 10)
        self.assertEqual(data["countries"]["count"], 1)
        self.assertEqual(data["border"]["outbound"], 100)
        self.assertEqual(data["registry"]["count"], 2)
        self.assertEqual(data["registry"]["atRisk"], 1)
        self.assertEqual(data["employers"]["sent"], 1000)
        self.assertEqual(data["employers"]["formalShare"], 60)
        self.assertEqual(data["sos"]["open"], 1)
        self.assertEqual(data["violations"]["total"], 8412)

    def test_summary_survives_empty_database(self) -> None:
        # Country ga PROTECT bilan bog'langan — avval bog'liq yozuvlar
        Migrant.objects.all().delete()
        SosEvent.objects.all().delete()
        Employer.objects.all().delete()
        Country.objects.all().delete()
        response = self.client.get(reverse("dashboard-summary"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["countries"]["total"], 0)
        self.assertEqual(response.data["employers"]["formalShare"], 0)
