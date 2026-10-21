# Deployment

This project can run locally with Docker Compose and on one host with the
production Compose file. It does not include a managed-cloud account, domain,
or live deployment.

## Processes

| Process | Command | Responsibility |
|---|---|---|
| Migration | `python scripts/init_db.py` | Apply versioned SQL once per release |
| API | `uvicorn app.main:app --host 0.0.0.0 --port 8000` | HTTP API and OpenAPI |
| Worker | `python scripts/worker.py` | Claim and process ingestion jobs |
| Frontend | `npm run start` | Next.js interface |

The API and worker use the same backend image with different commands.

## Local development

```bash
cp .env.example .env
docker compose -f docker/docker-compose.yml --env-file .env up --build
```

`POSTGRES_PASSWORD` and `SECRET_KEY` are required. Compose starts PostgreSQL,
runs migrations, then starts the API, worker, and frontend. Uploaded files use
the shared `document_storage` volume.

## Single-host deployment

Build and publish the backend and frontend images, then run:

```bash
export BACKEND_IMAGE=<registry>/enterprise-ai-backend:<tag>
export FRONTEND_IMAGE=<registry>/enterprise-ai-frontend:<tag>
export DATABASE_URL=<managed-postgres-url>
export SECRET_KEY=<at-least-32-random-characters>
export GROQ_API_KEY=<provider-key>
export CORS_ORIGINS=https://<frontend-origin>

docker compose -f docker/docker-compose.prod.yml up -d
```

The frontend image must be built with `NEXT_PUBLIC_API_URL` set to the public
API origin because Next.js embeds that value at build time.

## Release order

1. Build immutable images.
2. Apply `scripts/release_migrate.sh` or the Compose `migrate` service.
3. Start or replace the API and worker.
4. Confirm `GET /ready` returns HTTP 200.
5. Confirm the frontend can authenticate against the API.

Do not start multiple new API versions before their migration has completed.

## Database

Use PostgreSQL 16 with the `vector` and `pgcrypto` extensions. Keep the
database private to the application network. Take backups before migrations and
test restoration separately; this repository does not automate backups.

## Storage and scaling

The current storage implementation writes files to a local directory. API and
worker replicas must share that persistent volume. Independent hosts require an
object-storage adapter, which is not implemented.

API replicas can scale horizontally because requests do not store session state
in process memory. Rate limiting is in-memory, so it is not shared across
replicas. Workers can scale because job claims use `FOR UPDATE SKIP LOCKED`.

## Health checks

- `GET /health` confirms the API process is running.
- `GET /ready` confirms PostgreSQL accepts a trivial query.
- Readiness does not call the LLM provider.

## Secrets

Supply secrets through the deployment environment. Do not bake them into images
or commit them. Required values are `DATABASE_URL` or the local Postgres
password, `SECRET_KEY`, and `GROQ_API_KEY`.

## What this deployment does not provide

- A provisioned cloud project or DNS/TLS certificate
- Automatic image publishing
- Multi-host shared storage
- A shared rate-limit store
- Database backup automation
- Measured availability or latency targets
