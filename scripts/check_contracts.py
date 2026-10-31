"""
Detect contract changes (src/shared) since this developer last acknowledged them.

Usage: python scripts/check_contracts.py               (human-readable; exit 1 if unacknowledged changes)
       python scripts/check_contracts.py --ack         (acknowledge the current contract after reviewing it)
       python scripts/check_contracts.py --hook EVENT  (Claude Code hook: emit additionalContext JSON)
"""
from __future__ import annotations
import json
import re
import sys
from datetime import UTC, datetime
from repo import (
    CONTRACT_ACK_FILE,
    CONTRACT_NOTIFIED_FILE,
    ROOT,
    SHARED_DIR,
    contract_hash,
    current_team,
    git,
    load_json_file,
)

VERSION_FILE = ROOT / SHARED_DIR / "eduhub_shared" / "version.py"
CHANGELOG_FILE = ROOT / SHARED_DIR / "CHANGELOG.md"
TEST_COMMANDS = {
    "backend": "pytest src/backend src/shared",
    "ai": "pytest src/ai src/shared",
    "frontend": "regenerate API types from src/shared/contracts/openapi.json and run the front tests/typecheck",
}

def contract_version() -> str:
    """
    Read CONTRACT_VERSION from version.py.
    """
    match = re.search(r'CONTRACT_VERSION\s*=\s*"([^"]+)"', VERSION_FILE.read_text(encoding="utf-8"))
    return match.group(1) if match else "unknown"

def latest_changelog_entry() -> str:
    """
    Return the most recent CHANGELOG section (first '## ' block).
    """
    if not CHANGELOG_FILE.exists():
        return "(no CHANGELOG.md)"
    sections = re.split(r"\n(?=## )", CHANGELOG_FILE.read_text(encoding="utf-8"))
    entries = [s for s in sections if s.startswith("## ")]
    return entries[0].strip() if entries else "(empty CHANGELOG)"

def change_report(ack: dict) -> str:
    """
    Build the message describing what changed since the acknowledged contract.
    """
    team = current_team() or "<your team>"
    lines = [
        "CONTRACT CHANGE DETECTED in src/shared since this developer last acknowledged it.",
        f"Acknowledged version: {ack.get('version', 'none')} -> current version: {contract_version()}.",
    ]
    since = ack.get("commit")
    if since:
        log = git("log", "--oneline", f"{since}..HEAD", "--", SHARED_DIR)
        stat = git("diff", "--stat", since, "--", SHARED_DIR)
        lines += [f"Commits touching contracts:\n{log or '(none: uncommitted local changes)'}", f"Diff:\n{stat}"]
    lines += [
        f"Latest CHANGELOG entry:\n{latest_changelog_entry()}",
        "REQUIRED before writing more code: (1) stop and tell the developer; (2) read the CHANGELOG entry and the "
        f"diff; (3) run `{TEST_COMMANDS.get(team, 'your team tests')}` and check whether the change breaks this "
        "team's implementation; (4) ask the developer how to proceed. Only after the developer confirms, run "
        "`python scripts/check_contracts.py --ack`.",
    ]
    return "\n".join(lines)

def acknowledge() -> None:
    """
    Record the current contract as reviewed by this developer.
    """
    data = {
        "hash": contract_hash(),
        "version": contract_version(),
        "commit": git("rev-parse", "HEAD") or None,
        "acked_at": datetime.now(UTC).isoformat(),
    }
    CONTRACT_ACK_FILE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Contract v{data['version']} acknowledged.")

def pending_message() -> str | None:
    """
    Return the change report when the contract differs from the acknowledged one, else None.
    """
    ack = load_json_file(CONTRACT_ACK_FILE)
    if not ack:
        return (
            "CONTRACT NOT YET ACKNOWLEDGED on this clone. Ask the developer to review src/shared (CHANGELOG.md, "
            "docs/architecture.md) and then run `python scripts/check_contracts.py --ack`."
        )
    if ack.get("hash") == contract_hash():
        return None
    return change_report(ack)

def emit_hook(event: str) -> None:
    """
    Print Claude Code hook JSON with the pending message. PostToolUse only notifies once per contract state.
    """
    message = pending_message()
    if message is None:
        return
    if event == "PostToolUse":
        state = contract_hash()
        if CONTRACT_NOTIFIED_FILE.exists() and CONTRACT_NOTIFIED_FILE.read_text(encoding="utf-8") == state:
            return
        CONTRACT_NOTIFIED_FILE.write_text(state, encoding="utf-8")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": message}}))

def main() -> None:
    """
    Dispatch on the command-line flags.
    """
    if "--ack" in sys.argv:
        acknowledge()
        return
    if "--hook" in sys.argv:
        index = sys.argv.index("--hook")
        emit_hook(sys.argv[index + 1] if len(sys.argv) > index + 1 else "UserPromptSubmit")
        return
    message = pending_message()
    if message:
        print(message)
        sys.exit(1)
    print(f"Contract v{contract_version()} acknowledged and unchanged.")

if __name__ == "__main__":
    main()
