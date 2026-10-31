# Back team (Mark)

Owns `src/backend/`: data ingestion, persistence, analysis jobs, HTTP API, publishing and deployment.
Implements contracts **C2** (`PostSource`), the **C4** HTTP API, and `PostPublisher`. Calls the AI through **C3**.

## Responsibilities

1. `PostSource` adapters: `TwitterApiIoSource` (suggested first), optionally `ScraperSource`, and **`FixturePostSource`** (replays a saved `AccountSnapshot`; needed for tests and demo safety).
2. Analysis job runner: queued → fetching → analyzing → done/failed, with progress reporting. FastAPI background tasks or an `asyncio` task are enough; no Celery or queue needed.
3. Storage for jobs, snapshots and reports (SQLite or a JSON store is fine for the hackathon).
4. Every route in `src/shared/contracts/openapi.json`, with request and response models taken from `eduhub_shared`.
5. Feature flags (`GET /features`) and `DEMO_MODE` (serves pre-computed reports for the demo account).
6. Deployment of the Python service (backend + `eduhub_ai`), plus CORS configured for the front URL.

## Suggested tools (your call)

FastAPI · uvicorn · httpx (async) · pydantic-settings · tenacity (retries) · SQLite (via `sqlite3`/SQLModel) · Docker · Railway, Render or Fly.io · pytest + pytest-asyncio + `httpx.AsyncClient` for API tests · respx to mock twitterapi.io in tests.

## Open questions (research and write your answers here)

- [x] **Data source:** **twitterapi.io** (`TwitterApiIoSource`), used when `DEMO_MODE=0`. It only needs an API key, is cheap, and the ban risk sits with the provider. The official API is reliable but has paid tiers and strict read limits. Scraping is free but fragile and the riskiest for a live demo.
- [x] **Impressions and bookmarks:** yes. `/twitter/user/last_tweets` returns `viewCount` and `bookmarkCount` on every tweet. All 190 posts of the demo account have impressions. No contract change needed.
- [x] **Detail expands / profile clicks / link clicks:** not from twitterapi.io (only the official API with OAuth, on your own tweets). We leave them as `None`.
- [x] **Trends:** yes, `/twitter/trends?woeid=23424747` returns about 25–30 current Argentina trends. If it fails, the analysis fails with `source_unavailable`.
- [x] **Posting:** the demo uses the **X intent URL**. `POST /publications` answers `intent` with a pre-filled `https://x.com/intent/post?text=...` link. No auth, no cost; the user confirms in X.
- [x] **Scheduling:** **simulated** for the demo. `scheduled_for` is echoed back as `scheduled`; nothing is stored or posted later. Real scheduling only makes sense together with an official-API publisher.
- [x] **Posts per analysis:** default 200 (the API accepts 10–500). Pages hold 20 tweets and plain retweets are dropped, so paging stops at the limit, at the last page, or after `ceil(limit/20) * 2` pages, whichever comes first. Cost is about $0.15 per 1,000 tweets, so roughly $0.03–0.06 per 200-post analysis. Fetch time hasn't been measured yet. The free tier allows one request every 5 seconds, which is too slow for paging; any paid balance raises the limit (the account has been topped up).
- [ ] Hosting provider, and how secrets are set there. *Not decided: the demo may run locally.*
- [x] **Demo account:** **@bilinkis** (Santiago Bilinkis: tech, AI, critical thinking; 130k followers; 190 posts, 63% of them replies), plus the shared `demo_finanzas`. Both live in `src/backend/fixtures/` and are seeded in `DEMO_MODE`. Regenerate them with `set -a; source .env; set +a; EDUHUB_FAKE_AI=0 python -m eduhub_backend.tools.snapshot bilinkis --include-shared` (the AI reads `OPENROUTER_API_KEY` from the environment).

## Running locally

```bash
source .venv/bin/activate          # Windows Git Bash: source .venv/Scripts/activate
pip install -e src/backend && pip install --group src/backend/pyproject.toml:test
DEMO_MODE=1 EDUHUB_FAKE_AI=0 uvicorn eduhub_backend.app:main --factory --env-file .env   # http://localhost:8000
pytest src/shared src/backend
```

**Always pass `--env-file .env`.** Our `Settings` reads `.env` itself, but `eduhub_ai` reads `OPENROUTER_API_KEY` and `AI_*` only from the process environment. Without the flag the analyzer silently runs in template mode (no LLM), drafts use the fake generator and the sandbox is off; the only sign is a warning in the log. Variables set on the command line win over `.env`. `EDUHUB_FAKE_AI=1` stays as the emergency switch if OpenRouter fails during the demo.

Settings (see `.env.example`): `DEMO_MODE` (1 = fixture source + seeded demo reports, 0 = twitterapi.io, needs `TWITTERAPI_IO_KEY`), `EDUHUB_FAKE_AI`, `FRONTEND_ORIGIN` (comma-separated), `DATABASE_PATH` (default `data/eduhub.sqlite3`), `FIXTURES_DIR` (default `src/backend/fixtures`).

Real snapshots for the AI team's evaluation live in `src/backend/snapshots/` (not seeded in `DEMO_MODE`).
