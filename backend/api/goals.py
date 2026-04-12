"""
Digital Force — Goals API
Full CRUD + agent trigger endpoints for the Goal resource.
"""

import json
import uuid
import secrets
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel

from database import get_db, Goal, AgentLog
from auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/goals", tags=["goals"])


# ─── Schemas ─────────────────────────────────────────────

class CreateGoalRequest(BaseModel):
    description: str                           # Natural language goal
    title: Optional[str] = None
    platforms: Optional[list[str]] = None
    deadline: Optional[str] = None
    asset_ids: Optional[list[str]] = []
    success_metrics: Optional[dict] = {}
    constraints: Optional[dict] = {}
    priority: Optional[str] = "normal"


class ApproveGoalRequest(BaseModel):
    approved: bool
    notes: Optional[str] = None
    modifications: Optional[dict] = None      # Human edits to the plan


# ─── Background worker ───────────────────────────────────

async def run_planning_agent(goal_id: str, goal_description: str, initial_state: dict):
    """Runs the planning graph and saves the plan to the database."""
    try:
        from agent.graph import planning_graph
        from database import async_session, Goal as GoalModel, AgentLog as LogModel
        import json

        logger.info(f"[PlanningAgent] Starting for goal {goal_id}")

        final_state = await planning_graph.ainvoke(initial_state)

        async with async_session() as db:
            goal = await db.get(GoalModel, goal_id)
            if goal:
                plan = final_state.get("campaign_plan", {})
                tasks = final_state.get("tasks", [])
                plan["tasks"] = tasks

                # Assign IDs to tasks
                for t in tasks:
                    if not t.get("id"):
                        t["id"] = str(uuid.uuid4())

                goal.plan = json.dumps(plan)
                goal.platforms = json.dumps(final_state.get("platforms", []))
                goal.success_metrics = json.dumps(final_state.get("success_metrics", {}))
                goal.tasks_total = len(tasks)
                goal.status = "awaiting_approval"
                goal.approval_token = secrets.token_urlsafe(32)

                # Log agent messages
                for msg in final_state.get("messages", []):
                    log = LogModel(
                        goal_id=goal_id,
                        agent=msg.get("role", "system"),
                        level="info",
                        thought=msg.get("content", ""),
                    )
                    db.add(log)

                await db.commit()
                logger.info(f"[PlanningAgent] Plan saved for goal {goal_id}. {len(tasks)} tasks planned.")

                # Send approval notification
                await _send_approval_notification(goal_id, goal.approval_token, plan)

    except Exception as e:
        logger.error(f"[PlanningAgent] Failed for goal {goal_id}: {e}")
        async with async_session() as db:
            goal = await db.get(Goal, goal_id)
            if goal:
                goal.status = "failed"
                await db.commit()


async def _send_approval_notification(goal_id: str, token: str, plan: dict):
    """Send email notification for plan approval."""
    try:
        from config import get_settings
        s = get_settings()
        if not s.smtp_username:
            logger.info("[Notify] SMTP not configured — skipping email")
            return

        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        approve_url = f"{s.frontend_url}/goals/{goal_id}/approve?token={token}&action=approve"
        review_url = f"{s.frontend_url}/goals/{goal_id}/approve"

        task_count = len(plan.get("tasks", []))
        campaign_name = plan.get("campaign_name", "Campaign")

        body = f"""
        <html><body style="font-family:sans-serif;max-width:600px;margin:auto">
        <h2 style="color:#6C63FF">🤖 Digital Force has a plan ready</h2>
        <p>Your campaign plan is ready for review.</p>
        <table style="width:100%;border-collapse:collapse">
          <tr><td style="padding:8px;font-weight:bold">Campaign</td><td>{campaign_name}</td></tr>
          <tr><td style="padding:8px;font-weight:bold">Tasks Planned</td><td>{task_count}</td></tr>
          <tr><td style="padding:8px;font-weight:bold">Summary</td><td>{plan.get('campaign_summary','')}</td></tr>
        </table>
        <br>
        <a href="{approve_url}" style="background:#6C63FF;color:white;padding:12px 24px;text-decoration:none;border-radius:8px">✅ Approve Plan</a>
        &nbsp;&nbsp;
        <a href="{review_url}" style="background:#333;color:white;padding:12px 24px;text-decoration:none;border-radius:8px">👁 Review in Detail</a>
        </body></html>
        """

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[Digital Force] Plan Ready: {campaign_name} ({task_count} tasks)"
        msg["From"] = f"{s.smtp_from_name} <{s.smtp_from_email}>"
        msg["To"] = s.smtp_username
        msg.attach(MIMEText(body, "html"))

        with smtplib.SMTP(s.smtp_host, s.smtp_port) as server:
            server.starttls()
            server.login(s.smtp_username, s.smtp_password)
            server.send_message(msg)

        logger.info(f"[Notify] Approval email sent for goal {goal_id}")
    except Exception as e:
        logger.warning(f"[Notify] Email failed: {e}")


