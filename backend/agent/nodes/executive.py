"""
Digital Force — Executive Node
The conversational face of Digital Force. Instantly receives user commands, determines intent, replies based on configured User Tone, and conditionally passes the execution to the Manager.
"""

import logging
from agent.state import AgentState
from agent.llm import generate_structured_output
from agent.chat_push import chat_push

logger = logging.getLogger(__name__)

async def executive_node(state: AgentState) -> dict:
    """
    Acts as the entry point for all UI interaction.
    Reads the latest message, determines if an action/goal is required, and replies directly to the UI.
    """
    user_id = state.get("created_by", "")
    goal_id = state.get("goal_id")
    messages = state.get("messages", [])
    
    if not messages:
        return {"next_agent": "__end__"}
        
    last_message = messages[-1] if isinstance(messages[-1], str) else messages[-1].get("content", "")
    logger.info(f"[Executive] Processing user message: {last_message[:50]}...")
    
    # Fetch Persona Tone
    agent_tone = "Highly professional, direct, and slightly futuristic"
    if user_id:
        from database import async_session, AgencySettings
        from sqlalchemy import select
        async with async_session() as session:
            result = await session.execute(select(AgencySettings).where(AgencySettings.user_id == user_id))
            settings = result.scalar_one_or_none()
            if settings and settings.agent_tone:
                agent_tone = settings.agent_tone
                
    # 1. NLP Intent Evaluation
    from agent.llm import generate_json
    import json
    
    recent_history = [
        {"role": m.get("role", "user") if isinstance(m, dict) else "user", 
         "content": m.get("content", "") if isinstance(m, dict) else str(m)}
        for m in messages[-4:]
    ]

    prompt = f"""You are the Executive interface of Digital Force, an autonomous AI agency.
Determine the user's intent from the following message, and reply.
Your persona and tone: {agent_tone}

Recent context:
{json.dumps(recent_history, indent=2)}

Determine if the user is asking you to start a task, create a goal, execute something, or analyze data. If yes, it requires the Manager's attention.
If the user is approving a previously proposed plan, mark approval_status as "approved". If rejecting, mark "rejected". Otherwise "none".

Return strictly JSON:
{{
  "reply": "Your dynamic response to the user, in character.",
  "requires_manager": <boolean>,
  "approval_status": "approved" | "rejected" | "none"
}}"""

    try:
        response = await generate_json(prompt)
        reply = response.get("reply", "Acknowledged.")
        requires_manager = response.get("requires_manager", False)
        approval_status = response.get("approval_status", "none")
    except Exception as e:
        logger.error(f"[Executive] NLP parsing failed: {e}")
        reply = "Acknowledged. Routing internal systems to compensate."
        requires_manager = True
        approval_status = "none"

    # 2. Push direct response to user
    await chat_push(
        user_id=user_id,
        content=reply,
        agent_name="digital force - executive",
        goal_id=goal_id
    )

    if requires_manager:
        if approval_status in ["approved", "rejected"]:
            return {"next_agent": "manager", "approval_status": approval_status}
        return {"next_agent": "manager"}
    
    return {"next_agent": "__end__"}
