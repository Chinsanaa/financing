"""FastAPI docs/schema routes are hidden when ENVIRONMENT=production."""
from main import docs_kwargs


def test_docs_disabled_in_production():
    assert docs_kwargs("production") == {"docs_url": None, "redoc_url": None, "openapi_url": None}
    assert docs_kwargs("PROD") == docs_kwargs("production")


def test_docs_enabled_elsewhere():
    assert docs_kwargs("development") == {}