# ─── Routes ──────────────────────────────────────────────

@router.post("")
async def create_goal(
    body: CreateGoalRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    Create a new goal and immediately trigger the planning agent.
    The agent runs in the background; poll GET /goals/{id} for status.
    """
    goal = Goal(
        id=str(uuid.uuid4()),
        title=body.title or body.description[:100],
        description=body.description,
        platforms=json.dumps(body.platforms or []),
        deadline=datetime.fromisoformat(body.deadline) if body.deadline else None,
        assets=json.dumps(body.asset_ids or []),
        success_metrics=json.dumps(body.success_metrics or {}),
        constraints=json.dumps(body.constraints or {}),
        priority=body.priority or "normal",
        status="planning",
        created_by=user.get("sub"),
    )
    db.add(goal)
    await db.flush()

    # Prepare initial agent state
    initial_state = {
        "goal_id": goal.id,
        "goal_description": body.description,
        "platforms": body.platforms or [],
        "deadline": body.deadline,
        "asset_ids": body.asset_ids or [],
        "success_metrics": body.success_metrics or {},
        "constraints": body.constraints or {},
        "messages": [],
        "research_findings": {},
        "campaign_plan": {},
        "tasks": [],
        "completed_task_ids": [],
        "failed_task_ids": [],
        "kpi_snapshot": {},
        "needs_replan": False,
        "approval_status": "pending",
        "human_feedback": None,
        "new_skills_created": [],
        "next_agent": None,
        "error": None,
        "iteration_count": 0,
        "replan_count": 0,
        "current_task_id": None,
    }

    # Fire the planning agent in background
    background_tasks.add_task(run_planning_agent, goal.id, body.description, initial_state)

    return {
        "id": goal.id,
        "title": goal.title,
        "status": goal.status,
        "message": "Goal created. Agent is now planning your campaign. You'll be notified when the plan is ready for approval.",
    }


@router.get("")
async def list_goals(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    result = await db.execute(select(Goal).order_by(desc(Goal.created_at)).limit(50))
    goals = result.scalars().all()
    return [{
        "id": g.id, "title": g.title, "status": g.status,
        "priority": g.priority, "progress_percent": g.progress_percent,
        "tasks_total": g.tasks_total, "tasks_completed": g.tasks_completed,
        "platforms": json.loads(g.platforms or "[]"),
        "created_at": g.created_at.isoformat(),
        "deadline": g.deadline.isoformat() if g.deadline else None,
    } for g in goals]


@router.get("/{goal_id}")
async def get_goal(
    goal_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    goal = await db.get(Goal, goal_id)
    if not goal:
        raise HTTPException(404, "Goal not found")

    # Get recent agent logs
    logs_result = await db.execute(
        select(AgentLog).where(AgentLog.goal_id == goal_id).order_by(desc(AgentLog.created_at)).limit(50)
    )
    logs = [{
        "id": l.id, "agent": l.agent, "level": l.level,
        "thought": l.thought, "action": l.action,
        "created_at": l.created_at.isoformat(),
    } for l in logs_result.scalars().all()]

    return {
        "id": goal.id, "title": goal.title, "description": goal.description,
        "status": goal.status, "priority": goal.priority,
        "platforms": json.loads(goal.platforms or "[]"),
        "plan": json.loads(goal.plan) if goal.plan else None,
        "success_metrics": json.loads(goal.success_metrics or "{}"),
        "tasks_total": goal.tasks_total,
        "tasks_completed": goal.tasks_completed,
        "tasks_failed": goal.tasks_failed,
        "progress_percent": goal.progress_percent,
        "kpi_snapshot": goal.last_monitor_at,
        "agent_logs": logs,
        "created_at": goal.created_at.isoformat(),
        "deadline": goal.deadline.isoformat() if goal.deadline else None,
        "approved_at": goal.approved_at.isoformat() if goal.approved_at else None,
    }


@router.post("/{goal_id}/approve")
async def approve_goal(
    goal_id: str,
    body: ApproveGoalRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Human approves or rejects the agent's plan."""
    goal = await db.get(Goal, goal_id)
    if not goal:
        raise HTTPException(404, "Goal not found")
    if goal.status != "awaiting_approval":
        raise HTTPException(400, f"Goal is not awaiting approval (status: {goal.status})")

    if not body.approved:
        goal.status = "planning"
        goal.approval_notes = body.notes
        goal.replan_count = (goal.replan_count or 0) + 1

        # Re-trigger planning with human feedback
        plan_json = json.loads(goal.plan or "{}")
        initial_state = {
            "goal_id": goal.id,
            "goal_description": goal.description,
            "platforms": json.loads(goal.platforms or "[]"),
            "asset_ids": json.loads(goal.assets or "[]"),
            "success_metrics": json.loads(goal.success_metrics or "{}"),
            "constraints": json.loads(goal.constraints or "{}"),
            "human_feedback": body.notes,
            "messages": [{"role": "human", "content": f"Plan rejected. Feedback: {body.notes}"}],
            "research_findings": {},
            "campaign_plan": {}, "tasks": [],
            "completed_task_ids": [], "failed_task_ids": [],
            "kpi_snapshot": {}, "needs_replan": False,
            "approval_status": "rejected", "new_skills_created": [],
            "next_agent": None, "error": None, "iteration_count": 0,
            "replan_count": goal.replan_count, "current_task_id": None, "deadline": None,
        }
        background_tasks.add_task(run_planning_agent, goal.id, goal.description, initial_state)
        await db.commit()
        return {"status": "replanning", "message": "Agent will revise the plan with your feedback."}

    # Approved — apply any human modifications and start execution
    if body.modifications:
        existing_plan = json.loads(goal.plan or "{}")
        existing_plan.update(body.modifications)
        goal.plan = json.dumps(existing_plan)

    goal.status = "executing"
    goal.approved_by = user.get("sub")
    goal.approved_at = datetime.utcnow()
    goal.approval_notes = body.notes

    await db.commit()

    # Fire execution agent
    background_tasks.add_task(_run_execution_agent, goal_id)

    return {"status": "executing", "message": "Plan approved. Agent is now executing your campaign."}


async def _run_execution_agent(goal_id: str):
    """Launch the execution graph for an approved goal."""
    try:
        from agent.graph import execution_graph
        from database import async_session, Goal as GoalModel
        import json

        async with async_session() as db:
            goal = await db.get(GoalModel, goal_id)
            if not goal:
                return
            plan = json.loads(goal.plan or "{}")

        state = {
            "goal_id": goal_id,
            "goal_description": goal.description,
            "platforms": json.loads(goal.platforms or "[]"),
            "asset_ids": json.loads(goal.assets or "[]"),
            "success_metrics": json.loads(goal.success_metrics or "{}"),
            "constraints": json.loads(goal.constraints or "{}"),
            "campaign_plan": plan,
            "tasks": plan.get("tasks", []),
            "messages": [], "research_findings": {},
            "completed_task_ids": [], "failed_task_ids": [],
            "kpi_snapshot": {}, "needs_replan": False,
            "approval_status": "approved", "human_feedback": None,
            "new_skills_created": [], "next_agent": None, "error": None,
            "iteration_count": 0, "replan_count": 0, "current_task_id": None, "deadline": None,
        }

        await execution_graph.ainvoke(state)
        logger.info(f"[ExecutionAgent] Completed for goal {goal_id}")

        async with async_session() as db:
            goal = await db.get(GoalModel, goal_id)
            if goal:
                goal.status = "monitoring"
                await db.commit()

    except Exception as e:
        logger.error(f"[ExecutionAgent] Failed for goal {goal_id}: {e}")


@router.get("/approve/{token}")
async def approve_via_token(token: str, action: str = "approve", db: AsyncSession = Depends(get_db)):
    """One-click email approval link."""
    result = await db.execute(select(Goal).where(Goal.approval_token == token))
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(404, "Invalid or expired approval token")
    if goal.status != "awaiting_approval":
        return {"status": goal.status, "message": f"Goal is already {goal.status}"}

    if action == "approve":
        goal.status = "executing"
        goal.approved_at = datetime.utcnow()
        await db.commit()
        from fastapi.responses import RedirectResponse
        from config import get_settings
        s = get_settings()
        return RedirectResponse(f"{s.frontend_url}/goals/{goal.id}?approved=true")

    return {"status": "pending", "goal_id": goal.id}
