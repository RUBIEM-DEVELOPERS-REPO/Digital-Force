"""
Digital Force — Agent Web Search Tool
Powered by Tavily API. Available to ALL agents as a shared utility.

Usage (from any agent node):
    from agent.tools.web_search import web_search, search_for_solution

    results = await web_search("trending AI hashtags LinkedIn 2025")
    fix = await search_for_solution("httpx ConnectionError posting to Facebook API")
"""

import logging
from typing import Optional
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

TAVILY_URL = "https://api.tavily.com/search"


async def web_search(
    query: str,
    count: int = 5,
    search_depth: str = "basic",   # "basic" or "advanced"
    include_answer: bool = True,   # Tavily direct answer synthesis
    include_domains: list[str] = None,
    exclude_domains: list[str] = None,
) -> dict:
    """
    Search the web via Tavily and return structured results.

    Returns:
        {
            "success": True,
            "answer": "AI-synthesized direct answer",
            "results": [
                { "title", "url", "content", "score" },
                ...
            ],
            "query": original query
        }
    """
    if not settings.tavily_api_key:
        logger.warning("[WebSearch] Tavily API key not set — returning empty results")
        return {"success": False, "error": "Tavily API key not configured", "results": [], "query": query}

    import httpx
    payload = {
        "api_key": settings.tavily_api_key,
        "query": query,
        "max_results": count,
        "search_depth": search_depth,
        "include_answer": include_answer,
        "include_raw_content": False,
    }
    if include_domains:
        payload["include_domains"] = include_domains
    if exclude_domains:
        payload["exclude_domains"] = exclude_domains

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(TAVILY_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()

        return {
            "success": True,
            "answer": data.get("answer", ""),
            "results": [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", "")[:600],  # cap at 600 chars
                    "score": r.get("score", 0),
                }
                for r in data.get("results", [])
            ],
            "query": query,
        }
    except Exception as e:
        logger.error(f"[WebSearch] Search failed for '{query}': {e}")
        return {"success": False, "error": str(e), "results": [], "query": query}


async def search_for_solution(error_description: str, context: str = "") -> str:
    """
    Search the web specifically to find a solution to a technical error.
    Returns a plain-English summary of the best solution found.
    Used by SkillForge when it needs ideas for fixing a failed task.
    """
    query = f"fix solution: {error_description} python social media API"
    if context:
        query += f" {context}"

    result = await web_search(query, count=5, search_depth="advanced", include_answer=True)

    if not result["success"]:
        return f"Could not search for solution: {result.get('error')}"

    # Build a rich context string for the LLM
    parts = []
    if result["answer"]:
        parts.append(f"Direct answer: {result['answer']}")

    for r in result["results"][:3]:
        parts.append(f"\n[{r['title']}] {r['content']}")

    return "\n".join(parts) if parts else "No relevant solutions found online."


async def search_social_trends(
    topic: str,
    platforms: list[str] = None,
) -> dict:
    """
    Search for trending content, hashtags, and strategies for a specific topic.
    Optimised for social media marketing context.
    """
    platform_str = " ".join(platforms) if platforms else "social media"
    query = f"{topic} trending {platform_str} content strategy 2025"

    result = await web_search(
        query,
        count=6,
        search_depth="advanced",
        include_answer=True,
        exclude_domains=["reddit.com"],  # exclude Reddit noise for trends
    )

    # Deduplicate and rank
    seen_domains = set()
    top_results = []
    for r in result.get("results", []):
        domain = r["url"].split("/")[2] if "/" in r["url"] else r["url"]
        if domain not in seen_domains:
            seen_domains.add(domain)
            top_results.append(r)

    result["results"] = top_results
    result["topic"] = topic
    result["platforms"] = platforms or []
    return result


async def scrape_website(url: str) -> str:
    """
    Extract the raw content of a specific URL using Tavily's extract API.
    Bypasses Cloudflare and other bot protections.
    """
    if not settings.tavily_api_key:
        return "Error: Tavily API key not configured."

    import httpx
    payload = {
        "api_key": settings.tavily_api_key,
        "urls": [url],
        "include_raw_content": True
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post("https://api.tavily.com/extract", json=payload)
            resp.raise_for_status()
            data = resp.json()
            
        results = data.get("results", [])
        if results and results[0].get("raw_content"):
            return results[0]["raw_content"]
        else:
            return f"Failed to extract content from {url}. It may be blocking scrapers or returning empty HTML."
    except Exception as e:
        logger.error(f"[Scraper] Failed to scrape {url}: {e}")
        return f"Error scraping {url}: {str(e)}"
