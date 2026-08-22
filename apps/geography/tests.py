"""Geografiya testlari: davlat ko'rsatkichlari, punkt, tuman."""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User

from .models import BorderPoint, Country, District, Region


class GeographyApiTests(APITestCase):
    def setUp(self) -> None:
        role = Role.objects.create(name="Super administrator")
        self.user = User.objects.create_user(
            "admin.test", "kuchli-parol-123", full_name="Test Admin", role=role,
        )
        self.client.force_authenticate(self.user)
        self.region = Region.objects.create(
            name="Toshkent viloyati", latitude=40.9, longitude=69.9,
            departed=31200, returned=22800, risk_score=30,
        )
        self.country = Country.objects.create(
            code="RU", name="Rossiya", flag="🇷🇺", hub="Moskva",
            latitude=55.75, longitude=37.62, total=1184300,
            departed=268400, returned=171200, work=214800, study=8400,
            medical=5100, residence=21600, travel=18500,
            wanted=1420, jailed=2840, missing=312,
            remittance_amount=4820, remittance_count=1180, risk_score=62,
        )

    def test_country_exposes_all_indicators(self) -> None:
        response = self.client.get(reverse("country-detail", args=["RU"]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for field in ("work", "study", "medical", "residence", "travel",
                      "wanted", "jailed", "missing", "remit", "remitCount", "risk"):
            self.assertIn(field, response.data, f"{field} maydoni yo‘q")
        self.assertEqual(response.data["work"], 214800)
        self.assertEqual(response.data["jailed"], 2840)
        self.assertEqual(response.data["remitCount"], 1180)

    def test_country_lookup_is_by_iso_code(self) -> None:
        response = self.client.get(reverse("country-detail", args=["RU"]))
        self.assertEqual(response.data["name"], "Rossiya")

    def test_country_code_is_normalised(self) -> None:
        response = self.client.post(reverse("country-list"), {
            "code": "kz", "name": "Qozog‘iston", "lat": 43.2, "lng": 76.8,
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["code"], "KZ")

    def test_purpose_total_property(self) -> None:
        self.assertEqual(self.country.purpose_total, 268400)

    def test_border_point_requires_region(self) -> None:
        response = self.client.post(reverse("border-point-list"), {
            "name": "Viloyatsiz punkt", "out": 10, "in": 5, "load": 20,
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("region", response.data)

    def test_border_point_round_trips_in_field(self) -> None:
        response = self.client.post(reverse("border-point-list"), {
            "region": "Toshkent viloyati", "name": "“Yallama”",
            "out": 2180, "in": 1840, "load": 88,
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["in"], 1840)
        self.assertEqual(response.data["out"], 2180)
        self.assertTrue(response.data["isOverloaded"])

        point = BorderPoint.objects.get(name="“Yallama”")
        self.assertEqual(point.inbound, 1840)
        self.assertEqual(point.region, self.region)

    def test_overloaded_flag_threshold(self) -> None:
        point = BorderPoint.objects.create(
            region=self.region, name="Past yuklama", load_percent=84,
        )
        self.assertFalse(point.is_overloaded)
        point.load_percent = 85
        self.assertTrue(point.is_overloaded)

    def test_district_is_unique_within_region(self) -> None:
        District.objects.create(region=self.region, name="Zangiota")
        response = self.client.post(reverse("district-list"), {
            "region": "Toshkent viloyati", "name": "Zangiota",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_districts_filter_by_region(self) -> None:
        District.objects.create(region=self.region, name="Zangiota", departed=3800)
        other = Region.objects.create(name="Samarqand", latitude=39.6, longitude=66.9)
        District.objects.create(region=other, name="Urgut", departed=900)

        response = self.client.get(reverse("district-list"), {"region__name": "Samarqand"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Urgut")

    def test_region_reports_district_count(self) -> None:
        District.objects.create(region=self.region, name="Zangiota")
        District.objects.create(region=self.region, name="Qibray")
        response = self.client.get(reverse("region-list"), {"search": "Toshkent"})
        self.assertEqual(response.data["results"][0]["districtCount"], 2)
