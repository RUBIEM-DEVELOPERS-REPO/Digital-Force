"""
Digital Force — Chat API
SSE-streaming interface to the ASMIA agency with persistent memory and agent push polling.
"""

import json
import asyncio
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from database import get_db, ChatMessage
from auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatMessageBody(BaseModel):
    message: str
    context: Optional[dict] = {}


@router.post("/stream")
async def chat_stream(
    body: ChatMessageBody,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    Pass the message directly to the LangGraph execution graph.
    The graph's nodes (like Executive) will push real-time responses to the DB,
    which the frontend polls.
    """
    user_id = user.get("sub", "unknown")
    
    # 1. Save user message to DB
    from database import ChatMessage
    import uuid
    msg_db = ChatMessage(
        id=str(uuid.uuid4()),
        user_id=user_id,
        role="user",
        content=body.message
    )
    db.add(msg_db)
    await db.commit()

    async def generate():
        try:
            yield f"data: {json.dumps({'type': 'action', 'content': 'Transmitting to Digital Force...'})}\\n\\n"
            await asyncio.sleep(0.1)

            # 2. Build AgentState
            from agent.graph import execution_graph
            
            # Fetch goals or context if any
            from database import Goal
            active_goals_query = select(Goal).where(
                Goal.created_by == user_id,
                Goal.status.in_(["planning", "executing", "awaiting_approval", "monitoring"])
            ).order_by(desc(Goal.created_at)).limit(1)
            active_goals_result = await db.execute(active_goals_query)
            active_goal = active_goals_result.scalar_one_or_none()
            
            # We want to pull recent history as well
            hist_result = await db.execute(
                select(ChatMessage)
                .where(ChatMessage.user_id == user_id)
                .order_by(desc(ChatMessage.created_at)).limit(10)
            )
            hist = hist_result.scalars().all()
            hist_msgs = [{"role": m.role, "content": m.content} for m in reversed(hist)]
            
            initial_state = {
                "created_by": user_id,
                "goal_id": active_goal.id if active_goal else None,
                "messages": hist_msgs,
                "tasks": [],
                "platforms": [],
            }
            
            # Launch graph in background so we don't block the HTTP request returning 
            # and the UI can immediately resume polling.
            asyncio.create_task(execution_graph.ainvoke(initial_state))
            
            yield f"data: {json.dumps({'type': 'done', 'content': ''})}\\n\\n"
        except Exception as e:
            logger.error(f"[Chat] Stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\\n\\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.get("/history")
async def get_chat_history(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
    limit: int = 100,
):
    """
    Return recent chat messages for the current user.
    Includes user, assistant, and agent-pushed messages.
    """
    user_id = user.get("sub", "unknown")
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == user_id)
        .order_by(ChatMessage.created_at.asc())
        .limit(limit)
    )
    messages = result.scalars().all()

    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "agent_name": m.agent_name,
            "goal_id": m.goal_id,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]


@router.get("/updates")
async def get_chat_updates(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
    since: Optional[str] = Query(None, description="ISO timestamp — return messages created after this"),
):
    """
    Polling endpoint for agent-pushed messages since a given timestamp.
    Frontend calls this every 10s to pick up autonomous agent updates.
    Returns { "messages": [...], "agents_active": True/False }
    """
    from database import Goal
    user_id = user.get("sub", "unknown")

    # 1. Fetch active goals to determine if agents are currently running
    active_goals_query = select(Goal).where(
        Goal.created_by == user_id,
        Goal.status.in_(["planning", "executing", "awaiting_approval", "monitoring"])
    ).limit(1)
    active_goals_result = await db.execute(active_goals_query)
    active_goal = active_goals_result.scalar_one_or_none()
    agents_active = active_goal is not None

    current_activity = None
    if active_goal:
        from database import AgentLog
        from sqlalchemy import desc
        log_res = await db.execute(select(AgentLog).where(AgentLog.goal_id == active_goal.id).order_by(desc(AgentLog.created_at)).limit(1))
        latest_log = log_res.scalar_one_or_none()
        if latest_log:
            current_activity = f"{latest_log.agent.upper()}: {latest_log.thought}"

    # 2. Fetch new agent messages
    query = (
        select(ChatMessage)
        .where(ChatMessage.user_id == user_id)
        .where(ChatMessage.role == "agent")
        .order_by(ChatMessage.created_at.asc())
    )

    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
            # Use naive UTC comparison — strip tzinfo to match DB datetime
            since_naive = since_dt.replace(tzinfo=None)
            query = query.where(ChatMessage.created_at > since_naive)
        except ValueError:
            pass  # Bad timestamp — return all agent messages

    result = await db.execute(query)
    messages = result.scalars().all()

    return {
        "agents_active": agents_active,
        "current_activity": current_activity,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "agent_name": m.agent_name,
                "goal_id": m.goal_id,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ]
    }


@router.delete("/history")
async def clear_chat_history(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Clear all chat history for the current user."""
    from sqlalchemy import delete
    user_id = user.get("sub", "unknown")
    await db.execute(
        delete(ChatMessage).where(ChatMessage.user_id == user_id)
    )
    await db.commit()
    return {"status": "cleared", "message": "Chat history cleared."}
