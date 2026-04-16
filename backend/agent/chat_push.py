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
        from database import ChatMessage, AgentLog, async_session
        async with async_session() as session:
            session.add(ChatMessage(
                user_id=user_id,
                role="agent",
                agent_name=agent_name,
                content=content,
                goal_id=goal_id,
                meta=json.dumps(metadata or {}),
            ))
            if goal_id:
                session.add(AgentLog(
                    goal_id=goal_id,
                    agent=agent_name,
                    level="info",
                    thought=content,
                    action="chat_push"
                ))
            await session.commit()
        logger.info(f"[ChatPush] [{agent_name.upper()}] → user {user_id[:8]}: {content[:80]}")
    except Exception as e:
        # Never let a chat push failure crash an agent node
        logger.error(f"[ChatPush] Failed to persist message from '{agent_name}': {e}")


async def agent_thought_push(
    user_id: str,
    agent_name: str,
    context: str,
    goal_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> None:
    """
    Rapidly uses a lightweight LLM to generate a dynamic, first-person thought
    about what the agent is currently doing, then pushes it to the UI.
    """
    from agent.llm import generate_completion
    prompt = f"You are {agent_name.upper()}, an autonomous AI agent in the Digital Force network. You are currently: {context}. Give a dynamic, first-person present-tense thought (max 1 sentence) about what you are doing right now. NO hashtags, NO emojis, NO quotation marks, just raw telemetry thought."
    try:
        dynamic_thought = await generate_completion(prompt, temperature=0.3)
        await chat_push(user_id, dynamic_thought.strip(' "').replace("\n", ""), agent_name, goal_id, metadata)
    except Exception as e:
        logger.warning(f"[ThoughtPush] Fast thought generation failed, falling back to context: {e}")
        await chat_push(user_id, f"{agent_name.capitalize()}: Initializing {context}...", agent_name, goal_id, metadata)
