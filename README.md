# FastAPI + PostgreSQL Scaffold for Vercel

FastAPI backend with a simple SPHEREx image explorer, SQLAlchemy 2.x, psycopg 3, Alembic, Pydantic Settings, and pytest.

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

The frontend is a responsive HTML page served by FastAPI at `/`. Its Load image button calls `/spherex` on the same origin and displays the PNG response, with loading and error messages. No Node.js build or separate frontend deployment is required. SPHEREx FITS cutouts are processed in memory.

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
  static/
    index.html
alembic/
tests/
alembic.ini
.env.example
.python-version
pyproject.toml
README.md
```

## API

- `GET /` (HTML image explorer)
- `GET /health`
- `GET /db-health`
- `POST /examples`
- `GET /examples`
- `GET /examples/{id}`
- `GET /spherex?ra_deg=210.80227&dec_deg=54.34895&fake_color_theme=plasma`

`/health` checks only the API process. `/db-health` executes `SELECT 1` against PostgreSQL.

`/spherex` calls `app.services.spherex_service.query_spherex()` and returns an
`image/png` response for the earliest overlapping spectral image. Required query
parameters are `ra_deg` (0 inclusive to 360 exclusive) and `dec_deg` (-90 to 90).
Optional parameters are `cutout_size_i` (degrees, default 0.05, greater than 0 and
at most 1) and `fake_color_theme` (Matplotlib colormap, default `gray`).
It returns 422 for invalid input, 404 for no coverage, and 502 for IRSA retrieval
errors. No FITS or PNG output files are saved. This endpoint returns one image;
it does not yet provide a timeline or video.

For example, save the response locally with:

```bash
curl --fail "http://127.0.0.1:8000/spherex?ra_deg=210.80227&dec_deg=54.34895&fake_color_theme=plasma" -o output.png
```

The query and cutout download require access to IRSA. Cutout parameters follow
the [IRSA SPHEREx cutout service](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/cutout_tool.html).

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
http://127.0.0.1:8000/
```

Enter right ascension and declination in degrees, optionally adjust the cutout size and color theme, then click **Load image**. IRSA retrieval may take a minute; some positions have no coverage. The image explorer and `/spherex` do not require a running database. Interactive API documentation remains available at `/docs`.

The Uvicorn command is for local development only. Vercel loads the FastAPI ASGI application directly.

## Tests

```bash
pytest
```

The basic tests do not require a live PostgreSQL server. `/db-health` and CRUD integration tests do require a database if you add them later.

## Deploy to Vercel

Vercel detects FastAPI applications in standard entrypoints including `app/main.py`, as described in its [FastAPI deployment guide](https://vercel.com/docs/frameworks/backend/fastapi). This scaffold therefore does not include an `/api` wrapper or `vercel.json` rewrite. The same deployment serves the HTML page and API.

1. Push the repository to GitHub.
2. Import the repository into Vercel with the repository root as the Root Directory. Use the detected FastAPI framework. Leave build command and output directory overrides unset; there is no frontend build step. Dependencies are declared in `pyproject.toml`.
3. Add the following project environment variables (the database URL is needed only for database routes):
   - `DATABASE_URL`
   - `APP_ENV=production`
   - `LOG_LEVEL=INFO`
4. Deploy, then open `https://<your-project>.vercel.app/` and click **Load image**. Check `/health` for API availability and `/docs` for API documentation.

Keep `app/static/index.html` in the repository; FastAPI serves it directly, and setuptools includes it as package data. Frontend requests use the relative `/spherex` URL, so no API base URL or CORS configuration is needed. Changes deployed from the connected Git branch update both the page and API.

If image requests time out, inspect the Vercel function logs and the project's function duration settings: the request includes an IRSA query, FITS download, and PNG rendering. Deployment must also fit Vercel's Python function bundle limits, including the scientific Python dependencies. Deployment success and live IRSA coverage must be verified in your Vercel project.

Use a managed PostgreSQL service; PostgreSQL does not run inside this Vercel application.

For `DATABASE_URL`, prefer your provider's pooled connection endpoint when the provider recommends one for serverless applications. The scaffold keeps the SQLAlchemy engine at module scope so warm Vercel instances can reuse it and enables `pool_pre_ping` to detect dead connections.

Do not commit production credentials. In Vercel, store `DATABASE_URL` as a Secret environment variable.

## Production migrations

Do not run `alembic upgrade head` on every API startup.

Run migrations explicitly against the target database before or as a controlled deployment step. For a small project, the simplest workflow is to run Alembic from a trusted local/CI environment with the production `DATABASE_URL` configured.

## Notes on serverless database connections

Each Vercel Python instance can own its own SQLAlchemy pool. Connection limits therefore matter as the application scales. Prefer a managed PostgreSQL provider's serverless/pooler URL when available and monitor its connection limit before increasing SQLAlchemy pool sizes.

The exact pooling strategy is provider-specific. This scaffold intentionally avoids hard-coding `NullPool` or provider-specific settings until a database provider is selected.
