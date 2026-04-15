"""
Digital Force — Chat Agent (Memory-Aware, Multi-Bubble)
The command interface to the autonomous agency.
- Loads full conversation history from ChatMessage table (per-user memory)
- Streams multi-bubble responses so each logical message is its own bubble
- Dispatches to real LangGraph agents when a campaign action is needed
- Agents push updates back into chat via chat_push.py
"""

import json
import uuid
import logging
import asyncio
from typing import AsyncGenerator
from datetime import datetime

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are ASMIA — the command interface to Digital Force, a team of autonomous AI agents.

Your agents:
  - Orchestrator: parses goals into structured briefs
  - Researcher: gathers real-time trends, hashtags, competitor data
  - Strategist: builds the full campaign plan
  - Content Director: creates the actual posts
  - Publisher: posts to social platforms via API
  - SkillForge: builds new capabilities when agents hit a wall
  - Monitor: tracks goal progress and triggers replanning if needed

Your personality:
  - Speak like a world-class senior marketing strategist at a $50M agency
  - Confident, direct, honest — never sugarcoat, never filler
  - First person: "I'm dispatching...", "According to the data..."
  - You remember everything said in this conversation

══ CRITICAL RULES — READ CAREFULLY ══
  1. NEVER invent agent status, post URLs, review stages, engagement numbers, or timelines.
     If you do not have that data in the LIVE AGENCY STATE block below, say so plainly:
     "The agents haven't reported that detail yet — I'll update you when they do."
  2. NEVER say "the agents are checking", "it looks like it's being reviewed", or ANY status
     unless you are reading it DIRECTLY from the LIVE AGENCY STATE block.
  3. You ONLY know what is written in the LIVE AGENCY STATE section below. Nothing more.
  4. If a campaign shows status AWAITING_APPROVAL — tell the user the plan is ready and ask them to approve it.
  5. If a campaign shows status EXECUTING — say agents are actively running. No fabricated details.
  6. If a campaign shows status MONITORING — say it completed and monitoring is underway.
  7. If no campaigns exist yet — say so and invite them to brief the agency.

Response format:
  Separate your response into two parts with the marker: ===BREAK===
  Part 1 (1-3 sentences): Brief acknowledgment of the user's message
  Part 2: Your actual answer, status, or action
  Omit the marker entirely if the answer naturally fits in one paragraph.
"""


async def _load_history(user_id: str, limit: int = 30) -> list[dict]:
    """Fetch recent ChatMessage records for this user, newest last."""
    try:
        from database import ChatMessage, async_session
        from sqlalchemy import select, desc
        async with async_session() as session:
            result = await session.execute(
                select(ChatMessage)
                .where(ChatMessage.user_id == user_id)
                .order_by(desc(ChatMessage.created_at))
                .limit(limit)
            )
            rows = result.scalars().all()
        # Reverse so oldest is first (for LLM context window)
        return [
            {"role": r.role, "content": r.content, "agent_name": r.agent_name}
            for r in reversed(rows)
        ]
    except Exception as e:
        logger.warning(f"[ChatAgent] Could not load history: {e}")
        return []


async def _save_message(user_id: str, role: str, content: str, goal_id: str = None) -> None:
    """Persist a chat message."""
    try:
        from database import ChatMessage, async_session
        async with async_session() as session:
            session.add(ChatMessage(
                user_id=user_id,
                role=role,
                content=content,
                goal_id=goal_id,
            ))
            await session.commit()
    except Exception as e:
        logger.warning(f"[ChatAgent] Could not save message: {e}")


async def _get_agency_context(user_id: str) -> str:
    """Build a detailed, factual agency state snapshot to inject into the system prompt."""
    try:
        from database import Goal, async_session
        from sqlalchemy import select, desc
        import json as _json
        async with async_session() as session:
            result = await session.execute(
                select(Goal)
                .where(Goal.created_by == user_id)
                .order_by(desc(Goal.created_at)).limit(10)
            )
            goals = result.scalars().all()

        if not goals:
            return "No campaigns have been created yet for this user."

        lines = []
        for g in goals:
            # Parse tasks from plan JSON
            try:
                plan = _json.loads(g.plan or "{}")
                tasks = plan.get("tasks", [])
                task_lines = []
                for t in tasks[:5]:  # Show first 5 tasks
                    t_status = t.get("status", "pending")
                    task_lines.append(f"    • [{t_status.upper()}] {t.get('title', t.get('action', 'task'))}")
            except Exception:
                task_lines = []

            platforms = ", ".join(_json.loads(g.platforms or "[]")) or "not specified"
            lines.append(
                f"Campaign: \"{g.title}\""
                f"\n  Status: {g.status.upper()}"
                f"\n  Platforms: {platforms}"
                f"\n  Progress: {g.progress_percent:.0f}% ({g.tasks_completed} of {g.tasks_total} tasks done, {g.tasks_failed} failed)"
                f"\n  Priority: {g.priority}"
                f"\n  Created: {g.created_at.strftime('%Y-%m-%d %H:%M UTC')}"
            )
            if task_lines:
                lines.append("  Tasks:\n" + "\n".join(task_lines))
            lines.append("")  # spacing

        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"[ChatAgent] Could not load agency context: {e}")
        return "Unable to fetch agency state — database may be unavailable."


async def handle_chat_message(
    message: str,
    context: dict,
    user_id: str,
) -> AsyncGenerator[dict, None]:
    """
    Core chat handler. Yields SSE-compatible dicts:
      { type: "thinking" | "action" | "bubble_start" | "message" | "bubble_end" | "error" | "done",
        content: str, bubble_id: str (optional) }

    Multi-bubble protocol:
      bubble_start → stream message tokens → bubble_end → (optional) more bubbles → done
    """
    from agent.llm import stream_chat_with_history

    # ── 1. Load conversation history (memory) ──────────────────────────────
    yield {"type": "thinking", "content": "Recalling our conversation..."}
    history = await _load_history(user_id, limit=30)

    # ── 2. Load agency state ───────────────────────────────────────────────
    yield {"type": "thinking", "content": "Checking agency status..."}
    agency_context = await _get_agency_context(user_id)

    # ── 3. Build system prompt with live context ───────────────────────────
    system = SYSTEM_PROMPT + f"""

