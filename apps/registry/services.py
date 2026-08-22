"""
Risk ball hisoblash.

Mantiq frontenddagi `src/data/schemas.js` dagi `scoreOf()` bilan bir xil:
foydalanuvchi ballni bo'sh qoldirsa, model uni o'zi hisoblaydi.
Omillar `analytics.RiskWeight` dagi vaznlar bilan bir xil tartibda.
"""
from __future__ import annotations

MIN_SCORE = 4
MAX_SCORE = 96

COUNTRY_RISK_FACTOR = 0.42

PURPOSE_POINTS = {
    "Ishlash (norasmiy)": 22,
    "Ishlash (rasmiy)": 6,
    "Doimiy yashash": 4,
}

LEGAL_STATUS_POINTS = {
    "Qidiruvda": 30,
    "Jazoni o‘tamoqda": 34,
    "Bedarak yo‘qolgan": 38,
}

UNREGISTERED_EMPLOYER = "Ro‘yxatdan o‘tmagan"
HEALTH_RISK_STATUSES = {"Nogironlik", "Surunkali kasallik"}

CONVICTION_POINTS = 14
UNREGISTERED_EMPLOYER_POINTS = 9
HEALTH_POINTS = 4


def calculate_risk_score(
    *,
    country_risk: int = 30,
    purpose: str = "",
    legal_status: str = "",
    is_convicted: bool = False,
    employer_name: str = "",
    health_status: str = "",
) -> int:
    """
    0–100 oralig'idagi risk ballni qaytaradi.

    >>> calculate_risk_score(country_risk=62, purpose="Ishlash (norasmiy)")
    48
    """
    score = round(country_risk * COUNTRY_RISK_FACTOR)
    score += PURPOSE_POINTS.get(purpose, 0)

    if is_convicted:
        score += CONVICTION_POINTS
    if not employer_name or employer_name == UNREGISTERED_EMPLOYER:
        score += UNREGISTERED_EMPLOYER_POINTS
    if health_status in HEALTH_RISK_STATUSES:
        score += HEALTH_POINTS

    score += LEGAL_STATUS_POINTS.get(legal_status, 0)
    return max(MIN_SCORE, min(MAX_SCORE, score))


def score_for_migrant(migrant) -> int:
    """`Migrant` obyekti uchun ballni hisoblaydi."""
    return calculate_risk_score(
        country_risk=getattr(migrant.country, "risk_score", 30),
        purpose=migrant.purpose,
        legal_status=migrant.legal_status,
        is_convicted=migrant.is_convicted,
        employer_name=migrant.employer_name,
        health_status=migrant.health_status,
    )
