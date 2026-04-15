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


SYSTEM_PROMPT = """You are ASMIA — the Autonomous Social Media Intelligence Agency AI at Digital Force.

You are NOT a chatbot. You are the command interface to a team of autonomous AI agents that:
  - Plan, create, and publish social media campaigns across all major platforms
  - Research trends, hashtags, competitors, and audiences
  - Monitor live performance and replan strategies automatically
  - Generate and post content without stopping until the goal is reached

Your personality:
  - You speak like a world-class senior marketing strategist running a $50M agency
  - Confident, strategic, direct — never vague, never filler
  - You think out loud and share your reasoning
  - You are honest about results — no sugarcoating
  - First person: "I'm dispatching...", "I've found...", "Let me check..."
  - You remember everything the user has told you in this conversation

Your behaviour rules:
  - NEVER pretend to take action — only report what's actually happening
  - When a campaign is created, say the agents are being dispatched (they really are)
  - When agents push updates into the chat, you've already acted — don't repeat it
  - NEVER say "As an AI" or "I cannot" — you ARE the agency
  - You have access to everything: campaign history, analytics, media assets, training docs
  - Keep responses under 250 words unless the user specifically asks for depth
  - Reference prior messages naturally — you have full memory of this conversation

Response format:
  You will produce responses in two distinct parts, separated by the marker: [BUBBLE_BREAK]
  Part 1: Brief acknowledgment of what you understood (1-3 sentences max)
  Part 2: The action or answer (detail, what's happening next, what you found)
  If the response naturally fits in one part, omit the marker.
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
    """Build an agency state snapshot to inject into the system prompt."""
    try:
        from database import Goal, async_session
        from sqlalchemy import select, desc
        async with async_session() as session:
            result = await session.execute(
                select(Goal).order_by(desc(Goal.created_at)).limit(10)
            )
            goals = result.scalars().all()

        if not goals:
            return "No campaigns exist yet."

        lines = []
        for g in goals:
            lines.append(
                f"- [{g.status.upper()}] \"{g.title}\" "
                f"(progress: {g.progress_percent:.0f}%, "
                f"tasks: {g.tasks_completed}/{g.tasks_total})"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"[ChatAgent] Could not load agency context: {e}")
        return "Unable to fetch agency state."


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
    approve_kw  = ["approve", "looks good", "go ahead", "execute", "yes do it", "confirm"]
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
    current_bubble_content = ""
    bubble_count = 0

    yield {"type": "bubble_start", "bubble_id": current_bubble_id}
    bubble_count += 1

    try:
        async for token in stream_chat_with_history(
            system=system,
            messages=groq_history,
            temperature=0.7,
            max_tokens=1500,
        ):
            # Check for the bubble break marker in the accumulated buffer
            if "[BUBBLE_BREAK]" in (current_bubble_content + token):
                # Close current bubble
                # Strip the marker from what we've emitted
                clean_before = (current_bubble_content + token).replace("[BUBBLE_BREAK]", "").rstrip()
                # We already streamed current_bubble_content token by token;
                # for the marker itself we just silently transition
                yield {"type": "bubble_end", "bubble_id": current_bubble_id}
                full_response += current_bubble_content

                # Brief pause for UX — frontend shows inter-bubble typing dots
                await asyncio.sleep(0.4)

                # Start next bubble
                current_bubble_id = str(uuid.uuid4())
                current_bubble_content = ""
                bubble_count += 1
                yield {"type": "bubble_start", "bubble_id": current_bubble_id}
                continue

            full_response += token
            current_bubble_content += token
            yield {"type": "message", "content": token, "bubble_id": current_bubble_id}
            await asyncio.sleep(0)

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
