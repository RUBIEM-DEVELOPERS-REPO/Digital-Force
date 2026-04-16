"""
Digital Force — Supervisor Node (Neural Hub)
Dynamically routes state to the appropriate agent instead of a linear pipeline.
"""

import json
import logging
from agent.state import AgentState
from agent.llm import generate_json
from agent.chat_push import chat_push

logger = logging.getLogger(__name__)

async def manager_node(state: AgentState) -> dict:
    """
    Evaluates current state and dynamically routes to the next best agent.
    If we are gathering info: -> researcher
    If we need a plan: -> strategist
    If we need content: -> content_director
    If we need publishing: -> publisher
    If we hit errors: -> skillforge
    """
    goal_id = state['goal_id']
    user_id = state.get('created_by', '')
    logger.info(f"[Supervisor] Evaluating state for goal: {goal_id[:8]}...")
    
    # 1. Compress State for LLM
    tasks = state.get("tasks", [])
    completed = state.get("completed_task_ids", [])
    failed = state.get("failed_task_ids", [])
    uncompleted = [t for t in tasks if t.get("id") not in completed and t.get("id") not in failed]
    
    compressed_state = {
        "status": state.get("approval_status", "pending"),
        "has_platforms": bool(state.get("platforms")),
        "has_research": bool(state.get("research_findings")),
        "needs_replanning_research": state.get("needs_replanning_research", False),
        "has_campaign_plan": bool(state.get("campaign_plan")),
        "tasks_total": len(tasks),
        "tasks_completed": len(completed),
        "tasks_failed": len(failed),
        "uncompleted_content_tasks": len([t for t in uncompleted if t.get("task_type") == "post_content" and not t.get("result")]),
        "uncompleted_publish_tasks": len([t for t in uncompleted if t.get("task_type") == "post_content" and t.get("result")]),
    }

    # 2. Dynamic True NLP Routing
    prompt = f"""You are the Manager Node of Digital Force.
Your job is to route to the correct agent based on the current state.

State Summary:
{json.dumps(compressed_state, indent=2)}

Available Agents:
- "skillforge": if there are broken/failed tasks
- "orchestrator": if platforms are not set up yet
- "researcher": if research is missing or needs replanning
- "strategist": if campaign plan is missing but research is done
- "content_director": if there are uncompleted content tasks (need generating)
- "publisher": if there are uncompleted publish tasks (content generated, need posting)
- "monitor": if all tasks are processed or executing is done
- "__end__": if the plan is ready but status is still pending (halt for human approval)

Evaluate the state and decide the single most logical next_agent to route to.

Return strictly JSON:
{{
  "thought": "Your dynamic internal reasoning about what you decided and why. Short and concise.",
  "next_agent": "..."
}}"""

    try:
        response = await generate_json(prompt)
        next_agent = response.get("next_agent", "__end__")
        thought = response.get("thought", "Routing determined from current state.")
        await chat_push(user_id, f"Manager: {thought}", "digital force - manager", goal_id)
        return {"next_agent": next_agent}
    except Exception as e:
        logger.error(f"[Manager] NLP Routing failed: {e}")
        # absolute fallback
        return {"next_agent": "__end__"}
