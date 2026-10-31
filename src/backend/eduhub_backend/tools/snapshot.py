"""
Build demo fixtures: fetch accounts from twitterapi.io, analyze them and save <handle>.json + <handle>.report.json.

Usage (repo root): python -m eduhub_backend.tools.snapshot bilinkis [more handles]
                   [--max-posts 200] [--out DIR] [--include-shared]
"""
import argparse
import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path
from pydantic import BaseModel
from eduhub_backend.deps import ConfigError, build_ai
from eduhub_backend.settings import Settings
from eduhub_backend.sources.twitterapi_io import TwitterApiIoSource
from eduhub_shared.errors import ContractError
from eduhub_shared.fixtures import load_report, load_snapshot
from eduhub_shared.interfaces import Analyzer, PostSource
from eduhub_shared.models import AccountSnapshot

SOURCE_ID = "twitterapi.io"
MIN_POSTS = 10
MAX_POSTS = 500
DEFAULT_POSTS = 200

def fixture_paths(out: Path, handle: str) -> list[Path]:
    """
    Return the snapshot and report paths of handle in out.
    """
    return [out / f"{handle}.json", out / f"{handle}.report.json"]

def write_json(path: Path, model: BaseModel) -> None:
    """
    Write model to path as indented JSON, creating parent directories.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(model.model_dump_json(indent=2) + "\n", encoding="utf-8")

async def build_snapshot(source: PostSource, handle: str, max_posts: int) -> AccountSnapshot:
    """
    Fetch the profile, up to max_posts posts and the current trends of handle.
    """
    profile = await source.fetch_profile(handle)
    posts = await source.fetch_posts(profile.handle, max_posts)
    trends = await source.fetch_trends()
    return AccountSnapshot(
        profile=profile, posts=posts, trends=trends, source=SOURCE_ID, collected_at=datetime.now(UTC)
    )

async def write_fixture(snapshot: AccountSnapshot, analyzer: Analyzer, out: Path) -> list[Path]:
    """
    Analyze snapshot and write it and its report to out; return the written paths.
    """
    report = await analyzer.analyze(snapshot)
    paths = fixture_paths(out, snapshot.profile.handle)
    for path, model in zip(paths, (snapshot, report), strict=True):
        await asyncio.to_thread(write_json, path, model)
    return paths

def write_shared(out: Path) -> list[Path]:
    """
    Write the shared fixture account (snapshot and report) to out; return the written paths.
    """
    snapshot = load_snapshot()
    paths = fixture_paths(out, snapshot.profile.handle)
    for path, model in zip(paths, (snapshot, load_report()), strict=True):
        write_json(path, model)
    return paths

def build_parser() -> argparse.ArgumentParser:
    """
    Return the command-line parser.
    """
    parser = argparse.ArgumentParser(prog="python -m eduhub_backend.tools.snapshot", description=__doc__)
    parser.add_argument("handles", nargs="+", help="X handles to fetch, with or without @")
    parser.add_argument("--max-posts", type=int, default=DEFAULT_POSTS, help=f"{MIN_POSTS}..{MAX_POSTS}")
    parser.add_argument("--out", type=Path, default=None, help="output directory (default: FIXTURES_DIR)")
    parser.add_argument("--include-shared", action="store_true", help="also write the shared demo account")
    return parser

def parse_args(argv: list[str]) -> argparse.Namespace | None:
    """
    Parse argv, returning None (after argparse printed why) when the arguments are invalid.
    """
    try:
        args = build_parser().parse_args(argv)
    except SystemExit:
        return None
    if not MIN_POSTS <= args.max_posts <= MAX_POSTS:
        print(f"--max-posts tiene que estar entre {MIN_POSTS} y {MAX_POSTS}.", file=sys.stderr)
        return None
    return args

def default_source(settings: Settings) -> PostSource | None:
    """
    Return a TwitterApiIoSource from settings, or None (after printing why) when the key is missing.
    """
    key = (settings.twitterapi_io_key or "").strip()
    if not key:
        print("Falta TWITTERAPI_IO_KEY (en .env o en el entorno).", file=sys.stderr)
        return None
    return TwitterApiIoSource(key)

def default_analyzer(settings: Settings) -> Analyzer | None:
    """
    Return the analyzer chosen by EDUHUB_FAKE_AI, or None (after printing why) when it is not available.
    """
    try:
        return build_ai(settings)[0]
    except ConfigError as error:
        print(str(error), file=sys.stderr)
        return None

async def run(
    argv: list[str], settings: Settings, source: PostSource | None = None, analyzer: Analyzer | None = None
) -> int:
    """
    Run the tool and return its exit code: 0 ok, 1 a source/analysis error, 2 bad arguments or configuration.
    """
    args = parse_args(argv)
    if args is None:
        return 2
    source = source or default_source(settings)
    analyzer = analyzer or default_analyzer(settings)
    if source is None or analyzer is None:
        return 2
    out = args.out or settings.fixtures_dir
    written: list[Path] = []
    try:
        for handle in args.handles:
            snapshot = await build_snapshot(source, handle, args.max_posts)
            written += await write_fixture(snapshot, analyzer, out)
    except ContractError as error:
        print(error.message, file=sys.stderr)
        return 1
    if args.include_shared:
        written += write_shared(out)
    for path in written:
        print(f"Guardado: {path}")
    return 0

def main() -> None:
    """
    Command-line entry point.
    """
    sys.exit(asyncio.run(run(sys.argv[1:], Settings())))

if __name__ == "__main__":
    main()
