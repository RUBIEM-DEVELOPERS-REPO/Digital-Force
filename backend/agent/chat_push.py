"""
Digital Force — Agent→Chat Push Utility
Any LangGraph agent node can call chat_push() to post a message directly
into the user's chat feed. This is the real-time bridge between the
background autonomous agents and the frontend conversation.
"""

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Colour/emoji mapping for each agent's chat badge
AGENT_META = {
    "orchestrator":     {"emoji": "🎯", "label": "Orchestrator"},
    "researcher":       {"emoji": "🔍", "label": "Researcher"},
    "strategist":       {"emoji": "📋", "label": "Strategist"},
    "content_director": {"emoji": "✍️",  "label": "Content Director"},
    "publisher":        {"emoji": "📤", "label": "Publisher"},
    "skillforge":       {"emoji": "⚡", "label": "SkillForge"},
    "monitor":          {"emoji": "📊", "label": "Monitor"},
}


async def chat_push(
    user_id: str,
    content: str,
    agent_name: str,
    goal_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> None:
    """
    Post a message from an autonomous agent into the user's chat feed.

    Called by LangGraph nodes at key milestones so the user sees real
    agent activity in the conversation — not silence.

    Args:
        user_id:    The user who owns this campaign (from Goal.created_by).
        content:    The message text to display in chat.
        agent_name: Which agent is speaking (e.g. "strategist").
        goal_id:    The campaign goal this relates to (optional).
        metadata:   Extra JSON context to attach (optional).
    """
    if not user_id:
        logger.warning(f"[ChatPush] Skipped — no user_id for agent '{agent_name}'")
        return

    try:
        from database import ChatMessage, async_session
        async with async_session() as session:
            session.add(ChatMessage(
                user_id=user_id,
                role="agent",
                agent_name=agent_name,
                content=content,
                goal_id=goal_id,
                meta=json.dumps(metadata or {}),
            ))
            await session.commit()
        logger.info(f"[ChatPush] [{agent_name.upper()}] → user {user_id[:8]}: {content[:80]}")
    except Exception as e:
        # Never let a chat push failure crash an agent node
        logger.error(f"[ChatPush] Failed to persist message from '{agent_name}': {e}")
