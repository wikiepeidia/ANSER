import os

import pytest

os.environ.setdefault("USE_POSTGRES", "False")
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

import app as app_module


@pytest.fixture(scope="session")
def app():
    # Prefer module-level app so route registry matches runtime wiring.
    flask_app = getattr(app_module, "app", None)
    if flask_app is None:
        flask_app = app_module.create_app()

    flask_app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        RATELIMIT_ENABLED=False,
    )
    return flask_app


@pytest.fixture()
def client(app):
    return app.test_client()
