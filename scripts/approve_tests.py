"""
HUMAN ONLY: approve (freeze) test files after reviewing them. Requires an interactive terminal on purpose.

Usage: python scripts/approve_tests.py PATH [PATH...]   (files or directories)
       python scripts/approve_tests.py --revoke PATH    (unfreeze a test file)
       python scripts/approve_tests.py --list
"""
from __future__ import annotations
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from repo import APPROVED_TESTS_FILE, ROOT, load_json_file, owner_of, relative, sha256_bytes

TEST_PATTERNS = ("test_*.py", "*_test.py", "*.test.ts", "*.test.tsx", "*.spec.ts", "*.spec.tsx")

def collect(paths: list[str]) -> list[str]:
    """
    Expand files and directories into repo-relative test file paths.
    """
    found: set[str] = set()
    for raw in paths:
        path = Path(raw).resolve()
        candidates = [path] if path.is_file() else [p for pattern in TEST_PATTERNS for p in path.rglob(pattern)]
        for candidate in candidates:
            rel = relative(candidate)
            if rel and "node_modules" not in rel:
                found.add(rel)
    return sorted(found)

def save(manifest: dict) -> None:
    """
    Write the approved-tests manifest.
    """
    APPROVED_TESTS_FILE.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def confirm(files: list[str], action: str) -> str:
    """
    Show the files and ask the human for their name; abort if not run from an interactive terminal.
    """
    if not sys.stdin.isatty():
        print("Refusing: approving tests requires a human at an interactive terminal.", file=sys.stderr)
        sys.exit(2)
    print(f"About to {action}:")
    for name in files:
        print(f"  {name}  (team: {owner_of(name) or 'repo'})")
    name = input("Type your name to confirm (empty = cancel): ").strip()
    if not name:
        print("Cancelled.")
        sys.exit(1)
    return name

def main() -> None:
    """
    Approve, revoke or list frozen test files.
    """
    manifest = load_json_file(APPROVED_TESTS_FILE)
    args = sys.argv[1:]
    if not args or args == ["--list"]:
        for name, entry in sorted(manifest.items()):
            print(f"{name}  approved by {entry['approved_by']} at {entry['approved_at']}")
        return
    if args[0] == "--revoke":
        files = collect(args[1:])
        confirm(files, "UNFREEZE these tests")
        for name in files:
            manifest.pop(name, None)
        save(manifest)
        return
    files = collect(args)
    if not files:
        print("No test files found.", file=sys.stderr)
        sys.exit(1)
    approver = confirm(files, "APPROVE and freeze these tests")
    now = datetime.now(UTC).isoformat()
    for name in files:
        digest = sha256_bytes((ROOT / name).read_bytes())
        manifest[name] = {"sha256": digest, "approved_by": approver, "approved_at": now}
    save(manifest)
    print(f"Approved {len(files)} test file(s). Commit .approved-tests.json together with them.")

if __name__ == "__main__":
    main()
