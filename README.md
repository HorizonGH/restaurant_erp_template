# Restaurant ERP Template

A professional backend for restaurant inventory management built with a modular monolith architecture. Designed to scale from a single restaurant to a multi-branch chain.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.13 |
| Framework | FastAPI |
| ORM | SQLAlchemy 2.0 (async) |
| Validation | Pydantic v2 |
| Database | PostgreSQL |
| Migrations | Alembic |
| Package Manager | uv |
| Logging | structlog |
| Server | Uvicorn |
| Code Quality | Ruff, Pyright, pre-commit |

## Prerequisites

- **Python 3.13** — check with `python --version`
- **uv** — install from [docs.astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/)
- **PostgreSQL 14+** — running locally or via Docker

## Installation

```bash
# 1. Clone the repository
git clone <repo-url>
cd restaurant_erp_template

# 2. Copy environment variables
cp .env.example .env

# 3. Edit .env with your database credentials
#    DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/restaurant_erp

# 4. Install dependencies
uv sync
```

## Database Setup

```bash
# Create the database (if using psql)
psql -U postgres -c "CREATE DATABASE restaurant_erp;"

# Run migrations
uv run alembic upgrade head
```

## Running the Server

```bash
# Development (with auto-reload)
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at `http://localhost:8000`.

## Running with Docker

> Docker Compose is planned for Sprint 0 and is not yet available. Once added, the command will be:

```bash
# Start all services (app + PostgreSQL + Redis + pgAdmin + Mailpit)
docker compose up -d

# Run migrations inside the container
docker compose exec app alembic upgrade head
```

## API Documentation

Once the server is running, interactive docs are available at:

| Interface | URL |
|-----------|-----|
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| OpenAPI JSON | http://localhost:8000/openapi.json |

## API Reference

See [docs/catalog-api.md](docs/catalog-api.md) for the full endpoint reference with request/response examples.

**Implemented endpoints:**

| Module | Prefix | Endpoints |
|--------|--------|-----------|
| Health | `/api/v1` | `GET /health` |
| Categories | `/api/v1/catalog/categories` | CRUD (5 endpoints) |
| Units of Measure | `/api/v1/catalog/units` | CRUD (5 endpoints) |
| Ingredients | `/api/v1/catalog/ingredients` | CRUD + supplier links (7 endpoints) |
| Suppliers | `/api/v1/catalog/suppliers` | CRUD + ingredient links (8 endpoints) |

## Project Structure

```
restaurant_erp_template/
├── app/
│   ├── main.py                         # FastAPI application entry point
│   ├── core/
│   │   ├── settings.py                 # Environment configuration
│   │   ├── logging.py                  # structlog setup
│   │   └── shared/                     # Reusable base layer
│   │       ├── domain/
│   │       │   ├── entities.py         # BaseEntity (UUID PK + timestamps)
│   │       │   ├── exceptions.py       # AppException hierarchy
│   │       │   └── helpers.py          # utcnow()
│   │       ├── infrastructure/
│   │       │   ├── database.py         # SQLAlchemy async session factory
│   │       │   ├── repository.py       # BaseRepository[T] with CRUD
│   │       │   └── filters.py          # BaseFilterSet with pagination
│   │       ├── application/
│   │       │   ├── service.py          # BaseService[T]
│   │       │   └── validators.py       # StrippedStr, LowerStr
│   │       └── presentation/
│   │           ├── responses.py        # APIResponse[T], ErrorResponse
│   │           ├── pagination.py       # PageParams, Page[T]
│   │           ├── schemas.py          # BaseInputSchema, BaseOutputSchema
│   │           └── exception_handlers.py
│   ├── middlewares/
│   │   └── logging_middleware.py       # Request ID + duration logging
│   └── modules/
│       └── catalog/                    # Catalog module (Sprint 2)
│           ├── domain/
│           │   ├── models.py           # SQLAlchemy models
│           │   ├── enums.py            # UnitType
│           │   └── exceptions.py       # Domain-specific exceptions
│           ├── infrastructure/
│           │   ├── repository.py       # Typed repositories
│           │   └── filters.py          # FilterSets
│           ├── application/
│           │   ├── schemas.py          # Pydantic input/output schemas
│           │   └── service.py          # Business logic services
│           └── presentation/
│               ├── router.py           # Aggregated router
│               ├── categories_router.py
│               ├── units_router.py
│               ├── ingredients_router.py
│               └── suppliers_router.py
├── migrations/                         # Alembic migrations
│   └── env.py
├── docs/
│   └── catalog-api.md                  # API reference with curl examples
├── pyproject.toml
├── alembic.ini
└── .env.example
```

## Development

### Code Quality

```bash
# Lint and format
uv run ruff check .
uv run ruff format .

# Type checking
uv run pyright

# Run all pre-commit hooks
uv run pre-commit run --all-files
```

### Pre-commit Hooks

Pre-commit runs automatically on every `git commit`. First-time setup:

```bash
uv run pre-commit install
```

Hooks configured: trailing whitespace, end-of-file fixer, YAML/TOML validation, Ruff lint + format, Pyright.

### Conventional Commits

This project follows [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(catalog): add ingredient search by SKU
fix(inventory): prevent negative stock on exit
docs: update API reference
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | — | PostgreSQL async URL (`postgresql+asyncpg://...`) |
| `LOG_LEVEL` | No | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `LOG_JSON` | No | `true` | Output logs as JSON (`true`) or pretty-print (`false`) |

> Additional variables for Redis, JWT, SMTP, and Celery will be added in Sprint 0 (infrastructure setup).

## Architecture

This project follows a **Modular Monolith** pattern:

- Each module (`catalog`, `inventory`, `purchasing`, etc.) is self-contained with its own models, schemas, services, repositories, and routers.
- Modules communicate **only through public service interfaces** (`public.py`) — never by importing each other's repositories directly.
- The shared `core/` layer provides base classes that all modules inherit from.
- All responses follow a unified envelope: `{"data": ...}` for success, `{"message": ..., "errors": [...]}` for errors.
- All tables use UUID primary keys and soft-delete (`deleted_at`) rather than hard deletes.
