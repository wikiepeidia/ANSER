"""SEC-03 coverage: core/config.py must fail fast (RuntimeError at import
time) when SECRET_KEY is absent from the environment, instead of silently
falling back to a hardcoded, guessable value.

Reloads `core.config` inside the test rather than only asserting against
the already-imported module, so this genuinely exercises the class-body
`raise` on a fresh import -- not just checking Config.SECRET_KEY's current
value (which conftest.py's other fixtures may have already established).
"""
import importlib

import pytest


def test_secret_key_missing_raises_runtime_error(monkeypatch):
    monkeypatch.delenv('SECRET_KEY', raising=False)
    # Prevent core.config's module-level load_project_env() from silently
    # repopulating SECRET_KEY out of this dev machine's real .env on reload.
    monkeypatch.setattr('core.env_loader.load_project_env', lambda *a, **k: None)

    import core.config

    with pytest.raises(RuntimeError, match='SECRET_KEY'):
        importlib.reload(core.config)

    # Leave the module in a valid state for any test file collected after
    # this one -- every other module does `from core.config import Config`
    # (binds its own reference at first import, unaffected by this reload),
    # so only core/config.py itself needs this restoring reload.
    monkeypatch.setenv('SECRET_KEY', 'test-secret-key-for-fail-fast-reload')
    importlib.reload(core.config)
    assert core.config.Config.SECRET_KEY == 'test-secret-key-for-fail-fast-reload'


def test_secret_key_present_succeeds(monkeypatch):
    monkeypatch.setattr('core.env_loader.load_project_env', lambda *a, **k: None)
    monkeypatch.setenv('SECRET_KEY', 'another-test-secret-key')

    import core.config
    importlib.reload(core.config)

    assert core.config.Config.SECRET_KEY == 'another-test-secret-key'

    # Restore a stable value for subsequent tests in the suite.
    monkeypatch.setenv('SECRET_KEY', 'test-secret-key-for-fail-fast-reload')
    importlib.reload(core.config)
