# URL Shortener

A Flask URL shortener with pluggable short-code strategies (hashing / base64), a
Redis-backed redirect cache, a Redis Bloom filter for O(1) collision checks,
rate limiting, and optional read-replica routing. Backed by PostgreSQL in
production (SQLite in dev).

## Architecture

```
Frontend/                 Single-page UI (static HTML/JS)
Backend/
  app.py                  App factory, routes, health check, Bloom-filter warmup
  config.py               Env-driven config (DB, Redis, strategy, replica)
  extensions.py           db, limiter, redis_client, read-replica session
  Controllers/            HTTP layer
  Services/               Business logic + caching
  Repositories/           DB access (read-replica aware)
  Models/                 SQLAlchemy models
  Domains/Strategy/       Short-code strategies (HashingStrategy, Base64Strategy)
  Utils/BloomFilter.py    Redis-backed Bloom filter (double hashing)
```

## API

| Method | Path                  | Description                          |
| ------ | --------------------- | ------------------------------------ |
| POST   | `/api/shorten`        | Body `{"url": "...", "strategy": "hashing\|base64"}` |
| GET    | `/<short_code>`       | 302 redirect to the original URL     |
| GET    | `/api/stats/<code>`   | Click count and metadata             |
| GET    | `/api/recent`         | 10 most recent URLs                  |
| GET    | `/healthz`            | Health check (DB required, Redis optional) |

## Run locally

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
redis-server --port 6379 &            # optional; app degrades gracefully without it
export DATABASE_URL="sqlite:///dev.db"
export REDIS_URL="redis://localhost:6379"
export SECRET_KEY="dev"
gunicorn --chdir Backend app:app --bind 127.0.0.1:5000
```

Then open http://localhost:5000.

## Deploy to Render

This repo ships a [`render.yaml`](render.yaml) blueprint that provisions a web
service, a PostgreSQL database, and a Redis instance, wired together via
environment variables.

1. Push this repo to GitHub (already done).
2. In the [Render dashboard](https://dashboard.render.com/), choose **New → Blueprint**.
3. Connect this repository. Render reads `render.yaml` and creates all three services.
4. `SECRET_KEY` is generated automatically; `DATABASE_URL` and `REDIS_URL` are
   injected from the provisioned services. No manual env setup required.

The web service exposes `/healthz` as its health check path. Redis is treated as
an optional optimization: if it is briefly unreachable, the app still boots and
serves requests (collision checks and the redirect cache fall back to the DB).

## Configuration

| Env var            | Default                     | Purpose                                  |
| ------------------ | --------------------------- | ---------------------------------------- |
| `DATABASE_URL`     | `sqlite:///urls.db`         | Primary DB (`postgres://` auto-normalized) |
| `REDIS_URL`        | `redis://localhost:6379`    | Cache + rate-limit storage + Bloom filter |
| `SECRET_KEY`       | dev placeholder             | Flask secret                             |
| `DEFAULT_STRATEGY` | `hashing`                   | Default short-code strategy              |
| `READ_REPLICA_URL` | unset                       | Optional Postgres read replica for SELECTs |
