"""Configuration and Supabase client initialization."""
from pydantic_settings import BaseSettings
from supabase import create_client, Client


class Settings(BaseSettings):
    """Load environment variables."""

    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    environment: str = "development"

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
