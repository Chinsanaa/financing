"""Pre-auth helper routes.

Sign-up, sign-in and sign-out happen in the browser via supabase-js. The old
/auth/signup and /auth/login endpoints were removed: they signed in on the
shared service-role client, which swaps that client's token to the user's
JWT for every later backend query.
"""
from fastapi import APIRouter, Request
from pydantic import BaseModel
from config import supabase_client
from errors import internal_error
from limiter import limiter

router = APIRouter()


class ResolveIdentifierRequest(BaseModel):
    identifier: str


@router.post("/resolve-identifier")
@limiter.limit("10/minute")
async def resolve_identifier(request: Request, req: ResolveIdentifierRequest):
    """Resolve a username to its account email for the login form.

    Used before a session exists (pre-auth), so this route is public
    (see main.py PUBLIC_PATHS). The lookup previously went through a
    Supabase RPC directly callable by anon clients — that let anyone
    harvest any username's real email address (direct PII disclosure).
    Routing it through this rate-limited endpoint, using the service-role
    client (which bypasses the RPC's now-revoked anon grant), keeps the
    same lookup but bounds how fast it can be enumerated.

    Returns {"email": None} for an unresolved identifier rather than a
    404/400 — the caller falls back to treating the raw identifier as an
    email, and a differentiated response here would itself leak whether a
    username exists.
    """
    identifier = req.identifier.strip()
    if "@" in identifier:
        return {"email": None}
    try:
        result = supabase_client.rpc(
            "get_email_for_username", {"check_username": identifier}
        ).execute()
        return {"email": result.data or None}
    except Exception as e:
        raise internal_error(e)
