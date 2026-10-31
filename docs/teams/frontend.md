# Front team (Lupa, Varela)

Owns `src/frontend/`: everything the user (and the jury) sees and touches. The UI is in **Spanish (es-AR)**.
Talks only to the backend, through the **C4** HTTP API (`src/shared/contracts/openapi.json`).

## Screens (demo path first)

1. **Landing**: value proposition plus an `@handle` input → "Analizar".
2. **Analysis in progress**: poll `GET /analyses/{id}` and show the steps (fetching posts → analyzing → generating insights) with progress.
3. **Dashboard** (MUST, the star of the demo):
   - KPI tiles: engagement, save, share, reply and passive rates, plus average views and posts per week.
   - Day × hour heatmap and the top 3 best time slots.
   - Performance by topic, format, length and tone.
   - Top and bottom posts, each with its explanation and metrics.
   - Insights (with evidence) and recommendations (with a "Crear post con esto" button).
   - A short summary.
4. **Create** (WANTED): pick a recommendation or a topic → 3 drafts → edit → publish or schedule.
5. **Sandbox** (STRETCH): test 2–3 variants against the synthetic audience → reactions by segment.

Use `GET /features` to hide anything disabled (generation, publishing, simulation).

## Suggested tools (your call)

Next.js (App Router) + TypeScript strict · Tailwind CSS + shadcn/ui · charts: Recharts (bars and lines) plus a custom CSS grid for the heatmap (or nivo) · TanStack Query (polling, caching) · **openapi-typescript + openapi-fetch** (typed client generated from the contract) · **MSW** or a mock mode serving the shared JSON fixtures, so you can build the whole UI before the backend exists · Vitest + React Testing Library · Playwright smoke test for the demo path · Vercel.

```bash
npx openapi-typescript ../shared/contracts/openapi.json -o src/lib/api/schema.d.ts
```

## Open questions

- [ ] Product name, logo and color palette.
- [ ] Desktop first (the judges use computers), with responsive layout as a bonus?
- [ ] Mock mode switch (e.g. `NEXT_PUBLIC_API_MOCK=1`) for development and as a demo fallback.
- [ ] Who records the ~20-second backup demo video?
