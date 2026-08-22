"""
Demo ma'lumotni bazaga yozadi.

    python manage.py seed_demo            # bo'sh jadvallarni to'ldiradi
    python manage.py seed_demo --flush    # avval tozalab, qaytadan yozadi

Manba — `backend/seed/demo_seed.json`, uni frontenddagi `src/data/mock.js`
dan `node backend/scripts/export_seed.mjs` yaratadi.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import AuditLogEntry, Role, SystemSetting, User
from apps.analytics.models import (
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
from apps.geography.models import BorderPoint, BorderSource, Country, District, Region
from apps.monitoring.models import (
    ConsulateService,
    ReturnProgram,
    SosChannel,
    SosEvent,
    ViolationType,
)
from apps.registry.models import Employer, Migrant

DEFAULT_PASSWORD = "demo"

# --flush bilan tozalanadigan modellar (bog'liqlik tartibida)
CLEARED_MODELS = [
    AuditLogEntry, Migrant, Employer, SosEvent, SosChannel,
    ConsulateService, ReturnProgram, ViolationType,
    BorderPoint, BorderSource, District, Region, Country,
    MetricTile, ShareSlice, TimeSeries, AiInsight, AiSuggestion,
    Integration, RiskWeight, ReportTemplate, ReportArchiveEntry,
    User, Role, SystemSetting,
]


def parse_date(value: str | None):
    """`12.03.2026` yoki `2026-03-12` — ikkalasini ham tushunadi."""
    if not value:
        return None
    for pattern in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            continue
    return None


class Command(BaseCommand):
    help = "Demo ma'lumotni bazaga yozadi"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--flush", action="store_true",
            help="Avval barcha demo jadvallarni tozalaydi",
        )
        parser.add_argument(
            "--password", default=DEFAULT_PASSWORD,
            help=f"Barcha demo hisoblar uchun parol (standart: {DEFAULT_PASSWORD})",
        )

    def handle(self, *args, **options) -> None:
        seed_file: Path = settings.BASE_DIR / "seed" / "demo_seed.json"
        if not seed_file.exists():
            raise CommandError(
                f"{seed_file} topilmadi. Avval `node backend/scripts/export_seed.mjs` ni bajaring."
            )

        data = json.loads(seed_file.read_text(encoding="utf-8"))
        password = options["password"]

        with transaction.atomic():
            if options["flush"]:
                self.clear_tables()

            roles = self.seed_roles(data["roles"])
            self.seed_users(data["users"], roles, password)
            self.seed_settings(data["settings"])

            countries = self.seed_countries(data["countries"])
            regions = self.seed_regions(data["regions"])
            self.seed_districts(data["districts"], regions)
            self.seed_border(data["borderPoints"], data["borderSources"], regions)

            self.seed_migrants(data["migrants"], countries, regions)
            self.seed_employers(data["employers"], countries)

            self.seed_monitoring(data, countries)
            self.seed_analytics(data)

        self.stdout.write(self.style.SUCCESS("Demo ma'lumot yozildi."))
        self.report()

    # ------------------------------------------------------------ tozalash
    def clear_tables(self) -> None:
        for model in CLEARED_MODELS:
            deleted, _ = model.objects.all().delete()
            if deleted:
                self.stdout.write(f"  tozalandi: {model.__name__} ({deleted})")

    # ------------------------------------------------------ foydalanuvchilar
    def seed_roles(self, rows: list[dict]) -> dict[str, Role]:
        result = {}
        for index, row in enumerate(rows):
            role, _ = Role.objects.update_or_create(
                name=row["name"],
                defaults={
                    "scope": row.get("scope", ""),
                    "capacity": row.get("count", 0),
                    "tone": row.get("tone", "lapis"),
                },
            )
            result[role.name] = role
        return result

    def seed_users(self, rows: list[dict], roles: dict[str, Role], password: str) -> None:
        for row in rows:
            user, created = User.objects.update_or_create(
                login=row["login"],
                defaults={
                    "full_name": row["name"],
                    "role": roles.get(row.get("role", "")),
                    "unit": row.get("unit", ""),
                    "phone": row.get("phone", ""),
                    "status": row.get("status", User.Status.ACTIVE),
                },
            )
            if created or not user.has_usable_password():
                user.set_password(password)
            if user.login == "admin.root":
                user.is_staff = True
                user.is_superuser = True
            user.save()

    def seed_settings(self, rows: list[dict]) -> None:
        for row in rows:
            SystemSetting.objects.update_or_create(
                key=row["key"],
                defaults={
                    "label": row["label"],
                    "hint": row.get("hint", ""),
                    "kind": row.get("kind", SystemSetting.Kind.SWITCH),
                    "number_value": row.get("value"),
                    "is_enabled": bool(row.get("on", False)),
                },
            )

    # ------------------------------------------------------------ geografiya
    def seed_countries(self, rows: list[dict]) -> dict[str, Country]:
        result = {}
        for row in rows:
            country, _ = Country.objects.update_or_create(
                code=row["code"],
                defaults={
                    "name": row["name"],
                    "flag": row.get("flag", ""),
                    "hub": row.get("hub", ""),
                    "latitude": row["lat"],
                    "longitude": row["lng"],
                    "azimuth": row.get("angle", 0),
                    "distance_km": row.get("dist", 0),
                    "total": row.get("total", 0),
                    "departed": row.get("out", 0),
                    "returned": row.get("back", 0),
                    "work": row.get("work", 0),
                    "study": row.get("study", 0),
                    "medical": row.get("medical", 0),
                    "residence": row.get("residence", 0),
                    "travel": row.get("travel", 0),
                    "wanted": row.get("wanted", 0),
                    "jailed": row.get("jailed", 0),
                    "missing": row.get("missing", 0),
                    "remittance_amount": row.get("remit", 0),
                    "remittance_count": row.get("remitCount", 0),
                    "risk_score": row.get("risk", 0),
                },
            )
            result[country.code] = country
            result[country.name] = country
        return result

    def seed_regions(self, rows: list[dict]) -> dict[str, Region]:
        result = {}
        for row in rows:
            region, _ = Region.objects.update_or_create(
                name=row["name"],
                defaults={
                    "latitude": row["lat"],
                    "longitude": row["lng"],
                    "departed": row.get("out", 0),
                    "returned": row.get("back", 0),
                    "risk_score": row.get("risk", 0),
                },
            )
            result[region.name] = region
        return result

    def seed_districts(self, rows: list[dict], regions: dict[str, Region]) -> None:
        for row in rows:
            region = regions.get(row["region"])
            if region is None:
                continue
            District.objects.update_or_create(
                region=region, name=row["name"],
                defaults={
                    "departed": row.get("out", 0),
                    "returned": row.get("back", 0),
                    "risk_score": row.get("risk", 0),
                },
            )

    def seed_border(
        self, points: list[dict], sources: list[dict], regions: dict[str, Region],
    ) -> None:
        fallback = next(iter(regions.values()), None)
        for row in points:
            BorderPoint.objects.update_or_create(
                name=row["name"],
                defaults={
                    "region": regions.get(row.get("region", ""), fallback),
                    "outbound": row.get("out", 0),
                    "inbound": row.get("in", 0),
                    "load_percent": row.get("load", 0),
                },
            )
        for row in sources:
            BorderSource.objects.update_or_create(
                name=row["name"], defaults={"status": row.get("status", "ulangan")},
            )

    # --------------------------------------------------------------- reyestr
    def seed_migrants(
        self, rows: list[dict], countries: dict[str, Country], regions: dict[str, Region],
    ) -> None:
        fallback_region = next(iter(regions.values()), None)
        for row in rows:
            country = countries.get(row.get("countryCode", ""))
            if country is None:
                continue
            Migrant.objects.update_or_create(
                pinfl=row["pinfl"],
                defaults={
                    "full_name": row["name"],
                    "nationality": row.get("nationality", ""),
                    "gender": row.get("gender", Migrant.Gender.MALE),
                    "speciality": row.get("speciality", ""),
                    "country": country,
                    "region": regions.get(row.get("region", ""), fallback_region),
                    "purpose": row.get("purpose", Migrant.Purpose.FORMAL_WORK),
                    "remittance_band": row.get("remit", ""),
                    "marital_status": row.get("marital", ""),
                    "health_status": row.get("health", Migrant.Health.HEALTHY),
                    "is_convicted": bool(row.get("convicted", False)),
                    "employer_name": row.get("employer", ""),
                    "address": row.get("address", ""),
                    "phone": row.get("phone", ""),
                    "legal_status": row.get("risk", Migrant.LegalStatus.CLEAR),
                    "risk_score": row.get("score", 0),
                    "exit_date": parse_date(row.get("exitDate")),
                },
            )

    def seed_employers(self, rows: list[dict], countries: dict[str, Country]) -> None:
        for row in rows:
            employer, _ = Employer.objects.update_or_create(
                name=row["name"],
                defaults={
                    "direction": row.get("dir", ""),
                    "employment_type": row.get("employment", Employer.Employment.FORMAL),
                    "sent_count": row.get("sent", 0),
                    "remittance_amount": row.get("remit", 0),
                    "status": row.get("status", Employer.Status.WATCHED),
                },
            )
            linked = [countries[name] for name in row.get("countries", []) if name in countries]
            employer.countries.set(linked)

    # ------------------------------------------------------------ monitoring
    def seed_monitoring(self, data: dict, countries: dict[str, Country]) -> None:
        for index, row in enumerate(data["violations"]):
            ViolationType.objects.update_or_create(
                key=row["key"],
                defaults={
                    "label": row["label"], "value": row.get("value", 0),
                    "delta": row.get("delta", 0), "tone": row.get("tone", "coral"),
                    "position": index,
                },
            )
        for row in data["sosEvents"]:
            country = countries.get(row.get("countryCode", ""))
            if country is None:
                continue
            SosEvent.objects.update_or_create(
                code=row["id"],
                defaults={
                    "applicant_name": row["name"], "country": country,
                    "city": row.get("city", ""), "latitude": row.get("lat"),
                    "longitude": row.get("lng"), "event_type": row.get("type", ""),
                    "severity": row.get("severity", SosEvent.Severity.HIGH),
                    "minutes_ago": row.get("minutesAgo", 0), "phone": row.get("phone", ""),
                },
            )
        for index, row in enumerate(data["sosChannels"]):
            SosChannel.objects.update_or_create(
                name=row["name"],
                defaults={"share": row.get("share", 0), "icon": row.get("icon", "phone"),
                          "position": index},
            )
        for index, row in enumerate(data["consulateServices"]):
            ConsulateService.objects.update_or_create(
                label=row["label"],
                defaults={"value": row.get("value", 0), "tone": row.get("tone", "lapis"),
                          "position": index},
            )
        for index, row in enumerate(data["returnPrograms"]):
            ReturnProgram.objects.update_or_create(
                name=row["name"],
                defaults={"completed": row.get("done", 0), "target": row.get("target", 1),
                          "tone": row.get("tone", "lapis"), "position": index},
            )

    # ------------------------------------------------------------- analitika
    def seed_analytics(self, data: dict) -> None:
        for group, rows in data["metrics"].items():
            for index, row in enumerate(rows):
                MetricTile.objects.update_or_create(
                    group=group, label=row["label"],
                    defaults={
                        "key": row.get("key", ""), "value": row.get("value", 0),
                        "delta": row.get("delta", 0), "subtitle": row.get("sub", ""),
                        "tone": row.get("tone", "lapis"), "position": index,
                    },
                )
        for group, rows in data["shares"].items():
            for index, row in enumerate(rows):
                ShareSlice.objects.update_or_create(
                    group=group, label=row["label"],
                    defaults={
                        "key": row.get("key", ""), "value": row.get("value", 0),
                        "tone": row.get("tone", "lapis"), "position": index,
                    },
                )
        for row in data["series"]:
            TimeSeries.objects.update_or_create(
                key=row["key"],
                defaults={"name": row["name"], "color": row.get("color", "var(--turk)"),
                          "monthly_values": row["values"]},
            )
        for index, row in enumerate(data["aiInsights"]):
            AiInsight.objects.update_or_create(
                title=row["title"],
                defaults={
                    "tag": row.get("tag", AiInsight.Tag.FORECAST), "body": row.get("body", ""),
                    "recommended_action": row.get("action", ""),
                    "confidence": row.get("confidence", 80),
                    "tone": row.get("tone", "lapis"), "position": index,
                },
            )
        for index, row in enumerate(data["aiSuggestions"]):
            AiSuggestion.objects.update_or_create(
                text=row["text"], defaults={"position": index},
            )
        for row in data["integrations"]:
            Integration.objects.update_or_create(
                name=row["name"], defaults={"status": row.get("status", "Rejada")},
            )
        for index, row in enumerate(data["riskWeights"]):
            RiskWeight.objects.update_or_create(
                key=row["key"],
                defaults={"label": row["label"], "weight": row.get("w", 10), "position": index},
            )
        for index, row in enumerate(data["reportTemplates"]):
            ReportTemplate.objects.update_or_create(
                name=row["name"],
                defaults={
                    "description": row.get("desc", ""),
                    "period": row.get("period", ReportTemplate.Period.MONTHLY),
                    "formats": row.get("fmt", "XLSX, PDF"),
                    "tone": row.get("tone", "lapis"), "position": index,
                },
            )
        for row in data["reportArchive"]:
            ReportArchiveEntry.objects.update_or_create(
                name=row["name"],
                defaults={
                    "size": row.get("size", ""), "generated_on": parse_date(row.get("at")),
                    "generated_by": row.get("by", ""),
                },
            )

    # ---------------------------------------------------------------- hisobot
    def report(self) -> None:
        rows = [
            ("Rollar", Role.objects.count()),
            ("Foydalanuvchilar", User.objects.count()),
            ("Davlatlar", Country.objects.count()),
            ("Hududlar", Region.objects.count()),
            ("Tumanlar", District.objects.count()),
            ("O‘tkazish punktlari", BorderPoint.objects.count()),
            ("Migrantlar", Migrant.objects.count()),
            ("Ish beruvchilar", Employer.objects.count()),
            ("SOS murojaatlar", SosEvent.objects.count()),
            ("Ko‘rsatkichlar", MetricTile.objects.count()),
            ("Grafik qatorlari", TimeSeries.objects.count()),
        ]
        for label, count in rows:
            self.stdout.write(f"  {label:<24} {count}")
