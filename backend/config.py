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
supabase_client: Client = create_client(
    settings.supabase_url,
    settings.supabase_service_role_key
)
