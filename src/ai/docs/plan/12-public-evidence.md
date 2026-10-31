# Stage 12: public evidence (OpenARG) in the insights, demo version

- **Priority:** WANTED (demo). Branch `ai-public-evidence` (from `dev`), so nothing that already works is touched until it is merged.
- **Depends on:** 05, 06, 11.
- **Contract:** unchanged (v1.2.0). A later v1.3.0 may add `source`/`url`/`kind` to `Evidence`.

## Goal

Every insight is already backed by the account's own data. This stage adds **public evidence**: official Argentine statistics found through OpenARG (ENCC 2022-23, Cuenta Satélite de Cultura). An insight can cite one public fact as context, and the report **marks what is evidence-based and what is not**, so the UI can tell them apart.

The demo version makes **zero OpenARG calls at runtime**. The facts are a curated, packaged catalog (`public_data/data/public_facts.json`), the same as `personas.json`. The numbers are the ones in `docs/validation.md` §1, found with OpenARG's `buscar_datasets`. Both datasets are download-only there, so they were processed offline.

## Read first

`docs/validation.md` §1 · `insights/evidence.py`, `insights/writer.py`, `insights/prompts.py` · `analyzer.py` · `config.py` · `sandbox/personas.py` (the age-group values).

## Design

- **`public_data/facts.py`:**
  - `PublicFact` (id, source, url, text, age_groups), `load_public_facts()`, and `select_public_facts(context, limit=MAX_PUBLIC_FACTS)`.
  - `select_public_facts` returns `EvidenceItem`s with `kind="public"`, id `pub:<fact id>`, label `"Dato público · <source>"` (`PUBLIC_LABEL_PREFIX`), value = the fact's text, and `numbers={}`.
  - Facts with no `age_groups` are general and always offered. Age-specific facts are offered only when they match the brief's `audience_filters.age_groups`, and they come first.
- **Evidence pack:**
  - `build_evidence(..., public_facts=None)` adds `EvidencePack.public_facts`, which is included in `items()`.
  - When non-empty, `prompt_json()` gets a `datos_publicos` list (id, label, value). Its numbers enter `allowed_numbers` the usual way, so grounding is unchanged.
  - Without public facts, the pack and the prompt are exactly as before.
- **Writer rules (code):**
  - An insight needs at least one **account** evidence item. Public-only insights are dropped, and count as dropped for the retry rule.
  - At most `MAX_PUBLIC_PER_INSIGHT = 1` public item per insight, placed after the account items.
  - Confidence and related posts come from the account items only.
- **Writer prompt:** rules for `datos_publicos`. They are context, never account data. Cite one only when it really applies, together with an account id. Name the source. Don't mix public numbers and account multipliers in the same sentence. Don't use them in recommendations or the summary.
- **Analyzer:** passes `select_public_facts(snapshot.context)` when `settings.enable_public_evidence` (`AI_PUBLIC_EVIDENCE`, default `1`; `0` turns it off).
- **Templates:** unchanged (no public facts in template mode).

## How the report marks evidence (no contract change)

| Item | Evidence-based when | Mark |
|---|---|---|
| Insight | always (it has ≥1 account item) | "Basado en tus datos" |
| `Insight.evidence[i]` | label starts with `Dato público ·` | "Dato público" chip (source in the label) |
| Recommendation | `based_on_insight_ids` non-empty | "Basado en tus datos"; empty → "Sugerencia general" |
| Summary, post explanations | n/a | no mark |

Front hand-off: `12-public-evidence-frontend.md`.

## Tests to write first

`src/ai/tests/test_stage_12_public_evidence.py`.

## Definition of done

- [ ] Stage 12 tests approved and green, plus every earlier test.
- [ ] `ruff check src/ai` and `python scripts/check_style.py src/ai` clean.
- [ ] Front hand-off written.

## Handoff notes

(fill in)
