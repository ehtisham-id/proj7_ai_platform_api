
# AI Platform API

Compact FastAPI backend for file conversions, PDF processing, QR generation, image editing, summarization, and data analysis.

**Repository layout**
- `app/` — main application package (routers, services, models, schemas)
- `app/api/v1/endpoints/` — REST endpoints (see Endpoints section)
- `app/core/` — configuration, database, security helpers
- `app/models/` — SQLAlchemy models
- `app/services/` — business logic and external integrations (MinIO, PDF, QR, etc.)
- `alembic/` — DB migrations (scaffolded)
- `Dockerfile` — container image
- `requirements.txt` — Python dependencies

## Quickstart (local)

Prerequisites: Python 3.14, PostgreSQL, MinIO (or adjust storage), Redis for Celery if used.

1. Create and activate virtualenv:

```bash
python -m venv env
source env/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure environment variables (create a `.env` file) — see `app/core/config.py` for names. At minimum set:

- `DATABASE_URL` (e.g. `postgresql+asyncpg://user:pass@host:5432/db`)
- `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`
- `SECRET_KEY`

4. Run Alembic migrations (after installing alembic in env):

```bash
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

5. Run the app:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Or build and run the Docker image:

```bash
docker build -t proj7-api:local .
docker run --env-file .env -p 8000:8000 proj7-api:local
```

## Authentication

The API uses JWT bearer tokens. Authenticate via `/auth/login` to receive an `access_token` and `refresh_token`. Include `Authorization: Bearer <access_token>` header on protected endpoints.

## Endpoints

Base API root: `/api/v1` (see `app.main` for exact mounting). Below are the primary routes and short descriptions.

- **Authentication** (`/auth`)
	- `POST /auth/register` — register a user. Body: `UserCreate` (email, password, role).
	- `POST /auth/login` — obtain tokens. Form: `username`, `password` (OAuth2PasswordRequestForm).
	- `POST /auth/refresh` — refresh access token. Body: `{ "refresh_token": "..." }`

- **Files** (`/files`)
	- `POST /files/` — upload a file (multipart). Auth required. Returns file metadata.
	- `GET /files/{file_id}` — download file. Auth required.
	- `DELETE /files/{file_id}` — delete file. Auth required.
	- `PUT /files/{file_id}/rename` — rename file. Body: `FileRename`.
	- `GET /files/{file_id}/versions` — list versions for a file.

- **PDF** (`/pdf`)
	- `POST /pdf/merge` — merge multiple PDFs (multipart files). Auth required.
	- `POST /pdf/convert` — convert uploaded file to PDF.

- **QR Codes** (`/qrcode`)
	- `POST /qrcode/generate` — generate QR image from payload. Body: `QRGenerate`.

- **Photo Editing** (`/photo`)
	- `POST /photo/edit` — multipart form: `operations` (JSON string) + `file` (image). Returns edited image metadata and URL.
		- Note: `operations` should be JSON matching `PhotoEdit` schema.

- **File Conversion** (`/convert`)
	- `POST /convert/` — multipart form: `conversion` (JSON string) + `file` (file). Returns converted file metadata and URL.

- **Summarization** (`/summarize`)
	- `POST /summarize/` — upload text file to queue summarization job. Returns `job_id`.
	- `GET /summarize/jobs/{job_id}` — check job status and result URL.

- **AR Menu** (`/ar/menu`)
	- `POST /ar/menu/create` — upload CSV/JSON menu file; returns AR menu JSON preview URL and metadata.

- **Data Analysis** (`/analysis`)
	- `POST /analysis/upload` — upload CSV/XLSX dataset; returns analysis JSON and charts.

- **WebSocket** (`/ws`)
	- `WebSocket /ws/notifications` — WebSocket endpoint for notifications (authenticated via dependency).

For exact request/response schemas, see `app/schemas/*.py`.

## Notes & Recommendations

- Multipart endpoints that accept JSON models require the client to send the JSON as a form field, e.g. using `FormData.append('conversion', JSON.stringify({...}))` in browser clients.
- Ensure the `alembic` CLI uses the same `DATABASE_URL` as the app (we load settings in `alembic/env.py`).
- Consider adding tests and CI that run `python -m compileall`, `ruff`/`mypy`, and `pytest`.

## Development helpers

- Linting / formatting: `black`, `ruff` (add to `requirements-dev` as desired).
- Run background workers (Celery) if using tasks: configure `CELERY_BROKER_URL` and run `celery -A app.celery_app worker --loglevel=info`.

## Contributing

1. Fork and create a branch for your feature.
2. Run tests and linters locally.
3. Open a PR with clear description and changelog.

---
If you want, I can also generate example `curl` or Postman requests for each endpoint, or produce OpenAPI enhancements. Which would you prefer next?
