# End-to-end run of the real system (2026-10-31)

Full flow through the real HTTP API (analysis → report → drafts → simulation) on the 4 real accounts, with and without a creator brief, plus the audience sandbox on the whole ENCC pool (492 personas) vs. samples of 200. Branch `ai`, contract v1.2.0. No contract or product code was changed.

- **Data:** [`results.json`](results.json): every number below, plus the draft texts, report summaries and simulation summaries. The briefs used are in [`briefs/`](briefs/).
- **Raw outputs:** full reports and simulation results, which quote real posts (personal data), are kept **git-ignored** in `src/ai/tests/data/real/reports/e2e-2026-10-31/`.
- **Scripts to re-run:** `src/ai/scripts/e2e/e2e_api.py` (API flow) and `src/ai/scripts/e2e/sandbox_full.py` (full pool).

## Setup

| | |
|---|---|
| Backend | `uvicorn eduhub_backend.app:main --factory`, `EDUHUB_FAKE_AI=0`, env from `.env` exported (`set -a; source .env`) |
| Data source | `DEMO_MODE=1`, with `FIXTURES_DIR` set to a folder holding **only the 4 real snapshots**, so no fake reports were seeded. `.env` has no `TWITTERAPI_IO_KEY`, so the backend refuses `DEMO_MODE=0` (`ConfigError`). The twitterapi.io live fetch was **not** tested. |
| AI wiring | `/_e2e/usage` confirmed `HybridAnalyzer`, `LLMDraftGenerator`, `LLMAudienceSimulator`; `/features` → `simulation: true` |
| Model | `deepseek/deepseek-v4.1-flash` via OpenRouter, label reasoning off, max concurrency 8 |
| Cost | OpenRouter's reported cost per AI client, read before and after each step through a test-only launcher (in the session scratchpad, not committed). The launcher wraps the real app and adds one read-only `GET /_e2e/usage` route. |
| Per case | `POST /analyses` (max 200 posts) → poll → `GET /reports/{id}` + `GET /accounts/{handle}/report` → `POST /drafts` (3, no `context`, so the brief comes from `report.context`) → `POST /simulations` with the 3 drafts as variants, 100 personas, plus the brief as `context` when set |

## 1. API end to end: 8/8 green, 0 failures

132 LLM calls, **0 failed**. Every report: engine `hybrid-v1`, 6 insights and 6 recommendations, 100% of scored posts labeled, `/accounts/{handle}/report` returned the same report, the brief was echoed in `report.context`, and in the brief runs no insight or draft mentioned an `avoid_topics` entry.

| Account | Brief | Analysis | Drafts | Simulation (100 × 3) | Whole flow |
|---|---|---|---|---|---|
| bilinkis | no | 17.1 s · $0.0188 | 15.0 s · $0.0050 | 9.5 s · $0.0228 | 41.5 s · $0.047 |
| bilinkis | launch | **42.9 s** · $0.0165 | 7.3 s · $0.0023 | 11.8 s · $0.0224 | 62.0 s · $0.041 |
| mercadolibre | no | 12.6 s · $0.0121 | 5.2 s · $0.0023 | 8.2 s · $0.0196 | 25.9 s · $0.034 |
| mercadolibre | traffic | 17.0 s · $0.0121 | 3.5 s · $0.0012 | 7.7 s · $0.0190 | 28.2 s · $0.032 |
| paulina_cocina | no | 19.1 s · $0.0225 | 5.7 s · $0.0020 | 9.7 s · $0.0202 | 34.4 s · $0.045 |
| paulina_cocina | sell | 17.9 s · $0.0269 | 4.0 s · $0.0017 | 7.6 s · $0.0218 | 29.5 s · $0.050 |
| valearvejita | no | 18.3 s · $0.0113 | 11.5 s · $0.0042 | 8.1 s · $0.0192 | 37.9 s · $0.035 |
| valearvejita | community | 15.0 s · $0.0095 | 6.0 s · $0.0020 | 7.5 s · $0.0220 | 28.5 s · $0.034 |
| **median / mean** | | **17.5 s · $0.016** | **5.8 s · $0.0026** | **8.2 s · $0.021** | **~31 s · $0.040** |

