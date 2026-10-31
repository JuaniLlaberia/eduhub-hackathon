# Development workflow

These rules apply to every human and every Claude Code session. `CLAUDE.md` repeats them for Claude, and hooks enforce them.

## 1. Teams and folder ownership

| Team | Members | Owns | `EDUHUB_TEAM` |
|---|---|---|---|
| Front | Lupa, Varela | `src/frontend/`, `docs/teams/frontend.md` | `frontend` |
| Back | Mark | `src/backend/`, `docs/teams/backend.md` | `backend` |
| AI | Llabe, Tomi | `src/ai/`, `docs/teams/ai.md` | `ai` |

- **Never edit another team's folder.** If you need something from another team, ask them, or propose a contract change.
- Lupa, Varela and Tomi may switch teams. They then change `EDUHUB_TEAM` in their local settings.
- Each developer sets their team once, in `.claude/settings.local.json` (git-ignored):
  ```json
  { "env": { "EDUHUB_TEAM": "backend" } }
  ```
  Claude Code hooks block edits outside your team's folder, and ask before any edit to `src/shared/`.

## 2. Test-driven development (TDD)

1. **Write the tests first** for the feature. Claude may draft them.
2. **A human from the owning team reviews and approves them.** To approve, the human runs:
   ```bash
   python scripts/approve_tests.py src/<team>/tests/test_x.py   # interactive; records a hash in .approved-tests.json
   ```
3. **Approved tests are frozen.** Claude cannot edit them: the hook asks the human, and the git pre-commit hook rejects changed approved tests whose hashes weren't re-approved. To change one, a human re-approves it after reviewing the change.
4. Then write the code that makes the tests pass. **Never weaken a test to make the code pass.**

Frameworks: `pytest` + `pytest-asyncio` (back, AI, shared). The front team chooses its own; we suggest Vitest + React Testing Library.

## 3. Contracts (`src/shared/`)

- **Version 1 is approved by the whole team before anyone starts coding.**
- To change a contract:
  1. Talk to the affected teams and agree on the change.
  2. Edit `src/shared/`, bump `CONTRACT_VERSION` in `src/shared/eduhub_shared/version.py`, add an entry to `src/shared/CHANGELOG.md` (what changed, who agreed, what breaks), and regenerate `openapi.json` and the fixtures (`python -m eduhub_shared.openapi && python -m eduhub_shared.fixtures.build`). Run `pytest src/shared`.
  3. Commit with a message starting with `contract:` (the git hook enforces this for any change under `src/shared/`).
  4. Tell the other teams. They pull.
- **Detecting changes:** after every `git pull` or merge, and at the start of every Claude session (and on every prompt), `scripts/check_contracts.py` compares the contract against the version you last acknowledged.
  - If it changed, Claude must **stop, show you the CHANGELOG entry and diff, run your team's tests, and ask you how to proceed** before writing more code.
  - You acknowledge with `python scripts/check_contracts.py --ack`.

## 4. Code style

### Python (back, AI, shared)

- Follow best practices: type hints on **every** function (arguments and return), small functions, no bare `except`, use `pathlib`, use `async` for I/O.
- **Every function, method and class has a docstring** in this exact format:
  ```python
  def fetch_posts(handle: str, limit: int) -> list[Post]:
      """
      Fetch the latest posts of an account, newest first.
      """
  ```
  The opening `"""` is on its own line, followed by the text, then the closing `"""` on its own line.
- **No blank line between the docstring and the first line of code** in a function or class.
- **Exactly one blank line between functions and classes, never two.** This overrides PEP 8, so **don't run `black` or `ruff format`**, because they insert two blank lines.
- Lint: `ruff check` (configured in `pyproject.toml`) + `python scripts/check_style.py` (checks the docstring format and blank-line rule).

### Frontend (Next.js + TypeScript)

- TypeScript strict mode, ESLint + Prettier, App Router, server components by default, client components only where needed.
- API types are **generated** from `src/shared/contracts/openapi.json`. Never edit them by hand.

## 5. Git

- `main` is protected by convention. Work in branches named `<team>/<feature>` and merge often.
- The first full integration happens when the three parts are merged. **Run every team's tests before merging into `main`.**
- One-time setup per clone:
  ```bash
  git config core.hooksPath .githooks
  ```
