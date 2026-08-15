# Fluxera BESS Intelligence & Assurance Platform

Sprint 1 is a secure, evidence-centric modular monolith for manual Pre-Bid requirement assurance.

## Local setup

Prerequisites: Python 3.12, Docker Compose, and a virtual environment tool.

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -e '.[test]'
cp .env.example .env
docker compose up -d
uvicorn apps.api.main:app --reload
```

The API is available at `http://localhost:8000`; health is `GET /health` and readiness is `GET /ready`.

Start the web workspace in a second terminal:

```bash
cd apps/web
npm install
npm run dev
```

The web app is available at `http://localhost:3000`. Set `NEXT_PUBLIC_API_URL` in `apps/web/.env.local` when the API is not on localhost.

Run checks with:

```bash
pytest
ruff check .
ruff format --check .
mypy apps packages
```

Stop local dependencies with `docker compose down`. No production deployment is implied by this local stack.
