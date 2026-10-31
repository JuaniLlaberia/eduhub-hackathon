# Hackathon: rules and logistics

**Hackathon EDU HU₿ · LABITCONF 2026**, Costa Salguero, Buenos Aires. Track: **Creator Economy**.
Source: [labitconf-hackathon.netlify.app](https://labitconf-hackathon.netlify.app/). Staff contact: Ro Minvielle (Coordinadora EDU HU₿), contacto@labitconf.com.

> Track text: "Crear ya no es solo un talento: es una economía propia. Construí las herramientas que le dan a cada creador el control real sobre lo que hace y lo que gana."

> Challenge: "Teniendo en cuenta el eje temático elegido, creen un MVP funcional que resuelva un problema dentro de ese eje. **Es obligatorio que la solución esté justificada con datos de OpenARG y que aplique al territorio argentino.**"

## Key dates

| When | What |
|---|---|
| Fri 30, 19:30 | Venue closes (we keep working remotely) |
| Sat 31, 09:30 | Masterclass: how to pitch (Eli Marto, M²) |
| Sat 31, 09:45–14:00 | Development and final mentoring |
| **Sat 31, 14:00** | **Delivery: link to a working demo, in person at the EDU HUB space** |
| Sat 31, 15:00–17:00 | Pitches: **1 minute + 1 minute of jury questions** |
| Sat 31, 18:10 | Awards (Workshop stage) |

## Deliverables

- **A link that opens on any computer** (hosted; nothing to install). Slides alone are not accepted.
- Repo: not required (we can show it anyway).
- Recommended: a **~20-second backup video** of the demo, in case the live demo fails.

## Judging (5 × 20%)

1. Impact and relevance of the problem
2. Business model
3. Pitch and communication
4. Prototype quality and use of technology/AI
5. Innovation and creativity

Jury: Federico Kohen (co-founder of TENT Creator Summit, marketing and content), Augusto Ardiles (GCBA Investment Undersecretary, fintech), Leonardo Damián Suárez (Head of Design, Paisanos.io), Tomás Moreno (PM at Moonsong Labs, blockchain professor at UTDT).

## 60-second pitch structure (official kit)

| Seconds | Block | Tip |
|---|---|---|
| 0–10 | Problem | One person, one situation |
| 10–20 | Solution | What it does, in one sentence |
| 20–45 | Demo | The main path, live or recorded |
| 45–55 | Why it works | What we validated and why this technology |
| 55–60 | Closing | What we'd do next week |

Typical jury questions and our answer drafts: [validation.md §8](validation.md#8-jury-qa-prep).

## Prizes

1st: USD 1,000 + one-week acceleration with Picante + HUMAI scholarships · 2nd: USD 500 + HUMAI scholarships · 3rd: HUMAI scholarships.

## OpenARG access

The OpenARG MCP is used for research only (not in the app). Each person uses **their own key** (free: 200 data queries + 10 questions per month). Never commit or paste the key:

```bash
claude mcp add --transport http openarg https://mcp.openarg.org/mcp \
  --header "Authorization: Bearer $OPENARG_API_KEY"
```
