# EduHub Hackathon · Creator analytics

An analysis engine for creators that explains why their posts work and recommends what, how and when to post. It starts with X. Built for the **EDU HU₿ · LABITCONF 2026** hackathon (Creator Economy track).

Docs: [`docs/README.md`](docs/README.md) · rules for humans and Claude: [`CLAUDE.md`](CLAUDE.md), [`docs/workflow.md`](docs/workflow.md).

## Setup (every team member, once)

```bash
git clone git@github.com:JuaniLlaberia/eduhub-hackathon.git && cd eduhub-hackathon
git config core.hooksPath .githooks                        # ownership, frozen tests, contract checks

# Your team: frontend | backend | ai   (used by the Claude Code hooks and the git hooks)
printf '{\n  "env": { "EDUHUB_TEAM": "backend" }\n}\n' > .claude/settings.local.json

# Python 3.14 (back, AI, shared)
python3.14 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest src/shared                                          # contract tests should pass

cp .env.example .env                                       # fill in your keys (never commit .env)
python scripts/check_contracts.py --ack                    # after reviewing the contract (src/shared)
```

Front team: Node 20+ and the Next.js app in `src/frontend/` (see `src/frontend/CLAUDE.md`).

## Layout

| Path | Owner | What |
|---|---|---|
| `src/shared/` | all, via the contract process | Contracts: models, interfaces, `contracts/openapi.json`, metrics, fixtures, fakes |
| `src/backend/` | Back (Mark) | FastAPI service: data sources, jobs, API, publishing, deployment |
| `src/ai/` | AI (Llabe, Tomi) | `eduhub_ai`: analysis, insights, drafts, audience sandbox |
| `src/frontend/` | Front (Lupa, Varela) | Next.js app |
| `docs/` | all | Product, validation (evidence), architecture, workflow, team docs |
| `scripts/` | all | Repo tooling: style, contract and test checks, hooks |

## Everyday commands

```bash
pytest src/shared src/<team>                       # tests
ruff check . && python scripts/check_style.py      # lint + house style (never run black / ruff format)
python scripts/check_contracts.py                  # did the contract change since my last ack?
python scripts/approve_tests.py <test files>       # HUMANS ONLY: freeze reviewed tests
python -m eduhub_shared.openapi                    # regenerate openapi.json after a contract change
python -m eduhub_shared.fixtures.build             # regenerate fixtures after a contract change
```
