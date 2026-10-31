# Contract changelog

Newest first. Every change to `src/shared/` adds an entry: version, date, author, who agreed, what changed, and what breaks.

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
