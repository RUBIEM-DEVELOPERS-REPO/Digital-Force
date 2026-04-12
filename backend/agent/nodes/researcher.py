"""
Digital Force — Researcher Agent Node
Gathers real-time market intelligence: trends, competitors, audience data.
"""

import logging
import httpx
from agent.state import AgentState
from agent.llm import generate_json
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def _brave_search(query: str, count: int = 5) -> list[dict]:
    """Use Brave Search API for web research."""
    if not settings.brave_search_api_key:
        return []
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={"Accept": "application/json", "X-Subscription-Token": settings.brave_search_api_key},
            params={"q": query, "count": count}
        )
        if resp.status_code == 200:
            data = resp.json()
            return [{"title": r.get("title"), "snippet": r.get("description"), "url": r.get("url")}
                    for r in data.get("web", {}).get("results", [])]
    return []


async def researcher_node(state: AgentState) -> dict:
    """
    Conducts web research to inform the campaign strategy.
    Searches for: trending topics, competitor content, audience insights.
    """
    logger.info(f"[Researcher] Starting research for goal {state['goal_id']}")

    platforms = state.get("platforms", [])
    goal = state["goal_description"]

    # Build targeted search queries
    queries = [
        f"trending content {' '.join(platforms)} {datetime.now().strftime('%B %Y')}",
        f"best performing social media content strategy {' '.join(platforms)}",
        f"viral content tactics {platforms[0] if platforms else 'social media'} 2025",
    ]

    # Add goal-specific searches
    import re
    keywords = re.findall(r'\b[A-Z][a-z]+\b|\b\w{6,}\b', goal)[:3]
    if keywords:
        queries.append(f"{' '.join(keywords[:2])} social media campaign ideas")

    raw_results = []
    for q in queries[:3]:  # Limit to 3 searches
        results = await _brave_search(q, count=3)
        raw_results.extend(results)

    # Synthesize findings with LLM
    if raw_results:
        synthesis_prompt = f"""
Based on these search results about social media trends and the goal below, 
extract the most actionable insights for a social media campaign.

GOAL: {goal}
PLATFORMS: {platforms}

SEARCH RESULTS:
{chr(10).join([f"- {r['title']}: {r['snippet']}" for r in raw_results if r.get('snippet')])}

Return JSON with:
{{
  "trending_topics": ["topic1", "topic2"],
  "recommended_hashtags": {{"linkedin": [], "instagram": [], "tiktok": []}},
  "content_angles": ["angle1", "angle2"],
  "competitor_insights": "...",
  "audience_insights": "...",
  "timing_recommendations": {{}}
}}
"""
        try:
            from datetime import datetime
            findings = await generate_json(synthesis_prompt)
        except Exception:
            findings = {"trending_topics": [], "content_angles": [], "raw_results": raw_results[:3]}
    else:
        # No API key — use LLM knowledge directly
        from datetime import datetime
        findings_prompt = f"""
Based on your knowledge of social media trends as of {datetime.now().strftime('%Y')}, 
provide research insights for this campaign:

GOAL: {goal}
PLATFORMS: {platforms}

Return JSON:
{{
  "trending_topics": ["topic1", "topic2"],
  "recommended_hashtags": {{"linkedin": [], "instagram": [], "tiktok": []}},
  "content_angles": ["angle1", "angle2"],
  "audience_insights": "...",
  "timing_recommendations": {{}}
}}
"""
        try:
            findings = await generate_json(findings_prompt)
        except Exception as e:
            logger.warning(f"[Researcher] Research synthesis failed: {e}")
            findings = {}

    logger.info(f"[Researcher] Research complete. Found {len(findings.get('trending_topics', []))} trends.")

    return {
        "research_findings": findings,
        "messages": [{"role": "researcher", "content": f"Research complete. {len(findings.get('content_angles', []))} content angles identified."}],
        "next_agent": "strategist",
    }


# Fix missing import
from datetime import datetime
