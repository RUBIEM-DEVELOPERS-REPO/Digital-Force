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
    Stream a natural language conversation with the Digital Force agency.
    Returns SSE with typed chunks:
      { type: "thinking" | "action" | "bubble_start" | "message" | "bubble_end" | "error" | "done",
        content: str, bubble_id?: str }
    """

    async def generate():
        try:
            from agent.chat_agent import handle_chat_message
            async for chunk in handle_chat_message(
                message=body.message,
                context=body.context or {},
                user_id=user.get("sub", "unknown"),
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
                await asyncio.sleep(0)
        except Exception as e:
            logger.error(f"[Chat] Stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        finally:
            yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"

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
        Goal.status.in_(["planning", "executing"])
    ).limit(1)
    active_goals_result = await db.execute(active_goals_query)
    agents_active = active_goals_result.first() is not None

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