Current Date/Time: {datetime.utcnow().strftime('%A, %B %d %Y, %H:%M UTC')}

LIVE AGENCY STATE:
{agency_context}

CONVERSATION RULES:
- The conversation history is above. Reference it naturally.
- If the user says "post the AI Tech Forum banner", you actually dispatch that to an agent — don't ask again.
- When dispatching agents, tell the user agents are running, and they'll see updates in this chat.
"""

    # ── 4. Build full messages array (history + current message) ──────────
    # Convert history to Groq-compatible format (agent msgs become assistant)
    groq_history = []
    for h in history:
        role = h["role"]
        if role == "agent":
            agent_label = (h.get("agent_name") or "agent").capitalize()
            content = f"[{agent_label} update]: {h['content']}"
            role = "assistant"
        else:
            content = h["content"]
        groq_history.append({"role": role, "content": content})

    groq_history.append({"role": "user", "content": message})

    # ── 5. Detect intent for action chips ─────────────────────────────────
    msg_lower = message.lower()
    create_kw   = ["create", "launch", "start", "build", "new campaign", "post", "publish", "run", "make", "set up"]
    status_kw   = ["status", "how is", "update", "progress", "overview", "report", "what's happening", "show me"]
    approve_kw  = ["approve", "looks good", "go ahead", "execute", "yes do it", "confirm", "do it", "retry", "yes"]
    replan_kw   = ["replan", "change strategy", "pivot", "adjust", "rethink", "not working"]

    if any(k in msg_lower for k in create_kw):
        yield {"type": "action", "content": "🎯 Parsing campaign request..."}
    elif any(k in msg_lower for k in status_kw):
        yield {"type": "action", "content": "📊 Pulling campaign data..."}
    elif any(k in msg_lower for k in approve_kw):
        yield {"type": "action", "content": "✅ Processing approval..."}
    elif any(k in msg_lower for k in replan_kw):
        yield {"type": "action", "content": "🔄 Evaluating replan strategy..."}

    # ── 6. Stream LLM response with bubbles ───────────────────────────────
    full_response = ""
    current_bubble_id = str(uuid.uuid4())
    bubble_count = 0

    yield {"type": "bubble_start", "bubble_id": current_bubble_id}
    bubble_count += 1

    try:
        marker = "===BREAK==="
        buffer = ""

        async for token in stream_chat_with_history(
            system=system,
            messages=groq_history,
            temperature=0.7,
            max_tokens=1500,
        ):
            buffer += token

            # We also check for marker with newlines attached that the LLM might generate
            if marker in buffer or "===BREAK" in buffer and len(buffer) > len("===BREAK") + 5:
                # If we loosely matched ===BREAK (e.g. ===BREAKThe), force clean it
                clean_before = buffer.split("===BREAK")[0]
                
                # Marker found! Close current bubble
                yield {"type": "bubble_end", "bubble_id": current_bubble_id}
                
                # Take everything before the marker, just in case
                if clean_before:
                    full_response += clean_before
                    yield {"type": "message", "content": clean_before, "bubble_id": current_bubble_id}

                # We flush the buffer but keep whatever came AFTER the break marker
                after_marker = ""
                if marker in buffer:
                    after_marker = buffer.split(marker)[-1]
                else:
                    after_marker = buffer.split("===BREAK")[-1].lstrip("=")

                buffer = after_marker.lstrip() # remove leading spaces/newlines from the second bubble
                await asyncio.sleep(0.4)

                # Start next bubble
                current_bubble_id = str(uuid.uuid4())
                bubble_count += 1
                yield {"type": "bubble_start", "bubble_id": current_bubble_id}
                continue

            # Check if buffer ends with a partial chunk of the marker
            is_partial = False
            for i in range(1, len(marker)):
                if buffer.endswith(marker[:i]):
                    is_partial = True
                    break

            if not is_partial:
                # Safe to yield the buffer completely
                full_response += buffer
                yield {"type": "message", "content": buffer, "bubble_id": current_bubble_id}
                buffer = ""
                await asyncio.sleep(0)

        if buffer:
            # Yield any remaining text
            full_response += buffer
            yield {"type": "message", "content": buffer, "bubble_id": current_bubble_id}

    except Exception as e:
        logger.error(f"[ChatAgent] LLM stream error: {e}")
        yield {"type": "bubble_end", "bubble_id": current_bubble_id}
        yield {"type": "error", "content": "Connection issue — check your API keys in Settings."}
        return

    # Close final bubble
    yield {"type": "bubble_end", "bubble_id": current_bubble_id}

    # ── 7. Persist both sides of the conversation ──────────────────────────
    await _save_message(user_id, "user", message, context.get("goal_id"))
    await _save_message(user_id, "assistant", full_response, context.get("goal_id"))

    # ── 8. Real agent dispatch (only when genuinely needed) ────────────────
    if any(k in msg_lower for k in create_kw):
        try:
            yield {"type": "action", "content": "⚙️ Dispatching agents to the field..."}
            await _create_goal_and_dispatch(message, user_id)
            yield {"type": "action", "content": "✅ Agents deployed — updates will appear in this chat."}
        except Exception as e:
            logger.warning(f"[ChatAgent] Goal dispatch failed: {e}")
            
    elif any(k in msg_lower for k in approve_kw):
        try:
            from database import Goal, async_session
            from sqlalchemy import select, desc
            async with async_session() as session:
                result = await session.execute(
                    select(Goal)
                    .where(Goal.created_by == user_id)
                    .order_by(desc(Goal.created_at)).limit(1)
                )
                goal = result.scalar_one_or_none()
            
            if goal:
                yield {"type": "action", "content": "✅ Executing approved tasks..."}
                from api.goals import _run_execution_agent
                asyncio.create_task(_run_execution_agent(goal.id))
        except Exception as e:
            logger.warning(f"[ChatAgent] Auto-approval failed: {e}")

async def _create_goal_and_dispatch(message: str, user_id: str) -> None:
    """Create a Goal and fire the LangGraph planning graph as a background task."""
    import uuid as _uuid
    from agent.llm import generate_json
    from database import Goal, async_session

    extraction_prompt = f"""
