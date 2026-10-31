"""
Claude Code PreToolUse hook for Edit/Write/MultiEdit/NotebookEdit: enforce folder ownership and frozen files.

- other team's folder or team doc  -> deny
- src/shared (contracts)          -> ask (human must confirm the change was agreed)
- approved (frozen) test          -> ask (human must re-approve with scripts/approve_tests.py)
- tooling state files             -> deny
- repo-wide files                 -> ask, unless EDUHUB_TEAM=all
- own folder, personal settings, or outside the repo -> normal permission flow
"""
from __future__ import annotations
import json
import sys
from repo import (
    ALL_TEAMS,
    APPROVED_TESTS_FILE,
    CONTRACT_ACK_FILE,
    CONTRACT_NOTIFIED_FILE,
    TEAMS,
    current_team,
    load_json_file,
    owner_of,
    relative,
)

PROTECTED = {p.name for p in (APPROVED_TESTS_FILE, CONTRACT_ACK_FILE, CONTRACT_NOTIFIED_FILE)}
PERSONAL = {".claude/settings.local.json", "CLAUDE.local.md"}
SETUP_HELP = (
    'Set your team first: create .claude/settings.local.json with {"env": {"EDUHUB_TEAM": "<team>"}} '
    f"where <team> is one of {', '.join(TEAMS)} (or '{ALL_TEAMS}' for repo maintenance)."
)

def decision(kind: str, reason: str) -> None:
    """
    Print a PreToolUse permission decision and exit.
    """
    output = {"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": kind, "permissionDecisionReason": reason,
    }}
    print(json.dumps(output))
    sys.exit(0)

def target_path(payload: dict) -> str | None:
    """
    Return the file path a tool call is about to modify.
    """
    tool_input = payload.get("tool_input", {})
    return tool_input.get("file_path") or tool_input.get("notebook_path")

def evaluate(rel: str, team: str | None) -> None:
    """
    Decide on an edit to the repo-relative path rel by a developer of team.
    """
    if rel in PERSONAL:
        return
    if rel in PROTECTED:
        decision("deny", f"{rel} is tooling state managed by humans through scripts/. Do not edit it.")
    if rel in load_json_file(APPROVED_TESTS_FILE):
        decision("ask", (
            f"{rel} is an APPROVED (frozen) test. Only change it if the developer explicitly agrees; a human must "
            "then re-approve it with `python scripts/approve_tests.py`."
        ))
    if team not in (*TEAMS, ALL_TEAMS):
        decision("deny", SETUP_HELP)
    owner = owner_of(rel)
    if owner == "shared":
        decision("ask", (
            f"{rel} is a CONTRACT file. Confirm the affected teams agreed. Required: bump CONTRACT_VERSION, add a "
            "src/shared/CHANGELOG.md entry, regenerate openapi.json/fixtures, run pytest src/shared, commit with "
            "'contract:' prefix and notify the other teams."
        ))
    if owner in TEAMS and owner != team and team != ALL_TEAMS:
        decision("deny", (
            f"{rel} belongs to the {owner} team; you are on the {team} team. Never edit another team's files: "
            "ask that team, or propose a contract change in src/shared."
        ))
    if owner is None and team != ALL_TEAMS:
        decision("ask", f"{rel} is a repo-wide file shared by all teams. Confirm the change was agreed.")

def main() -> None:
    """
    Read the hook payload from stdin and evaluate the target path.
    """
    payload = json.load(sys.stdin)
    path = target_path(payload)
    rel = relative(path) if path else None
    if rel is None:
        return
    evaluate(rel, current_team())

if __name__ == "__main__":
    main()
