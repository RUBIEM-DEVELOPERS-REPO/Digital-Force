"""
Digital Force — Orchestrator Agent Node
Parses natural language goals into structured mission briefs.
"""

import json
import logging
from pathlib import Path
from agent.state import AgentState
from agent.llm import generate_json

logger = logging.getLogger(__name__)

_PROMPT = (Path(__file__).parent.parent / "prompts" / "orchestrator.md").read_text()


async def orchestrator_node(state: AgentState) -> dict:
    """
    Receives the raw goal description, produces a structured mission brief.
    Updates state with: platforms, success_metrics, constraints, next_agent.
    """
    logger.info(f"[Orchestrator] Processing goal: {state['goal_description'][:100]}...")

    prompt = f"""
GOAL: {state['goal_description']}
DEADLINE: {state.get('deadline', 'not specified')}
ASSET IDs PROVIDED: {state.get('asset_ids', [])}

Parse this goal and produce the mission brief JSON.
"""

    try:
        result = await generate_json(prompt, _PROMPT, prefer_reasoning=True)

        # Update state
        return {
            "platforms": result.get("platforms", state.get("platforms", [])),
            "success_metrics": result.get("success_metrics", {}),
            "constraints": result.get("constraints", {}),
            "messages": [{"role": "orchestrator", "content": json.dumps(result)}],
            "next_agent": "researcher" if result.get("requires_research") else "strategist",
            "iteration_count": state.get("iteration_count", 0) + 1,
        }

    except Exception as e:
        logger.error(f"[Orchestrator] Error: {e}")
        return {
            "error": str(e),
            "next_agent": "strategist",  # Skip research, go direct
        }
