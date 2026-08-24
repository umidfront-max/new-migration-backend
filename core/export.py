"""
CSV eksport.

Frontenddagi "Eksport" tugmalari shu endpointga murojaat qiladi.
Excel'da to'g'ri ochilishi uchun UTF-8 BOM bilan yoziladi.
"""
import csv
import unicodedata
from datetime import date
from urllib.parse import quote

from django.http import HttpResponse
from rest_framework.decorators import action
from rest_framework.throttling import ScopedRateThrottle

UTF8_BOM = "﻿"

# O'zbek lotinidagi belgilar uchun ASCII muqobillari
TRANSLITERATION = str.maketrans({
    "‘": "", "’": "", "—": "-", "–": "-", "“": "", "”": "", "«": "", "»": "",
    " ": "-", ".": "", ",": "", "/": "-", "\\": "-", ":": "", ";": "", '"': "",
})


def ascii_filename(name: str) -> str:
    """
    Sarlavhaga yoziladigan ASCII nom.

    Lotin bo'lmagan belgi qolsa Django butun sarlavhani MIME-kodlab qo'yadi va
    brauzer buzuq nom oladi — shuning uchun nom oldindan tozalanadi.
    """
    cleaned = unicodedata.normalize("NFKD", name.translate(TRANSLITERATION))
    ascii_only = cleaned.encode("ascii", "ignore").decode("ascii")
    safe = "-".join(part for part in ascii_only.split("-") if part)
    return safe.lower() or "export"


def build_csv_response(filename: str, headers: list[str], rows) -> HttpResponse:
    """
    Sarlavha va qatorlardan CSV javob yasaydi.

    `Content-Disposition` da ikki nom beriladi: eski brauzerlar uchun ASCII
    (`filename=`) va to'liq nom uchun RFC 5987 (`filename*=`).
    """
    stamp = date.today().isoformat()
    full_name = f"{filename}-{stamp}.csv"
    safe_name = f"{ascii_filename(filename)}-{stamp}.csv"

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="{safe_name}"; '
        f"filename*=UTF-8''{quote(full_name)}"
    )
    response.write(UTF8_BOM)

    writer = csv.writer(response, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    return response


class CsvExportMixin:
    """
    ViewSet ga `GET /<resurs>/export/` amalini qo'shadi.

    Merosxo'r sinf `export_headers` va `export_row()` ni belgilaydi.
    Filtrlar odatdagidek ishlaydi: `?export/?risky=true&country=RU`.
    """

    export_headers: list[str] = []
    export_filename: str = "export"
    # prefetch_related bilan iterator() ishlashi uchun chunk_size majburiy
    export_chunk_size: int = 500

    def export_row(self, instance) -> list:
        raise NotImplementedError("export_row() ni aniqlang")

    @action(detail=False, methods=["get"], throttle_classes=[ScopedRateThrottle])
    def export(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        rows = queryset.iterator(chunk_size=self.export_chunk_size)
        response = build_csv_response(
            self.export_filename,
            self.export_headers,
            (self.export_row(item) for item in rows),
        )
        if hasattr(self, "write_audit"):
            self.write_audit("eksport qilindi")
        return response

    export.throttle_scope = "export"
