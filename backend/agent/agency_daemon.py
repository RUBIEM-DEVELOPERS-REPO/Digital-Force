"""
Digital Force — Agency Daemon
The 24/7 autonomous heartbeat of the entire agency.

Starts on server boot, runs every 5 minutes forever.
Never needs a user to trigger it. It drives:
  - Executing pending/stalled goals
  - Monitoring active campaigns
  - Proactive trend research (every 2hrs, autonomous mode users only)
  - Scheduled briefings (daily/weekdays/weekly/once, per user config)
  - Idle detection + opportunity reports when nothing is running
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# ─── Intervals ────────────────────────────────────────────────────────────────
DAEMON_CYCLE_SECONDS   = 300   # 5 minutes between full cycles
PROACTIVE_RESEARCH_HRS = 2     # Research every 2 hours per user
IDLE_THRESHOLD_HRS     = 24    # Push opportunity report if no activity for 24h


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN DAEMON LOOP
# ═══════════════════════════════════════════════════════════════════════════════

async def agency_daemon():
    """
    Entry point — called from main.py lifespan as asyncio.create_task().
    Runs indefinitely, cycling every DAEMON_CYCLE_SECONDS.
    """
    logger.info("🤖 Agency Daemon started — Digital Force is now autonomous")

    # Small startup delay so DB is fully ready
    await asyncio.sleep(10)

    while True:
        try:
            await _run_cycle()
        except Exception as e:
            logger.error(f"[Daemon] Unhandled cycle error: {e}", exc_info=True)

        await asyncio.sleep(DAEMON_CYCLE_SECONDS)


# ═══════════════════════════════════════════════════════════════════════════════
# ONE CYCLE
# ═══════════════════════════════════════════════════════════════════════════════

async def _run_cycle():
    """One full agency daemon cycle."""
    from database import async_session, AgencySettings, Goal, User
    from sqlalchemy import select

    logger.info("[Daemon] ── Starting cycle ──")
    now = datetime.utcnow()

    # ── Phase 1: Process ALL goals regardless of autonomous mode ─────────────
    await _phase_execute_goals(now)
    await _phase_retry_failed_posts(now)

    # ── Phase 2: Process autonomous-mode users ───────────────────────────────
    async with async_session() as session:
        result = await session.execute(
            select(AgencySettings).where(AgencySettings.autonomous_mode == True)
        )
        all_settings = result.scalars().all()

    for agency_cfg in all_settings:
        try:
            await _process_user(agency_cfg, now)
            # Update daemon_last_ran
            async with async_session() as session:
                cfg = await session.get(AgencySettings, agency_cfg.id)
                if cfg:
                    cfg.daemon_last_ran = now
                    await session.commit()
        except Exception as e:
            logger.error(f"[Daemon] Error processing user {agency_cfg.user_id}: {e}")

    logger.info("[Daemon] ── Cycle complete ──")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1 — EXECUTE GOALS
# ═══════════════════════════════════════════════════════════════════════════════

async def _phase_execute_goals(now: datetime):
    """
    Pick up goals that need agent work and fire their graphs.
    Works for ALL users — no autonomous mode required.
    """
    from database import async_session, Goal
    from sqlalchemy import select

    async with async_session() as session:
        result = await session.execute(
            select(Goal).where(
                Goal.status.in_(["planning", "executing", "awaiting_approval"])
            )
        )
        goals = result.scalars().all()

    for goal in goals:
        try:
            if goal.status == "planning":
                # Stuck in planning? Check if it's been >10min with no plan
                age = (now - goal.created_at).total_seconds()
                if age > 600 and not goal.plan:
                    logger.info(f"[Daemon] Goal {goal.id} stuck in planning >10min — retrying")
                    await _retry_planning(goal)

            elif goal.status == "awaiting_approval":
                # Nudge user if they haven't approved in >1hr
                if goal.updated_at and (now - goal.updated_at).total_seconds() > 3600:
                    await _nudge_approval(goal, now)

            elif goal.status == "executing":
                # Still executing but looks stalled? Monitor it
                if goal.updated_at and (now - goal.updated_at).total_seconds() > 900:
                    logger.info(f"[Daemon] Goal {goal.id} executing for >15min — pushing status")
                    await _push_execution_status(goal)

        except Exception as e:
            logger.error(f"[Daemon] Error handling goal {goal.id}: {e}")


async def _retry_planning(goal):
    """Re-trigger planning for a stuck goal."""
    import json as _json
    from api.goals import run_planning_agent

    initial_state = {
        "goal_id": goal.id,
        "goal_description": goal.description,
        "created_by": goal.created_by,
        "platforms": _json.loads(goal.platforms or "[]"),
        "deadline": None, "asset_ids": [], "success_metrics": {}, "constraints": {},
        "messages": [], "research_findings": {}, "campaign_plan": {}, "tasks": [],
        "completed_task_ids": [], "failed_task_ids": [], "kpi_snapshot": {},
        "needs_replan": False, "approval_status": "pending", "human_feedback": None,
        "new_skills_created": [], "next_agent": None, "error": None,
        "iteration_count": 0, "replan_count": 0, "current_task_id": None,
    }
    asyncio.create_task(run_planning_agent(goal.id, goal.description, initial_state))


async def _nudge_approval(goal, now: datetime):
    """Remind user that a plan is waiting for their approval."""
    from agent.chat_push import chat_push
    from database import async_session, Goal
    from sqlalchemy import select

    # Only nudge once per hour max
    last_nudge_key = f"nudge_{goal.id}"
    # (simple in-memory throttle — good enough for production)
    if not hasattr(_nudge_approval, "_cache"):
        _nudge_approval._cache = {}

    last = _nudge_approval._cache.get(last_nudge_key)
    if last and (now - last).total_seconds() < 3600:
        return

    _nudge_approval._cache[last_nudge_key] = now
    await chat_push(
        goal.created_by,
        f"📋 Your campaign plan **\"{goal.title}\"** is ready and waiting for your approval. "
        f"Reply 'approve' to start execution, or open the Goals page to review the full plan.",
        "orchestrator",
        goal.id,
    )


async def _push_execution_status(goal):
    """Push a factual status update for a running goal."""
    from agent.chat_push import chat_push

    pct = goal.progress_percent or 0
    done = goal.tasks_completed or 0
    total = goal.tasks_total or 0

    if pct >= 100:
        msg = f"✅ Campaign **\"{goal.title}\"** is complete! All {total} tasks finished."
    else:
        msg = (
            f"📊 Campaign **\"{goal.title}\"** is running. "
            f"Progress: {pct:.0f}% ({done}/{total} tasks done). "
            f"I'll update you when the next milestone is reached."
        )

    await chat_push(goal.created_by, msg, "monitor", goal.id)


async def _phase_retry_failed_posts(now: datetime):
    """
    Sweeps for any posts that failed to publish and auto-queues a resilient 
    fallback execution task for the Publisher agent.
    """
    from database import async_session, PublishedPost, AgentTask
    from sqlalchemy import select
    import uuid

    async with async_session() as session:
        result = await session.execute(
            select(PublishedPost).where(PublishedPost.status == "failed")
        )
        failed_posts = result.scalars().all()

        for post in failed_posts:
            # Mark it as retrying to prevent infinite daemon loops
            post.status = "retrying"
            
            if post.goal_id:
                # Dispatch a fresh Publisher task bridging fallback systems
                new_task = AgentTask(
                    id=str(uuid.uuid4()),
                    goal_id=post.goal_id,
                    task_type="post_content",
                    agent="publisher",
                    description=f"Auto-Retry: Publish failed content on {post.platform}",
                    status="queued",
                    platform=post.platform,
                    connection_id=post.connection_id,
                )
                session.add(new_task)
                logger.info(f"[Daemon] Swept failed post {post.id}. Re-queued Publisher task: {new_task.id}")
                
        if failed_posts:
            await session.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — PER-USER AUTONOMOUS PROCESSING
# ═══════════════════════════════════════════════════════════════════════════════

async def _process_user(cfg, now: datetime):
    """Full autonomous processing for one user who has autonomous mode ON."""
    user_id = cfg.user_id

    # ── Check if there's anything to do ─────────────────────────────────────
    from database import async_session, Goal
    from sqlalchemy import select

    async with async_session() as session:
        result = await session.execute(
            select(Goal).where(
                Goal.created_by == user_id,
                Goal.status.in_(["planning", "executing", "awaiting_approval", "monitoring"])
            )
        )
        active_goals = result.scalars().all()

    # ── Idle detection ───────────────────────────────────────────────────────
    if not active_goals:
        last_ran = cfg.daemon_last_ran
        hours_idle = (now - last_ran).total_seconds() / 3600 if last_ran else IDLE_THRESHOLD_HRS + 1
        if hours_idle >= IDLE_THRESHOLD_HRS:
            await _push_idle_report(user_id, cfg, now)

    # ── Proactive research every 2 hours ─────────────────────────────────────
    last_research = cfg.last_proactive_research
    hours_since_research = (now - last_research).total_seconds() / 3600 if last_research else PROACTIVE_RESEARCH_HRS + 1
    if hours_since_research >= PROACTIVE_RESEARCH_HRS:
        await _run_proactive_research(user_id, cfg, now)
        # Update timestamp
        async with async_session() as session:
            s = await session.get(type(cfg), cfg.id)
            if s:
                s.last_proactive_research = now
                await session.commit()

    # ── Scheduled briefs ─────────────────────────────────────────────────────
    await _check_brief_schedule(user_id, cfg, now, active_goals)


# ═══════════════════════════════════════════════════════════════════════════════
# PROACTIVE RESEARCH
# ═══════════════════════════════════════════════════════════════════════════════

async def _run_proactive_research(user_id: str, cfg, now: datetime):
    """
    Research trending topics and surface 2-3 content ideas.
    Learns from: training docs (RAG) + recent chat history + past campaign goals.
    """
    from agent.llm import generate_completion
    from agent.chat_push import chat_push
    from database import async_session, Goal, ChatMessage
    from sqlalchemy import select, desc

    logger.info(f"[Daemon] Running proactive research for {user_id}")

    # ── Gather learning context ──────────────────────────────────────────────
    # Past campaigns
    async with async_session() as session:
        goals_result = await session.execute(
            select(Goal).where(Goal.created_by == user_id)
            .order_by(desc(Goal.created_at)).limit(10)
        )
        past_goals = goals_result.scalars().all()

        # Recent conversations (learning from chat)
        chat_result = await session.execute(
            select(ChatMessage).where(ChatMessage.user_id == user_id)
            .order_by(desc(ChatMessage.created_at)).limit(30)
        )
        recent_chats = chat_result.scalars().all()

    # Build context summary
    past_campaigns_text = "\n".join([
        f"- {g.title} ({g.status}, platforms: {g.platforms})"
        for g in past_goals
    ]) or "No past campaigns."

    chat_context = "\n".join([
        f"[{m.role}]: {m.content[:200]}"
        for m in reversed(recent_chats)
    ]) or "No conversation history."

    industry = cfg.industry or "technology and business"

    prompt = f"""You are a proactive marketing research agent.

