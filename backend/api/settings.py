"""
Digital Force — Settings API
Read and write application configuration at runtime.
Persists overrides to settings_override.json.
"""

import json
import logging
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/settings", tags=["settings"])

SETTINGS_FILE = Path(__file__).parent.parent / "settings_override.json"


def _load_overrides() -> dict:
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text())
        except Exception:
            return {}
    return {}


def _save_overrides(data: dict):
    SETTINGS_FILE.write_text(json.dumps(data, indent=2))


class SettingsUpdate(BaseModel):
    # General
    app_name: Optional[str] = None
    frontend_url: Optional[str] = None
    environment: Optional[str] = None
    cors_origins: Optional[str] = None

    # LLM
    groq_api_key_1: Optional[str] = None
    groq_api_key_2: Optional[str] = None
    groq_api_key_3: Optional[str] = None
    groq_primary_model: Optional[str] = None
    groq_secondary_model: Optional[str] = None
    groq_fallback_model: Optional[str] = None

    # Publishing
    buffer_access_token: Optional[str] = None
    facebook_page_id: Optional[str] = None
    facebook_access_token: Optional[str] = None

    # Qdrant
    qdrant_url: Optional[str] = None
    qdrant_api_key: Optional[str] = None

    # Email
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_name: Optional[str] = None
    smtp_from_email: Optional[str] = None
    target_notification_emails: Optional[str] = None

    # Agent
    agent_max_iterations: Optional[int] = None
    agent_timeout_seconds: Optional[int] = None

    # Storage
    storage_backend: Optional[str] = None
    s3_bucket: Optional[str] = None
    s3_region: Optional[str] = None


MASKED_KEYS = {
    "groq_api_key_1", "groq_api_key_2", "groq_api_key_3", "buffer_access_token",
    "facebook_access_token", "qdrant_api_key", "smtp_password",
    "s3_access_key", "s3_secret_key", "r2_access_key", "r2_secret_key",
    "encryption_key", "jwt_secret_key",
}


def _mask(key: str, value: str) -> str:
    if not value:
        return ""
    if key in MASKED_KEYS and len(value) > 8:
        return value[:4] + "•" * (len(value) - 8) + value[-4:]
    return value


@router.get("")
async def get_settings(user: dict = Depends(get_current_user)):
    """Return current effective settings (with secrets masked)."""
    from config import get_settings as _get_settings
    s = _get_settings()
    overrides = _load_overrides()

    raw = {
        "app_name": s.app_name,
        "environment": s.environment,
        "frontend_url": s.frontend_url,
        "cors_origins": s.cors_origins,
        "debug": s.debug,

        # LLM
        "groq_api_key_1": s.groq_api_key_1,
        "groq_api_key_2": s.groq_api_key_2,
        "groq_api_key_3": s.groq_api_key_3,
        "groq_primary_model": s.groq_primary_model,
        "groq_secondary_model": s.groq_secondary_model,
        "groq_fallback_model": s.groq_fallback_model,

        # Publishing
        "buffer_access_token": s.buffer_access_token,
        "facebook_page_id": s.facebook_page_id,
        "facebook_access_token": s.facebook_access_token,

        # Qdrant
        "qdrant_url": s.qdrant_url,
        "qdrant_api_key": s.qdrant_api_key,
        "qdrant_local_path": s.qdrant_local_path,

        # Email
        "smtp_host": s.smtp_host,
        "smtp_port": s.smtp_port,
        "smtp_username": s.smtp_username,
        "smtp_password": s.smtp_password,
        "smtp_from_name": s.smtp_from_name,
        "smtp_from_email": s.smtp_from_email,
        "target_notification_emails": s.target_notification_emails,

        # Agent
        "agent_max_iterations": s.agent_max_iterations,
        "agent_timeout_seconds": s.agent_timeout_seconds,

        # Storage
        "storage_backend": s.storage_backend,
        "media_upload_dir": s.media_upload_dir,

        # Overrides applied indicator
        "_has_overrides": bool(overrides),
        "_override_keys": list(overrides.keys()),
    }

    # Apply overrides
    raw.update({k: v for k, v in overrides.items() if k in raw})

    # Mask secrets for response
    masked = {k: (_mask(k, str(v)) if isinstance(v, str) else v) for k, v in raw.items()}
    return masked


@router.put("")
async def update_settings(
    body: SettingsUpdate,
    user: dict = Depends(get_current_user),
):
    """Persist setting overrides to settings_override.json."""
    if user.get("role") not in ("admin", "operator", None):
        raise HTTPException(403, "Only admins can update settings")

    overrides = _load_overrides()
    updates = {k: v for k, v in body.model_dump().items() if v is not None}

    if not updates:
        raise HTTPException(400, "No settings provided to update")

    overrides.update(updates)
    _save_overrides(overrides)

    logger.info(f"[Settings] Updated {list(updates.keys())} by user {user.get('sub')}")
    return {
        "status": "saved",
        "updated_keys": list(updates.keys()),
        "message": "Settings saved. Restart the backend to apply LLM/DB changes.",
    }


@router.delete("/overrides")
async def reset_overrides(user: dict = Depends(get_current_user)):
    """Remove all setting overrides and revert to .env defaults."""
    if SETTINGS_FILE.exists():
        SETTINGS_FILE.unlink()
    return {"status": "reset", "message": "All overrides cleared. Using .env defaults."}


@router.get("/status")
async def settings_status(user: dict = Depends(get_current_user)):
    """Quick check of which integrations are configured."""
    from config import get_settings as _get_settings
    s = _get_settings()
    overrides = _load_overrides()

    def is_set(key: str) -> bool:
        val = overrides.get(key) or getattr(s, key, "")
        return bool(val and str(val).strip())

    return {
        "llm": {
            "groq_1": is_set("groq_api_key_1"),
            "groq_2": is_set("groq_api_key_2"),
            "groq_3": is_set("groq_api_key_3"),
        },
        "publishing": {
            "buffer": is_set("buffer_access_token"),
            "facebook": is_set("facebook_access_token") and is_set("facebook_page_id"),
        },
        "vector_db": {
            "qdrant_cloud": is_set("qdrant_url") and is_set("qdrant_api_key"),
            "qdrant_local": True,  # always available
        },
        "email": {
            "smtp": is_set("smtp_username") and is_set("smtp_password"),
        },
        "storage": {
            "backend": s.storage_backend,
            "s3": is_set("s3_bucket"),
        },
    }
