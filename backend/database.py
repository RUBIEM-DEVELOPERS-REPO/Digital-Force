"""
Digital Force — Database Models & Session Management
Full SQLAlchemy async ORM with all core models.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import (
    String, Float, Boolean, Integer, Text, DateTime,
    ForeignKey, JSON, BigInteger, Enum
)
from datetime import datetime
from typing import Optional
import uuid

from config import get_settings


class Base(DeclarativeBase):
    pass


# ═══════════════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════════════

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="operator")  # admin | operator | viewer
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ═══════════════════════════════════════════════════════════
# GOALS — The top-level mission objects
# ═══════════════════════════════════════════════════════════

class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(500))           # Short label
    description: Mapped[str] = mapped_column(Text)            # Full natural language goal
    platforms: Mapped[Optional[str]] = mapped_column(Text, nullable=True)        # JSON list: ["linkedin","facebook","tiktok"]
    assets: Mapped[Optional[str]] = mapped_column(Text, nullable=True)           # JSON list of MediaAsset IDs to use
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    success_metrics: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON: {"followers": 10000}
    constraints: Mapped[Optional[str]] = mapped_column(Text, nullable=True)      # JSON: {"no_weekends": true}
    priority: Mapped[str] = mapped_column(String(20), default="normal")          # low | normal | high | urgent

    # Status lifecycle
    status: Mapped[str] = mapped_column(
        String(50), default="briefing"
    )
    # briefing → planning → awaiting_approval → executing → monitoring → complete | paused | failed

    # The agent's plan (set by Strategist agent)
    plan: Mapped[Optional[str]] = mapped_column(Text, nullable=True)             # JSON structured campaign plan

    # Human approval
    approval_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    approval_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)   # Human feedback
    approved_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Progress tracking
    tasks_total: Mapped[int] = mapped_column(Integer, default=0)
    tasks_completed: Mapped[int] = mapped_column(Integer, default=0)
    tasks_failed: Mapped[int] = mapped_column(Integer, default=0)
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0)
    last_monitor_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    replan_count: Mapped[int] = mapped_column(Integer, default=0)

    # Metadata
    created_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    tasks: Mapped[list["AgentTask"]] = relationship(back_populates="goal", cascade="all, delete-orphan")
    logs: Mapped[list["AgentLog"]] = relationship(back_populates="goal", cascade="all, delete-orphan")


# ═══════════════════════════════════════════════════════════
# AGENT TASKS — Atomic units of work the agents execute
# ═══════════════════════════════════════════════════════════

class AgentTask(Base):
    __tablename__ = "agent_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    goal_id: Mapped[str] = mapped_column(String(36), ForeignKey("goals.id"), index=True)

    # Task identity
    task_type: Mapped[str] = mapped_column(String(100))
    # generate_content | post_content | research | analyze | notify | forge_skill | monitor | adapt_asset
    agent: Mapped[str] = mapped_column(String(100))
    # orchestrator | strategist | researcher | content_director | visual_designer | publisher | skillforge | monitor
    description: Mapped[str] = mapped_column(Text)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)        # Why the agent chose this task

    # Tool execution
    tool_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tool_params: Mapped[Optional[str]] = mapped_column(Text, nullable=True)      # JSON
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)           # JSON output
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Scheduling — agent decides these
    depends_on: Mapped[Optional[str]] = mapped_column(Text, nullable=True)       # JSON list of task IDs
    scheduled_for: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    platform: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # target platform

    # Status
    status: Mapped[str] = mapped_column(String(50), default="pending_approval")
    # pending_approval | approved | queued | executing | done | failed | skipped | cancelled
    priority: Mapped[int] = mapped_column(Integer, default=5)   # 1=highest, 10=lowest
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)

    # Timing
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    goal: Mapped["Goal"] = relationship(back_populates="tasks")


# ═══════════════════════════════════════════════════════════
# AGENT LOGS — Full transparency of agent thinking
# ═══════════════════════════════════════════════════════════

class AgentLog(Base):
    __tablename__ = "agent_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    goal_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("goals.id"), nullable=True, index=True)
    task_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("agent_tasks.id"), nullable=True)
    agent: Mapped[str] = mapped_column(String(100))          # Which agent
    level: Mapped[str] = mapped_column(String(20), default="info")  # info | thinking | action | error | success
    thought: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Agent reasoning
    action: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    observation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Tool output / result
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    goal: Mapped[Optional["Goal"]] = relationship(back_populates="logs")


# ═══════════════════════════════════════════════════════════
# GENERATED SKILLS — SkillForge output
# ═══════════════════════════════════════════════════════════

class GeneratedSkill(Base):
    __tablename__ = "generated_skills"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)     # Python function name
    display_name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    code: Mapped[str] = mapped_column(Text)                  # The actual Python function
    input_schema: Mapped[Optional[str]] = mapped_column(Text, nullable=True)    # JSON schema
    output_schema: Mapped[Optional[str]] = mapped_column(Text, nullable=True)   # JSON schema
    sandbox_test_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # E2B test output
    test_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by_goal_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_execution_ms: Mapped[float] = mapped_column(Float, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


# ═══════════════════════════════════════════════════════════
# MEDIA ASSETS — Media library
# ═══════════════════════════════════════════════════════════

class MediaAsset(Base):
    __tablename__ = "media_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename: Mapped[str] = mapped_column(String(500))
    original_filename: Mapped[str] = mapped_column(String(500))
    file_path: Mapped[str] = mapped_column(String(1000))
    public_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    mime_type: Mapped[str] = mapped_column(String(100))
    asset_type: Mapped[str] = mapped_column(String(50))  # image | video | audio | pdf | document

    # Media dimensions
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # AI-generated metadata
    auto_tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)        # JSON list of tags
    ai_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)   # GPT-4o Vision description
    platform_suitability: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON {"linkedin": 0.9}
    dominant_colors: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Manual metadata
    manual_tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    alt_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    campaign_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # Qdrant embedding
    embedding_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Qdrant point ID

    # Usage tracking
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    uploaded_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ═══════════════════════════════════════════════════════════
# KNOWLEDGE ITEMS — RAG training data
# ═══════════════════════════════════════════════════════════

class KnowledgeItem(Base):
    __tablename__ = "knowledge_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(500))
    source_type: Mapped[str] = mapped_column(String(50))
    # pdf | url | image | video | audio | csv | text | docx | youtube

    source_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)  # file path or URL
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Parsed content
    raw_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # AI-generated summary

    # Vector storage
    qdrant_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)       # JSON list of point IDs
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)

    # Categorization
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # brand_voice | product_info | competitor | market_research | content_examples | other
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)             # JSON list

    # Processing state
    processing_status: Mapped[str] = mapped_column(String(50), default="pending")
    # pending | processing | indexed | failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    uploaded_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ═══════════════════════════════════════════════════════════
# PUBLISHED POSTS — Record of all posts sent to platforms
# ═══════════════════════════════════════════════════════════

class PublishedPost(Base):
    __tablename__ = "published_posts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    goal_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("goals.id"), nullable=True)
    task_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("agent_tasks.id"), nullable=True)

    # Content
    caption: Mapped[str] = mapped_column(Text)
    hook: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hashtags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)     # JSON list
    cta: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    media_asset_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list

    # Platform
    platform: Mapped[str] = mapped_column(String(50))  # linkedin | facebook | twitter | tiktok | instagram
    platform_post_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    platform_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    publisher: Mapped[str] = mapped_column(String(50), default="buffer")  # buffer | facebook_graph

    # Status
    status: Mapped[str] = mapped_column(String(50), default="queued")
    # queued | published | failed | deleted
    scheduled_for: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Analytics snapshot (updated by Monitor agent)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    reach: Mapped[int] = mapped_column(Integer, default=0)
    engagement_rate: Mapped[float] = mapped_column(Float, default=0.0)
    analytics_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ═══════════════════════════════════════════════════════════
# PLATFORM CONNECTIONS
# ═══════════════════════════════════════════════════════════

class PlatformConnection(Base):
    __tablename__ = "platform_connections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    platform: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(200))
    account_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    account_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Encrypted credentials
    access_token_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refresh_token_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    api_key_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra_config: Mapped[Optional[str]] = mapped_column(Text, nullable=True)     # JSON for platform-specific

    # Status
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    connection_status: Mapped[str] = mapped_column(String(50), default="disconnected")
    # connected | disconnected | error | token_expired
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Publishing config
    posts_per_day_limit: Mapped[int] = mapped_column(Integer, default=10)
    preferred_post_times: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ═══════════════════════════════════════════════════════════
# NOTIFICATIONS
# ═══════════════════════════════════════════════════════════

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    goal_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    type: Mapped[str] = mapped_column(String(50))
    # plan_ready | milestone | goal_complete | goal_failed | replan_needed | skill_created
    title: Mapped[str] = mapped_column(String(500))
    message: Mapped[str] = mapped_column(Text)
    action_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_via_email: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ═══════════════════════════════════════════════════════════
# DATABASE ENGINE
# ═══════════════════════════════════════════════════════════

settings = get_settings()
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """Create all tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """FastAPI dependency: yields an async DB session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
