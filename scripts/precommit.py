"""
Git pre-commit checks (run by .githooks/pre-commit):

1. Staged files belong to the committer's team (EDUHUB_TEAM), shared contracts or repo-wide files.
2. Approved tests are unchanged (or re-approved).
3. Contract changes bump CONTRACT_VERSION, add a CHANGELOG entry, keep openapi.json/fixtures in sync and pass tests.
4. Staged Python files pass ruff (if installed) and the house style checker.

Bypass the ownership check only with EDUHUB_ALLOW_CROSS_TEAM=1 (e.g. agreed integration commits).
"""
from __future__ import annotations
import os
import subprocess
import sys
from repo import ALL_TEAMS, ROOT, SHARED_DIR, TEAMS, current_team, git, owner_of

PYTHON = sys.executable
PYTHON_DIRS = ("src/shared/", "src/backend/", "src/ai/", "scripts/")

def staged_files() -> list[str]:
    """
    Return staged (added, copied, modified, renamed) repo-relative paths.
    """
    output = git("diff", "--cached", "--name-only", "--diff-filter=ACMR")
    return [line for line in output.splitlines() if line]

def run(command: list[str]) -> bool:
    """
    Run a command from the repo root, streaming its output; return True on success.
    """
    return subprocess.run(command, cwd=ROOT, check=False).returncode == 0

def check_ownership(files: list[str], team: str | None) -> list[str]:
    """
    Return errors for staged files owned by another team.
    """
    if os.environ.get("EDUHUB_ALLOW_CROSS_TEAM") == "1" or team == ALL_TEAMS:
        return []
    if team not in TEAMS:
        return ["EDUHUB_TEAM is not set (see docs/workflow.md §1)."]
    foreign = [f for f in files if owner_of(f) in TEAMS and owner_of(f) != team]
    return [f"{f} belongs to the {owner_of(f)} team (you are {team})" for f in foreign]

def check_contract_change(files: list[str]) -> list[str]:
    """
    Return errors when contract files are staged without the required bookkeeping or with failing checks.
    """
    shared = [f for f in files if f.startswith(f"{SHARED_DIR}/")]
    if not shared:
        return []
    errors = []
    if f"{SHARED_DIR}/eduhub_shared/version.py" not in shared:
        errors.append("contract changed: bump CONTRACT_VERSION in src/shared/eduhub_shared/version.py")
    if f"{SHARED_DIR}/CHANGELOG.md" not in shared:
        errors.append("contract changed: add an entry to src/shared/CHANGELOG.md")
    if not run([PYTHON, "-m", "eduhub_shared.openapi", "--check"]):
        errors.append("openapi.json outdated: python -m eduhub_shared.openapi")
    if not run([PYTHON, "-m", "eduhub_shared.fixtures.build", "--check"]):
        errors.append("fixtures outdated: python -m eduhub_shared.fixtures.build")
    if not run([PYTHON, "-m", "pytest", SHARED_DIR, "-q"]):
        errors.append("shared contract tests fail")
    return errors

def check_python(files: list[str]) -> list[str]:
    """
    Return errors from ruff and the house style checker on staged Python files.
    """
    python_files = [f for f in files if f.endswith(".py") and f.startswith(PYTHON_DIRS)]
    if not python_files:
        return []
    errors = []
    if not run([PYTHON, "scripts/check_style.py", *python_files]):
        errors.append("house style errors (python scripts/check_style.py)")
    if run([PYTHON, "-m", "ruff", "--version"]) and not run([PYTHON, "-m", "ruff", "check", *python_files]):
        errors.append("ruff errors (ruff check)")
    return errors

def main() -> None:
    """
    Run every check and abort the commit on any error.
    """
    files = staged_files()
    errors = check_ownership(files, current_team())
    if not run([PYTHON, "scripts/check_approved_tests.py", "--staged"]):
        errors.append("approved tests changed without re-approval")
    errors += check_contract_change(files)
    errors += check_python(files)
    if errors:
        print("\npre-commit failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
