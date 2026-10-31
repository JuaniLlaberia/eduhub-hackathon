# Contract changelog

Newest first. Every change to `src/shared/` adds an entry: version, date, author, who agreed, what changed, and what breaks.

## 1.2.0 · 2026-10-31 · creator brief ("el para qué")
- Author: AI team (Llabe, with Claude Code). Agreed by Llabe (repo maintainer); backend (Mark) and front (Lupa, Varela) notified, with the front hand-off in `src/ai/docs/plan/11-creator-context-frontend.md`.
- Added: `CreatorContext` (all optional: `goal`, `goal_detail`, `offering`, `target_audience`, `audience_filters`, `brand_voice`, `avoid_topics`, `preferred_cta`) and the enums `CreatorGoal` (sell, traffic, reach, community, launch, other) and `PreferredCta` (link, reply, save, share, follow, none).
- Added: optional `context: CreatorContext | None = None` on `AnalysisRequest`, `AccountSnapshot`, `AnalysisReport`, `DraftRequest` and `SimulationRequest`.
- Moved: `AudienceFilters` to `models/audience.py` (to avoid an import cycle). It is still importable from `eduhub_shared.models` and `eduhub_shared.models.simulation`; the wire format is unchanged.
- OpenAPI: `CreatorContext` and `AudienceFilters` keep **one schema** for requests and responses (`json_schema_serialization_defaults_required=False` on those two models), so `AudienceFilters` keeps its name instead of splitting into `-Input`/`-Output`. In responses, their defaulted fields are optional in the generated TS types. `AnalysisReport.context` is present in every report (`null` when there was no brief).
- Fakes: `FakeAnalyzer` copies `snapshot.context` into `report.context`. Fixtures: the `demo_finanzas` snapshot and report carry an example brief (goal `sell`).
- Breaks: nothing at runtime (additive, all optional). **Back:** copy `AnalysisRequest.context` into the `AccountSnapshot`. **Front:** regenerated TS types; add es-AR labels for `CreatorGoal` and `PreferredCta`.

## 1.1.0 · 2026-10-31 · hook and CTA labels
- Author: AI team (Llabe, with Claude Code). Agreed by Llabe before any team started coding; other teams to be notified.
- Added: `PostFeatures.hook` and `PostFeatures.cta` (optional `str`, default `None`; the label sets are defined by `eduhub_ai`).
- Added: `SegmentDimension.HOOK` / `.CTA` and `InsightCategory.HOOK` / `.CTA`.
- Fakes: `segment_value` supports the new dimensions (`FakeAnalyzer` leaves them `None`, so it emits no hook/CTA segments).
- Breaks: nothing at runtime (additive). **Front:** the regenerated TS types include the new enum values, so add Spanish labels for `hook` and `cta` in any exhaustive label map.

## 1.0.0 · 2026-10-30 · initial contract
- Author: setup session (Claude Code), approved by Llabe for all teams before coding started.
- C1 models, C2/C3 interfaces + errors, C4 routes → `contracts/openapi.json`, C5 metrics, C6 fixtures + fakes, conformance helpers in `testing.py`.
- Breaks: nothing (first version).
