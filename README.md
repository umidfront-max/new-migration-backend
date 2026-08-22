# Migratsiya monitoringi — backend

Django 5 + Django REST Framework. Mehnat migratsiyasi monitoringi platformasi
uchun REST API: reyestr, geografiya, chegara, konsullik, SOS xizmati, analitika,
foydalanuvchilar va audit jurnali.

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

| Manzil | Nima |
|---|---|
| `/api/` | REST API |
| `/api/docs/` | Swagger UI — interaktiv hujjat |
| `/api/redoc/` | ReDoc |
| `/api/schema/` | OpenAPI 3 sxemasi (YAML) |
| `/admin/` | Django admin paneli |

Demo hisoblar: `admin.root`, `sh.rasulova`, `konsul.msk`, `operator.fargona`,
`chegara.termiz` — parol hammasida **`demo`**. `operator.andijon` bloklangan
(kirishni tekshirish uchun).

### Docker bilan

```bash
docker compose up --build
docker compose exec api python manage.py seed_demo --flush
```

PostgreSQL, migratsiya va gunicorn avtomatik ishga tushadi.

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

Bloklangan hisob `403`, noto'g'ri parol `401` qaytaradi. Parolni tanlab ko'rishga
qarshi cheklov: bir IP dan daqiqada 10 urinish (`THROTTLE_SIGN_IN`), oshib ketsa
`429`. Har bir kirish urinishi — muvaffaqiyatlisi ham, rad etilgani ham — audit
jurnaliga tushadi.

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

### Qo'shimcha amallar

| Amal | Nima qiladi |
|---|---|
| `GET /api/migrants/export/` | CSV eksport — joriy filtrlar bo'yicha |
| `GET /api/employers/export/` | CSV eksport |
| `GET /api/sos-events/export/` | CSV eksport |
| `POST /api/sos-events/{id}/resolve/` | murojaatni yopadi (takroriy urinish — `409`) |
| `POST /api/sos-events/{id}/reopen/` | yopilgan murojaatni qayta ochadi |
| `POST /api/report-templates/{id}/generate/` | shablon bo'yicha arxivga yozuv qo'shadi |

CSV UTF-8 BOM bilan yoziladi — Excel'da to'g'ri ochiladi. Eksport ham audit
jurnaliga tushadi va soatiga cheklangan (`THROTTLE_EXPORT`).

## Muhim mantiq

**Risk ball avtomatik.** Migrant qo'shishda `score` berilmasa,
`apps/registry/services.py::calculate_risk_score` uni yo'nalish davlati xavfi,
chiqish maqsadi, sudlanganlik, ish beruvchi va huquqiy holat asosida hisoblaydi.
Formula frontenddagi `schemas.js::scoreOf` bilan bir xil.

**Ish beruvchi bog'lanishi.** Migrantdagi `employer` — matn. Agar reyestrda
shunday nomli tashkilot bo'lsa, `Migrant.employer` foreign key avtomatik
bog'lanadi; bo'lmasa erkin matn sifatida saqlanadi. Shu sababli ish beruvchi
sahifasida uning migrantlari sonini ko'rish mumkin (`migrantCount`).

**Ish beruvchi shartnomasi.** `countries` — davlat nomlari ro'yxati, bo'sh
bo'lishi mumkin emas. `employment` ikki qiymatdan biri; `formal` (100 yoki 0)
shundan kelib chiqadi va faqat o'qish uchun.

**Parol.** Django'ning standart PBKDF2 hashi ishlatiladi. `password` faqat
yozish uchun — javobda hech qachon qaytmaydi. Tahrirlashda bo'sh qoldirilsa eski
parol saqlanadi.

**Audit jurnali.** `core/viewsets.py::AuditedModelViewSet` har bir qo'shish,
o'zgartirish, o'chirish va eksportni jurnalga yozadi. API orqali jurnalga qo'lda
yozib bo'lmaydi (`405`).

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
│   ├── export.py          CsvExportMixin, build_csv_response()
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
├── seed/              demo_seed.json (repozitoriyada saqlanadi)
├── Dockerfile
└── docker-compose.yml
```

O'xshash KPI to'plamlari (dashboard, konsullik, qaytish, chegara, SOS, audit)
alohida jadval emas — bitta `MetricTile` modelida `group` maydoni bilan
saqlanadi. Taqsimotlar ham shunday: `ShareSlice`.

### Demo ma'lumotni yangilash

`seed/demo_seed.json` frontenddagi `src/data/mock.js` dan olingan. Frontend
ma'lumoti o'zgarsa qayta chiqarish:

```bash
node scripts/export_seed.mjs                                   # yonma-yon papkani o'zi topadi
node scripts/export_seed.mjs /yo'l/migrant-dashboard/src/data/mock.js
```

Bu qadam ixtiyoriy — backendni ishga tushirish uchun frontend kerak emas.

## Testlar

```bash
python manage.py test
```

**59 ta test**, barcha ilovalarni qoplaydi:

| Ilova | Nima tekshiriladi |
|---|---|
| `accounts` | kirish/chiqish, bloklangan hisob, parol o'rnatish va yangilash, rol huquqlari, jurnalning o'zgarmasligi |
| `registry` | risk ball formulasi va chegaralari, PINFL tekshiruvi, ish beruvchi davlatlari, `risky` filtri |
| `geography` | davlat ko'rsatkichlari, ISO kod normallashuvi, punktdagi `in`/`out`, tuman noyobligi |
| `monitoring` | SOS kodi va koordinatasi, resolve/reopen, CSV eksport va filtrlar |
| `analytics` | guruh filtrlari, 12 oylik qator, hisobot shakllantirish, yig'ma ko'rsatkichlar |

## Sozlamalar

Muhit o'zgaruvchilari `.env` faylidan yoki muhitdan o'qiladi (`.env.example`
dan nusxa oling). Muhitdagi qiymat fayldagisidan ustun turadi.

| O'zgaruvchi | Standart | Izoh |
|---|---|---|
| `DJANGO_SECRET_KEY` | dev kaliti | Prodda majburiy, 50+ belgi |
| `DJANGO_DEBUG` | `True` | Prodda `False` |
| `DJANGO_ALLOWED_HOSTS` | localhost | Vergul bilan |
| `DATABASE_URL` | — | Bo'sh bo'lsa SQLite; `postgresql://…` qo'llanadi |
| `CORS_ALLOWED_ORIGINS` | Vite portlari | Frontend manzillari |
| `THROTTLE_SIGN_IN` | `10/min` | Kirish urinishlari cheklovi |
| `THROTTLE_EXPORT` | `20/min` | Eksport cheklovi |
| `SECURE_SSL_REDIRECT` | `True` | Reverse-proxy HTTPS ni hal qilsa — `False` |

`DEBUG=False` bo'lganda HSTS, xavfsiz cookie va SSL yo'naltirish yoqiladi;
`manage.py check --deploy` ogohlantirishsiz o'tadi. Statik fayllar WhiteNoise
orqali beriladi.

## Nima qilinmagan

- **Frontend hali ulanmagan** — `migrant-dashboard` hamon `localStorage` bilan
  ishlaydi. Serializerlar frontend kutgan shaklda yozilgan, shuning uchun ulash
  asosan `db.js` ni API klientiga almashtirishdan iborat.
- **Hisobot fayllari** — `generate` amali arxivga yozuv qo'shadi, lekin XLSX/PDF
  generatsiyasi yo'q (`apps/analytics/views.py::generate` shu joyga ulanadi).
- **AI tahlil** — `ai-insights` qo'lda kiritiladigan ma'lumot, model yo'q.
