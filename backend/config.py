"""Configuration and Supabase client initialization."""
from pydantic_settings import BaseSettings
from supabase import create_client, Client


class Settings(BaseSettings):
    """Load environment variables."""

    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    environment: str = "development"
    # Optional: enables the LLM fallback classification tier (src/llm_classify.py).
    # Groq's free-tier inference API (open model, no cost) — not a paid
    # provider. Unset in dev/test just means that tier is skipped, same as
    # having no trained model — rows stay in the review queue with no
    # suggestion.
    groq_api_key: str | None = None
    # Optional: enables budget-alert emails (backend/email.py). Unset in
    # dev/test just means send_alert_email() no-ops — the in-app bell/action
    # items still work either way, since they don't depend on email.
    resend_api_key: str | None = None

    class Config:
        env_file = ".env"


# Global settings instance
settings = Settings()

# Initialize Supabase client (for backend use with service role key)
#
# SECURITY INVARIANT: this client uses the service-role key, which bypasses
# Row Level Security on every table. There is no database-level safety net
# scoping queries to a user. Every query against a user-data table MUST
# include `.eq("user_id", request.state.user_id)` (or equivalent) explicitly
# in application code — omitting it returns/mutates every user's rows, not
# just the caller's. All current routes do this correctly; keep it that way
# for any new one.
supabase_client: Client = create_client(
    settings.supabase_url,
    settings.supabase_service_role_key
)
