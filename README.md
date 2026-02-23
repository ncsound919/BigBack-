# BigBack- · BackendMCP

A full-stack **backend configurator** — pick your framework, database, cache, auth strategy, and feature flags through a sleek UI, then export the ready-to-use JSON spec.

```
Frontend (React)  →  http://localhost:3000
API (FastAPI)     →  http://localhost:8000   · Swagger at /docs
Metrics           →  http://localhost:8000/metrics
```

---

## Quickstart (Docker)

```bash
# 1. Clone
git clone https://github.com/ncsound919/BigBack-
cd BigBack-

# 2. (Optional) set a real secret key
export SECRET_KEY="your-super-secret-key"

# 3. Start everything
docker compose up --build
```

Open **http://localhost:3000** — the UI is live.

---

## Local development (without Docker)

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev        # starts on http://localhost:3000
```

> The Vite dev server proxies `/api/*` requests to `http://localhost:8000` automatically.

### Tests

```bash
cd backend
pytest tests/ -v
```

---

## Stack

| Layer      | Technology                        |
|------------|-----------------------------------|
| UI         | React 18 + Vite 5                 |
| API        | FastAPI 0.111 · Python 3.12       |
| Auth       | JWT (python-jose) + bcrypt        |
| Database   | PostgreSQL 16 (async SQLAlchemy)  |
| Cache      | Redis 7                           |
| Rate limit | SlowAPI (100 req/min default)     |
| Metrics    | Prometheus (`/metrics`)           |
| Container  | Docker + Docker Compose           |