Industry: {industry}
Brand context: {cfg.brand_voice or 'Not specified'}

Past campaigns:
{past_campaigns_text}

Recent conversation with the user:
{chat_context}

Based on:
1. Current date: {now.strftime('%A, %B %d %Y')}
2. The user's past campaigns and conversation patterns
3. What typically trends in {industry} at this time of year

Generate a brief proactive research report with:
- 2-3 trending opportunities in this industry RIGHT NOW
- 2-3 specific, actionable content ideas the agency could execute this week
- 1 competitor angle to watch

Format as a clear, executive-level brief. Be specific. No fluff.
Keep under 300 words."""

    try:
        report = await generate_completion(prompt, "You are a world-class marketing research analyst.")
        await chat_push(
            user_id,
            f"🔍 **Proactive Research Brief — {now.strftime('%b %d, %Y')}**\n\n{report}\n\n"
            f"_Reply to brief me on any of these, or say 'launch [idea]' to get started._",
            "researcher",
        )
    except Exception as e:
        logger.error(f"[Daemon] Proactive research failed for {user_id}: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# IDLE REPORT
# ═══════════════════════════════════════════════════════════════════════════════

async def _push_idle_report(user_id: str, cfg, now: datetime):
    """Push an opportunity report when the agency has been idle too long."""
    from agent.llm import generate_completion
    from agent.chat_push import chat_push

    logger.info(f"[Daemon] Pushing idle report for {user_id}")

    industry = cfg.industry or "technology and business"
    prompt = f"""The Digital Force agency has been idle — no active campaigns.

