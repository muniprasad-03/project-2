# BuildOnce: AI-Based Career Recommendation System

An AI-powered, cloud-native career recommendation backend built with FastAPI, machine learning (Scikit-learn), and generative AI (Groq/Llama 3 & Gemini). This API processes user skills and resumes, recommends career paths using O*NET occupational data, generates personalized learning roadmaps, and persists user history securely to a cloud database.

## Architecture & Design Principles

This project adheres to a **Cloud-First** design principle. Every stateful resource lives online, ensuring a fully stateless, zero-configuration local development experience.

- **Database**: Supabase PostgreSQL (Cloud) — No local SQLite or Postgres installation required.
- **File Storage**: In-memory parsing for resumes. No files touch the local or container disk.
- **Machine Learning**: Pre-generated TF-IDF artifacts (`.pkl`) are loaded at application startup, enabling fast, stateless inference.
- **LLM Integrations**: Uses free-tier LLM APIs (Groq and Gemini) with built-in failovers for text extraction and roadmap generation.

## Features

- **Skill-Based Recommendations (`/api/v1/recommend/skills`)**: Uses cosine similarity against O*NET data to find the best career matches for a given set of skills.
- **Resume Parsing (`/api/v1/resume/parse`)**: Extracts text from PDF and DOCX files entirely in-memory and identifies key skills using LLMs.
- **Learning Roadmaps (`/api/v1/roadmap/generate`)**: Generates structured, multi-week learning roadmaps tailored to missing skills for a target career.
- **AI Career Chat (`/api/v1/chat/advise`)**: Contextual, multi-turn career advice powered by Generative AI.
- **History & Bookmarks (`/api/v1/history`)**: Persists recommendation history and bookmarks securely in Supabase PostgreSQL.

## Tech Stack

- **Framework**: FastAPI (Python 3.10+)
- **ORM & DB**: SQLAlchemy 2.0, Alembic, psycopg2-binary, Supabase PostgreSQL
- **Machine Learning**: Scikit-Learn, Pandas, NumPy, Joblib
- **Generative AI**: Groq (Llama 3), Google Gemini 2.5 Flash
- **Deployment**: Docker (Multi-stage builds)
- **Testing**: Pytest, httpx TestClient

## Prerequisites

You need zero local database installations to run this project. You only need:

1. Python 3.10+
2. A free [Supabase](https://supabase.com) account (for PostgreSQL)
3. A free [Groq Cloud](https://console.groq.com) API key
4. A free [Google AI Studio](https://aistudio.google.com) API key

## Local Setup

### 1. Clone the repository and install dependencies

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the `backend/` directory:

```env
ENVIRONMENT=development
PORT=8000

# Supabase Postgres Connection String (Session pooler)
DATABASE_URL=postgresql://postgres.xxxx:password@aws-0-region.pooler.supabase.com:5432/postgres

# Free LLM Providers
GROQ_API_KEY=your_groq_key_here
GEMINI_API_KEY=your_gemini_key_here

CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

### 3. Run Database Migrations

Apply the database schema directly to your Supabase project using Alembic:

```bash
alembic upgrade head
```

*(Note: Alembic will connect using the `DATABASE_URL` in your `.env` file. Do not edit `alembic.ini` for credentials).*

### 4. Start the Application

```bash
uvicorn app.main:app --reload
```

The API will be available at [http://localhost:8000](http://localhost:8000).  
Interactive Swagger documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

## Docker Deployment

This project uses a multi-stage Dockerfile designed for cloud deployments (e.g., Google Cloud Run, AWS ECS, Render) with a completely stateless container. 

To run locally via Docker Compose:

```bash
docker-compose up -d --build
```
*(This will start the backend and a local Postgres fallback container for testing, though in production you should link the standalone container directly to Supabase via environment variables).*

## Testing

Tests are written using `pytest` and execute against a separate test database to avoid modifying production data.

Configure `TEST_DATABASE_URL` in your environment (pointing to a separate Supabase project/schema), then run:

```bash
pytest
```

## Project Structure

```
backend/
├── app/
│   ├── api/v1/         # FastAPI endpoint routers (history, recommend, resume, roadmap, chat)
│   ├── core/           # Configuration and DB session management
│   ├── ml/             # ML preprocessing, training, and inference scripts
│   ├── models/         # Pydantic schemas and SQLAlchemy DB models
│   └── services/       # External clients (LLMs, Resume Parsers)
├── data/
│   └── artifacts/      # Pickled ML models (tfidf_vectorizer, occupation_matrix)
├── tests/              # Pytest suite
├── alembic/            # Database migration scripts
├── Dockerfile          # Multi-stage production container
└── requirements.txt    # Python dependencies
```
