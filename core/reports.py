"""
Eksport ta'riflari — yagona manba.

Har bir to'plam uchun sarlavhalar va qator quruvchisi shu yerda bir marta
aniqlanadi. Ularni ikki joy ishlatadi:

  * `GET /api/<resurs>/export/` — ViewSet dagi `CsvExportMixin`
  * `GET /api/report-archive/{id}/download/` — arxivdagi hisobot fayli

Shu sababli hisobot fayli va to'g'ridan-to'g'ri eksport bir xil ustunlarni
beradi.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .export import build_csv_response


@dataclass(frozen=True)
class ExportSpec:
    """Bitta to'plamning CSV ko'rinishi."""

    filename: str
    headers: list[str]
    row: Callable[[object], list]
    queryset: Callable[[], object] = field(repr=False, default=None)

    def build_response(self, rows, filename: str | None = None):
        return build_csv_response(filename or self.filename, self.headers,
                                 (self.row(item) for item in rows))


def _date(value) -> str:
    return value.strftime("%d.%m.%Y") if value else ""


# ------------------------------------------------------------------ reyestr
def migrant_row(migrant) -> list:
    return [
        migrant.pinfl, migrant.full_name, migrant.gender, migrant.nationality,
        migrant.speciality, migrant.country.name, migrant.region.name,
        migrant.purpose, migrant.employer_label, migrant.legal_status,
        migrant.risk_score, _date(migrant.exit_date), migrant.phone,
    ]


MIGRANT_EXPORT = ExportSpec(
    filename="migrantlar",
    headers=[
        "PINFL", "F.I.Sh", "Jinsi", "Millati", "Mutaxassisligi",
        "Davlat", "Hudud", "Maqsad", "Ish beruvchi",
        "Holati", "Risk ball", "Chiqish sanasi", "Telefon",
    ],
    row=migrant_row,
)


def employer_row(employer) -> list:
    return [
        employer.name, employer.direction,
        ", ".join(country.name for country in employer.countries.all()),
        employer.employment_type, employer.sent_count,
        employer.remittance_amount, employer.status,
    ]


EMPLOYER_EXPORT = ExportSpec(
    filename="ish-beruvchilar",
    headers=[
        "Kompaniya", "Yo‘nalishi", "Davlatlar", "Shartnoma",
        "Yuborilgan", "Jo‘natma (mln $)", "Holati",
    ],
    row=employer_row,
)


# --------------------------------------------------------------- monitoring
def sos_row(event) -> list:
    return [
        event.code, event.applicant_name, event.country.name, event.city,
        event.event_type, event.get_severity_display(), event.minutes_ago,
        event.phone, "ha" if event.is_resolved else "yo‘q",
    ]


SOS_EXPORT = ExportSpec(
    filename="sos-murojaatlar",
    headers=[
        "Raqami", "Murojaatchi", "Davlat", "Shahar", "Turi",
        "Jiddiyligi", "Necha daqiqa oldin", "Telefon", "Hal etilgan",
    ],
    row=sos_row,
)


# `ReportDataset` qiymatlari bilan mos kalitlar
EXPORT_SPECS: dict[str, ExportSpec] = {
    "migrants": MIGRANT_EXPORT,
    "employers": EMPLOYER_EXPORT,
    "sos-events": SOS_EXPORT,
}


def build_dataset_csv(dataset: str, filename: str):
    """
    Arxivdagi hisobot uchun CSV javob yasaydi.

    Import halqasi bo'lmasligi uchun modellar funksiya ichida olinadi.
    """
    from apps.monitoring.models import SosEvent
    from apps.registry.models import Employer, Migrant

    querysets = {
        "migrants": lambda: Migrant.objects.select_related("country", "region", "employer"),
        "employers": lambda: Employer.objects.prefetch_related("countries"),
        "sos-events": lambda: SosEvent.objects.select_related("country"),
    }

    spec = EXPORT_SPECS.get(dataset)
    if spec is None or dataset not in querysets:
        return None
    rows = querysets[dataset]().iterator(chunk_size=500)
    return spec.build_response(rows, filename=filename)