Today is {now.strftime('%A, %B %d %Y')}.
Industry: {industry}

Generate a short report (under 200 words) that:
1. States there are currently no active campaigns
2. Lists 3 specific campaign ideas we could launch this week based on the industry calendar and trends
3. Suggests which one to prioritise and why

Format it as if you're a marketing director reporting to the business owner."""

    try:
        report = await generate_completion(prompt, "You are Digital Force's autonomous marketing director.")
        await chat_push(
            user_id,
            f"🟡 **Agency Status: Idle**\n\n{report}\n\n"
            f"_Say 'launch [idea]' to get the agents started on any of these._",
            "orchestrator",
        )
    except Exception as e:
        logger.error(f"[Daemon] Idle report failed for {user_id}: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# BRIEF SCHEDULER
# ═══════════════════════════════════════════════════════════════════════════════

async def _check_brief_schedule(user_id: str, cfg, now: datetime, active_goals: list):
    """Check if any brief slots are due and send them."""
    try:
        import pytz
        slots = json.loads(cfg.brief_slots or "[]")
        if not slots:
            return

        tz = pytz.timezone(cfg.timezone or "UTC")
        user_now = now.replace(tzinfo=pytz.utc).astimezone(tz)
        user_hhmm = user_now.strftime("%H:%M")
        user_date = user_now.strftime("%Y-%m-%d")
        user_weekday = user_now.weekday()  # 0=Mon, 6=Sun
        updated = False

        for slot in slots:
            last_sent = slot.get("last_sent_date")
            recurrence = slot.get("recurrence", "daily")
            scheduled_time = slot.get("time")

            is_due = False

            if recurrence == "once":
                slot_date = slot.get("date")
                if not slot_date or last_sent:  # Already sent once
                    continue
                if user_date > slot_date or (user_date == slot_date and user_hhmm >= scheduled_time):
                    is_due = True
            else:
                if last_sent == user_date:
                    continue  # Already sent today
                if user_hhmm >= scheduled_time:
                    if recurrence == "daily":
                        is_due = True
                    elif recurrence == "weekdays" and user_weekday < 5:
                        is_due = True
                    elif recurrence == "weekly" and user_weekday == 0:
                        is_due = True

            if is_due:
                await _send_brief(user_id, cfg, slot, now, active_goals)
                slot["last_sent_date"] = user_date
                updated = True

        if updated:
            from database import async_session
            cfg.brief_slots = json.dumps(slots)
            async with async_session() as session:
                # Refresh object to push to DB
                cfg_ref = await session.merge(cfg)
                await session.commit()

    except Exception as e:
        logger.error(f"[Daemon] Brief schedule check failed for {user_id}: {e}")


async def _send_brief(user_id: str, cfg, slot: dict, now: datetime, active_goals: list):
    """Generate and send a scheduled brief to the user's chat."""
    from agent.llm import generate_completion
    from agent.chat_push import chat_push
    import json as _json

    label = slot.get("label", "Brief")
    logger.info(f"[Daemon] Sending '{label}' to {user_id}")

    # Compose campaign status summary
    if active_goals:
        campaign_lines = []
        for g in active_goals:
            campaign_lines.append(
                f"- {g.title}: {g.status.upper()} — "
                f"{g.progress_percent:.0f}% complete "
                f"({g.tasks_completed}/{g.tasks_total} tasks)"
            )
        campaigns_text = "\n".join(campaign_lines)
    else:
        campaigns_text = "No active campaigns."

    prompt = f"""You are the Digital Force autonomous marketing director.
Generate a {label} for the business owner.

Date/Time: {now.strftime('%A, %B %d %Y, %H:%M UTC')}
Active campaigns:
{campaigns_text}

The brief should include:
1. What the agents did since the last brief
2. Current campaign status
3. What's planned next
4. Any decisions needed from the user (flagged clearly)
5. One strategic recommendation

Keep it under 250 words. Executive tone. No fluff."""

    try:
        brief_text = await generate_completion(prompt, "You are Digital Force's marketing director writing a board-level brief.")
        await chat_push(
            user_id,
            f"📋 **{label} — {now.strftime('%b %d, %Y')}**\n\n{brief_text}",
            "orchestrator",
        )
    except Exception as e:
        logger.error(f"[Daemon] Brief send failed for {user_id}: {e}")
