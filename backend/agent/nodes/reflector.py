"""
Digital Force — Reflector Node
Post-campaign analysis and Episodic Memory Generation.
"""
import logging
import uuid
import json
from datetime import datetime
from agent.state import AgentState
from agent.llm import generate_completion
from agent.chat_push import agent_thought_push, chat_push
from database import async_session, KnowledgeItem

logger = logging.getLogger(__name__)

async def reflector_node(state: AgentState) -> dict:
    """
    Evaluates completed campaigns to extract actionable lessons and saves them
    into Qdrant as Episodic Memory so the Strategist never makes the same mistake twice.
    """
    goal_id = state['goal_id']
    user_id = state.get('created_by', '')
    logger.info(f"[Reflector] Analyzing completed goal {goal_id} for Episodic Memory.")

    await agent_thought_push(
        user_id=user_id,
        context="campaign completed. engaging neural reflection to generate episodic memories for future campaigns",
        agent_name="reflector",
        goal_id=goal_id
    )

    plan = str(state.get("campaign_plan", {}))
    kpis = state.get("kpi_snapshot", {})
    failed_tasks = state.get("failed_task_ids", [])
    
    prompt = f"""You are the Reflector Node of an autonomous social media agency.
A campaign just finished. 

Plan executing:
{plan[:1500]}

KPI Snapshot:
Total Tasks: {kpis.get('total_tasks', 0)}
Failed Tasks: {len(failed_tasks)}

Analyze the approach and extract exactly ONE core actionable "Lesson" (an episodic memory) that should be remembered for all future campaigns to improve performance. 
Format it as a single straightforward sentence. e.g. "Using formal language on TikTok results in worse engagement, use colloquial internet slang."
"""
    try:
        lesson = await generate_completion(prompt, "You are a senior marketing strategist analyzing post-mortem data.")
        lesson = lesson.strip(' "') # clean quotes
        
        # Save as Knowledge Item (Episodic Memory)
        async with async_session() as session:
            ki = KnowledgeItem(
                id=str(uuid.uuid4()),
                title=f"Episodic Memory: Goal {goal_id[:8]}",
                source_type="text",
                raw_content=lesson,
                category="episodic_memory",
                tags=json.dumps(["auto_generated", "lesson"]),
                processing_status="processing", # ready for qdrant worker
                uploaded_by=user_id
            )
            session.add(ki)
            await session.commit()
            
        await agent_thought_push(user_id, "reflector", f"extracted permanent episodic memory: {lesson}.", goal_id)
        
    except Exception as e:
        logger.error(f"[Reflector] Failed to generate episodic memory: {e}")
        
    # After reflecting, the graph truly ends.
    return {"next_agent": "__end__"}
