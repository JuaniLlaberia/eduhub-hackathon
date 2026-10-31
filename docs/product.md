# Product

> Working name: **TBD**. Evidence for everything here: [validation.md](validation.md).

## One-liner

**An analysis engine for creators that explains why their posts work and tells them what, how and when to post next.** We start with X; Instagram, TikTok and YouTube come next on the same engine.

## Problem

"Los creadores argentinos publican a ciegas: no saben por qué un posteo funciona y otro no, y eso les impide crecer y conseguir acuerdos con marcas."
11.8M Argentines post weekly, and 2.9M of them on X. Digital content jobs doubled in six years, and 90.7% are informal (OpenARG). Only 1–4% of creators earn sustainably.

## Target user

**Primary persona:** an Argentine micro-creator (~1k–100k followers on X), 18–35, posts several times a week, wants to grow to land brand deals, and has no team or analyst.
Later: agencies and community managers handling several accounts (paid tier).

## Features and priority

| Priority | Feature | What it does |
|---|---|---|
| **MUST** | **Account analysis** | Ingests the creator's recent posts and computes features, metrics, insights ("why it worked") and recommendations (what, how, when) |
| **MUST** | **Dashboard** | KPIs, day × hour heatmap, performance by topic/format/length/tone, top and bottom posts with explanations, recommendations |
| WANTED | **Draft generation** | Drafts in the creator's voice based on their insights, with a suggested time and an estimated score relative to their baseline |
| WANTED | **Posting** | Publish a draft now, or schedule it (depends on data source; see backend open questions) |
| STRETCH | **Audience sandbox** | Tests a draft against synthetic personas sampled from real ENCC respondents (OpenARG): reactions by segment, and comparison of variants |

Rules:
- The MUST features must work on their own.
- WANTED and STRETCH features can be removed without breaking anything. **Nothing may depend on the sandbox.**

## User flow (demo path)

1. **Landing** → "Analizá tu cuenta de X" → enter an `@handle` (no login for analysis).
2. **Analysis in progress** → progress state: fetching posts → analyzing → generating insights.
3. **Dashboard** → KPIs, best times, what works and what doesn't, top posts explained, recommendations.
4. **Create** → pick a recommendation or a topic → get 3 drafts in your voice + suggested time → edit → (publish or schedule).
5. **(Stretch) Test** → run a draft through the Argentine synthetic audience → reactions by age, province and segment → pick the best variant.

The demo shows one path from start to end: **handle → dashboard → recommendation → draft**.

## Metrics (per post; aggregated per account)

All rates use **impressions (views)** as the denominator. Definitions are frozen in the contracts.

| Metric | Formula |
|---|---|
| Engagement rate | (likes + reposts + quotes + replies + bookmarks) ÷ impressions |
| Save rate | bookmarks ÷ impressions |
| Share rate | (reposts + quotes) ÷ impressions |
| Reply rate | replies ÷ impressions |
| Like rate | likes ÷ impressions |
| Passive rate | 1 − engagement rate ("saw it, didn't interact"; proxy for skip rate) |
| Performance score | Post engagement relative to the account's median (1.0 = typical post). Defined by the AI team |

Optional private metrics (only with the official API + OAuth on own posts): detail expands, profile clicks, link clicks.

## Features analyzed per post (initial list; the AI team refines it)

Length (characters, words) · hour and weekday (in Argentina time) · media type (none/photo/video/GIF) · link · hashtags · mentions · question or not · emojis · thread/reply/quote · **topic** · **tone/register** (e.g. humorous, informative, opinion, personal) · sentiment · language · whether it matches a current trend.

## Business model

Subscription with monthly credits plus extra credit packs; Free → Creator → Agency tiers; priced in ARS. Details in [validation.md §6](validation.md#6-business-model).

## Out of scope (hackathon)

Other platforms · full multi-user auth and billing · historical trend data (only current trends) · learning over time (it's in the pitch, not the demo) · blockchain/crypto.
