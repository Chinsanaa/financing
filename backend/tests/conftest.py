"""Shared fixtures for backend/tests/.

Sets up sys.path and dummy Supabase env vars BEFORE any test imports
`config`/`main` (pydantic-settings has no defaults and would otherwise
raise, and importing `main` at collection time would try to build a real
Supabase client). Dummy env vars also guarantee a real local backend/.env
(if one exists on a dev machine) can never leak into a test run, since
os.environ takes precedence over a .env file.
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
for _p in (str(BACKEND_DIR), str(REPO_ROOT), str(REPO_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.environ.setdefault("SUPABASE_URL", "https://test-project.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("ENVIRONMENT", "test")

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


@pytest.fixture(scope="session")
def ec_keypair():
    """A local ES256 keypair standing in for Supabase's real signing key."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


@pytest.fixture
def patch_jwks(monkeypatch, ec_keypair):
    """Make auth_utils trust our local test keypair instead of fetching
    Supabase's real JWKS over the network."""
    _, public_pem = ec_keypair

    class _FakeSigningKey:
        def __init__(self, key):
            self.key = key

    class _FakeJWKClient:
        def get_signing_key_from_jwt(self, token):
            return _FakeSigningKey(public_pem)

    import auth_utils

    monkeypatch.setattr(auth_utils, "_get_jwk_client", lambda: _FakeJWKClient())


@pytest.fixture
def make_token(ec_keypair):
    """Factory fixture: make_token(sub=..., aud=..., private_key=..., ...)
    mints a JWT. Pass a different private_key to simulate a token signed by
    someone who doesn't hold Supabase's real key (i.e. a forged token)."""
    trusted_private_pem, _ = ec_keypair

    def _make(
        sub: str = "user-a",
        aud: str = "authenticated",
        exp_delta: timedelta = timedelta(hours=1),
        private_key: bytes | None = None,
        algorithm: str = "ES256",
        extra_claims: dict | None = None,
    ) -> str:
        key = private_key if private_key is not None else trusted_private_pem
        now = datetime.now(timezone.utc)
        payload = {"sub": sub, "aud": aud, "iat": now, "exp": now + exp_delta}
        if extra_claims:
            payload.update(extra_claims)
        return jwt.encode(payload, key, algorithm=algorithm, headers={"kid": "test-kid"})

    return _make


@pytest.fixture
def client():
    """FastAPI TestClient for the real app, auth middleware included."""
    from fastapi.testclient import TestClient

    import main

    return TestClient(main.app)


@pytest.fixture
def fake_db(monkeypatch):
    """Swap the real service-role Supabase client for the in-memory fake in
    every route module this suite touches. Each route module bound
    `supabase_client` by name at import time (`from config import
    supabase_client`), so patching `config.supabase_client` alone would not
    affect already-imported route modules — each one must be patched."""
    from fake_supabase import FakeSupabaseClient

    fake = FakeSupabaseClient()

    import routes.categories as categories_module
    import routes.dashboard as dashboard_module
    import routes.settings as settings_module

    monkeypatch.setattr(categories_module, "supabase_client", fake)
    monkeypatch.setattr(dashboard_module, "supabase_client", fake)
    monkeypatch.setattr(settings_module, "supabase_client", fake)

    return fake
