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
| API        | FastAPI 0.111 | Python 3.12       |
| Auth       | JWT (python-jose) + bcrypt        |
| Database   | PostgreSQL 16 (async SQLAlchemy)  |
| Cache      | Redis 7                           |
| Rate limit | SlowAPI (100 req/min default)     |
| Metrics    | Prometheus (`/metrics`)           |
| Container  | Docker + Docker Compose           |

---

## Deterministic Backend Generator (no LLM)

BigBack is now also a **spec-driven backend generator**: give it an entity DSL
schema and it emits a complete, runnable backend in **five frameworks** —
`fastapi`, `express`, `hono`, `fastify`, `flask` — with zero LLM calls. Same
spec → same bytes, every time.

### Entity DSL

```text
entity User {
  id string pk
  email string unique
  age int optional
  role Role
}
enum Role { admin member guest }
```

Field types: `string`, `int`, `float`, `bool`, `datetime`, `uuid`, any declared
enum, or any declared entity (relation). Modifiers: `pk`, `unique`, `optional`,
`list`.

### Spec format

```json
{
  "project": "acme-api",
  "framework": "hono",
  "auth": true,
  "health": true,
  "schema": "entity User { id string pk, email string unique }"
}
```

### CLI

```bash
cd backend
python -m generator.cli --list-frameworks
python -m generator.cli spec.json ./out
cat spec.json | python -m generator.cli - ./out
```

### API

```
POST /api/v1/generator/plan          # in-memory plan: files[].rendered
POST /api/v1/generator/materialize   # write to disk (confined to BIGBACK_OUT_ROOT)
GET  /api/v1/generator/frameworks    # available frameworks
```

### What each generated backend includes

- **Validation** — zod (TS frameworks) / pydantic (FastAPI) / deterministic
  validator (Flask)
- **Deterministic in-memory store + seed** — runs with zero external services
- **Real CRUD routes** for every entity — list/create/get/update/delete
- **Optional Bearer-token write-guard** (`API_TOKEN` env)
- **Real integration tests** that pass on first run (`pytest` / `vitest run`)
- **`bigback.spec.json` + `bigback.manifest.json`** — spec + file manifest for
  drift checks

Verified end-to-end: generated FastAPI + Flask backends pass `pytest`; Express +
Hono + Fastify pass `vitest run` and `tsc --noEmit` clean.

### Tests

```bash
cd backend
python -m pytest tests/ -v        # 29 tests (13 generator + 16 app)
```
