"""Shared fixtures for backend/tests/.

Sets up sys.path and dummy Supabase env vars BEFORE any test imports
`config`/`main` (pydantic-settings has no defaults and would otherwise
raise, and importing `main` at collection time would try to build a real
Supabase client). Dummy env vars also guarantee a real local backend/.env
(if one exists on a dev machine) can never leak into a test run, since
os.environ takes precedence over a .env file.
"""
import importlib
import os
import sys
import types
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
for _p in (str(BACKEND_DIR), str(REPO_ROOT), str(REPO_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# jieba doesn't build in every environment (same mock used by
# tests/test_matching_optimization.py at the repo root) — importing `main`
# pulls in routes/training.py -> src/retrain -> src/segment -> jieba
# transitively, even though no backend test here exercises Chinese
# tokenization directly.
if "jieba" not in sys.modules:
    from unittest.mock import MagicMock
    sys.modules["jieba"] = MagicMock()
    sys.modules["jieba"].cut = lambda text, cut_all=False: text.split()

os.environ.setdefault("SUPABASE_URL", "https://test-project.supabase.co")
# supabase-py's create_client validates the key looks JWT-shaped
# (dot-separated segments) before ever making a network call, so the dummy
# values need three segments even though nothing here is a real credential.
os.environ.setdefault("SUPABASE_ANON_KEY", "test.anon.key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test.service.role.key")
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
        import auth_utils
        payload = {
            "sub": sub, "aud": aud, "iat": now, "exp": now + exp_delta,
            "iss": auth_utils.EXPECTED_ISSUER,
        }
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


@pytest.fixture(autouse=True)
def translation_requests(monkeypatch):
    """Record background-translation requests instead of starting worker
    threads (which would outlive the test and hit the network). Tests of the
    worker itself call translations.translate_user_transactions directly."""
    import translations
    import routes.transactions as transactions_module

    calls: list = []
    record = lambda user_id: calls.append(user_id) or True
    monkeypatch.setattr(translations, "request_translation", record)
    monkeypatch.setattr(transactions_module, "request_translation", record)
    monkeypatch.setattr(translations, "_last_periodic", {})  # throttle state per test
    return calls


@pytest.fixture
def fake_db(monkeypatch):
    """Swap the real service-role Supabase client for the in-memory fake in
    every route module this suite touches. Each route module bound
    `supabase_client` by name at import time (`from config import
    supabase_client`), so patching `config.supabase_client` alone would not
    affect already-imported route modules — each one must be patched."""
    from fake_supabase import FakeSupabaseClient

    fake = FakeSupabaseClient()

    import routes.auth as auth_module
    import routes.categories as categories_module
    import routes.classify as classify_module
    import routes.dashboard as dashboard_module
    import routes.settings as settings_module
    import routes.training as training_module
    import routes.uploads as uploads_module
    import routes.subscriptions as subscriptions_module
    import routes.transactions as transactions_module
    import alerts as alerts_module
    import budget as budget_module
    import main as main_module
    import translations as translations_module

    monkeypatch.setattr(main_module, "supabase_client", fake)
    monkeypatch.setattr(translations_module, "supabase_client", fake)
    monkeypatch.setattr(auth_module, "supabase_client", fake)
    monkeypatch.setattr(categories_module, "supabase_client", fake)
    monkeypatch.setattr(classify_module, "supabase_client", fake)
    monkeypatch.setattr(dashboard_module, "supabase_client", fake)
    monkeypatch.setattr(settings_module, "supabase_client", fake)
    monkeypatch.setattr(training_module, "supabase_client", fake)
    monkeypatch.setattr(uploads_module, "supabase_client", fake)
    monkeypatch.setattr(subscriptions_module, "supabase_client", fake)
    monkeypatch.setattr(transactions_module, "supabase_client", fake)
    monkeypatch.setattr(alerts_module, "supabase_client", fake)
    monkeypatch.setattr(budget_module, "supabase_client", fake)

    # backend/fx.py and routes/fx.py (home-currency rates) may not exist on
    # every branch yet; patch them when they do.
    for module_name in ("fx", "routes.fx"):
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            continue
        if hasattr(module, "supabase_client"):
            monkeypatch.setattr(module, "supabase_client", fake)
        if hasattr(module, "_new_client"):
            # fx's background backfill builds its own client; keep it on the fake.
            monkeypatch.setattr(module, "_new_client", lambda: fake)

    return fake


@pytest.fixture(autouse=True)
def fx_background(monkeypatch):
    """Reset fx's in-process throttle/cache state around every test. fx's
    own suite (test_fx.py) needs real background threads, so `_spawn` is
    NOT stubbed here; tests that want to record spawns patch it locally.
    No-op if backend/fx.py is absent on this branch."""
    try:
        import fx
    except ImportError:
        yield []
        return
    calls: list = []
    reset = getattr(fx, "_reset_state", None)
    if reset:
        reset()
    yield calls
    if reset:
        reset()


class FakeRateTable:
    """In-memory stand-in for fx.RateTable (API v5 §2 lookup rules)."""

    def __init__(self, rates: dict):
        self.rates = dict(sorted(rates.items()))  # date -> rate

    def strict(self, d: date):
        best = [r for rd, r in self.rates.items() if d - timedelta(days=7) <= rd <= d]
        return best[-1] if best else None

    def lenient(self, d: date):
        strict = self.strict(d)
        if strict is not None:
            return strict, False
        if not self.rates:
            return None, False
        older = [r for rd, r in self.rates.items() if rd <= d]
        return (older[-1] if older else next(iter(self.rates.values()))), True

    def latest(self, on_or_before: date):
        older = [(rd, r) for rd, r in self.rates.items() if rd <= on_or_before]
        return older[-1] if older else (None, None)


@pytest.fixture
def fake_fx(monkeypatch):
    """Install a fake `fx` module (B3's backend/fx.py interface) so dashboard
    home-currency maths is testable without real rates or network.

    Set `fake_fx.home[user_id] = "USD"` and `fake_fx.rates[date] = 0.14`.
    `fake_fx.load_calls` records every load_rates call (one per request)."""
    module = types.ModuleType("fx")
    module.home = {}
    module.rates = {}
    module.load_calls = []
    module.SUPPORTED = {"USD": "US Dollar", "EUR": "Euro"}

    def row_date(ts):
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if ts.tzinfo is not None:
            ts = ts.astimezone(timezone.utc)
        return ts.date()

    async def get_home_currency(user_id):
        return module.home.get(user_id)

    async def load_rates(quote, start, end):
        module.load_calls.append((quote, start, end))
        return FakeRateTable(module.rates)

    def request_backfill_for_user(user_id, start=None):
        return None

    module.row_date = row_date
    module.get_home_currency = get_home_currency
    module.load_rates = load_rates
    module.request_backfill_for_user = request_backfill_for_user
    module.RateTable = FakeRateTable
    monkeypatch.setitem(sys.modules, "fx", module)
    return module
