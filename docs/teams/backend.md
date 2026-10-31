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

- [ ] **Data source:** twitterapi.io vs scraping vs the official API. Check cost, reliability and ban risk. Whichever you pick, the rest of the system doesn't change.
- [ ] Does the chosen source return **impressions (views)** and **bookmarks** for each tweet? Both are required for our rates. If something is missing, flag it so we can make the field optional in the contract.
- [ ] Does any source provide **detail expands / profile clicks / link clicks**? (Probably only the official API with OAuth, for your own tweets.) These are optional fields in `PostMetrics`.
- [ ] **Trends:** is there an endpoint for current trends in Argentina (WOEID 23424747)? Historical trends are out of scope.
- [ ] **Posting:** options are the official API with OAuth 2.0 PKCE (~$0.015 per post), third-party write endpoints (usually need login cookies), or a **zero-cost fallback: the X intent URL** `https://x.com/intent/post?text=...`, which opens the composer pre-filled with no auth needed. Decide what the demo uses.
- [ ] **Scheduling:** real scheduling (APScheduler + a running process) or simulated for the demo?
- [ ] How many posts per analysis (default 200)? How long does fetching take, and what does it cost?
- [ ] Hosting provider, and how secrets are set there.
- [ ] Demo account: fetch it once and save the snapshot as a fixture.
