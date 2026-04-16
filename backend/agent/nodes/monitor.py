"""
Digital Force — Monitor Agent Node
Tracks goal progress, compares KPIs to targets, triggers re-planning if needed.
"""

import json
import logging
from datetime import datetime
from agent.state import AgentState
from agent.llm import generate_json
from agent.chat_push import chat_push, agent_thought_push

logger = logging.getLogger(__name__)


async def monitor_node(state: AgentState) -> dict:
    """
    Evaluates campaign progress against goal targets.
    Triggers re-planning if trajectory is off.
    """
    goal_id = state['goal_id']
    user_id = state.get('created_by', '')
    logger.info(f"[Monitor] Checking progress for goal {goal_id}")

    tasks     = state.get("tasks", [])
    completed = state.get("completed_task_ids", [])
    failed    = state.get("failed_task_ids", [])

    total   = len(tasks)
    done    = len([t for t in tasks if t.get("id") in completed])
    fail    = len([t for t in tasks if t.get("id") in failed])
    pending = total - done - fail

    progress_pct = (done / total * 100) if total > 0 else 0

    success_metrics = state.get("success_metrics", {})
    kpi_snapshot    = state.get("kpi_snapshot", {})
    replan_count    = state.get("replan_count", 0)

    needs_replan  = False
    replan_reason = None

    if fail > 0 and fail >= done:
        needs_replan  = True
        replan_reason = f"{fail} tasks failed while only {done} succeeded. Strategy adjustment needed."

    if replan_count >= 3:
        needs_replan = False

    is_complete = pending == 0 and fail == 0
    is_failed   = pending == 0 and fail == total

    kpi_update = {
        "total_tasks":      total,
        "completed_tasks":  done,
        "failed_tasks":     fail,
        "pending_tasks":    pending,
        "progress_percent": round(progress_pct, 1),
        "checked_at":       datetime.utcnow().isoformat(),
    }

    status_message = (
        f"Campaign {'complete' if is_complete else 'in progress'}: "
        f"{done}/{total} tasks done ({progress_pct:.0f}%)"
    )
    logger.info(f"[Monitor] {status_message}")

    # Push meaningful updates to chat
    if is_complete:
        await agent_thought_push(
            user_id=user_id,
            context=f"finalizing operations, all {total} tasks have successfully resolved. Campaign objectives achieved",
            agent_name="monitor",
            goal_id=goal_id,
            metadata=kpi_update,
        )
    elif is_failed:
        await agent_thought_push(
            user_id=user_id,
            context=f"detecting critical stall, {fail}/{total} tasks failed. Initializing contingency protocols",
            agent_name="monitor",
            goal_id=goal_id,
            metadata=kpi_update,
        )
    elif needs_replan:
        await agent_thought_push(
            user_id=user_id,
            context=f"identified a strategy breakdown: {replan_reason}. Sending directives to Strategist to route a new plan",
            agent_name="monitor",
            goal_id=goal_id,
            metadata=kpi_update,
        )
    else:
        # Periodic progress update (only push if something is actually happening)
        if done > 0:
            await agent_thought_push(
                user_id=user_id,
                context=f"evaluating metrics: {done}/{total} tasks complete ({progress_pct:.0f}%). {pending} tasks remain active in queue",
                agent_name="monitor",
                goal_id=goal_id,
                metadata=kpi_update,
            )

    return {
        "kpi_snapshot": kpi_update,
        "needs_replan": needs_replan,
        "messages": [{"role": "monitor", "content": status_message}],
        "next_agent": "strategist" if needs_replan else "END",
        "replan_count": replan_count + (1 if needs_replan else 0),
    }
