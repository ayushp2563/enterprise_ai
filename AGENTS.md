## Cursor Cloud specific instructions

Docker is not installed here. Use host PostgreSQL 16 with the `pgvector` extension instead of Compose.

- If Postgres is down, start it with `sudo pg_ctlcluster 16 main start`. Package install does not start the cluster because `policy-rc.d` blocks service starts.
- Python dependencies are in `venv/` at the repo root. Create it with `python3 -m venv venv`, install CPU torch from `https://download.pytorch.org/whl/cpu`, then `pip install -r requirements.txt`. The image Python is 3.12; that is enough for the pinned requirements.
- Local secrets live in a gitignored `.env` copied from `.env.example`. `SECRET_KEY` must be at least 32 characters. Host processes need `DATABASE_URL=postgresql://postgres:<password>@localhost:5432/enterprise_ai`. Compose builds its own database URL and does not read `DATABASE_URL` from the file.
- `GROQ_API_KEY` must be non-empty or settings fail to load. A placeholder lets the API boot. Chat and RAG calls need a real Groq key; none is present in this environment.
- Next.js reads `frontend/.env.local`, not the repo-root `.env`. Set `NEXT_PUBLIC_API_URL=http://localhost:8000` there.
- Apply migrations from the repo root with `./venv/bin/python scripts/init_db.py` so `load_dotenv()` finds `.env`.
- API: `./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000` from the repo root. Readiness is `http://localhost:8000/ready`. OpenAPI is `http://localhost:8000/docs`.
- Frontend: in `frontend/`, `npm ci` once, then `npm run dev -- --hostname 0.0.0.0 --port 3000`.
- Tests use `enterprise_ai_test`. Migrate that database, then run `DATABASE_URL=postgresql://postgres:<password>@localhost:5432/enterprise_ai_test RUN_DB_TESTS=1 ./venv/bin/pytest -q`. `tests/conftest.py` only fills `DATABASE_URL` when it is unset, and its default password is `postgres`.
- Do not commit `.env` or `frontend/.env.local`.
