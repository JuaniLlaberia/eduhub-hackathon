"""
Shared helpers for repo tooling scripts and hooks (standard library only).
"""
from __future__ import annotations
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEAMS = ("frontend", "backend", "ai")
ALL_TEAMS = "all"
SHARED_DIR = "src/shared"
APPROVED_TESTS_FILE = ROOT / ".approved-tests.json"
CONTRACT_ACK_FILE = ROOT / ".contracts-ack"
CONTRACT_NOTIFIED_FILE = ROOT / ".contracts-notified"
LOCAL_SETTINGS = ROOT / ".claude" / "settings.local.json"
IGNORED_PARTS = {"__pycache__", ".pytest_cache", ".ruff_cache"}

def current_team() -> str | None:
    """
    Return the developer's team from EDUHUB_TEAM, falling back to .claude/settings.local.json.
    """
    team = os.environ.get("EDUHUB_TEAM")
    if not team and LOCAL_SETTINGS.exists():
        try:
            team = json.loads(LOCAL_SETTINGS.read_text(encoding="utf-8")).get("env", {}).get("EDUHUB_TEAM")
        except (json.JSONDecodeError, OSError):
            team = None
    return team.strip().lower() if team else None

def relative(path: str | Path) -> str | None:
    """
    Return path relative to the repo root (POSIX style), or None when it is outside the repo.
    """
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return None

def owner_of(rel_path: str) -> str | None:
    """
    Return the team owning a repo-relative path, 'shared' for contracts, or None for repo-wide files.
    """
    for team in TEAMS:
        if rel_path.startswith(f"src/{team}/") or rel_path == f"docs/teams/{team}.md":
            return team
    if rel_path.startswith(f"{SHARED_DIR}/"):
        return "shared"
    return None

def git(*args: str) -> str:
    """
    Run a git command in the repo and return its stdout ('' on failure).
    """
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""

def sha256_bytes(data: bytes) -> str:
    """
    Return the hex SHA-256 of data.
    """
    return hashlib.sha256(data).hexdigest()

def contract_files() -> list[Path]:
    """
    Return every file under src/shared that is part of the contract.
    """
    files = (ROOT / SHARED_DIR).rglob("*")
    return sorted(
        p for p in files
        if p.is_file() and not IGNORED_PARTS & set(p.parts) and p.suffix != ".pyc" and ".egg-info" not in str(p)
    )

def contract_hash() -> str:
    """
    Return a hash of the current contract (paths and contents of src/shared).
    """
    digest = hashlib.sha256()
    for path in contract_files():
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()

def load_json_file(path: Path) -> dict:
    """
    Load a JSON object from path, or return {} when missing or invalid.
    """
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
