# Backend Development Plan (Full, Cloud-Native)
## AI-Based Career Recommendation System

---

## 1. Design Principle: Cloud-First, Not System-First

Every stateful resource lives online, not on your machine or the container's disk:

| Resource | Where it lives | Why |
|---|---|---|
| Database | **Supabase Postgres** (free tier) — used for local dev *and* production, same instance or two Supabase projects | No local Postgres/SQLite install, no "works on my machine" schema drift, same connection string everywhere |
| File storage (resumes, if you choose to keep them) | **Supabase Storage** bucket | Resume files never touch your local disk or the container's filesystem — processed in memory, optionally archived to the bucket |
| Secrets | **`.env` locally, platform secrets in production** | Never hardcoded, never committed |
| ML model artifacts | Generated at build time, committed to the repo (or pushed to Supabase Storage) | Small files (a few MB), regenerating them locally is a one-command step, not a "system dependency" |

Practical effect: cloning this repo onto a brand-new machine and running it needs **zero local database installation** — just a `.env` file pointing at your Supabase project.

---

## 2. Full Technology Stack

| Layer | Technology | Notes |
|---|---|---|
| Language | Python 3.10+ | |
| API Framework | FastAPI | async, auto-generates OpenAPI docs |
| ASGI Server | Uvicorn | |
| Validation | Pydantic v2 + pydantic-settings | request/response contracts + env config |
| Classical ML | Scikit-learn, Pandas, NumPy, Joblib | TF-IDF + cosine similarity engine |
| Generative AI | Groq API (Llama 3), Gemini 2.5 Flash | both free-tier, used as primary/fallback pair |
| Document parsing | pdfplumber, python-docx | in-memory extraction, no temp files |
| **Database** | **Supabase Postgres (cloud, free tier)** | replaces SQLite entirely — one connection string for dev and prod |
| **File storage** | **Supabase Storage (cloud, free tier)** | optional resume archival, no local disk writes |
| ORM | SQLAlchemy 2.0 (async-capable) | |
| Migrations | Alembic | run against the Supabase instance directly |
| DB driver | `psycopg2-binary` (sync) or `asyncpg` (async) | Postgres-only from day one |
| Testing | Pytest, pytest-mock, httpx `TestClient` | LLM calls mocked, DB calls hit a separate Supabase test project/schema |
| Containerization | Docker (multi-stage) | |
| Hosting | Hugging Face Spaces or Render (free tier) | |
| CI | GitHub Actions | |

---

## 3. Cloud Resources Setup (do this before writing code)

