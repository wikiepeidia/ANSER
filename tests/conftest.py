import os

import pytest

os.environ.setdefault("USE_POSTGRES", "False")
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
# create_app() raises RuntimeError if SECRET_KEY is left at its insecure
# default outside of FLASK_ENV=development — needed for the `app`/`client`
# fixtures below to build a real Flask app in a test process that has no
# .env-provided SECRET_KEY.
os.environ.setdefault("FLASK_ENV", "development")

import app as app_module


@pytest.fixture(scope="session")
def app():
    flask_app = getattr(app_module, "app", None)
    if flask_app is None:
        flask_app = app_module.create_app()
    flask_app.config.update(TESTING=True, WTF_CSRF_ENABLED=False, RATELIMIT_ENABLED=False)
    return flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def sqlite_db(tmp_path, monkeypatch):
    """Real Database instance backed by a temporary SQLite file.

    Patches Config so USE_POSTGRES=False and DATABASE_PATH points to a
    fresh temp file — full schema is created by init_database().
    """
    from core.config import Config
    from core.db.connection import Database

    monkeypatch.setattr(Config, "DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(Config, "USE_POSTGRES", False)
    return Database()
