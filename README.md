# Fluxera BESS Intelligence Platform

Sprint 1 is a secure, evidence-centric modular monolith for Procurement Intelligence, beginning with the manual Pre-Bid Intelligence workflow. Procurement Assurance is the evidence and review capability within that module.

Current validated scope, pending MVP checkpoints, risks, and verification evidence are maintained in [docs/mvp-progress.md](docs/mvp-progress.md).

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

The web app is available at `http://localhost:3000`. By default, Next.js proxies browser `/api/*` requests to the local API, so no browser-visible API URL is needed.

## Validate an upload

1. Start the API before the web app. Do not open `http://localhost:8000` in a browser; it is an API, so `/` returning `404` is expected. Use `http://localhost:8000/docs` or `/health` instead.
2. In the web app, select **Create workspace**, then **Create project**. The PDF picker intentionally remains disabled until a project exists.
3. Choose a real PDF. The current implementation accepts only files with MIME type `application/pdf`, PDF magic bytes, and a configured maximum of 50 MB / 500 pages.

### Codespaces

Forward only port `3000` and open its URL from the Ports view. The Next.js proxy forwards `/api/*` internally to the API at port `8000`, so the browser does not need access to the Codespace's API port and no CORS override is required.

When the API runs on a different host, set `NEXT_PUBLIC_API_URL` to that browser-visible URL and add the web origin to `FLUXERA_CORS_ORIGINS`. Restart `uvicorn` and `npm run dev` after changing either setting.

Run checks with:

```bash
pytest
ruff check .
ruff format --check .
mypy apps packages
```

Stop local dependencies with `docker compose down`. No production deployment is implied by this local stack.
