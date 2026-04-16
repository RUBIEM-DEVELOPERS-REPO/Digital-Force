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
                "goal_description": active_goal.description if active_goal else "Unspecified conversational inquiry.",
                "messages": hist_msgs,
                "tasks": json.loads(active_goal.plan).get("tasks", []) if active_goal and active_goal.plan else [],
                "platforms": json.loads(active_goal.platforms) if active_goal and active_goal.platforms else [],
                "asset_ids": json.loads(active_goal.assets) if active_goal and active_goal.assets else [],
                "success_metrics": json.loads(active_goal.success_metrics) if active_goal and active_goal.success_metrics else {},
                "constraints": json.loads(active_goal.constraints) if active_goal and active_goal.constraints else {},
                "completed_task_ids": [],
                "failed_task_ids": [],
                "research_findings": {},
                "kpi_snapshot": {},
                "approval_status": "none",
                "human_feedback": None,
                "new_skills_created": [],
                "needs_replan": False,
                "next_agent": None,
                "error": None,
                "iteration_count": 0,
                "replan_count": 0,
                "current_task_id": None,
                "deadline": active_goal.deadline.isoformat() if active_goal and active_goal.deadline else None,
            }
            
            # ---- LLM EVALUATION (INSTANT STREAMING) ----
            from agent.llm import generate_json
            
            agent_tone = "Highly professional, direct, and slightly futuristic"
            from database import AgencySettings, PlatformConnection
            from sqlalchemy import or_
            cfg_res = await db.execute(select(AgencySettings).where(AgencySettings.user_id == user_id))
            cfg = cfg_res.scalar_one_or_none()
            if cfg and cfg.agent_tone:
                agent_tone = cfg.agent_tone
                
            prompt = f"""You are the Executive interface of Digital Force, an autonomous AI agency.
Determine the user's intent from the following message, and reply.
Your persona and tone: {agent_tone}

Recent context:
{json.dumps(hist_msgs[-4:], indent=2)}

Determine if the user is asking you to start a task, create a goal, execute something, or analyze data. If yes, it requires the Manager's attention.
If the user is approving a previously proposed plan, mark approval_status as "approved". If rejecting, mark "rejected". Otherwise "none".
If the user is explicitly providing credentials, a password, a 2FA code, or telling you to inherently update the 'Truth Bucket' for an account, provide the account name you detect, and the specific text to append to their auth_data bucket.

Return strictly JSON:
{{
  "reply": "Your dynamic response to the user, in character.",
  "requires_manager": <boolean>,
  "approval_status": "approved" | "rejected" | "none",
  "update_truth_bucket": {{
     "account_name_match": "string matching account name (e.g. 'Acme Corp') or null",
     "text_to_append": "Exact credential string to append safely to DB (e.g. 'Backup pass: 123') or null"
  }}
}}"""
            try:
                response = await generate_json(prompt)
                reply = response.get("reply", "Acknowledged.")
                requires_manager = response.get("requires_manager", False)
                approval_status = response.get("approval_status", "none")
                truth_update = response.get("update_truth_bucket")
                
                if truth_update and isinstance(truth_update, dict) and truth_update.get("account_name_match"):
                    account_match = truth_update.get("account_name_match")
                    text_to_append = truth_update.get("text_to_append")
                    if text_to_append:
                        match_str = f"%{account_match}%"
                        conn = (await db.execute(select(PlatformConnection).where(or_(PlatformConnection.account_label.ilike(match_str), PlatformConnection.display_name.ilike(match_str))))).scalars().first()
                        if conn:
                            conn.auth_data = f"{conn.auth_data or ''}\\n[Agent Auto-Saved Update]: {text_to_append}".strip()
                            await db.commit()
            except Exception as e:
                reply = "Acknowledged. Routing internal systems to compensate."
                requires_manager = True
                approval_status = "none"

            # Save the agent reply directly to DB so it persists
            bot_msg_id = str(uuid.uuid4())
            db.add(ChatMessage(id=bot_msg_id, user_id=user_id, role="agent", agent_name="digital force - executive", content=reply, goal_id=active_goal.id if active_goal else None))
            await db.commit()

            # STREAM RESULT TO UI IMMEDIATELY
            yield f"data: {json.dumps({'type': 'bubble_start', 'bubble_id': bot_msg_id})}\\n\\n"
            chunk_size = 5
            for i in range(0, len(reply), chunk_size):
                yield f"data: {json.dumps({'type': 'message', 'content': reply[i:i+chunk_size]})}\\n\\n"
                await asyncio.sleep(0.01)
            yield f"data: {json.dumps({'type': 'bubble_end'})}\\n\\n"

            # Launch graph in background explicitly specifying next routing logic
            if requires_manager:
                initial_state["next_agent"] = "manager"
                if approval_status in ["approved", "rejected"]:
                    initial_state["approval_status"] = approval_status
            else:
                initial_state["next_agent"] = "__end__"
                
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
