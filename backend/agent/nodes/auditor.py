"""
Digital Force — Auditor Node
Dynamic Risk Vector Topology. Grades risk and enforces thresholds.
"""
import logging
from agent.state import AgentState
from agent.llm import generate_completion
from agent.chat_push import agent_thought_push, chat_push
from database import async_session, AgencySettings
from sqlalchemy import select

logger = logging.getLogger(__name__)

async def auditor_node(state: AgentState) -> dict:
    user_id = state.get("created_by", "")
    target = state.get("target_agent", "")
    goal_id = state.get("goal_id", "")
    plan = str(state.get("campaign_plan", {}))
    
    if not target:
        logger.warning("[Auditor] No target_agent provided. Defaulting to END.")
        return {"next_agent": "__end__"}

    tools_used = "Publisher (APIs)" if target == "publisher" else "SkillForge (Sandboxed Web Execution)"
    await agent_thought_push(user_id, "auditor", f"intercepted flow to {target}. calculating risk vector topology...", goal_id)
    
    # 1. Fetch risk_tolerance
    risk_tolerance = 70
    try:
        async with async_session() as session:
            result = await session.execute(select(AgencySettings).where(AgencySettings.user_id == user_id))
            cfg = result.scalar_one_or_none()
            if cfg and cfg.risk_tolerance is not None:
                risk_tolerance = cfg.risk_tolerance
    except Exception as e:
        logger.error(f"[Auditor] Error fetching settings: {e}")
        
    # 2. Grade Risk
    prompt = f"""
You are the Risk Management Auditor for an autonomous social media agency.
The manager wants to execute a task using the {tools_used}.

Target: {target}
Current Campaign Context: {plan[:1000]}

Rate the risk of this single action from 0 to 100 based on these criteria:
0-30: Safe (drafting text, querying open internet, fetching metrics)
40-70: Moderate (posting standard content via official APIs, running harmless Playwright searches)
80-100: Critical / Dangerous (injecting banking passwords, scraping behind logins, spending money, executing unknown injected code)

Output ONLY an integer between 0 and 100.
"""
    try:
        score_str = await generate_completion(prompt, "You output raw integers only.")
        score = int(''.join(filter(str.isdigit, score_str))) # parse just numbers
    except Exception as e:
        logger.warning(f"[Auditor] LLM failed to grade risk: {e}. Defaulting to 90.")
        score = 90
        
    await agent_thought_push(user_id, "auditor", f"assessed action risk at {score}/100. Tolerance is {risk_tolerance}/100.", goal_id)
    
    if score > risk_tolerance:
        # Halt execution
        msg = f"🛑 **Action Blocked by Auditor.** Risk score ({score}) exceeds your tolerance ({risk_tolerance}). I need manual approval to proceed with `{target}`."
        await chat_push(user_id, msg, "auditor", goal_id)
        
        return {
            "risk_score": score,
            "next_agent": "__end__",  # Freeze graph
            "approval_status": "awaiting_approval_high_risk" 
        }
    else:
        # Forward freely!
        return {
            "risk_score": score,
            "next_agent": target, # Forward accurately to where Manager wanted!
            "target_agent": None  # Clean up proxy
        }
