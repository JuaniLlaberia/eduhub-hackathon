# Stage 00: Contract v1.1.0 (hook + CTA labels)

- **Status:** todo
- **Priority:** MUST
- **Depends on:** none
- **Touches:** `src/shared/`. This is a **contract change**, so the guard hook will ask for confirmation. Follow root `CLAUDE.md` §3.

## Goal

Add two optional semantic features to the contract so the AI can label how a post opens (**hook**) and what it asks the reader to do (**CTA**), and group performance by them.

## Read first

- `src/shared/CLAUDE.md`
- `src/shared/eduhub_shared/models/analysis.py` (`PostFeatures`, `SegmentDimension`, `InsightCategory`)
- `src/shared/eduhub_shared/fakes.py` (`segment_value` maps every `SegmentDimension`)
- `../research.md` §9 D9

## Pre-conditions (human)

- [ ] The developer confirms the other teams agreed (or will be notified right after). This change is **additive** (optional fields, new enum values), so it is minor version **1.1.0**.
- [ ] **Front heads-up:** new `SegmentDimension` / `InsightCategory` values appear in the generated TS types. Any exhaustive label map needs two new entries.

## Change spec

1. `PostFeatures`: add
   - `hook: str | None = None`, description "How the post opens (see eduhub_ai label set).", and
   - `cta: str | None = None`, description "What the post asks the reader to do."

   Plain `str` (not enums) keeps the label sets in the AI package, so they can change without a contract bump. The AI documents the allowed values (stage 03).
2. `SegmentDimension`: add `HOOK = "hook"` and `CTA = "cta"`.
3. `InsightCategory`: add `HOOK = "hook"` and `CTA = "cta"`.
4. `eduhub_shared/fakes.py`:
   - `segment_value` must handle the new dimensions (`features.hook`, `features.cta`). Otherwise `build_segments` raises `KeyError`.
   - `FakeAnalyzer` keeps them `None`. Optionally, derive a naive hook (`"pregunta"` if the text starts with "¿").
5. `version.py` → `"1.1.0"`. Add a `CHANGELOG.md` entry (Added; Breaks: none, but the front should add labels).
6. Regenerate: `python -m eduhub_shared.openapi && python -m eduhub_shared.fixtures.build`.

## Tests to write first (`src/shared/tests/test_contract_v1_1.py`) → STOP for approval

- `PostFeatures` accepts `hook`/`cta` and defaults both to `None`. Old payloads without them still validate.
- `SegmentDimension` contains `hook` and `cta`, and `InsightCategory` contains `hook` and `cta`.
- `build_segments` (fake) runs on a report whose posts have `hook`/`cta` set and emits segments for those dimensions.
- The existing shared tests keep passing, and `openapi.json` and the fixtures are up to date.

## Definition of done

- [ ] `pytest src/shared` green, `ruff check`, `python scripts/check_style.py`
- [ ] Version 1.1.0 + CHANGELOG entry (author, who agreed, Breaks: none / front labels)
- [ ] Committed on `ai` with a message starting with `contract:`
- [ ] Merged into `dev` as soon as possible, and the other teams notified (they merge `dev` and run `check_contracts.py --ack`)

## Handoff notes

- Done on 2026-10-31, directly on `main` (decided by Llabe, before any team started coding). Contract **v1.1.0**.
- Approved tests: `src/shared/tests/test_contract_v1_1.py` (6 tests, approved by Juan). All 64 shared tests are green.
- Changed: `models/analysis.py` (`PostFeatures.hook`/`cta`, `SegmentDimension.HOOK`/`CTA`, `InsightCategory.HOOK`/`CTA`), `fakes.py` (`segment_value`), `version.py` + `pyproject.toml` → 1.1.0, CHANGELOG, regenerated `openapi.json` and fixtures.
- `FakeAnalyzer` still leaves hook/CTA as `None`. The real labels arrive in stage 03.
- Follow-up: the other teams merge `main`/`dev` and run `check_contracts.py --ack`. The front adds Spanish labels for the new enum values.
