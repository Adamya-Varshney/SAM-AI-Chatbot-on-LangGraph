import re
from pydantic import field_validator
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    supabase_url: str
    supabase_anon_key: str
    supabase_jwt_secret: str = ""
    supabase_db_url: str

    @field_validator("supabase_db_url")
    @classmethod
    def strip_bracketed_host(cls, v: str) -> str:
        """Supabase wraps the hostname in IPv6-style brackets that
        Python 3.12's stricter urlparse rejects."""
        return re.sub(r"@\[([^\]]+)\]:", r"@\1:", v)

    openai_api_key: str
    tavily_api_key: str = ""

    google_client_id: str = ""
    google_client_secret: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""

    encryption_key: str = ""

    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
