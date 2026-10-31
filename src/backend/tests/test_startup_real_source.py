import pytest
from eduhub_backend.deps import ConfigError, build_deps
from eduhub_backend.sources.twitterapi_io import TwitterApiIoSource

def test_demo_mode_off_uses_twitterapi_io(settings):
    deps = build_deps(settings.model_copy(update={"demo_mode": False, "twitterapi_io_key": "test-key"}))
    assert isinstance(deps.source, TwitterApiIoSource)

@pytest.mark.parametrize("key", [None, "", "   "])
def test_demo_mode_off_without_a_key_is_a_config_error(settings, key):
    with pytest.raises(ConfigError):
        build_deps(settings.model_copy(update={"demo_mode": False, "twitterapi_io_key": key}))
