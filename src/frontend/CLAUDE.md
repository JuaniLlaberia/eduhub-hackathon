# src/frontend: Front team (Lupa, Varela)

Screens, suggested tools and open questions: `docs/teams/frontend.md`. The UI is in **Spanish (es-AR)**.

Contract obligations:
- Talk only to the backend HTTP API defined in `src/shared/contracts/openapi.json`. **Generate the TS types from it** (`npx openapi-typescript ../shared/contracts/openapi.json -o src/lib/api/schema.d.ts`), and never hand-write or edit API types. Regenerate them after every contract change.
- Build against the JSON examples in `src/shared/eduhub_shared/fixtures/` (mock mode, e.g. MSW or `NEXT_PUBLIC_API_MOCK=1`). They have exactly the shape the backend returns.
- Analysis is async: `POST /analyses` → poll `GET /analyses/{id}` every ~2 seconds until `done` or `failed` → `GET /reports/{report_id}`.
- Call `GET /features` and hide disabled features (generation, publishing, simulation). Handle `ErrorResponse` bodies: show `error.message`, which is already in es-AR.
- Enum values (e.g. `photo`, `short`, `timing`) are English codes. Map them to Spanish labels in the UI. Datetimes are UTC; show them in `America/Argentina/Buenos_Aires`.
- `publish` may return `status: "intent"` with a `url`: open it, because it's the X compose window, pre-filled.
- Scaffolding: `create-next-app` refuses a non-empty folder. Create the app in a temp folder and move it in, keeping this `CLAUDE.md`.
- TDD applies (Vitest + RTL suggested). Tests are approved by Lupa or Varela with `python scripts/approve_tests.py`.
