"""Tests for JWT verification: auth_utils.decode_supabase_jwt (unit level)
and AuthMiddleware (integration level via TestClient).

`test_decode_token_signed_by_wrong_keypair_rejected` is the direct
regression test for the vulnerability this suite exists to close: under the
old `verify_signature: False` code, a token like that was accepted as a
valid session for any `sub` claim -- full account impersonation, no real
signature required. It must fail against the pre-fix code and pass here.
"""
from datetime import timedelta

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


# --- unit tests: auth_utils.decode_supabase_jwt ---

def test_decode_valid_token_returns_claims(patch_jwks, make_token):
    import auth_utils

    token = make_token(sub="user-a")
    payload = auth_utils.decode_supabase_jwt(token)
    assert payload["sub"] == "user-a"
    assert payload["aud"] == "authenticated"


def test_decode_expired_token_raises(patch_jwks, make_token):
    import auth_utils

    token = make_token(exp_delta=timedelta(hours=-1))
    with pytest.raises(jwt.ExpiredSignatureError):
        auth_utils.decode_supabase_jwt(token)


def test_decode_tampered_signature_raises(patch_jwks, make_token):
    import auth_utils

    token = make_token()
    header, payload, signature = token.split(".")
    tampered_char = "A" if signature[0] != "A" else "B"
    tampered_token = f"{header}.{payload}.{tampered_char + signature[1:]}"
    with pytest.raises(jwt.PyJWTError):
        auth_utils.decode_supabase_jwt(tampered_token)


def test_decode_wrong_audience_raises(patch_jwks, make_token):
    import auth_utils

    token = make_token(aud="some-other-audience")
    with pytest.raises(jwt.InvalidAudienceError):
        auth_utils.decode_supabase_jwt(token)


def test_decode_forged_hs256_token_rejected(patch_jwks):
    """Signed with a plain string secret via HS256 -- the algorithm
    allowlist (`algorithms=["ES256"]`) must reject this outright,
    independent of any key material. Closes the classic alg-confusion
    attack where a server naively trusts the token's own `alg` header."""
    import auth_utils

    token = jwt.encode(
        {"sub": "user-a", "aud": "authenticated"},
        "attacker-controlled-secret",
        algorithm="HS256",
    )
    with pytest.raises(jwt.PyJWTError):
        auth_utils.decode_supabase_jwt(token)


def test_decode_token_signed_by_wrong_keypair_rejected(patch_jwks):
    """A token signed by an attacker-generated keypair (not the one JWKS
    trusts), with an arbitrary `sub` and a valid-looking `aud`. This is
    exactly what the pre-fix code accepted."""
    import auth_utils

    attacker_key = ec.generate_private_key(ec.SECP256R1())
    attacker_pem = attacker_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    forged_token = jwt.encode(
        {"sub": "victim-user-id", "aud": "authenticated"},
        attacker_pem,
        algorithm="ES256",
        headers={"kid": "test-kid"},
    )
    with pytest.raises(jwt.InvalidSignatureError):
        auth_utils.decode_supabase_jwt(forged_token)


# --- integration tests: AuthMiddleware via TestClient ---

def test_public_paths_bypass_auth(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_missing_auth_header_401(client):
    response = client.get("/categories/")
    assert response.status_code == 401


def test_malformed_bearer_401(client):
    response = client.get("/categories/", headers={"Authorization": "NotBearer abc"})
    assert response.status_code == 401


def test_valid_token_reaches_handler_200(client, patch_jwks, make_token, fake_db):
    token = make_token(sub="user-a")
    response = client.get("/categories/", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {"categories": []}


def test_expired_token_401_via_middleware(client, patch_jwks, make_token):
    token = make_token(exp_delta=timedelta(hours=-1))
    response = client.get("/categories/", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_tampered_token_401_via_middleware(client, patch_jwks, make_token):
    token = make_token()
    header, payload, signature = token.split(".")
    tampered_char = "A" if signature[0] != "A" else "B"
    tampered_token = f"{header}.{payload}.{tampered_char + signature[1:]}"
    response = client.get(
        "/categories/", headers={"Authorization": f"Bearer {tampered_token}"}
    )
    assert response.status_code == 401


def test_forged_token_401_via_middleware(client, patch_jwks):
    """End-to-end version of the impersonation regression test: a forged
    token must not reach a real route handler."""
    attacker_key = ec.generate_private_key(ec.SECP256R1())
    attacker_pem = attacker_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    forged_token = jwt.encode(
        {"sub": "victim-user-id", "aud": "authenticated"},
        attacker_pem,
        algorithm="ES256",
        headers={"kid": "test-kid"},
    )
    response = client.get(
        "/categories/", headers={"Authorization": f"Bearer {forged_token}"}
    )
    assert response.status_code == 401
