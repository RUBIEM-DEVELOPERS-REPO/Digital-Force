"""
Digital Force — Strategist Agent Node
Creates full campaign plans from mission briefs + research.
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from agent.state import AgentState
from agent.llm import generate_json
from agent.chat_push import chat_push

logger = logging.getLogger(__name__)

_PROMPT = (Path(__file__).parent.parent / "prompts" / "strategist.md").read_text()


async def strategist_node(state: AgentState) -> dict:
    """
    Takes the parsed goal + research findings, produces a full campaign plan
    with concrete tasks for every piece of content to be created and published.
    """
    goal_id = state['goal_id']
    user_id = state.get('created_by', '')
    logger.info(f"[Strategist] Creating campaign plan for goal {goal_id}")

    await chat_push(
        user_id=user_id,
        content="📋 Building your full campaign plan — content schedule, tasks, and publishing strategy...",
        agent_name="strategist",
        goal_id=goal_id,
    )

    deadline = state.get("deadline") or (datetime.utcnow() + timedelta(days=7)).isoformat()
    research = state.get("research_findings", {})

    prompt = f"""
MISSION:
- Goal: {state['goal_description']}
- Platforms: {state.get('platforms', [])}
- Deadline: {deadline}
- Success Metrics: {json.dumps(state.get('success_metrics', {}))}
- Constraints: {json.dumps(state.get('constraints', {}))}
- Media Assets Available: {state.get('asset_ids', [])}
- Today's Date: {datetime.utcnow().strftime('%Y-%m-%d')}

RESEARCH FINDINGS:
{json.dumps(research, indent=2) if research else 'No research conducted.'}

Create a comprehensive, detailed campaign plan with ALL tasks specified.
Each task must have enough detail for the Content Director to act without clarification.
"""

    try:
        plan = await generate_json(prompt, _PROMPT, prefer_reasoning=True)

        tasks = plan.get("tasks", [])
        duration = plan.get('duration_days', 7)
        logger.info(f"[Strategist] Generated plan with {len(tasks)} tasks")

        await chat_push(
            user_id=user_id,
            content=(
                f"📋 Campaign plan ready: **{plan.get('campaign_name', 'Your Campaign')}**\n"
                f"{len(tasks)} tasks planned over {duration} days.\n"
                f"{plan.get('campaign_summary', '')}\n"
                f"Awaiting your approval before execution begins."
            ),
            agent_name="strategist",
            goal_id=goal_id,
            metadata={"task_count": len(tasks), "duration_days": duration},
        )

        return {
            "campaign_plan": plan,
            "tasks": tasks,
            "messages": [{"role": "strategist", "content": f"Plan created: {len(tasks)} tasks over {duration} days"}],
            "next_agent": "approval_gateway",
        }

    except Exception as e:
        logger.error(f"[Strategist] Error: {e}")
        await chat_push(
            user_id=user_id,
            content=f"⚠️ Strategist encountered an issue building the plan. Will retry.",
            agent_name="strategist",
            goal_id=goal_id,
        )
        return {
            "error": str(e),
            "next_agent": "approval_gateway",
        }
