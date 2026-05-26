# Nexus Company | B2B Intelligence

A premium full-stack B2B intelligence platform designed to scrape, match, and explore Indian company listings from **Zauba Corp** and **data.gov.in**, storing processed records in **NeonDB** and exporting generated CSV/XLSX to **Cloudflare R2**.

🚀 **A product of [Patience AI](https://patienceai.in)**

---

## Features

- **Beautiful Glassmorphic UI**: High-fidelity dark mode with modern typography, subtle glow highlights, interactive micro-animations, and custom material form-fields with glowing bottom borders.
- **Full Light/Dark Theme Switching**: Complete system-wide visual styles matching active theme selections (including Auth Login & Signup pages).
- **Tesla-Style Animations**: Elegant page elements staggered load fade-ins and smooth translations on viewport entrance.
- **Precision Data Separation**: Clean segmented filters on the main dashboard to view:
  - **All**: Standard view showing the entire directory merged together.
  - **Companies Only**: Traditional registered businesses and corporations.
  - **Startups Only**: High-growth validated technology startups.
- **Robust Scraper Engine**: Orchestrated Playwright (for Zauba Corp) + HTTPX (for data.gov.in) with APScheduler automations and custom RapidFuzz confidence scoring.
- **Enterprise File Exports**: Parallel XLSX and CSV generators with R2 object store integration and automatic presigned-URL expiration links.
- **Unified Cost-Efficient Production Container**: Fast multi-stage Docker build recipe compiling the Angular frontend and serving it directly through the FastAPI backend, allowing single web service deployment.

---

## Directory Architecture

```
nexus-company/
├── backend/
│   ├── alembic/                      # Database migrations
│   ├── app/
│   │   ├── main.py                   # FastAPI entrance + SPA routing + static files server
│   │   ├── config.py                 # Pydantic configuration loader
│   │   ├── database.py               # Async DB connection setup
│   │   ├── models/                   # SQL ORM models
│   │   ├── schemas/                  # Pydantic request/response schemas
│   │   ├── routers/                  # Router endpoints (auth, companies, scraper, exports)
│   │   └── services/
│   │       ├── auth_service.py       # Security, hashing, and token logic
│   │       ├── zauba_scraper.py      # Playwright Zauba scraper
│   │       ├── datagov_scraper.py    # data.gov.in API consumer
│   │       ├── matcher_service.py    # RapidFuzz match algorithm
│   │       ├── r2_service.py         # Cloudflare R2 uploader & URL signer
│   │       ├── export_service.py     # CSV / Excel formatting
│   │       └── scheduler_service.py  # APScheduler daily orchestrator
│   ├── scripts/                      # Admin and setup scripts
│   ├── seed_companies.py             # Development database seed script
│   ├── run_zauba_seed.py             # Scraper pipeline trigger script
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── index.html                # App entry with Material fonts and custom Favicon
│   │   ├── styles.scss               # Premium light/dark variables and page animations
│   │   └── app/
│   │       ├── app.routes.ts         # Dynamic browser route names and title config
│   │       └── features/
│   │           ├── auth/             # Login & Signup modules
│   │           └── dashboard/        # B2B search, filters, and downloads
│   └── package.json
├── Dockerfile                        # Unified Multi-Stage Production Builder
├── docker-compose.yml                # Single service local compose orchestrator
└── render.yaml                       # Unified Platform-as-a-Service blueprint
```

---

## Quick Start (Local Docker Orchestration)

To spin up the entire application instantly (both frontend and backend running on a single port):

```bash
docker-compose up --build -d
```

- **Unified Web Interface**: `http://localhost:8001`
- **Swagger Documentation**: `http://localhost:8001/docs`
- **API Health Check**: `http://localhost:8001/health`

---

## Manual Local Development Setup

### 1. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate       # macOS/Linux
# .\venv\Scripts\activate      # Windows

pip install -r requirements.txt
playwright install chromium
```

Create a `.env` file in the `backend/` directory:

```env
DATABASE_URL=postgresql+asyncpg://USER:PASS@HOST/DB?sslmode=require
DATABASE_URL_SYNC=postgresql://USER:PASS@HOST/DB?sslmode=require
SECRET_KEY=<random-32-char-string>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
APP_ENV=development
R2_ACCOUNT_ID=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET_NAME=startupintel-exports
R2_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com
DATAGOV_API_KEY=<your-key>
```

Run database migrations:

```bash
alembic upgrade head
```

Start the FastAPI application:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

### 2. Frontend Setup

```bash
cd frontend
npm ci --legacy-peer-deps
npm start
```

- **App Web Interface**: `http://localhost:4200`
- Custom environment configs are located in `frontend/src/environments/`.

---

### 3. Create Admin Account

```bash
cd backend
python scripts/create_admin.py
```
Default credentials:
- **Email**: `admin@nexusintel.in`
- **Password**: `Admin@110426`

---

### 4. Seeding Data

#### Synthetic Seed
To easily seed 500 fake companies with highly realistic MCA patterns, names, and capital:
```bash
python seed_companies.py
```

#### Real-time Scrape
To trigger a real scraping pipeline manually across the last 5 days:
```bash
python run_zauba_seed.py
```

---

## Automated Testing

Run the FastAPI test suite containing 30 robust endpoint and unit assertions:
```bash
cd backend
pytest -v
```

---

## License

Private repository - Proprietary software.
Developed under **Patience AI**.
