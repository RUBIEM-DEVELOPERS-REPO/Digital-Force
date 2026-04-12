"""
Digital Force — Monitor Agent Node
Tracks goal progress, compares KPIs to targets, triggers re-planning if needed.
"""

import json
import logging
from datetime import datetime
from agent.state import AgentState
from agent.llm import generate_json

logger = logging.getLogger(__name__)


async def monitor_node(state: AgentState) -> dict:
    """
    Evaluates campaign progress against goal targets.
    Triggers re-planning if trajectory is off.
    """
    logger.info(f"[Monitor] Checking progress for goal {state['goal_id']}")

    tasks = state.get("tasks", [])
    completed = state.get("completed_task_ids", [])
    failed = state.get("failed_task_ids", [])

    total = len(tasks)
    done = len([t for t in tasks if t.get("id") in completed])
    fail = len([t for t in tasks if t.get("id") in failed])
    pending = total - done - fail

    progress_pct = (done / total * 100) if total > 0 else 0

    # Assess if goal is on track
    success_metrics = state.get("success_metrics", {})
    kpi_snapshot = state.get("kpi_snapshot", {})
    replan_count = state.get("replan_count", 0)

    # Determine if re-planning is needed
    needs_replan = False
    replan_reason = None

    if fail > 0 and fail >= done:
        needs_replan = True
        replan_reason = f"{fail} tasks failed while only {done} succeeded. Strategy adjustment needed."

    if replan_count >= 3:
        needs_replan = False  # Don't keep replanning indefinitely

    # Determine if goal is complete
    is_complete = pending == 0 and fail == 0
    is_failed = pending == 0 and fail == total

    kpi_update = {
        "total_tasks": total,
        "completed_tasks": done,
        "failed_tasks": fail,
        "pending_tasks": pending,
        "progress_percent": round(progress_pct, 1),
        "checked_at": datetime.utcnow().isoformat(),
    }

    status_message = (
        f"Campaign {'complete' if is_complete else 'in progress'}: "
        f"{done}/{total} tasks done ({progress_pct:.0f}%)"
    )

    logger.info(f"[Monitor] {status_message}")

    return {
        "kpi_snapshot": kpi_update,
        "needs_replan": needs_replan,
        "messages": [{"role": "monitor", "content": status_message}],
        "next_agent": "strategist" if needs_replan else "END",
        "replan_count": replan_count + (1 if needs_replan else 0),
    }
