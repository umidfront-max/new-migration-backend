# Migratsiya monitoringi — backend

Django 5 + Django REST Framework. Migratsiya monitoringi dashboardi uchun REST
API: reyestr, geografiya, monitoring, analitika, foydalanuvchilar va audit
jurnali.

Mustaqil loyiha — frontend (`migrant-dashboard`) alohida repozitoriyada.

## Ishga tushirish

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo --flush     # demo ma'lumot
python manage.py runserver 8000
```

Demo ma'lumot `seed/demo_seed.json` faylidan olinadi — u repozitoriyada bor,
qo'shimcha qadam kerak emas.

API — `http://127.0.0.1:8000/api/`, admin panel — `/admin/`.

Demo hisoblar: `admin.root`, `sh.rasulova`, `konsul.msk`, `operator.fargona`,
`chegara.termiz` — parol hammasida **`demo`**. `operator.andijon` bloklangan
(kirishni tekshirish uchun).

## Autentifikatsiya

Token asosida. Avval token olinadi, keyin har bir so'rovga qo'shiladi:

```bash
curl -X POST http://127.0.0.1:8000/api/auth/login/ \
     -H "Content-Type: application/json" \
     -d '{"login": "admin.root", "password": "demo"}'
# -> {"token": "...", "user": {...}}

curl http://127.0.0.1:8000/api/migrants/ -H "Authorization: Token <TOKEN>"
```

| Endpoint | Vazifasi |
|---|---|
| `POST /api/auth/login/` | login + parol → token |
| `POST /api/auth/logout/` | tokenni bekor qiladi |
| `GET /api/auth/me/` | joriy foydalanuvchi |

Bloklangan hisob `403`, noto'g'ri parol `401` qaytaradi. Har bir kirish urinishi —
muvaffaqiyatlisi ham, rad etilgani ham — audit jurnaliga tushadi.

## Endpointlar

Nomlar frontenddagi to'plam nomlari bilan mos, javob maydonlari ham frontend
kutayotgan shaklda (`out`, `back`, `remit`, `countryCode`) — shuning uchun
`src/stores/db.js` ni API ga o'tkazishda qayta nomlash kerak emas.

**Geografiya:** `countries` (lookup — ISO kod), `regions`, `districts`,
`border-points`, `border-sources`

**Reyestr:** `migrants`, `employers`

**Monitoring:** `violations`, `sos-events`, `sos-channels`,
`consulate-services`, `return-programs`

**Analitika:** `metrics?group=…`, `shares?group=…`, `series` (lookup — kalit),
`ai-insights`, `ai-suggestions`, `integrations`, `risk-weights`,
`report-templates`, `report-archive`

**Tizim:** `users`, `roles`, `settings` (lookup — kalit), `audit-log` (faqat o'qish)

**Yig'ma:** `GET /api/dashboard/summary/` — barcha asosiy raqamlar bitta so'rovda.

Har bir ro'yxatda `?search=`, `?ordering=`, `?page=`, `?page_size=` ishlaydi.
Filtrlar: `migrants?risky=true&country=RU&gender=Ayol`,
`employers?employment_type=Norasmiy bandlik`, `sos-events?severity=critical`.

## Muhim mantiq

**Risk ball avtomatik.** Migrant qo'shishda `score` berilmasa,
`apps/registry/services.py::calculate_risk_score` uni yo'nalish davlati xavfi,
chiqish maqsadi, sudlanganlik, ish beruvchi va huquqiy holat asosida hisoblaydi.
Formula frontenddagi `schemas.js::scoreOf` bilan bir xil.

**Ish beruvchi.** `countries` — davlat nomlari ro'yxati, bo'sh bo'lishi mumkin emas.
`employment` ikki qiymatdan biri; `formal` (100 yoki 0) shundan kelib chiqadi va
faqat o'qish uchun.

**Parol.** Django'ning standart PBKDF2 hashi ishlatiladi. `password` faqat
yozish uchun — javobda hech qachon qaytmaydi. Tahrirlashda bo'sh qoldirilsa eski
parol saqlanadi. Frontenddagi vaqtinchalik `src/composables/usePassword.js` shu
API ga o'tilgach keraksiz bo'ladi.

**Audit jurnali.** `core/viewsets.py::AuditedModelViewSet` har bir qo'shish,
o'zgartirish va o'chirishni jurnalga yozadi. API orqali jurnalga qo'lda yozib
bo'lmaydi (`405`).

**Huquqlar.** O'qish — barcha kirgan foydalanuvchilarga. `users`, `roles` va
`settings` ni o'zgartirish faqat *Super administrator* va
*Respublika administratori* rollariga ruxsat etilgan (`core/permissions.py`).

## Tuzilma

```
migrant-backend/
├── config/            sozlamalar, URL yo'nalishlari, WSGI/ASGI
├── core/              umumiy qatlam
│   ├── models.py          TimeStampedModel, OrderedModel
│   ├── viewsets.py        AuditedModelViewSet
│   ├── permissions.py     IsAdministrator, ReadOnly
│   ├── pagination.py      DefaultPagination, LargePagination
│   └── management/commands/seed_demo.py
├── apps/
│   ├── accounts/      User, Role, SystemSetting, AuditLogEntry
│   ├── geography/     Country, Region, District, BorderPoint, BorderSource
│   ├── registry/      Migrant, Employer, calculate_risk_score()
│   ├── monitoring/    ViolationType, SosEvent, SosChannel, ConsulateService,
│   │                  ReturnProgram
│   └── analytics/     MetricTile, ShareSlice, TimeSeries, AiInsight,
│                      AiSuggestion, Integration, RiskWeight, ReportTemplate,
│                      ReportArchiveEntry
├── scripts/           export_seed.mjs — frontend demo ma'lumotini chiqaradi
└── seed/              demo_seed.json (repozitoriyada saqlanadi)
```

### Demo ma'lumotni yangilash

`seed/demo_seed.json` frontenddagi `src/data/mock.js` dan olingan. Frontend
ma'lumoti o'zgarsa qayta chiqarish:

```bash
node scripts/export_seed.mjs                                   # yonma-yon papkani o'zi topadi
node scripts/export_seed.mjs /yo'l/migrant-dashboard/src/data/mock.js
```

Bu qadam ixtiyoriy — backendni ishga tushirish uchun frontend kerak emas.

O'xshash KPI to'plamlari (dashboard, konsullik, qaytish, chegara, SOS, audit)
alohida jadval emas — bitta `MetricTile` modelida `group` maydoni bilan
saqlanadi. Taqsimotlar ham shunday: `ShareSlice`.

## Testlar

```bash
python manage.py test
```

27 ta test: risk ball formulasi, PINFL tekshiruvi, ish beruvchi davlatlari,
kirish/chiqish, bloklangan hisob, parol o'rnatish va yangilash, rol huquqlari,
audit jurnalining o'zgarmasligi.

## Sozlamalar

Muhit o'zgaruvchilari `.env` faylidan yoki muhitdan o'qiladi
(`.env.example` dan nusxa oling). Muhitda allaqachon bor qiymat faylnikidan
ustun turadi. Ishlab chiqarishda
`DJANGO_SECRET_KEY` va `DJANGO_DEBUG=False` majburiy; SQLite o'rniga PostgreSQL
ga o'tish uchun `config/settings.py` dagi `DATABASES` ni almashtirish yetarli.

CORS Vite dev serveri portlariga (5173–5175) ochiq.
