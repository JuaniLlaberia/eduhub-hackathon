# Stage 11 (front): Creator brief ("el para qué") — hand-off for the front team

- **From:** AI team (Juan). The contract, AI and backend parts are done in [`11-creator-context.md`](11-creator-context.md).
- **For:** front team (Lupa, Varela), on branch `frontend`, in a Claude session with `EDUHUB_TEAM=frontend`.
- **Priority:** WANTED. **Nothing breaks if you don't do it:** without a brief, the API and the AI behave exactly as today.
- **Start when:** contract **v1.2.0** is in `dev`. Merge `dev` into `frontend` and run `python scripts/check_contracts.py --ack`.
- **Estimate:** 2–3 h.

## What it is

Creators, brands and agencies can tell us **what they publish for**: their goal, product or campaign, target audience, brand voice, topics to avoid and preferred CTA. We call it the *brief*. It's sent once with the analysis and kept inside the report. With it:

- The **recommendations** follow the goal. Example: for someone selling, "keep the link, put it in a reply" instead of "drop the link".
- The **drafts** are written for the campaign, in the creator's voice.
- The **simulator** defaults to the brief's target audience.

**The numbers never change** (scores, stats, best times): the brief only changes how they're framed and which come first.

## Contract (v1.2.0, all additive and optional)

Types come from `src/shared/contracts/openapi.json`. **Regenerate them; never edit them by hand.**

```ts
// generated types, shown here for reference
type CreatorGoal = "sell" | "traffic" | "reach" | "community" | "launch" | "other";
type PreferredCta = "link" | "reply" | "save" | "share" | "follow" | "none";

interface CreatorContext {
  goal?: CreatorGoal | null;
  goal_detail?: string | null;      // ≤ 300 chars
  offering?: string | null;         // ≤ 500 chars: product, service or campaign
  target_audience?: string | null;  // ≤ 300 chars
  audience_filters?: { age_groups: string[]; genders: string[]; provinces: string[] };
  brand_voice?: string | null;      // ≤ 300 chars
  avoid_topics?: string[];          // ≤ 10 items, each ≤ 60 chars
  preferred_cta?: PreferredCta | null;
}
```

New optional `context?: CreatorContext | null` on:

| Request / response | Meaning |
|---|---|
| `POST /analyses` body (`AnalysisRequest`) | The brief for this analysis |
| `GET /reports/{id}` and `GET /accounts/{handle}/report` (`AnalysisReport.context`) | The brief the report was made with (echo) |
| `POST /drafts` body (`DraftRequest`) | Optional override: if you send it, it replaces `report.context` for these drafts |
| `POST /simulations` body (`SimulationRequest`) | Optional: lets the simulator know the product and default audience |

A request with an invalid brief (too long, unknown enum value) gets a 422 with the usual `ErrorResponse`.

### es-AR labels (add these to your label maps)

| `goal` | Label |
|---|---|
| `sell` | Vender un producto o servicio |
| `traffic` | Llevar gente a un link |
| `reach` | Crecer en alcance |
| `community` | Armar comunidad |
| `launch` | Lanzar algo nuevo |
| `other` | Otro |

| `preferred_cta` | Label |
|---|---|
| `link` | Que entren a un link |
| `reply` | Que respondan |
| `save` | Que lo guarden |
| `share` | Que lo compartan |
| `follow` | Que te sigan |
| `none` | Sin llamado a la acción |

### Audience filter values (use exactly these strings)

The simulator only matches these values (from the ENCC survey personas):

- **age_groups:** `13 a 17 años`, `18 a 29 años`, `30 a 49 años`, `50 a 64 años`, `65 años y mas`
- **genders:** `Mujer`, `Varón`
- **provinces:** `Buenos Aires`, `Catamarca`, `Chaco`, `Chubut`, `Ciudad Autónoma de Buenos Aires`, `Corrientes`, `Córdoba`, `Entre Ríos`, `Formosa`, `Jujuy`, `La Pampa`, `La Rioja`, `Mendoza`, `Misiones`, `Neuquén`, `Río Negro`, `Salta`, `San Juan`, `San Luis`, `Santa Cruz`, `Santa Fe`, `Santiago del Estero`, `Tierra del Fuego`, `Tucumán`

## Example payloads

```json
POST /analyses
{
  "handle": "paulina_cocina",
  "context": {
    "goal": "sell",
    "offering": "Ebook 'Soy Solito': recetas para una persona",
    "target_audience": "Gente que vive sola y cocina poco",
    "audience_filters": { "age_groups": ["18 a 29 años", "30 a 49 años"], "genders": [], "provinces": [] },
    "avoid_topics": ["política"],
    "preferred_cta": "link"
  }
}
```

```json
POST /drafts
{ "handle": "paulina_cocina", "count": 3 }
// uses report.context; to try another campaign, add "context": { ... }
```

## UI tasks

1. **Brief form on the analysis start screen**: a collapsible "Contale a la IA para qué publicás (opcional)".
   - Fields:
     - goal: a select with the labels above;
     - goal_detail, offering, target audience and brand voice: text areas with character counters;
     - avoid_topics: chips, max 10;
     - preferred CTA: a select;
     - audience filters: multi-selects with the values above.
   - Send `context` **only if at least one field is filled**. Otherwise omit it.
   - Short helper text: "Lo usamos para enfocar recomendaciones y borradores. No cambia tus números."
2. **Report header:** when `report.context` exists, show a compact summary, e.g. "Objetivo: Vender · Ebook 'Soy Solito' · Audiencia: 18 a 49 años". Add an "Editar brief y volver a analizar" link that reopens the form prefilled.
3. **Drafts screen:**
   - Show the brief in use (from `report.context`).
   - Add a "Usar otro brief para estos borradores" option that opens the form and sends `DraftRequest.context`. It doesn't touch the report.
4. **Simulator screen:**
   - Prefill the audience filters from `report.context.audience_filters`; the user can change them.
   - Send `SimulationRequest.context = report.context`.
5. **Earlier items, if not done yet:**
   - es-AR labels for the `hook` and `cta` segment and insight values (contract v1.1.0).
   - Show the simulator's `interaction_rate` **as a comparison between variants** (bars or a ranking), never as a forecast of real engagement. The summary text already compares, e.g. "La variante 2 generó 1,5 veces más interacción…". Keep the disclaimer visible.

## Acceptance checks

- [ ] Without filling the form, requests have no `context` and nothing changes on screen.
- [ ] With a brief, `POST /analyses` sends it, the report header shows it, and it survives a page reload (it comes back in `report.context`).
- [ ] Drafts use the report's brief by default, and the override is sent only when chosen.
- [ ] The simulator's filters are prefilled from the brief, and changing them works.
- [ ] A too-long field shows the counter and blocks sending (the API would answer 422).
- [ ] With the API mock (`NEXT_PUBLIC_API_MOCK=1`), the regenerated fixtures include an example brief for `demo_finanzas`, so the screens can be built before the backend is deployed.
- [ ] Type check, lint and your tests green; regenerated types committed.

## Questions

Ask the AI team (Juan) about what the AI does with each field, and Mark about the API.
