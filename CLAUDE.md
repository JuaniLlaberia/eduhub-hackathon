# EduHub Hackathon · Creator analytics (LABITCONF 2026)

Analysis engine for creators: it explains why their X posts work and recommends what, how and when to post.
**Deadline: Sat 31 Oct 2026, 14:00 ART.** Scope and priorities: analysis = MUST · drafts + publishing = WANTED · audience sandbox = STRETCH (nothing may depend on it).

Read before working: `docs/README.md` (index) → `docs/architecture.md` (system and contracts) → `docs/workflow.md` (rules) → your team doc in `docs/teams/`.

## 1. Know your team

The developer's team is in `EDUHUB_TEAM` (`frontend` | `backend` | `ai` | `all` = repo maintenance), set in `.claude/settings.local.json`. If it is not set, ask the developer and tell them how to set it (`docs/workflow.md` §1).

| Team | Owns |
|---|---|
| frontend (Lupa, Varela) | `src/frontend/`, `docs/teams/frontend.md` |
| backend (Mark) | `src/backend/`, `docs/teams/backend.md` |
| ai (Llabe, Tomi) | `src/ai/`, `docs/teams/ai.md` |
| shared contracts | `src/shared/`, changed only through the contract process (§3) |

## 2. Hard rules

- **Never modify another team's files**, by any means: no Edit/Write, and no shell commands (`sed`, `cat >`, `mv`, `rm`, `git checkout --`…) that would get around the guard hook. If you need something from another team, stop and tell the developer.
- **Never bypass hooks**: no `--no-verify`, no editing `.approved-tests.json`, `.contracts-ack` or the hook scripts to get unblocked. If a hook blocks you, explain why to the developer.
- **Secrets** live only in `.env` (never committed, never read). Use `.env.example` for variable names.
- **Language:** code, contracts and docs in English. Anything users see (UI, insights, recommendations, drafts) in Spanish (es-AR).

## 3. Contracts (`src/shared/`)

The contract is the only way the teams depend on each other: models (C1), interfaces (C2/C3), `contracts/openapi.json` (C4), `metrics.py` (C5), fixtures and fakes (C6).

- **Code against the contract, never against another team's internals.** Back calls the AI only through `eduhub_ai.create_analyzer/create_generator/create_simulator`. The front calls only the HTTP API in `openapi.json`. The AI receives only an `AccountSnapshot`.
- **Changing it:** any team may change it, if the change doesn't break the others and the affected teams are notified. Before editing, confirm with the developer that the affected teams agreed. Then:
  1. Bump `CONTRACT_VERSION` in `src/shared/eduhub_shared/version.py`.
  2. Add an entry to `src/shared/CHANGELOG.md` (what changed, who agreed, what breaks).
  3. Run `python -m eduhub_shared.openapi` and `python -m eduhub_shared.fixtures.build`.
  4. Run `pytest src/shared`.
  5. Commit with the prefix `contract:`.
  6. Remind the developer to notify the other teams.
- **When a hook reports `CONTRACT CHANGE DETECTED`** (after a pull or merge, at session start, or on a prompt): **stop what you're doing.** Show the developer the CHANGELOG entry and the diff, run your team's tests, say whether the change breaks this team's code, and **ask how to proceed** before writing more code. The developer then runs `python scripts/check_contracts.py --ack`.
- **Before every commit**, and **after every pull**, run `python scripts/check_contracts.py` and your team's tests.

## 4. TDD with frozen tests

1. Write the tests first, in your team's folder.
2. **Stop and ask a human from the owning team to review them.** The human approves them with `python scripts/approve_tests.py <files>`. You can't run that script, and must not try.
3. Approved tests are frozen. **Never edit, delete, skip or weaken an approved test** to make code pass. If one looks wrong, explain why and let the human decide.
4. Then write code until the tests pass.

## 5. Python style (backend, AI, shared, scripts)

- Type hints on every argument and return value. Every function, method and class has a docstring in exactly this format, with **no blank line after it**:
  ```python
  def fetch_posts(handle: str, limit: int) -> list[Post]:
      """
      Fetch the latest posts of an account, newest first.
      """
      posts = ...
  ```
- **Exactly one blank line between functions/classes** (never two, not even at the top level). **Never run `black` or `ruff format`.**
- Follow Python best practices: small functions, `pathlib`, async I/O, no bare `except`, imports at the top.
- Check: `ruff check .` and `python scripts/check_style.py`. Test functions are exempt from the docstring and type-hint rules only.

## 6. Commands

```bash
source .venv/bin/activate                       # Python 3.14 venv (setup: README.md)
pytest src/shared src/<team>                    # contract + team tests
ruff check . && python scripts/check_style.py   # lint + house style
python scripts/check_contracts.py               # contract changed since my last ack?
python scripts/check_approved_tests.py          # frozen tests untouched?
```

## 7. Branches: `<team>` → `dev` → `main`

- Work and commit **only on your team's branch** (`frontend`, `backend` or `ai`). Never commit directly to `dev` or `main`. If you're on the wrong branch, stop and tell the developer.
- **To integrate:**
  1. Merge `dev` into your team branch.
  2. Run your team's tests and `python scripts/check_contracts.py`.
  3. Merge the team branch into `dev`.
  4. Run **all** teams' tests on `dev`.
- `dev` → `main` only when everything works together: all tests green and the demo path working. Only do this when the developer explicitly asks.
- Contract changes go into `dev` as soon as they're agreed. Other teams then merge `dev` into their branch.
- Keep commits small, with clear messages. Run the checks in §6 before each commit. The git hooks enforce ownership, frozen tests and contract bookkeeping.
