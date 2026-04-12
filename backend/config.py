"""
Digital Force — Central Configuration
All environment variables, loaded once, cached globally.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
from typing import Optional
import os


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────
    app_name: str = "Digital Force"
    app_version: str = "1.0.0"
    environment: str = "development"  # development | staging | production
    debug: bool = True
    base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    # ── Security ─────────────────────────────────────────
    jwt_secret_key: str = "CHANGE-THIS-IN-PRODUCTION-USE-256-BIT-KEY"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 1440   # 24 hours
    encryption_key: str = "CHANGE-THIS-32-BYTE-KEY-IN-PROD!!"

    # ── Database ─────────────────────────────────────────
    # PostgreSQL for production, SQLite for dev
    database_url: str = "sqlite+aiosqlite:///./digitalforce.db"
    # PostgreSQL example:
    # database_url: str = "postgresql+asyncpg://user:pass@localhost:5432/digitalforce"

    # ── Redis ─────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    redis_password: Optional[str] = None

    # ── Primary LLM: Groq ─────────────────────────────────
    groq_api_key: str = ""
    groq_primary_model: str = "llama-3.3-70b-versatile"
    groq_fast_model: str = "llama-3.1-8b-instant"
    groq_max_tokens: int = 4096
    groq_temperature: float = 0.7

    # ── Reasoning LLM: OpenAI ─────────────────────────────
    openai_api_key: str = ""
    openai_reasoning_model: str = "gpt-4o"      # Complex strategy + vision
    openai_fast_model: str = "gpt-4o-mini"      # Quick tasks

    # ── Vector DB: Qdrant ─────────────────────────────────
    qdrant_url: str = ""                          # Cloud: https://xxx.qdrant.io
    qdrant_api_key: str = ""
    qdrant_local_path: str = "./qdrant_data"     # Local fallback
    # Collections
    qdrant_knowledge_collection: str = "df-knowledge"
    qdrant_media_collection: str = "df-media"
    qdrant_brand_collection: str = "df-brand"
    qdrant_dimension: int = 384                  # all-MiniLM-L6-v2

    # ── Publishing: Buffer API ────────────────────────────
    buffer_access_token: str = ""
    buffer_api_url: str = "https://api.bufferapp.com/1"

    # ── Publishing: Facebook Graph API ───────────────────
    facebook_page_id: str = ""
    facebook_access_token: str = ""
    facebook_api_version: str = "v21.0"

    # ── Image Generation ──────────────────────────────────
    # DALL-E 3 via OpenAI (openai_api_key above)
    stability_api_key: str = ""               # Stable Diffusion alternative

    # ── Image Storage ─────────────────────────────────────
    # Local storage (default) or S3/R2
    storage_backend: str = "local"           # local | s3 | r2
    media_upload_dir: str = "./media/uploads"
    media_processed_dir: str = "./media/processed"
    s3_bucket: str = ""
    s3_region: str = "us-east-1"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    r2_account_id: str = ""
    r2_access_key: str = ""
    r2_secret_key: str = ""
    r2_bucket: str = ""

    # ── Email (for approval notifications) ───────────────
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_name: str = "Digital Force"
    smtp_from_email: str = ""

    # ── SkillForge (E2B Sandbox) ──────────────────────────
    e2b_api_key: str = ""
    skillforge_enabled: bool = True

    # ── Web Research ──────────────────────────────────────
    brave_search_api_key: str = ""            # Brave Search API
    serpapi_key: str = ""                     # SerpAPI alternative

    # ── Agent Configuration ───────────────────────────────
    agent_max_iterations: int = 10
    agent_timeout_seconds: int = 300
    approval_token_expires_hours: int = 48

    # ── CORS ─────────────────────────────────────────────
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def qdrant_use_cloud(self) -> bool:
        return bool(self.qdrant_url and self.qdrant_api_key)

    class Config:
        env_file = os.path.join(os.path.dirname(__file__), "..", ".env")
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton — loaded once at startup."""
    return Settings()
