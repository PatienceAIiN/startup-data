# StartupIntel India

Full-stack B2B intelligence platform that scrapes Indian company data from **Zauba Corp** and **data.gov.in**, fuzzy-matches across sources, stores in **NeonDB**, and exports CSV/XLSX to **Cloudflare R2**.

- **Backend**: FastAPI (Python 3.12) + SQLAlchemy 2.0 async + asyncpg
- **Frontend**: Angular 18 (standalone components) + Angular Material + custom CSS-variable theming
- **Database**: NeonDB (Postgres serverless)
- **Storage**: Cloudflare R2 (S3-compatible)
- **Scraping**: Playwright (Zauba) + httpx (data.gov.in API) + RapidFuzz matching
- **Scheduling**: APScheduler — daily scrape at **2:00 PM IST**

---

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- A NeonDB project (free tier works)
- Cloudflare R2 access (account ID + access key + secret)
- An optional [data.gov.in API key](https://data.gov.in/help/how-use-apis-data-platform-india)

### 1. Backend setup

```bash
cd backend
python -m venv venv
.\venv\Scripts\activate           # Windows
# source venv/bin/activate        # macOS/Linux
pip install -r requirements.txt
playwright install chromium
```

Copy `.env.example` to `.env` and fill in:

```env
DATABASE_URL=postgresql+asyncpg://USER:PASS@HOST/DB?sslmode=require
DATABASE_URL_SYNC=postgresql://USER:PASS@HOST/DB?sslmode=require
SECRET_KEY=<random 32+ char string>
R2_ACCOUNT_ID=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET_NAME=startupintel-exports
R2_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com
DATAGOV_API_KEY=<optional>
```

> **Important**: The asyncpg driver needs `?ssl=require`, but the URL accepts `?sslmode=require` because `app/database.py` strips/rewrites it. Likewise `&channel_binding=require` is removed automatically.

Run migrations and start the server:

```bash
alembic upgrade head
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend: http://localhost:8000 · Swagger docs: http://localhost:8000/docs

### 2. Frontend setup

```bash
cd frontend
npm ci --legacy-peer-deps
npm start
```

Frontend: http://localhost:4200

### 3. Create an admin user

```bash
cd backend
python scripts/create_admin.py
```

Default: `admin@startupintel.in` / `Admin@110426`. Edit the script to change.

### 4. Create the R2 bucket (one-time)

```bash
python scripts/create_r2_bucket.py
```

The R2 service also creates the bucket lazily on first upload (`_ensure_bucket`).

### 5. Trigger a scrape

- **Via UI**: log in as admin, click **Run Scrape Now**.
- **Daily auto-scrape**: APScheduler fires at 2:00 PM IST every day.
- **Promote Zauba records when no DataGov match**: `python scripts/promote_zauba_to_matched.py`

---

## Architecture

```
startupintel/
├── backend/
│   ├── alembic/                      # Migrations
│   ├── app/
│   │   ├── main.py                   # FastAPI app + lifespan + scheduler hook
│   │   ├── config.py                 # Pydantic settings (.env loader)
│   │   ├── database.py               # Async engine (rewrites sslmode→ssl)
│   │   ├── models/                   # SQLAlchemy ORM models
│   │   ├── schemas/                  # Pydantic request/response
│   │   ├── routers/                  # auth, companies, scraper, exports
│   │   └── services/
│   │       ├── auth_service.py       # JWT + bcrypt 4.0.1
│   │       ├── zauba_scraper.py      # Playwright → Zauba Corp listing
│   │       ├── datagov_scraper.py    # httpx → data.gov.in resource API
│   │       ├── matcher_service.py    # RapidFuzz + CIN-priority matching
│   │       ├── r2_service.py         # boto3 + auto bucket-create
│   │       ├── export_service.py     # CSV / XLSX (openpyxl) generation
│   │       └── scheduler_service.py  # APScheduler — daily 2 PM IST
│   ├── scripts/                      # Admin / ops scripts
│   ├── tests/                        # 29 pytest cases (real NeonDB)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── styles.scss               # CSS variables for light/dark theme
│   │   ├── index.html                # Material Icons CDN, Roboto font
│   │   └── app/
│   │       ├── app.config.ts         # Standalone bootstrap
│   │       ├── app.routes.ts         # Lazy-loaded routes
│   │       ├── core/
│   │       │   ├── services/         # auth, theme, company, scraper, export
│   │       │   ├── interceptors/     # JWT bearer interceptor
│   │       │   ├── guards/           # authGuard
│   │       │   └── dialogs/          # ConfirmDialog
│   │       └── features/
│   │           ├── auth/             # login + signup
│   │           ├── dashboard/        # main dashboard with filters
│   │           └── companies/
│   │               ├── company-detail-dialog/  # modal popup
│   │               ├── company-detail/         # standalone page (legacy)
│   │               └── company-list/
│   ├── postcss.config.js
│   ├── tailwind.config.js
│   ├── nginx.conf                    # Production reverse proxy
│   └── Dockerfile                    # Multi-stage (build → nginx)
├── docker-compose.yml
└── render.yaml                       # Render.com deployment
```

---

## Key Constraints & Gotchas

| Issue | Why | Fix |
|---|---|---|
| `bcrypt 5.x` breaks passlib | strict 72-byte password limit | Pin `bcrypt==4.0.1` in requirements |
| `asyncpg` rejects `sslmode` | only accepts `ssl` keyword | `database.py` rewrites the URL |
| Cross-loop asyncpg errors in tests | `BaseHTTPMiddleware` clashes with asyncpg | Tests use uvicorn-in-thread (`conftest.py`) |
| 429 rate-limit in tests | `slowapi` defaults too aggressive | `os.environ` overrides set 1000/min in conftest |
| Pydantic rejects `.test` emails | special-use TLD validation | Use `@gmail.com` / real domains in tests |
| R2 bucket "NoSuchBucket" | Cloudflare R2 doesn't auto-create | `_ensure_bucket()` in `r2_service.py` + `create_r2_bucket.py` |
| Companies hidden by date filter | NULL `date_of_incorporation` excluded by `>=` | Backend now uses `OR ... IS NULL` |

---

## API Reference

### Auth

```
POST   /auth/signup          { email, password, full_name }
POST   /auth/login           { email, password }
GET    /auth/me              [Bearer]
```

### Companies

```
GET    /companies            ?page&page_size&search&date_from&date_to
                              &state&status&is_startup&min_score
GET    /companies/{id}
GET    /companies/stats
```

### Scraper (admin only)

```
POST   /scraper/trigger      ?date_from&date_to
GET    /scraper/status/{id}
GET    /scraper/jobs
```

### Exports

```
POST   /exports/csv          ?date_from&date_to&state&is_startup
POST   /exports/xlsx
GET    /exports/history
```

---

## Frontend Features

- **Theme toggle** (sun/moon icon) — dark ↔ light, persisted in localStorage
- **Search hero** with live debounced search + clear button
- **Collapsible advanced filters**: date range with quick presets (30d / 90d / 1y / 3y / all-time), state dropdown, segmented startup-only toggle
- **Filter badge** showing active filter count
- **Company detail modal** — click any company name to open a smooth animated popup with quick stats, financial details, address, copy-to-clipboard, and per-row CSV/Excel export
- **Logout confirmation dialog** to prevent accidental sign-outs
- **Mobile-responsive**: navbar collapses, filters stack, table scrolls horizontally, dialog adjusts to viewport
- **Hot reload** during development (`ng serve`)

---

## Testing

```bash
cd backend
pytest -v
```

29 tests pass (auth, companies, exports, matcher, scraper) against real NeonDB. Frontend tests with `ng test`.

---

## Deployment

### Docker

```bash
docker compose up --build
```

### Render.com

`render.yaml` defines two services (backend + frontend). Set the listed env vars as secrets, then push to your linked repo.

---

## Scripts

Located in `backend/scripts/`:

| Script | Purpose |
|---|---|
| `create_admin.py` | Create / update admin user |
| `make_admin.py` | Promote existing user to admin |
| `create_r2_bucket.py` | Create the R2 bucket if missing |
| `promote_zauba_to_matched.py` | Treat Zauba records as authoritative when DataGov has no overlap |
| `inspect_companies.py` | Diagnose null incorporation dates / sample rows |
| `test_playwright.py` | Verify Chromium installation |

---

## License

Private — internal tool.
