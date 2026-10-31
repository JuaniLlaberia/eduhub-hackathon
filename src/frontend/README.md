# Frontend (Next.js)

Front team: Lupa, Varela. Rules: root `CLAUDE.md`, `src/frontend/CLAUDE.md`, `docs/teams/frontend.md`. The UI is in es-AR.

## Run

```bash
cd src/frontend
npm install
cp .env.example .env.local      # NEXT_PUBLIC_API_MOCK=1 serves the shared fixtures, no backend needed
npm run dev                     # http://localhost:3000
npm run check                   # typecheck + lint + prettier + vitest (run before every commit)
npm run contract:sync           # after every contract change: regenerates schema.d.ts and copies the fixtures
```

Stack: Next.js 16 (App Router, Cache Components) · TypeScript strict · Tailwind 4 + shadcn/ui · TanStack Query · openapi-fetch · Recharts · Vitest + Testing Library.
Next 16 differs from older versions: read `node_modules/next/dist/docs/` before using a new API (see `AGENTS.md`).
Pages that read `params`/`searchParams` must do it inside `<Suspense>` (Cache Components), as the existing pages do.
CSS modules do not work here: the Turbopack `*.css` rule in `next.config.ts` turns them into plain CSS. Use Tailwind or prefixed global classes (see `components/landing/nova-field.css`).

## Routes

| Route | Screen | Priority |
|---|---|---|
| `/` | NOVA landing (brand brief: hero, Nova World, Nova Score, cómo funciona, example accounts) | MUST |
| `/analisis/[jobId]` | Analysis progress (polls the job) | MUST |
| `/cuenta/[handle]` | Dashboard (latest report) | MUST |
| `/cuenta/[handle]/crear?recomendacion=<id>` | Drafts + publish | WANTED |
| `/cuenta/[handle]/probar` | Audience sandbox | STRETCH |

## Layout

```
src/
├── app/                     # page.tsx = landing; (app)/ = product screens with SiteHeader (route group, same URLs)
├── components/
│   ├── ui/                  # shadcn (generated: `npx shadcn@latest add <name>`)
│   ├── brand/               # NovaLogo / NovaMark
│   ├── landing/             # landing sections; real-data.ts = contract fixtures of the demo account
│   ├── report/              # report visuals reused by landing and dashboard (post sky, heatmap, score strip…)
│   ├── analysis/ dashboard/ create/ sandbox/   # one folder per screen, one file per section
│   ├── section-card.tsx     # SectionCard + Pending placeholder
│   └── error-state.tsx
└── lib/
    ├── api/
    │   ├── schema.d.ts      # GENERATED from openapi.json, never edit
    │   ├── fixtures/        # GENERATED copy of src/shared fixtures, never edit
    │   ├── types.ts         # short aliases of the generated types
    │   ├── client.ts        # openapi-fetch client (mock fetch when NEXT_PUBLIC_API_MOCK=1)
    │   ├── mock-fetch.ts    # fake backend over the fixtures
    │   ├── errors.ts        # unwrap() + es-AR error messages
    │   └── queries.ts       # TanStack Query hooks: the only way components get data
    ├── labels.ts            # enum code → es-AR label
    └── format.ts            # es-AR numbers, percentages, scores, Argentina-time dates
```

## Status (skeleton, 2026-10-31 night)

Done: tooling, routes, layout, data hooks, placeholder sections (`<Pending />` marks what is missing; each component has a TODO comment with its spec).

**Tests approved (frozen) by Lupa on 2026-10-31.** `labels` and `format` are implemented (green); `mock-fetch` and `errors` are still stubs (`notImplemented()`), so `npm test` is partly red.

| Tests | Implements |
|---|---|
| `src/lib/api/mock-fetch.test.ts` | `createMockFetch` (mock mode: the whole UI depends on it) |
| `src/lib/api/errors.test.ts` | `unwrap`, `errorMessage` |
| `src/lib/labels.test.ts` | every label function (done) |
| `src/lib/format.test.ts` | every format function (done) |

Next steps, in order:
1. ~~Review and approve the four test files~~ (done).
2. Implement `mock-fetch.ts` and `errors.ts`. After that, the dashboard loads the fixture report in mock mode.
3. Screens, test first (component tests with Testing Library): handle form → progress page → dashboard sections → create.
4. Feature flags (`useFeatures`) to hide create/publish/sandbox, then a Playwright smoke test of the demo path and the Vercel deploy.

### Dashboard hand-off (Varela)

- Page and data are wired: `app/(app)/cuenta/[handle]/page.tsx` → `components/dashboard/dashboard-view.tsx` (`useLatestReport`). Each section in `components/dashboard/` is a placeholder with a TODO spec.
- Reuse the landing visuals in `components/report/`: `PostSky` (posts by date × score), `TimeHeatmapGrid`, `SegmentBars`, `ScoreStrip`, `InsightCard`, `score-style.ts` (score tiers and colors). They take contract types, so they work with any report.
- `lib/labels.ts` (enum → es-AR) and `lib/format.ts` (`formatScore` "1,8x", `formatPercent` "4,9%", Argentina dates) are implemented and tested.
- Until `mock-fetch.ts` is implemented, run the backend locally (`docs/teams/backend.md`) with `NEXT_PUBLIC_API_MOCK=0`, or render the fixture directly (`components/landing/real-data.ts`).

Contract note: the generated request types mark fields with defaults as required (e.g. `AnalysisRequest.max_posts`, `DraftRequest.count`), so send them explicitly.
