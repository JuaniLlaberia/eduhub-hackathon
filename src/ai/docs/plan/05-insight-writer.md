# Stage 05: Insight writer (grounded es-AR texts)

- **Status:** done
- **Priority:** MUST
- **Depends on:** 01 (LLM client), 04 (stats evidence)

## Goal

Turn the computed evidence into the report texts (`Insight[]`, `Recommendation[]`, top/bottom post explanations, `summary`) with **one LLM call**, in rioplatense Spanish. **Every number in the text must come from the evidence.** If the LLM fails or invents numbers, fall back to template texts built from the same evidence.

## Read first

- `../research.md` §4.4
- `04-stats-engine.md` handoff notes (`SegmentDetail`, the significance functions)
- `src/shared/eduhub_shared/models/analysis.py` (`Insight`, `Evidence`, `Recommendation`, `InsightCategory`, `Impact`)
- `src/shared/eduhub_shared/fakes.py` (`build_insights`, `build_recommendations`, `explain`, `build_summary`, the formatting helpers `format_pct`, `format_multiplier`, `label_es`)

## Design

- **`insights/evidence.py`:** `build_evidence(...) -> EvidencePack`, a pydantic model serialized to compact JSON. It contains:
  - KPIs, formatted the es-AR way (`2,1%`, `1,4x`);
  - **significant** segments only (dimension, value, n, median score, lift, CI);
  - the hour-block and best-slot stats;
  - the top and bottom 5 posts (id, text, features, score);
  - pattern-model effects, an optional field filled by stage 07; and
  - every number pre-formatted as a string, plus `allowed_numbers: set[str]` (all numbers that may appear).

  Each evidence item has a stable `id` (e.g. `seg:topic:presupuesto`) so insights can reference it.
- **`insights/writer.py`:** `async def write_texts(pack, client, settings) -> WrittenTexts`. Response schema:
  - `insights[]`: category, title, description, `evidence_ids[]`, impact, `related_post_ids[]`;
  - `recommendations[]`: category, action, rationale, priority, `insight_index[]`;
  - `explanations{post_id: text}`; and
  - `summary`.

  The prompt rules: es-AR with voseo; concrete and short; **use only numbers from the evidence, copied exactly**; no generic advice; at most 6 insights and 6 recommendations; titles under 70 characters.
- **`insights/grounding.py`:** `extract_numbers(text) -> set[str]` (es-AR formats: `2,1%`, `1,4x`, `21 h`, integers) and `ungrounded(text, allowed) -> set[str]`.
  - Drop any insight or explanation with ungrounded numbers. Retry once if more than half get dropped.
  - Small integers ≤ 7 (weekday counts, list numbering) are allowed.
- **Assembly into contract objects:**
  - `Insight.evidence` is built **in code** from `evidence_ids`, as label/value pairs taken from the pack, never typed by the LLM.
  - `confidence` comes from the stats (n and CI width), never from the LLM.
  - IDs are `ins-1…`, `rec-1…`.
  - Unknown post ids are filtered out.
- **`insights/fallback.py`:** `template_texts(pack) -> WrittenTexts`, which reuses or ports the fake's template builders on the significant segments and best slots. It's used when `AI_ENABLE_LLM=0`, when the LLM fails, or when grounding drops everything.

## Tests to write first (`src/ai/tests/test_stage_05_insights.py`) → STOP for approval

- The evidence pack only includes significant segments, has stable ids, and `allowed_numbers` contains every formatted number in it.
- `extract_numbers` finds `2,1%`, `1,4x`, `21 h` and `40` in an es-AR sentence. Grounding flags `3,7x` when it isn't in the pack.
- A scripted LLM response with grounded texts → insights with code-built `Evidence`, `confidence` from the stats, and valid recommendation → insight links.
- A scripted response with an invented number → that insight is dropped and the others are kept. If most are invented → one retry, then the template fallback.
- An LLM exception → template fallback with the same number of significant findings, and no raise.
- Unknown `related_post_ids` are removed.
- The output objects validate as the contract models (`Insight`, `Recommendation`). The summary isn't empty.

## Definition of done

- [x] Tests green, plus ruff and style (209 passed: shared + stages 01–05)
- [x] The prompt has no clock or date values (cache stability; asserted by a test)
- [ ] Optional manual check: run on the fixture with the real model and read the texts with the developer → `python src/ai/scripts/write_insights.py [snapshot.json]` (template-only without a key or with `AI_ENABLE_LLM=0`)
- [x] Commit `ai: stage 05 insight writer`

## Handoff notes

- Built on 2026-10-31: `insights/evidence.py` (`EvidenceItem`, `PostEvidence`, `EvidencePack`, `build_evidence`, `confidence_for`, es-AR formatters `fmt_x`/`fmt_pct`/`fmt_int`/`fmt_dec`), `insights/grounding.py` (`extract_numbers`, `ungrounded`), `insights/prompts.py` (`WRITER_SYSTEM`, `writer_user`, `retry_note`), `insights/writer.py` (`WriterResponse` + drafts, `write_texts`, `assemble`), `insights/fallback.py` (`WrittenTexts`, `template_texts`, `template_explanation`, `template_summary`), `src/ai/scripts/write_insights.py` (manual end-to-end check up to the writer).
- Tests: `src/ai/tests/test_stage_05_insights.py`. Approved by Juan (code was written before approval at the developer's request).
- API for stage 06: `pack = build_evidence(profile, kpis, posts, best_slots)` then `texts = await write_texts(pack, client, settings)` → `texts.insights`, `.recommendations`, `.explanations` (post id → text, every top/bottom post), `.summary`, `.source` (`llm`/`template`), `.errors`. Never raises on LLM failures.
- Evidence ids: `kpi:account:<key>`, `seg:<dimension>:<value>`, `time:<hour_block|day_type|hour_block_day_type>:<value>`, `slot:<weekday>:<hour>`. Findings = significant details **with a comparison** (`lift_vs_rest` not None), sorted by p-value then n, max 12. `allowed_numbers` = every number token in the prompt JSON.
- Decisions beyond the plan:
  - `direction` comes from `lift_vs_rest` (vs the other posts), not from median vs 1.0; template titles lead with the comparison ("Tus posts con video rinden 3,5x vs. el resto"), descriptions add the typical-post multiplier.
  - Long LLM lists are **capped in code** (6 insights / 6 recommendations) instead of rejected by the schema.
  - Insights need at least one valid `evidence_id`; ones without are dropped (count as dropped for the retry rule). Recommendations that only pointed at dropped insights are dropped; priorities are renumbered 1..n.
  - Grounding allows bare small integers ≤ 7 and the bare number of an allowed token ("21" if "21 h" is allowed); es-AR thousands dots are normalized ("3.386" → "3386").
  - Templates keep **one finding per (family, direction)** (all timing dimensions are one family), so the fallback doesn't repeat "noche" and "noche, semana". So the template may produce fewer insights than there are significant findings.
  - `confidence` = `0.2 + 0.5·min(n,30)/30 + 0.3/(1 + CI width / median)`, from the stats only.
  - Writer temperature 0.4. The prompt JSON is ~7–8k chars for 200-post accounts.
- Follow-up for stage 06: without LLM labels, topics are `None`, so templates can't talk about topics (the fixture's "presupuesto" story only shows up with labels or hashtag topics). Consider the hashtag fallback (`labeling.labeler.hashtag_topics`) when labeling is skipped.
