# Validation: problem, market, data and competition

Research done on 2026-10-30 for the EDU HU₿ · LABITCONF 2026 hackathon (track: **Creator Economy**).
Every number below has its source and how it was obtained, so it can be reused in the pitch and defended in the Q&A.

> **Hackathon rule:** "Es obligatorio que la solución esté justificada con datos de OpenARG y que aplique al territorio argentino."
> Typical jury question: "¿Qué dato de OpenARG respalda el problema?" → see [section 1](#1-openarg-evidence-mandatory).

---

## 0. Problem statement

One sentence, no technology (as the hackathon route requires):

> **"Los creadores argentinos publican a ciegas: no saben por qué un posteo funciona y otro no, y eso les impide crecer y conseguir acuerdos con marcas."**

Target user (decided): **Argentine micro-creators (~1k–100k followers) who want to grow and land brand deals.** Agencies managing many accounts are a later, higher-priced tier.

---

## 1. OpenARG evidence (mandatory)

Both datasets were found through the OpenARG catalog (`buscar_datasets`). They are listed as **download-only** in OpenARG (no queryable table), so they were downloaded from the official source and analyzed locally. Scripts: [`scripts/validation/`](../scripts/validation/).

### 1.1 Encuesta Nacional de Consumos Culturales (ENCC) 2022–2023, Ministerio de Cultura

- Source: [datos.cultura.gob.ar: Encuesta Nacional de Consumos Culturales](https://datos.cultura.gob.ar/dataset/251c2ac2-e670-451c-9dbf-a4212af225b5) (file `base-datos-encc-2022-2023.csv`, questionnaire `cuestionario-encc-2022-2023.pdf`).
- Sample: 3,380 respondents; weighted with the `expansor` column it represents **~29.5M people aged 13+** in urban localities.
- Questions used: `INT 11` (platforms used in the last year; `int11_6` = Twitter), `INT 12.1` (how often they **upload a post, video or content** to a social network), `INT 12.4` (how often they watch posts from friends, influencers or artists).

| Indicator (weighted) | Total 13+ | 13–17 | 18–29 | 30–49 | 50–64 | 65+ |
|---|---|---|---|---|---|---|
| **Uploads own content weekly or more** | **40.0% (~11.8M)** | 55.0% | 58.4% | 43.7% | 22.2% | 16.0% |
| Uploads content daily | 16.0% (~4.7M) | 28.0% | 24.9% | 16.8% | 5.5% | 5.5% |
| Watches influencer/friends/artists posts daily | 42.5% (~12.5M) | 65.9% | 63.6% | 45.5% | 21.3% | 14.2% |
| Used Twitter/X in the last year | 16.0% (~4.7M) | 29.7% | 31.2% | 11.9% | 7.0% | 3.8% |

- **X users who upload content weekly or more: 62.3% (~2.9M people).** X users post far more than the average user.
- Platform use, % of people aged 13+: WhatsApp 92.3%, YouTube 81.6%, Facebook 72.1%, Instagram 57.9%, TikTok 34.1%, **Twitter/X 16.0%**, Twitch 8.8%, LinkedIn 6.0%.
- By gender: uploads content weekly or more: women 40.9%, men 39.1%. Uses X: women 12.7%, men 19.5%.
- Provinces with the most people uploading weekly or more (expanded): Buenos Aires 4.18M, CABA 1.38M, Córdoba 1.30M, Santa Fe 0.68M, Mendoza 0.67M, Tucumán 0.59M.

### 1.2 Cuenta Satélite de Cultura: jobs in the "contenido digital" sector, INDEC / Ministerio de Cultura

- Source: [datos.cultura.gob.ar: Cuenta Satélite de Cultura, puestos de trabajo privados](https://datos.cultura.gob.ar/dataset/1ba8cfc4-a1e6-4f29-bc6e-0a0347989e76) (file `csc27-puestos-t-reg-no-reg-indeptes-sector.csv`; 2021 provisional, 2022 preliminary).

| Year | Digital content jobs | Registered | Unregistered | Self-employed |
|---|---|---|---|---|
| 2016 | 22,097 | 13.6% | 57.2% | 29.2% |
| 2019 | 21,965 | 15.3% | 59.0% | 25.7% |
| 2020 | 21,557 | 16.4% | 65.4% | 18.2% |
| 2021 | 31,177 | 12.2% | 60.1% | 27.7% |
| **2022** | **43,128** | **9.3%** | **59.7%** | **31.0%** |

- Digital content jobs **almost doubled (+95%) between 2016 and 2022**.
- **About 9 in 10 (90.7%) work unregistered or self-employed**, with no company, team or tools behind them.

### 1.3 Data for the synthetic-audience sandbox (stretch feature)

- The ENCC microdata has one row per real respondent: age, age group, gender, province, socioeconomic level (`niv_socioe`, `nse_3`), platforms used, consumption habits, and an expansion weight. **492 respondents use X.** We can sample *representative* personas from real respondents instead of inventing profiles.
- Population for scaling: RENAPER "Estructura de población Argentina" (queryable in OpenARG: `cache_datos_gob_ar_estructura_de_poblaci_n_argentin_rce341b72f2`, by province, June 2025).

### 1.4 Caveats

- ENCC covers **urban localities** and is from 2022–23. The Cuenta Satélite figure for 2022 is preliminary.
- "Uploads content" includes casual users, not only professional creators. Use it as the size of the **people who publish**, and use the 1–4% figure (section 2) for those who actually make money.
- OpenARG usage so far: 9 of 200 data-mode queries; 0 of 10 questions. If the jury wants to see an OpenARG query live, spend one `consultar_datos_publicos` question on it.

### 1.5 Pitch lines (Spanish)

> "En Argentina, **11,8 millones de personas publican contenido cada semana** (ENCC 2022-23) y el empleo en contenido digital **se duplicó en 6 años**, pero **9 de cada 10 trabaja en la informalidad**, sin equipo ni herramientas (Cuenta Satélite de Cultura). Publican a ciegas."

> "En X, **6 de cada 10 usuarios publican todas las semanas**: casi 3 millones de argentinos."

---

## 2. Market context (external sources)

| Data point | Value | Source |
|---|---|---|
| Internet users, Argentina | 41.6M (90.6% of population), Oct 2025 | [DataReportal Digital 2026: Argentina](https://datareportal.com/reports/digital-2026-argentina) |
| Social media user identities, Argentina | 32.9M (71.7%) | DataReportal |
| Ad reach per platform, Argentina | YouTube 32.9M · Instagram 31.1M (+9.9%) · Facebook 29.3M · TikTok 29.2M (+25.3%) · **X 6.70M (14.6%, −12.0%)** · LinkedIn 18.0M members | DataReportal (X figures fluctuate, ad reach ≠ MAU) |
| Creators who monetize sustainably, Argentina | **only 1–4%** | UdeSA study (S. Cabello), via [BAE Negocios](https://www.baenegocios.com/amp/Content-creator-un-trabajo-mucho-mas-arduo-de-lo-que-la-gente-imagina-20241212-0054/) and [UdeSA repository](https://repositorio.udesa.edu.ar/handle/10908/23188) |
| Monetization is the biggest challenge | 57% of ~10k creators (LatAm, Spain, US) | For_Me survey, via [iProfesional](https://www.iprofesional.com/tecnologia/464284-youtube-obliga-a-los-creadores-a-diversificar-sus-fuentes-de-ingreso) |
| Income from brand deals vs platform ads | 53% vs 16% | Same For_Me survey |
| Argentina influencer-eligible IG profiles | 6.11% of IG users (LatAm average 5.69%) | [Influencity LatAm study 2026](https://influencity.com/resources/studies/instagram-influencer-marketing-latin-america/) |
| Global creator economy | ~$250B (2025), ~23% CAGR, ~$1.35T by 2033 | Goldman Sachs / Grand View, via [Fungies](https://fungies.io/creator-economy-statistics/) (aggregator; cite the originals) |
| Argentine creator ecosystem | TENT Creator Summit 2025: 7,000+ attendees | [Mercado](https://mercado.com.ar/eventos/la-segunda-edicion-de-tent-creator-summit-reunio-a-mas-de-7000-asistentes-en-buenos-aires) |

**Why it matters:** 53% of creator income comes from brand deals, and brands pay for engagement. Better engagement means better deals, so the product helps creators earn more.

### Risk: "why X?"

X is the smallest and shrinking platform in Argentina (6.7M ad reach, −12%), so the jury will probably ask "why X?". Our answer:
- X is text-only, has the cheapest data access and public metrics (including **bookmarks** and **views**), so it's the fastest way to prove the engine.
- X users are the most active publishers (62.3% post weekly).
- The engine is **platform-agnostic**: Instagram and TikTok are next (31M and 29M reach).
- Pitch it as **"un motor de análisis para creadores; arrancamos por X"**, not as "una herramienta de X".

---

## 3. Data access (feasibility)

| Option | Cost | Risk / notes |
|---|---|---|
| **twitterapi.io** (suggested) | ~$0.15 per 1,000 tweets; ~$0.18 per 1,000 profiles; 20 tweets per page | Third-party, low risk. Returns public metrics. [Pricing](https://twitterapi.io/twitter-api-pricing) |
| Official X API (pay-per-use since 2026) | $0.005 per post read; $0.010 per user read; **$0.001 per owned read**; posting $0.015 per post ($0.20 with URL) | No ban risk; ~30x more expensive for reads; the only way to get private metrics. [Overview](https://postproxy.dev/blog/x-api-pricing-2026/) · [breakdown](https://twitterapi.io/blog/x-api-cost-breakdown-2026) |
| Scraping (twikit and similar) | Free | twikit is mostly unmaintained (2026), guest tokens are blocked, logged-in accounts get banned, and X's terms include a damages clause. [Status](https://www.xpoz.ai/blog/guides/open-source-social-media-scrapers-what-still-works-2026/) |

- Example cost: analyzing 200 tweets with twitterapi.io costs about **$0.03**. A demo with a few accounts costs a few dollars.
- **Decision:** twitterapi.io is suggested. Mark researches scraping (open question in [`teams/backend.md`](teams/backend.md)). **No other part of the system depends on where the data comes from** (enforced by the data contract).
- **Demo data caveat:** a brand-new demo account has no history and therefore no patterns. The demo must analyze an account with real history. Account to be decided.

---

## 4. Metrics (adapted to X)

The viral metrics the team researched (Instagram/TikTok) mapped to fields X makes available:

| Team metric | X equivalent | Formula | Availability |
|---|---|---|---|
| Saves per reach | **Save rate** | bookmarks ÷ impressions | Public (all sources) |
| Shares per reach | **Share rate** | (reposts + quotes) ÷ impressions | Public |
| Comments per reach | **Reply rate** | replies ÷ impressions | Public |
| Skip rate at 2–3s | **Passive rate** ("saw it, didn't interact") | 1 − (likes + reposts + quotes + replies + bookmarks) ÷ impressions | Public (proxy) |
| (exact version of the above) | Detail expands without interaction | detail_expands, profile_clicks, url_clicks | **Own tweets only, official API + OAuth.** Optional field. |
| (general) | Engagement rate | (likes + reposts + quotes + replies + bookmarks) ÷ impressions | Public |

Alignment with X's algorithm: X open-sourced its Grok-based ranker in January 2026 (major update in May 2026). It predicts the probability of like, reply, repost, click and similar actions, so our metrics follow the signals X itself optimizes for. **The exact weights were removed from the published code. Don't quote blog numbers.** Sources: [May 2026 update](https://pasqualepillitteri.it/en/news/2594/x-algorithm-open-source-may-2026), [overview](https://pub.towardsai.net/x-open-sourced-its-feed-algorithm-powered-by-grok-e5a13d67e741).

---

## 5. Competition and our angle

| Tool | Price (USD/month) | Focus |
|---|---|---|
| Typefully | 8–19 | Writing/scheduling, generic AI, basic analytics |
| Hypefury | 29–65 | Scheduling, templates, auto-engagement |
| Tweet Hunter | 29–49 | AI writing, viral tweet library, CRM |
| Metricool | freemium | Multi-platform scheduling and analytics, strong in Spanish-speaking markets (the jury will know it) |
| Buffer, Sprout Social | varies | Scheduling and dashboards for brands/agencies |
| Artificial Societies, Societies.io (YC W25) | varies | Synthetic audiences for pre-testing (LinkedIn, English) |

Sources: [Hypefury vs Typefully 2026](https://www.wearefounders.uk/hypefury-vs-typefully-2026-which-x-tool-is-worth-paying-for/), [Tweet Hunter pricing 2026](https://www.autotweet.io/blog/tweethunter-pricing-2026), [Artificial Societies](https://www.businesswire.com/news/home/20250730925181/en/Artificial-Societies-Reinvents-Market-Research-with-Accessible-AI-Societal-Simulator), [Societies.io](https://hn.svelte.dev/item/44755654).

**Gap:** existing tools show dashboards and write generic posts. None of them explain **why** a specific post worked *for this creator, in their context*.

**Our angle, in order of strength:**
1. **"Why it worked" insights per creator:** topic × format × time × tone, with evidence from their own posts, turned into concrete recommendations. *(core: must have)*
2. **Spanish- and Argentina-first:** rioplatense voice, local trends, prices in ARS.
3. **Drafts in the creator's voice**, based on their own insights, with a suggested time to post. *(wanted)*
4. **Pre-testing with a synthetic Argentine audience** built from real ENCC respondents (OpenARG). No competitor does this for Spanish or Argentine audiences, and it makes OpenARG part of the product itself. *(stretch)*
   - Caveat: independent benchmarks show many LLMs are close to random at predicting engagement ([AIMultiple](https://research.aimultiple.com/audience-simulation)). Present it as **"compare variants and preview reactions"**, never as "predict your likes".

---

## 6. Business model

- **Subscription with monthly credits, plus extra credit packs.** Credits map to real costs (data reads and LLM tokens), so the unit economics are easy to explain: a full 200-tweet analysis costs about $0.03 in data plus LLM tokens.
- Tiers (draft): **Free** (analysis of your last N posts) → **Creator** (monthly credits: re-analysis, drafts, posting) → **Agency** (multiple accounts). Priced in ARS.
- Growth: more platforms (Instagram, TikTok, YouTube) on the same engine, plus the agency tier.
- No blockchain/crypto (decided).

---

## 7. Pending validation

- [ ] **3 creator interviews** (team, Saturday 31 before the pitch). Ask what they already did, not "would you use it?". The hackathon's 3-question script: *¿Cuándo fue la última vez que te pasó? ¿Qué hiciste? ¿Qué fue lo peor?* Write the results in this section.
- [ ] Demo account with real post history.
- [ ] (Optional) One OpenARG question shown live in the pitch.

---

## 8. Jury Q&A prep

Standard questions from the hackathon's pitch kit:

| Question | Answer draft |
|---|---|
| ¿Qué dato de OpenARG respalda el problema? | ENCC 2022-23: 11.8M people post weekly (2.9M on X); Cuenta Satélite de Cultura: digital content jobs +95% (2016→2022), 90.7% informal. |
| ¿Con cuántas personas hablaron? | *(fill in after the interviews)* |
| ¿Qué parte de la demo funciona de verdad y qué está simulado? | *(fill in at the end; say it honestly)* |
| ¿Qué existe hoy y por qué esto es mejor? | Typefully, Hypefury and Metricool show dashboards and generic AI. We explain *why* each post worked for that creator and recommend what to do next, in rioplatense Spanish. |
| ¿Cómo se sostiene? ¿Quién paga? | The creator pays a subscription with credits, and agencies pay for multiple accounts. Costs per analysis are cents. |
| ¿Cuál es el mayor riesgo? | Platform data access (prices and terms of X). Mitigation: the engine doesn't depend on the data source, and we can add more platforms. |
| ¿Por qué X? | See section 2, "Risk: why X?". |
| ¿Qué harían la semana que viene? | *(fill in)* e.g. 10 real creators in a beta, plus Instagram support. |