1. **Create a Supabase project** at [supabase.com](https://supabase.com) (free tier: 500MB DB, 1GB storage).
2. From Project Settings → Database, copy the **connection string** (use the "Session pooler" URI for serverless-style connections). This becomes `DATABASE_URL`.
3. From Project Settings → API, copy the **Project URL** and **anon/service key** if you plan to use Supabase Storage for resume archival — otherwise skip storage entirely and process files purely in memory.
4. (Recommended) Create a **second, separate Supabase project (or a separate schema in the same one) for testing**, so Pytest never writes into your real data.
5. Get free LLM keys: Groq Cloud (console.groq.com), Google AI Studio for Gemini (aistudio.google.com).

Nothing else to install locally besides Python packages — no Postgres server, no SQLite file, no local storage folder for uploads.

---

## 4. Full Directory Structure (every file annotated)

```
backend/
│
├── app/
│   │
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── recommend.py        # POST /api/v1/recommend/skills — calls ml/inference.py, returns SkillMatchResponse
│   │       ├── resume.py           # POST /api/v1/resume/parse — validates upload, extracts text in-memory, calls llm_client, returns skill list
│   │       ├── roadmap.py          # POST /api/v1/roadmap/generate — takes target job + missing skills, calls llm_client, returns weekly plan
│   │       ├── chat.py             # POST /api/v1/chat/advise — contextual multi-turn advice via llm_client
│   │       └── history.py          # GET/POST/DELETE on RecommendationLogs — all reads/writes go straight to Supabase Postgres
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                # Settings(BaseSettings): DATABASE_URL (Supabase), GROQ_API_KEY, GEMINI_API_KEY,
│   │   │                             #   SUPABASE_URL, SUPABASE_KEY (if using Storage), CORS_ORIGINS — all read from .env
│   │   ├── database.py              # SQLAlchemy engine pointed at settings.DATABASE_URL (Supabase), session factory,
│   │   │                             #   get_db() dependency for FastAPI routes
│   │   └── security.py              # (optional) request validation helpers — file size/type checks, rate-limit helpers
│   │
│   ├── ml/
│   │   ├── __init__.py
│   │   ├── preprocess.py            # Downloads/cleans O*NET CSVs, aggregates skill terms per SOC code
│   │   ├── train.py                 # Fits TfidfVectorizer, saves tfidf_vectorizer.pkl / occupation_matrix.pkl / occupation_metadata.json
│   │   └── inference.py             # match_careers(user_skills, top_k) — loads .pkl artifacts once at import,
│   │                                 #   returns ranked matches + matched_skills + missing_skills as List[str]
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── schemas.py               # All Pydantic request/response models (SkillMatchRequest, CareerMatchResult,
│   │   │                             #   SkillMatchResponse, ResumeParseResponse, RoadmapRequest/Response, ChatMessage, etc.)
│   │   └── db_models.py             # SQLAlchemy ORM classes: Users, CareerProfiles, RecommendationLogs
│   │                                 #   (all tables live in Supabase Postgres — no local table)
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── llm_client.py            # LLMClient class — wraps Groq + Gemini calls, exponential backoff,
│   │   │                             #   provider fallback, validates JSON output against a Pydantic model before returning
│   │   ├── resume_parser.py         # extract_text(file_bytes, content_type) — pdfplumber for PDF, python-docx for DOCX,
│   │   │                             #   works entirely on in-memory bytes, never writes to disk
│   │   └── storage_client.py        # (optional) thin wrapper around Supabase Storage's Python client,
│   │                                 #   only used if you choose to archive original resume files
│   │
│   ├── __init__.py
│   └── main.py                      # FastAPI app instance, CORS middleware, exception handlers,
│                                     #   lifespan() that loads ML .pkl artifacts once at startup, includes all v1 routers
│
├── data/
│   ├── raw/                          # downloaded O*NET CSVs (gitignored — large, re-downloadable)
│   └── artifacts/                    # tfidf_vectorizer.pkl, occupation_matrix.pkl, occupation_metadata.json
│                                      #   (committed — small, and regenerating needs the raw CSVs)
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                  # pytest fixtures — TestClient, a session pointed at the SEPARATE test Supabase
│   │                                 #   project/schema, and mocked llm_client
│   ├── test_ml_inference.py         # asserts match_percentage bounds, missing_skills always List[str]
│   ├── test_recommend_api.py        # endpoint-level tests for /recommend/skills
│   ├── test_resume_api.py           # upload validation (size/type), mocked LLM extraction response
│   ├── test_roadmap_api.py
│   ├── test_chat_api.py
│   └── test_history_api.py          # verifies rows actually land in / clear from the test Supabase DB
│
├── alembic/
│   ├── versions/                    # one file per migration, autogenerated then reviewed
│   └── env.py                       # configured to read DATABASE_URL from settings, targets Supabase directly
├── alembic.ini
│
├── .env.example                     # DATABASE_URL, GROQ_API_KEY, GEMINI_API_KEY, SUPABASE_URL, SUPABASE_KEY, CORS_ORIGINS
├── .gitignore                        # .env, data/raw/, __pycache__/, *.pkl if you choose not to commit them
├── Dockerfile                        # real multi-stage build (see Section 7)
├── requirements.txt
├── alembic.ini
└── main.py -> app/main.py            # (or run via `uvicorn app.main:app`; keep one consistent entrypoint, not both)
```

**Note on the entrypoint:** pick one — either a thin `main.py` at the repo root that imports `app.main:app`, or run Uvicorn directly against `app.main:app` everywhere (Dockerfile, dev script, deployment config). Having both a root `main.py` and `app/main.py` is a common source of "which one is actually running" confusion — the tree above keeps `app/main.py` as the real app and a one-line root shim only if your hosting platform expects `main.py` at the root.

---

## 5. `requirements.txt` (cloud-DB version)

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
pydantic==2.9.2
pydantic-settings==2.5.2
scikit-learn==1.5.2
pandas==2.2.3
numpy==1.26.4
joblib==1.4.2
sqlalchemy==2.0.35
alembic==1.13.3
psycopg2-binary==2.9.9
pdfplumber==0.11.4
python-docx==1.1.2
python-multipart==0.0.12
httpx==0.27.2
python-dotenv==1.0.1
supabase==2.7.4
pytest==8.3.3
pytest-mock==3.14.0
```
No `sqlite3` dependency anywhere — Postgres via `psycopg2-binary` is the only DB driver, used identically in dev and prod. `supabase` is only needed if you use `storage_client.py`; drop it if you're not archiving resume files.

---

## 6. `.env.example`

```
# Supabase Postgres — from Project Settings > Database > Connection string (Session pooler)
DATABASE_URL=postgresql://postgres.xxxx:password@aws-0-region.pooler.supabase.com:5432/postgres

# Only needed if archiving resume files to Supabase Storage
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=your_service_or_anon_key

# Free LLM providers
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key

CORS_ORIGINS=["http://localhost:5173"]
```

---

## 7. Dockerfile (multi-stage, cloud-DB — no local volume needed)

```dockerfile
FROM python:3.10-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.10-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
No `VOLUME` directive, no bind-mounted DB file — the container is fully stateless, all state is in Supabase. This is what makes it trivially redeployable: kill the container, start a new one anywhere, nothing is lost because nothing was stored locally in the first place.

---

## 8. Data Flow (end to end)

```
User → POST /resume/parse (file bytes, in-memory)
         → resume_parser.py extracts text (no disk write)
         → llm_client.py → Groq/Gemini → JSON skill list
     → POST /recommend/skills (skills list)
         → ml/inference.py (loaded once at startup from data/artifacts/*.pkl)
         → ranked careers + missing_skills
     → POST /roadmap/generate (target job + missing_skills)
         → llm_client.py → weekly plan
     → All of the above optionally logged to Supabase Postgres via history.py
         (RecommendationLogs row: user_id, job_title, match %, missing_skills, roadmap, timestamp)
     → GET /history/{user_id} → reads straight from Supabase, no local cache
```

---

## 9. Development Order

1. **Supabase project created**, `DATABASE_URL` in `.env` — verify connectivity with a one-line script (`SELECT 1`) before writing any app code.
2. **Phase 1 — ML core**: `preprocess.py` → `train.py` → `inference.py`, verified offline against sample skill lists.
3. **Phase 2 — API skeleton**: `config.py`, `database.py` (pointed at Supabase), `schemas.py`, `main.py`, `recommend.py`.
4. **Phase 3 — LLM services**: `llm_client.py`, `resume_parser.py`, `resume.py`, `roadmap.py`, `chat.py`.
5. **Phase 4 — persistence**: `db_models.py`, Alembic migration run directly against Supabase, `history.py`.
6. **Phase 5 — tests, Docker, deploy**: point CI/test config at the *separate* test Supabase project, build the multi-stage image, deploy to Hugging Face Spaces or Render with the same `.env` values set as platform secrets.

---

## 10. Build Checklist

- [ ] Supabase project reachable from local machine via `DATABASE_URL`, no local DB installed
- [ ] `alembic upgrade head` creates all tables directly on Supabase
- [ ] ML artifacts generated once, committed to `data/artifacts/`
- [ ] `/recommend/skills` returns real matches
- [ ] Resume upload processed fully in memory, never written to local/container disk
- [ ] History reads/writes confirmed against Supabase (check rows in the Supabase table editor)
- [ ] Test suite runs against the separate test Supabase project, not production data
- [ ] Docker image has no volumes/bind mounts — fully stateless
- [ ] Deployed instance uses the same `DATABASE_URL` (or a prod Supabase project) via platform secrets, not `.env` files baked into the image
