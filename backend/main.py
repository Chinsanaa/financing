"""FastAPI backend for financing SaaS - multi-tenant transaction classification."""
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import jwt
from typing import Optional

from config import settings

# Initialize routers (will be imported below)
from routes import auth, categories, uploads, training, classify, dashboard

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

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://financing.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Auth Middleware ---
class AuthMiddleware:
    """Extract and validate JWT from Authorization header.

    Populates request.state.user_id if valid, otherwise raises 401.
    Uses Supabase JWT_SECRET to decode (backend validates token structure,
    RLS policies in Postgres enforce data access).
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, request: Request, call_next):
        # Skip auth for health check and public routes
        if request.url.path in ["/health", "/docs", "/openapi.json"]:
            return await call_next(request)

        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        user_id = None

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                # Decode JWT using Supabase secret
                payload = jwt.decode(
                    token,
                    settings.supabase_jwt_secret,
                    algorithms=["HS256"]
                )
                user_id = payload.get("sub")
            except jwt.InvalidTokenError as e:
                return JSONResponse(
                    {"detail": f"Invalid token: {e}"},
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


# Add auth middleware (before route handlers)
app.add_middleware(AuthMiddleware)


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
