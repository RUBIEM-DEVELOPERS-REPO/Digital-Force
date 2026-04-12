"""
Digital Force — Main FastAPI Application
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from config import get_settings
from database import init_db

# API Routers
from api.auth import router as auth_router
from api.goals import router as goals_router
from api.training import router as training_router
from api.media import router as media_router
from api.stream import router as stream_router
from api.skills import router as skills_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("🚀 Digital Force starting up...")
    await init_db()
    logger.info("✅ Database initialized")

    # Ensure Qdrant collections exist
    try:
        from rag.retriever import ensure_collections
        await ensure_collections()
        logger.info("✅ Qdrant collections ready")
    except Exception as e:
        logger.warning(f"⚠️  Qdrant not available: {e}")

    # Ensure media directories exist
    Path(settings.media_upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.media_processed_dir).mkdir(parents=True, exist_ok=True)
    logger.info("✅ Media directories ready")

    logger.info(f"🧠 LLM: Groq={bool(settings.groq_api_key)} | OpenAI={bool(settings.openai_api_key)}")
    logger.info(f"📡 Publishing: Buffer={bool(settings.buffer_access_token)} | Facebook={bool(settings.facebook_access_token)}")
    logger.info("✨ Digital Force is ready.")

    yield

    logger.info("👋 Digital Force shutting down...")


app = FastAPI(
    title="Digital Force API",
    description="Autonomous Social Media Intelligence Agency",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for media
media_dir = Path(settings.media_upload_dir)
media_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(media_dir)), name="media")

# Routers
app.include_router(auth_router)
app.include_router(goals_router)
app.include_router(training_router)
app.include_router(media_router)
app.include_router(stream_router)
app.include_router(skills_router)


@app.get("/api/health")
async def health():
    return {
        "status": "online",
        "service": "Digital Force",
        "version": "1.0.0",
        "llm": {
            "groq": bool(settings.groq_api_key),
            "openai": bool(settings.openai_api_key),
        },
        "publishing": {
            "buffer": bool(settings.buffer_access_token),
            "facebook": bool(settings.facebook_access_token),
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
