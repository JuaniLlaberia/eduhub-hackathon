"""
Git commit-msg check: commits touching src/shared must start with 'contract:'.
"""
from __future__ import annotations
import sys
from pathlib import Path
from repo import SHARED_DIR, git

def main() -> None:
    """
    Abort the commit when contract files are staged and the message lacks the 'contract:' prefix.
    """
    message = Path(sys.argv[1]).read_text(encoding="utf-8").strip()
    staged = git("diff", "--cached", "--name-only").splitlines()
    if any(f.startswith(f"{SHARED_DIR}/") for f in staged) and not message.startswith("contract:"):
        print("Commits that change src/shared must start with 'contract:' (see docs/workflow.md §3).", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
