"""Authentication routes: signup, login, logout."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from config import supabase_client

router = APIRouter()


class SignupRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/signup")
async def signup(req: SignupRequest):
    """Create a new user account.

    Supabase auth.users entry triggers on_auth_user_created() which:
    1. Inserts into profiles table (user_id)
    2. Triggers initialize_default_categories() to create 7 default categories
    3. Triggers create budget_config entry
    """
    try:
        user = supabase_client.auth.sign_up(
            email=req.email,
            password=req.password
        )
        return {
            "user_id": user.user.id,
            "email": user.user.email,
            "message": "Signup successful. Check your email for verification."
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
async def login(req: LoginRequest):
    """Authenticate user and return access token."""
    try:
        response = supabase_client.auth.sign_in_with_password(
            email=req.email,
            password=req.password
        )
        return {
            "user_id": response.user.id,
            "email": response.user.email,
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/logout")
async def logout(request: Request):
    """Sign out the current user."""
    user_id = request.state.user_id
    try:
        supabase_client.auth.sign_out()
        return {"message": "Logged out successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/refresh")
async def refresh_token(request: Request):
    """Refresh the access token using the refresh token."""
    # Typically handled client-side with Supabase SDK, but exposed here for flexibility
    return {"message": "Token refresh not yet implemented"}