- **Analysis latency:** 7 of 8 runs were under the 60 s target (12.6–19.1 s). The outlier is bilinkis with a brief at 42.9 s: same call count and similar tokens as without the brief. The per-call log lines weren't captured (the eduhub_ai INFO logs are not shown under uvicorn), so a slow provider is the likely cause but is **not verified**.
- **Analysis cost** averages **$0.016**, a bit above stage 10's $0.011 (same accounts, more output tokens this time). Still around 1–2 cents.
- **The simulation costs more than the analysis:** a 100-persona × 3-variant simulation costs ~$0.021, and at the API cap (200 × 3) about $0.044, roughly 3× an analysis. Worth keeping in mind for the demo budget, and for the default `audience_size` (50).
- **Error paths through the real stack:** `audience_size=492` → 422 `invalid_request`; unknown handle → 404; drafts for an account without a report → 404.
- Total spend for section 1: **$0.32**.

### What the brief changed (quality)

- **bilinkis (launch, newsletter, avoid "fútbol"):**
  - Without a brief, all 3 drafts were about the Mundial/football, following the trends.
  - With the brief: no football, 2 of 3 drafts name the newsletter, and the summary frames the link as "mover el link a la respuesta o la bio".
  - The simulation used only personas aged 30–64, the brief's filters ✓.
- **mercadolibre (traffic, Black Friday):** all 3 drafts name the Black Friday deals, with the link "en mi bio" or "en la primera respuesta" (the link trade-off from the insights). The summary names the goal and the link cost (0,7x).
- **paulina_cocina (sell, ebook):** 1 draft names "Soy Solito" explicitly, and all 3 point to the bio link. The Christmas "para uno" angle came back again, matching stage 11's run 2. The simulation respected the brief's ages (18–49) ✓.
- **valearvejita (community, preferred CTA reply):**
  - All 3 drafts end with a question to the reader ("¿Vos publicás en inglés o en español?").
  - The simulation respected the brief's ages (13–29) ✓.
  - Two drafts are about public funding of science (taxes, paywalls). That's close to "política" without naming it, so the word-level filter doesn't catch it.

### Quality issues found (to fix or decide)

1. **`[dato]` placeholders in drafts:** 3 of 24 drafts (bilinkis without a brief ×2, valearvejita with a brief ×1). This is by design: the prompt asks for a placeholder instead of an invented statistic. But users see it raw ("Un [dato] de los goles…"). Either the front highlights it as "completá este dato", or the generator should prefer drafts without one.
2. **Timing insights leak into drafts as fake event dates:** valearvejita without a brief, "El lunes 17, a las 17… Miércoles 13, a las 13". The best time slot ("lunes 17 h") was turned into a march date. Same root as stage 10's "2-post slots" follow-up.
3. **Brand claims in mercadolibre drafts:** without a brief, "partner oficial de @williamsracing" and "team partner de @alpinef1team" appear in different drafts, contradicting each other. These are invented product facts the brief rule doesn't cover when there is no brief.
4. **Summary says "1,0 veces más interacción"** when two variants are almost tied (bilinkis with a brief: 41.3% vs. 40.7%). It should use the "parecida / no hay una ganadora clara" wording when the ratio rounds to 1,0.
5. **"Donde mejor funcionó fue entre personas de 65 años y mas":** the summary picked 65+ twice at n=100 (a segment of about 4 personas). It is unstable, see §2, and the ENCC value is missing its accent ("más").
6. **Mixed metrics in one sentence:** paulina_cocina with a brief: "el video rinde 1,1x (3,5x vs. el resto)". Two different baselines in the same sentence read as a contradiction.

## 2. Audience sandbox: whole pool (492) vs. 200

`LLMAudienceSimulator` called directly. `SimulationRequest` caps `audience_size` at 200, so the full-pool request is built with `model_construct` in the script only (the contract is unchanged). Per variant set:

- 2 runs on all 492 personas (same personas, so this measures LLM noise);
- 3 runs of 200 with seeds 0/1/2 (the API always uses seed 0);
- plus, without new calls, the full runs' reactions restricted to each seed's 200 personas.

Sets:

- **A**: the 3 drafts generated for paulina_cocina with her brief;
- **B**: the 2 default variants of `scripts/simulate.py`, as in the stage 09 runs.

0 failed calls, 3 of 7,920 reactions dropped (one 200 run). Total spend **$0.53**.

