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

logger = logging.getLogger(__name__)

_PROMPT = (Path(__file__).parent.parent / "prompts" / "strategist.md").read_text()


async def strategist_node(state: AgentState) -> dict:
    """
    Takes the parsed goal + research findings, produces a full campaign plan
    with concrete tasks for every piece of content to be created and published.
    """
    logger.info(f"[Strategist] Creating campaign plan for goal {state['goal_id']}")

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
        logger.info(f"[Strategist] Generated plan with {len(tasks)} tasks")

        return {
            "campaign_plan": plan,
            "tasks": tasks,
            "messages": [{"role": "strategist", "content": f"Plan created: {len(tasks)} tasks over {plan.get('duration_days', 7)} days"}],
            "next_agent": "approval_gateway",
        }

    except Exception as e:
        logger.error(f"[Strategist] Error: {e}")
        return {
            "error": str(e),
            "next_agent": "approval_gateway",
        }
