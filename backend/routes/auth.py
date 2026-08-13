"""Authentication routes: signup, login, logout.

The frontend can also talk to Supabase Auth directly (supabase-js); these
endpoints exist for non-browser clients and add IP rate limiting.
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from config import supabase_client
from errors import internal_error
from limiter import limiter

router = APIRouter()


class SignupRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ResolveIdentifierRequest(BaseModel):
    identifier: str


@router.post("/signup")
@limiter.limit("5/hour")
async def signup(request: Request, req: SignupRequest):
    """Create a new user account.

    Supabase auth.users entry triggers on_auth_user_created() which:
    1. Inserts into profiles table
    2. Triggers initialize_default_categories() to create 7 default categories
    3. Creates the budget_config entry
    """
    try:
        # gotrue takes a single credentials dict — keyword args raise TypeError
        user = supabase_client.auth.sign_up({
            "email": req.email,
            "password": req.password,
        })
        return {
            "user_id": user.user.id,
            "email": user.user.email,
            "message": "Signup successful. Check your email for verification."
        }
    except HTTPException:
        raise
    except Exception as e:
        # Auth error messages (already registered, weak password) are
        # user-facing by design — relay them.
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
@limiter.limit("10/15 minutes")
async def login(request: Request, req: LoginRequest):
    """Authenticate user and return access token."""
    try:
        response = supabase_client.auth.sign_in_with_password({
            "email": req.email,
            "password": req.password,
        })
        return {
            "user_id": response.user.id,
            "email": response.user.email,
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid email or password")


@router.post("/logout")
async def logout(request: Request):
    """Acknowledge logout.

    Sessions are stateless JWTs validated per-request; the client discards
    its tokens (supabase-js signOut). Nothing to revoke on the shared
    service-role client — calling auth.sign_out() on it was a no-op bug.
    """
    return {"message": "Logged out successfully"}


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
