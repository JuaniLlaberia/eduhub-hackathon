"""
Verify that approved (frozen) tests have not changed since a human approved them.

Usage: python scripts/check_approved_tests.py            (working tree)
       python scripts/check_approved_tests.py --staged   (staged content, used by the pre-commit hook)
"""
from __future__ import annotations
import subprocess
import sys
from repo import APPROVED_TESTS_FILE, ROOT, load_json_file, sha256_bytes

def staged_content(name: str) -> bytes | None:
    """
    Return the staged content of a file, or None if it is not in the index.
    """
    result = subprocess.run(["git", "show", f":{name}"], cwd=ROOT, capture_output=True, check=False)
    return result.stdout if result.returncode == 0 else None

def changed_tests(staged: bool) -> list[str]:
    """
    Return the approved test files whose content no longer matches the approved hash.
    """
    changed = []
    for name, entry in sorted(load_json_file(APPROVED_TESTS_FILE).items()):
        path = ROOT / name
        content = staged_content(name) if staged else (path.read_bytes() if path.exists() else None)
        if content is None or sha256_bytes(content) != entry["sha256"]:
            changed.append(name)
    return changed

def main() -> None:
    """
    Exit 1 listing approved tests that changed without re-approval.
    """
    changed = changed_tests("--staged" in sys.argv)
    if changed:
        print("Approved tests changed without human re-approval:", file=sys.stderr)
        for name in changed:
            print(f"  {name}", file=sys.stderr)
        print("Revert them, or have a human review and run: python scripts/approve_tests.py <file>", file=sys.stderr)
        sys.exit(1)
    print("approved tests unchanged")

if __name__ == "__main__":
    main()
