"""Supabase JWT verification via JWKS (ES256, asymmetric signing).

Kept separate from main.py so tests can monkeypatch the key-lookup step
(`_get_jwk_client`) and verify against a local test keypair instead of a
live Supabase project.
"""
import jwt

from config import settings

JWKS_URL = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"

_jwk_client: jwt.PyJWKClient | None = None


def _get_jwk_client() -> jwt.PyJWKClient:
    """Build (once) and cache the JWKS client.

    PyJWKClient fetches and caches Supabase's signing keys internally
    (default 5-minute TTL), so no extra caching layer is needed here.
    """
    global _jwk_client
    if _jwk_client is None:
        _jwk_client = jwt.PyJWKClient(JWKS_URL)
    return _jwk_client


def decode_supabase_jwt(token: str) -> dict:
    """Verify `token`'s ES256 signature against Supabase's live JWKS and
    return its claims.

    Raises jwt.PyJWTError subclasses (ExpiredSignatureError,
    InvalidSignatureError, InvalidAudienceError, PyJWKClientError for an
    unrecognized `kid`, ...) on any failure — callers should catch
    jwt.PyJWTError, not the narrower jwt.InvalidTokenError.
    """
    signing_key = _get_jwk_client().get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["ES256"],
        audience="authenticated",
    )