| Set | Run | Personas | Interaction rate per variant | Ranking | Time | Cost |
|---|---|---|---|---|---|---|
| A | full #1 | 492 | 15.2% · **23.1%** · 11.9% | 2 > 1 > 3 | 27.3 s | $0.108 |
| A | full #2 | 492 | 13.0% · **24.1%** · 9.8% | 2 > 1 > 3 | 30.0 s | $0.091 |
| A | 200, seed 0 | 200 | 17.7% · **25.9%** · 16.1% | 2 > 1 > 3 | 13.9 s | $0.041 |
| A | 200, seed 1 | 200 | 11.8% · **19.5%** · 7.8% | 2 > 1 > 3 | 12.6 s | $0.044 |
| A | 200, seed 2 | 200 | 14.2% · **30.3%** · 9.6% | 2 > 1 > 3 | 12.8 s | $0.044 |
| A | API, 100 (§1) | 100 | 9.5% · **26.8%** · 11.2% | 2 > **3 > 1** | 7.6 s | $0.022 |
| B | full #1 | 492 | 28.8% · **41.7%** | 2 > 1 | 21.3 s | $0.065 |
| B | full #2 | 492 | 24.4% · **43.6%** | 2 > 1 | 20.3 s | $0.063 |
| B | 200, seed 0 | 200 | 26.7% · **50.9%** | 2 > 1 | 10.4 s | $0.026 |
| B | 200, seed 1 | 200 | 22.9% · **40.2%** | 2 > 1 | 11.5 s | $0.027 |
| B | 200, seed 2 | 200 | 31.5% · **48.7%** | 2 > 1 | 11.4 s | $0.027 |

**Do the rankings hold?**

- **The winner holds every time.** Set A's variant 2 won all 6 runs (and the API run at 100); set B's variant 2 won all 5, as in both stage 09 runs. In paired terms (full runs), 13–15% of the weighted audience engaged only with A's v2 vs. 4–6% only with v1; for B, 20–25% only v2 vs. 6–7% only v1.
- **Close pairs flip.** A's 2nd vs. 3rd place (v1 vs. v3, about 3 points apart) held in all 5 runs at 200 or more, but:
  - it flipped at n=100 in the API run;
  - it flipped in 1 of the 6 "same 200 personas inside the full runs" checks (seed 1, full #2: 10.4% vs. 10.6%).
  - Rule of thumb: trust the winner when the gap is ≥ 1.4×; treat gaps under ~3 points as ties.
- **Run-to-run noise on the same personas:** the two full runs agree on active vs. passive for 83% (A) and 78% (B) of the (persona, variant) pairs, at temperature 0.7. Individual reactions are noisy; the aggregate ranking isn't.
- **The multiplier in the summary is not stable:** for the same B variants, "La variante 2 generó X veces más" ranged over 1,4 / 1,8 (full) and 1,9 / 1,8 / 1,5 (200); for A, 1,5–2,1. The direction is stable, the size is ±0.3–0.4. Suggest a qualitative wording ("claramente más" when ≥ 1.4×, "algo más" when lower, "parecida" when < 1.1×) or a range.
- **The "best age group" sentence is not stable at 200:** the full runs said 30–49 in all 4. The 200 runs said 18–29, 50–64, 50–64 (A) and 30–49, 30–49, 65+ (B), and the 100 runs said 65+ twice. `MIN_SEGMENT_PERSONAS = 3` is too low: with 200 personas, 65+ has ~8. Suggest ≥ 20 personas and a minimum margin over the runner-up age group, or drop the sentence below the full pool.
- **Absolute rates are still inflated vs. real X** (10–50% interaction), as stage 09 found. Show them only as a comparison.
- **The full pool is affordable:**
  - 492 × 3 variants = 50 calls, 27–30 s, ~$0.10;
  - 492 × 2 = 20–21 s, ~$0.064;
  - 200 × 3 = 13–14 s, ~$0.043.
  - Latency is bounded by concurrency 8 (50 calls in ~7 waves). If the cap is ever raised, 492 fits in a 30 s request, but it costs 2.3× the 200 run for the same winner.

## Recommendations

1. **Keep the API cap at 200.** The winner at 200 always matched the full pool, so the full pool adds cost, not a different answer. If anything, the default of 50 is the risky size for close variants.
2. Fix the summary wording: tie at ≈ 1,0x, qualitative multiplier, and a stricter age-segment rule (issues 4–5).
3. Generator: avoid best-slot times as event dates, prefer drafts without `[dato]` (or have the front flag it), and don't invent brand partnerships (issues 1–3).
4. Test the live twitterapi.io path once a `TWITTERAPI_IO_KEY` is available (`DEMO_MODE=0`).
