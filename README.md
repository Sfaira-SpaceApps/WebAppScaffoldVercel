# FastAPI + PostgreSQL Scaffold for Vercel

Minimal backend scaffold using FastAPI, SQLAlchemy 2.x, psycopg 3, Alembic, Pydantic Settings, and pytest.

## Architecture

```text
HTTP client
    |
    v
Vercel-hosted FastAPI
    |
    v
Managed PostgreSQL
```

The application keeps the boundary deliberately small:

```text
route -> service -> database
```

There is no worker, queue, Redis, frontend, authentication layer, object storage, or FITS processing in this scaffold.

## Repository layout

```text
app/
  main.py
  config.py
  logging_config.py
  api/
  db/
  schemas/
  services/
alembic/
tests/
alembic.ini
.env.example
.python-version
pyproject.toml
README.md
```

## API

- `GET /`
- `GET /health`
- `GET /db-health`
- `POST /examples`
- `GET /examples`
- `GET /examples/{id}`

`/health` checks only the API process. `/db-health` executes `SELECT 1` against PostgreSQL.

## Local setup

Python 3.12 is selected in `.python-version` to match a currently supported Vercel Python runtime.

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

macOS/Linux:

```bash
source .venv/bin/activate
pip install -e ".[dev]"
```

Copy the environment template:

```bash
cp .env.example .env
```

On PowerShell:

```powershell
Copy-Item .env.example .env
```

## Local PostgreSQL

Use an existing PostgreSQL server or run one with Docker:

```bash
docker run --name scaffold-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=app \
  -p 5432:5432 \
  -d postgres:17
```

The default local connection string is:

```text
postgresql+psycopg://postgres:postgres@localhost:5432/app
```

## Migrations

Schema changes are explicit. Do not create tables during FastAPI startup.

Apply migrations with:

```bash
alembic upgrade head
```

Create a future migration with:

```bash
alembic revision --autogenerate -m "describe change"
```

## Run locally

```bash
uvicorn app.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000/docs
```

The Uvicorn command is for local development only. Vercel loads the FastAPI ASGI application directly.

## Tests

```bash
pytest
```

The basic tests do not require a live PostgreSQL server. `/db-health` and CRUD integration tests do require a database if you add them later.

## Deploy to Vercel

Vercel currently detects FastAPI applications in standard entrypoints including `app/main.py`. This scaffold therefore does not include an `/api` wrapper or `vercel.json` rewrite.

1. Push the repository to GitHub.
2. Import the repository into Vercel.
3. Add the following project environment variables:
   - `DATABASE_URL`
   - `APP_ENV=production`
   - `LOG_LEVEL=INFO`
4. Deploy.

Use a managed PostgreSQL service; PostgreSQL does not run inside this Vercel application.

For `DATABASE_URL`, prefer your provider's pooled connection endpoint when the provider recommends one for serverless applications. The scaffold keeps the SQLAlchemy engine at module scope so warm Vercel instances can reuse it and enables `pool_pre_ping` to detect dead connections.

Do not commit production credentials. In Vercel, store `DATABASE_URL` as a Secret environment variable.

## Production migrations

Do not run `alembic upgrade head` on every API startup.

Run migrations explicitly against the target database before or as a controlled deployment step. For a small project, the simplest workflow is to run Alembic from a trusted local/CI environment with the production `DATABASE_URL` configured.

## Notes on serverless database connections

Each Vercel Python instance can own its own SQLAlchemy pool. Connection limits therefore matter as the application scales. Prefer a managed PostgreSQL provider's serverless/pooler URL when available and monitor its connection limit before increasing SQLAlchemy pool sizes.

The exact pooling strategy is provider-specific. This scaffold intentionally avoids hard-coding `NullPool` or provider-specific settings until a database provider is selected.
