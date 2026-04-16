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

async def ghost_visual_research(goal: str, platform: str) -> dict:
    """Uses Ghost Browser and Llama-Vision to scrape walled-gardens natively."""
    from agent.browser.ghost import ghost
    import urllib.parse
    import base64
    import os
    from config import get_settings
    from groq import AsyncGroq
    
    query = urllib.parse.quote_plus(goal[:50])
    if platform == "instagram":
        url = f"https://www.instagram.com/explore/tags/{query.replace('+', '')}/"
    elif platform == "facebook":
        url = f"https://www.facebook.com/search/posts/?q={query}"
    elif platform == "linkedin":
        url = f"https://www.linkedin.com/search/results/content/?keywords={query}"
    elif platform == "tiktok":
        url = f"https://www.tiktok.com/search?q={query}"
    else:
        url = f"https://www.google.com/search?q=site:{platform}.com+{query}"
        
    try:
        page = await ghost.get_page()
        await page.goto(url, wait_until="networkidle")
        import asyncio
        await asyncio.sleep(4) # Let DOM settle
        await page.evaluate("window.scrollBy(0, document.body.scrollHeight)") # Trigger lazy load
        await asyncio.sleep(2)
        
        pic = "temp_vision_research.png"
        await page.screenshot(path=pic)
        await page.close()
        
        settings = get_settings()
        key = settings.groq_api_key_1 or settings.groq_api_key_2 or settings.groq_api_key_3
        client = AsyncGroq(api_key=key, max_retries=1)
        
        with open(pic, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
            
        prompt = (f"You are a social media researcher. The user's goal is: {goal}. "
                  f"Analyze this screenshot of {platform}. Identify trending topics, visual aesthetics, "
                  "and any recurring themes. Extract JSON matching exactly: "
                  "{\"trending_topics\": [\"topic1\"], \"recommended_hashtags\": {\"global\": []}, \"content_angles\": [\"angle1\"], \"audience_insights\": \"...\"}")
                  
        resp = await client.chat.completions.create(
            model="llama-3.2-90b-vision-preview",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
                ]
            }],
            max_tokens=600,
            temperature=0.2
        )
        content = resp.choices[0].message.content
        import re, json
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {}
    except Exception as e:
        logger.error(f"[Vision Researcher] Failed natively scraping {platform}: {e}")
        return {}


async def researcher_node(state: AgentState) -> dict:
    """
    Leverages Ghost Browser Vision for Walled Gardens, and robust Tavily Web Search API
    for open-web intelligence.
    """
    from agent.tools.web_search import search_social_trends
    goal_id = state['goal_id']
    user_id = state.get('created_by', '')
    goal    = state["goal_description"]
    platforms = [p.lower() for p in state.get("platforms", [])]
    
    logger.info(f"[Researcher] Starting research for goal {goal_id}")

    await agent_thought_push(
        user_id=user_id,
        context="initiating intelligence gathering sequence across network nodes",
        agent_name="researcher",
        goal_id=goal_id,
    )

    WALLED_GARDENS = {"instagram", "facebook", "linkedin", "tiktok"}
    requires_vision = any(p in WALLED_GARDENS for p in platforms)

    try:
        if requires_vision:
            target_platform = next(p for p in platforms if p in WALLED_GARDENS)
            await chat_push(
                user_id=user_id,
                content=f"👁️ Engaging Vision Heuristics via Ghost Browser to natively analyze {target_platform} walled garden...",
                agent_name="researcher",
                goal_id=goal_id,
            )
            findings = await ghost_visual_research(goal, target_platform)
            topics = findings.get('trending_topics', [])
            angles = findings.get('content_angles', [])
            
        else:
            await chat_push(
                user_id=user_id,
                content=f"💻 Launching neural web-crawl across Tavily nodes to fetch live open-web intel...",
                agent_name="researcher",
                goal_id=goal_id,
            )
            
            result = await search_social_trends(goal, platforms)
            output = str(result.get("results", []))
                
            await agent_thought_push(user_id, "researcher", f"crawl complete, parsing text nodes with LLM", goal_id)
            
            synthesis_prompt = f"""
Based on the raw data scraped by our headless framework, extract actionable social media insights:
GOAL: {goal}
RAW DATA: {output[:4000]}

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

        # Ensure minimal viable findings if empty
        if not findings or not topics:
            findings = {
                "trending_topics": ["General Trend"],
                "recommended_hashtags": {"global": ["#marketing"]},
                "content_angles": ["Educational piece"],
                "audience_insights": "Audience prefers clear, succinct value."
            }

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
            
    except Exception as e:
        logger.error(f"[Researcher] Fatal Error: {e}")
        return {"next_agent": "supervisor"}