Extract a social media campaign goal from this message: "{message}"

Return valid JSON:
{{
  "title": "Short campaign title (max 80 chars)",
  "description": "Full description for the planning agent",
  "platforms": ["facebook"],
  "priority": "normal"
}}

Rules:
- title should be descriptive but concise
- platforms: only include explicitly mentioned platforms; default to ["facebook","linkedin"]
- priority: "urgent" if time pressure, "high" if important, else "normal"
"""
    try:
        goal_data = await generate_json(
            extraction_prompt,
            "Extract campaign goal from message. Return JSON only."
        )
    except Exception:
        goal_data = {
            "title": message[:80],
            "description": message,
            "platforms": ["facebook", "linkedin"],
            "priority": "normal",
        }

    if not goal_data.get("description"):
        goal_data["description"] = message

    async with async_session() as session:
        goal = Goal(
            id=str(_uuid.uuid4()),
            title=goal_data.get("title", message[:80]),
            description=goal_data.get("description", message),
            platforms=json.dumps(goal_data.get("platforms", ["facebook", "linkedin"])),
            priority=goal_data.get("priority", "normal"),
            status="planning",
            created_by=user_id,
        )
        session.add(goal)
        await session.commit()
        goal_id = goal.id

    initial_state = {
        "goal_id": goal_id,
        "goal_description": goal_data.get("description", message),
        "created_by": user_id,
        "platforms": goal_data.get("platforms", ["facebook", "linkedin"]),
        "messages": [], "research_findings": {}, "campaign_plan": {},
        "tasks": [], "completed_task_ids": [], "failed_task_ids": [],
        "kpi_snapshot": {}, "needs_replan": False,
        "approval_status": "pending", "human_feedback": None,
        "new_skills_created": [], "next_agent": None, "error": None,
        "iteration_count": 0, "replan_count": 0, "current_task_id": None,
        "deadline": None, "asset_ids": [], "success_metrics": {}, "constraints": {},
    }

    from api.goals import run_planning_agent
    asyncio.create_task(run_planning_agent(goal_id, goal_data.get("description", message), initial_state))
    logger.info(f"[ChatAgent] Launched planning agent for goal {goal_id}")
