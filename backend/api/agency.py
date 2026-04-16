"""
Digital Force — Agency Autonomous Mode API
Endpoints for managing the 24/7 agency daemon settings per user:
  - Toggle autonomous mode
  - Set timezone
  - Manage brief slots (add/update/delete, with recurrence)
  - View daemon status
"""

import json
import uuid
import logging
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from database import get_db, AgencySettings
from auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agency", tags=["agency"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class BriefSlot(BaseModel):
    id: Optional[str] = None
    label: str                            # e.g. "Morning Brief", "Board Meeting Prep"
    time: str                             # "HH:MM" in user's local timezone
    recurrence: str                       # "daily" | "weekdays" | "weekly" | "once"
    date: Optional[str] = None            # "YYYY-MM-DD" — only used when recurrence=="once"


class AgencySettingsUpdate(BaseModel):
    autonomous_mode: Optional[bool] = None
    timezone: Optional[str] = None
    industry: Optional[str] = None
    brand_voice: Optional[str] = None
    agent_tone: Optional[str] = None
    brief_slots: Optional[List[BriefSlot]] = None


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _get_or_create_settings(user_id: str, db: AsyncSession) -> AgencySettings:
    result = await db.execute(select(AgencySettings).where(AgencySettings.user_id == user_id))
    cfg = result.scalar_one_or_none()
    if not cfg:
        cfg = AgencySettings(
            id=str(uuid.uuid4()),
            user_id=user_id,
            autonomous_mode=False,
            timezone="UTC",
            brief_slots="[]",
        )
        db.add(cfg)
        await db.flush()
    return cfg


def _serialize(cfg: AgencySettings) -> dict:
    return {
        "autonomous_mode": cfg.autonomous_mode,
        "timezone": cfg.timezone,
        "industry": cfg.industry,
        "brand_voice": cfg.brand_voice,
        "agent_tone": cfg.agent_tone,
        "brief_slots": json.loads(cfg.brief_slots or "[]"),
        "daemon_last_ran": cfg.daemon_last_ran.isoformat() if cfg.daemon_last_ran else None,
        "last_brief_sent": cfg.last_brief_sent.isoformat() if cfg.last_brief_sent else None,
        "last_proactive_research": cfg.last_proactive_research.isoformat() if cfg.last_proactive_research else None,
        "updated_at": cfg.updated_at.isoformat() if cfg.updated_at else None,
    }


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("")
async def get_agency_settings(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get the current user's autonomous agency settings."""
    user_id = user.get("sub")
    cfg = await _get_or_create_settings(user_id, db)
    await db.commit()
    return _serialize(cfg)


@router.put("")
async def update_agency_settings(
    body: AgencySettingsUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Update autonomous mode, timezone, industry context, or brief slots."""
    user_id = user.get("sub")
    cfg = await _get_or_create_settings(user_id, db)

    if body.autonomous_mode is not None:
        cfg.autonomous_mode = body.autonomous_mode
        logger.info(f"[Agency] Autonomous mode {'ON' if body.autonomous_mode else 'OFF'} for {user_id}")

    if body.timezone is not None:
        # Basic sanity check on timezone string
        try:
            import pytz
            pytz.timezone(body.timezone)
            cfg.timezone = body.timezone
        except Exception:
            raise HTTPException(400, f"Invalid timezone: {body.timezone}")

    if body.industry is not None:
        cfg.industry = body.industry

    if body.brand_voice is not None:
        cfg.brand_voice = body.brand_voice

    if body.agent_tone is not None:
        cfg.agent_tone = body.agent_tone

    if body.brief_slots is not None:
        slots = []
        for slot in body.brief_slots:
            # Validate
            if slot.recurrence not in ("daily", "weekdays", "weekly", "once"):
                raise HTTPException(400, f"Invalid recurrence: {slot.recurrence}")
            if slot.recurrence == "once" and not slot.date:
                raise HTTPException(400, "Date required for 'once' recurrence")
            try:
                h, m = slot.time.split(":")
                assert 0 <= int(h) <= 23 and 0 <= int(m) <= 59
            except Exception:
                raise HTTPException(400, f"Invalid time format: {slot.time} (use HH:MM)")

            slots.append({
                "id": slot.id or str(uuid.uuid4()),
                "label": slot.label,
                "time": slot.time,
                "recurrence": slot.recurrence,
                "date": slot.date,
            })
        cfg.brief_slots = json.dumps(slots)

    cfg.updated_at = datetime.utcnow()
    await db.commit()

    return {
        "status": "saved",
        **_serialize(cfg),
    }


@router.post("/briefs")
async def add_brief_slot(
    slot: BriefSlot,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Add a single new brief slot."""
    user_id = user.get("sub")
    cfg = await _get_or_create_settings(user_id, db)

    slots = json.loads(cfg.brief_slots or "[]")
    new_slot = {
        "id": str(uuid.uuid4()),
        "label": slot.label,
        "time": slot.time,
        "recurrence": slot.recurrence,
        "date": slot.date,
    }
    slots.append(new_slot)
    cfg.brief_slots = json.dumps(slots)
    cfg.updated_at = datetime.utcnow()
    await db.commit()

    return {"status": "added", "slot": new_slot, "all_slots": slots}


@router.delete("/briefs/{slot_id}")
async def delete_brief_slot(
    slot_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Remove a brief slot by ID."""
    user_id = user.get("sub")
    cfg = await _get_or_create_settings(user_id, db)

    slots = json.loads(cfg.brief_slots or "[]")
    before = len(slots)
    slots = [s for s in slots if s.get("id") != slot_id]

    if len(slots) == before:
        raise HTTPException(404, "Brief slot not found")

    cfg.brief_slots = json.dumps(slots)
    cfg.updated_at = datetime.utcnow()
    await db.commit()

    return {"status": "deleted", "all_slots": slots}


@router.get("/status")
async def agency_status(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Return live daemon status for this user."""
    from database import Goal as GoalModel
    user_id = user.get("sub")

    cfg = await _get_or_create_settings(user_id, db)
    await db.commit()

    # Active goals
    result = await db.execute(
        select(GoalModel).where(
            GoalModel.created_by == user_id,
            GoalModel.status.in_(["planning", "executing", "awaiting_approval", "monitoring"])
        )
    )
    active_goals = result.scalars().all()

    return {
        "autonomous_mode": cfg.autonomous_mode,
        "daemon_last_ran": cfg.daemon_last_ran.isoformat() if cfg.daemon_last_ran else None,
        "last_brief_sent": cfg.last_brief_sent.isoformat() if cfg.last_brief_sent else None,
        "last_proactive_research": cfg.last_proactive_research.isoformat() if cfg.last_proactive_research else None,
        "active_goals": len(active_goals),
        "active_goal_titles": [g.title for g in active_goals],
    }


@router.post("/trigger-research")
async def trigger_proactive_research(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Manually trigger a proactive research cycle right now."""
    import asyncio
    user_id = user.get("sub")
    cfg = await _get_or_create_settings(user_id, db)

    from agent.agency_daemon import _run_proactive_research
    asyncio.create_task(_run_proactive_research(user_id, cfg, datetime.utcnow()))

    return {"status": "triggered", "message": "Research cycle started — results will appear in your chat shortly."}
