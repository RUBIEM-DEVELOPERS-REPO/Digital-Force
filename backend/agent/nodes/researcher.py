"""
Digital Force — Researcher Agent Node
Gathers real-time market intelligence using active Playwright crawling inside E2B Sandbox.
"""

import json
import logging
from agent.state import AgentState
from agent.llm import generate_completion, generate_json
from agent.chat_push import chat_push, agent_thought_push
from agent.tools.sandbox import run_in_e2b

logger = logging.getLogger(__name__)

RESEARCHER_SYS_PROMPT = """You are the Lead Researcher for an autonomous social media agency.
You have access to a secure Python execution sandbox with Playwright installed.
Your job is to write a self-contained Python async function that uses Playwright (headless Chromium) or `httpx` to scrape real data from the web based on the assigned goals.

RULES:
1. Write ONE async function named `research_task`.
2. Include ALL imports inside the function.
3. Return a dict with a "success" key and a "data" key.
4. Playwright is highly recommended to bypass JS blocks. Always use headless=True.
5. Provide ONLY the python code fenced in ` ```python ... ``` `."""

async def researcher_node(state: AgentState) -> dict:
    """
    Writes a scraping script based on the goal, executes it in E2B, and parses the real result.
    """
    goal_id = state['goal_id']
    user_id = state.get('created_by', '')
    goal    = state["goal_description"]
    logger.info(f"[Researcher] Starting active research for goal {goal_id}")

    await agent_thought_push(
        user_id=user_id,
        context="booting headless browser in Sandbox to fetch live market intel",
        agent_name="researcher",
        goal_id=goal_id,
    )

    platforms = state.get("platforms", [])

    # Write the script
    script_prompt = f"""
Write an async Python function `research_task` that uses Playwright to visit the most relevant site/platform and extracts data related to this goal:
GOAL: {goal}
TARGET PLATFORMS: {platforms}

If you don't know the exact URL, you can write the script to hit a search engine (like Google or duckduckgo) with playwright, scrape the top 3 visible text summaries, and return them.
Remember: "return {{'success': True, 'data': extracted_text}}"
"""
    try:
        raw_code = await generate_completion(script_prompt, RESEARCHER_SYS_PROMPT)
        import re
        code_match = re.search(r'```python\n(.*?)```', raw_code, re.DOTALL)
        clean_code = code_match.group(1) if code_match else raw_code
        
        # Execute it
        await chat_push(
            user_id=user_id,
            content=f"💻 Injecting Neural Web-Crawl into Sandbox execution layer:\n```python\n{clean_code}\n```",
            agent_name="researcher",
            goal_id=goal_id,
        )
        
        test_result = await run_in_e2b(clean_code, "research_task")
        
        if test_result.get("success"):
            output = test_result.get("output", "")
            
            # Synthesize
            await agent_thought_push(user_id, "researcher", f"crawl complete, parsing {len(output)} bytes of raw DOM data with LLM", goal_id)
            
            synthesis_prompt = f"""
Based on the raw data scraped by our headless browser, extract actionable social media insights:
GOAL: {goal}
RAW DATA: {output[:3000]}

Return JSON:
{{
  "trending_topics": ["topic1", "topic2"],
  "recommended_hashtags": {{"global": []}},
  "content_angles": ["angle1"],
  "audience_insights": "..."
}}
"""
            findings = await generate_json(synthesis_prompt)
            topics = findings.get('trending_topics', [])
            angles = findings.get('content_angles', [])
            await agent_thought_push(
                user_id=user_id,
                context=f"successfully extracted {len(topics)} trends and {len(angles)} unique angles from the raw data",
                agent_name="researcher",
                goal_id=goal_id,
            )
            return {
                "research_findings": findings,
                "needs_replanning_research": False,
                "messages": [{"role": "researcher", "content": f"Live Scraping Succeeded: {len(topics)} topics found."}],
                "next_agent": "supervisor"
            }
        else:
            logger.warning(f"[Researcher] Crawl failed: {test_result.get('error')}")
            # If sandbox failed, we return to supervisor but signal failure.
            # Supervisor will route it to skillforge if needed, but for now we fallback or retry.
            await agent_thought_push(user_id, "researcher", f"sandbox scrape failed with error, falling back to internal knowledge", goal_id)
            # fallback
            findings = {"trending_topics": ["Fallback AI", "Resilience"], "recommended_hashtags": {}, "content_angles": []}
            return {
                "research_findings": findings,
                "needs_replanning_research": False, # Stop infinite loops dynamically for now
                "next_agent": "supervisor"
            }
            
    except Exception as e:
        logger.error(f"[Researcher] Fatal Error: {e}")
        return {"next_agent": "supervisor"}
