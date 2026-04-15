"""
Digital Force — Orchestrator Agent Node
Parses natural language goals into structured mission briefs.
"""

import json
import logging
from pathlib import Path
from agent.state import AgentState
from agent.llm import generate_json
from agent.chat_push import chat_push

logger = logging.getLogger(__name__)

_PROMPT = (Path(__file__).parent.parent / "prompts" / "orchestrator.md").read_text()


async def orchestrator_node(state: AgentState) -> dict:
    """
    Receives the raw goal description, produces a structured mission brief.
    Updates state with: platforms, success_metrics, constraints, next_agent.
    """
    goal_id    = state['goal_id']
    user_id    = state.get('created_by', '')
    goal_desc  = state['goal_description']
    logger.info(f"[Orchestrator] Processing goal: {goal_desc[:100]}...")

    # Announce in chat the moment we start
    await chat_push(
        user_id=user_id,
        content=f"🎯 Mission received. Parsing your goal and structuring the brief...",
        agent_name="orchestrator",
        goal_id=goal_id,
    )

    prompt = f"""
GOAL: {goal_desc}
DEADLINE: {state.get('deadline', 'not specified')}
ASSET IDs PROVIDED: {state.get('asset_ids', [])}

Parse this goal and produce the mission brief JSON.
"""

    try:
        result = await generate_json(prompt, _PROMPT, prefer_reasoning=True)

        platforms = result.get("platforms", state.get("platforms", []))
        next_node  = "researcher" if result.get("requires_research") else "strategist"

        await chat_push(
            user_id=user_id,
            content=(
                f"🎯 Brief complete. Platforms: {', '.join(platforms)}. "
                f"{'Dispatching Researcher to gather market intelligence...' if next_node == 'researcher' else 'Dispatching Strategist to build the campaign plan...'}"
            ),
            agent_name="orchestrator",
            goal_id=goal_id,
        )

        return {
            "platforms": platforms,
            "success_metrics": result.get("success_metrics", {}),
            "constraints": result.get("constraints", {}),
            "messages": [{"role": "orchestrator", "content": json.dumps(result)}],
            "next_agent": next_node,
            "iteration_count": state.get("iteration_count", 0) + 1,
        }

    except Exception as e:
        logger.error(f"[Orchestrator] Error: {e}")
        await chat_push(
            user_id=user_id,
            content=f"⚠️ Orchestrator hit an issue parsing the goal. Routing direct to Strategist.",
            agent_name="orchestrator",
            goal_id=goal_id,
        )
        return {
            "error": str(e),
            "next_agent": "strategist",
        }
