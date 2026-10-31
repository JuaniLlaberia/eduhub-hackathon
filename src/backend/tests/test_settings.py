from pathlib import Path
import pytest
from eduhub_backend.settings import Settings

ENV_VARS = ("EDUHUB_FAKE_AI", "DEMO_MODE", "FRONTEND_ORIGIN", "DATABASE_PATH", "FIXTURES_DIR", "TWITTERAPI_IO_KEY")

@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)

def test_defaults():
    settings = Settings(_env_file=None)
    assert settings.eduhub_fake_ai is True
    assert settings.demo_mode is False
    assert settings.frontend_origin == "http://localhost:3000"
    assert settings.database_path == Path("data/eduhub.sqlite3")
    assert settings.fixtures_dir == Path("src/backend/fixtures")
    assert settings.twitterapi_io_key is None

def test_reads_environment_variables(monkeypatch, tmp_path):
    monkeypatch.setenv("EDUHUB_FAKE_AI", "0")
    monkeypatch.setenv("DEMO_MODE", "1")
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://front.example")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "x.sqlite3"))
    monkeypatch.setenv("FIXTURES_DIR", str(tmp_path / "fx"))
    monkeypatch.setenv("TWITTERAPI_IO_KEY", "key")
    settings = Settings(_env_file=None)
    assert settings.eduhub_fake_ai is False
    assert settings.demo_mode is True
    assert settings.frontend_origin == "https://front.example"
    assert settings.database_path == tmp_path / "x.sqlite3"
    assert settings.fixtures_dir == tmp_path / "fx"
    assert settings.twitterapi_io_key == "key"

def test_frontend_origins_single():
    assert Settings(_env_file=None).frontend_origins == ["http://localhost:3000"]

def test_frontend_origins_comma_separated_list_is_trimmed():
    settings = Settings(_env_file=None, frontend_origin=" http://a.test , https://b.test,, ")
    assert settings.frontend_origins == ["http://a.test", "https://b.test"]
