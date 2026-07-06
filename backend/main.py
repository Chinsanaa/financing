"""FastAPI backend for financing SaaS - multi-tenant transaction classification."""
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
import jwt
from typing import Optional
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import settings

# Initialize routers (will be imported below)
from routes import auth, categories, uploads, training, classify, dashboard, settings as settings_router

# --- Startup / Shutdown ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """App startup and shutdown."""
    print("Starting Financing Backend API...")
    yield
    print("Shutting down Financing Backend API...")


# --- FastAPI App ---
app = FastAPI(
    title="Financing SaaS Backend",
    description="Multi-tenant transaction classification API",
    version="0.1.0",
    lifespan=lifespan,
)

# --- Rate Limiting ---
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later."}
    )


# --- Auth Middleware ---
# Must subclass BaseHTTPMiddleware: app.add_middleware() invokes the class as
# raw ASGI (scope, receive, send); a plain (request, call_next) __call__
# raises TypeError on every request, turning the whole API into 500s.
class AuthMiddleware(BaseHTTPMiddleware):
    """Extract and validate JWT from Authorization header.

    Populates request.state.user_id if valid, otherwise returns 401.
    Uses Supabase JWT_SECRET to decode; every route handler additionally
    scopes queries by user_id (the service-role client bypasses RLS).
    """

    PUBLIC_PATHS = frozenset({
        "/", "/health", "/docs", "/redoc", "/openapi.json",
        "/auth/signup", "/auth/login", "/auth/refresh",
    })

    async def dispatch(self, request: Request, call_next):
        # Skip auth for health check, docs, and public auth routes
        # (signup/login/refresh happen before a user has a token to send).
        # CORS preflights carry no Authorization header either.
        if request.url.path in self.PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        user_id = None

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = jwt.decode(
                    token,
                    settings.supabase_jwt_secret,
                    algorithms=["HS256"],
                    audience="authenticated",
                    options={"require": ["sub", "exp"]},
                )
                user_id = payload.get("sub")
            except jwt.InvalidTokenError:
                return JSONResponse(
                    {"detail": "Invalid or expired token"},
                    status_code=401
                )

        if not user_id:
            return JSONResponse(
                {"detail": "Missing or invalid Authorization header"},
                status_code=401
            )

        # Attach user_id to request state for downstream handlers
        request.state.user_id = user_id
        return await call_next(request)


# Middleware registration is LIFO (last added = outermost). CORS must be
# added AFTER auth so it wraps auth responses — otherwise 401s from the auth
# layer would be missing CORS headers and surface as opaque CORS errors in
# the browser instead of readable 401s.
app.add_middleware(AuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://financing.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Health Check ---
@app.get("/health")
def health_check():
    """Health check endpoint (no auth required)."""
    return {"status": "ok"}


# --- Include Route Groups ---
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(categories.router, prefix="/categories", tags=["categories"])
app.include_router(uploads.router, prefix="/uploads", tags=["uploads"])
app.include_router(training.router, prefix="/training", tags=["training"])
app.include_router(classify.router, prefix="/classify", tags=["classify"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(settings_router.router, prefix="/settings", tags=["settings"])


# --- Root ---
@app.get("/")
def root():
    return {
        "message": "Financing SaaS API",
        "version": "0.1.0",
        "environment": settings.environment,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development",
    )
