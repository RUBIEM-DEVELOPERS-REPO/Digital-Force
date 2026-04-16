"""
Digital Force — Executive Node
The conversational face of Digital Force. Instantly receives user commands, determines intent, replies based on configured User Tone, and conditionally passes the execution to the Manager.
"""

import logging
from agent.state import AgentState
from agent.chat_push import chat_push

logger = logging.getLogger(__name__)

async def executive_node(state: AgentState) -> dict:
    """
    Acts as the entry point for all UI interaction.
    Reads the latest message, determines if an action/goal is required, and replies directly to the UI.
    """
    user_id = state.get("created_by", "")
    
    if state.get("next_agent"):
        logger.info("[Executive] Bypassing NLP; intent already evaluated by streaming chat API.")
        return {"next_agent": state.get("next_agent")}
        
    goal_id = state.get("goal_id")
    messages = state.get("messages", [])
    
    if not messages:
        # Automated trigger / API POST without UI history: skip intent evaluation and go straight to Manager
        # BUGFIX: Ensure `messages` is seeded so the Manager does not throw IndexError on `messages[-1]`.
        state["messages"] = [{"role": "user", "content": "Trigger execution cycle."}]
        return {"messages": state["messages"], "next_agent": "manager"}
        
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
        {"role": m.get("role", "user") if isinstance(m, dict) and m.get("role") in ["user", "assistant", "system"] else "assistant", 
         "name": m.get("name") or (m.get("role") if isinstance(m, dict) and m.get("role") not in ["user", "assistant", "system"] else None),
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
If the user is explicitly providing credentials, a password, a 2FA code, or telling you to inherently update the 'Truth Bucket' for an account, provide the account name you detect, and the specific text to append to their auth_data bucket.

Return strictly JSON:
{{
  "reply": "Your dynamic response to the user, in character.",
  "requires_manager": <boolean>,
  "approval_status": "approved" | "rejected" | "none",
  "update_truth_bucket": {{
     "account_name_match": "string matching account name (e.g. 'Acme Corp') or null",
     "text_to_append": "Exact credential string to append safely to DB (e.g. 'Backup pass: 123') or null"
  }}
}}"""

    try:
        response = await generate_json(prompt)
        reply = response.get("reply", "Acknowledged.")
        requires_manager = response.get("requires_manager", False)
        approval_status = response.get("approval_status", "none")
        truth_update = response.get("update_truth_bucket")
        
        # Auto-save credentials to database Truth Bucket if detected
        if truth_update and isinstance(truth_update, dict) and truth_update.get("account_name_match"):
            account_match = truth_update.get("account_name_match")
            text_to_append = truth_update.get("text_to_append")
            if text_to_append:
                from database import async_session, PlatformConnection
                from sqlalchemy import select, or_
                async with async_session() as session:
                    match_str = f"%{account_match}%"
                    stmt = select(PlatformConnection).where(
                        or_(
                            PlatformConnection.account_label.ilike(match_str),
                            PlatformConnection.display_name.ilike(match_str)
                        )
                    )
                    conn = (await session.execute(stmt)).scalars().first()
                    if conn:
                        current = conn.auth_data or ""
                        conn.auth_data = f"{current}\n[Agent Auto-Saved Update]: {text_to_append}".strip()
                        await session.commit()
                        logger.info(f"[Executive] Successfully updated Truth Bucket for {conn.account_label}")
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
