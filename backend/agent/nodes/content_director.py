"""
Digital Force — Content Director Agent Node
Writes platform-optimized social media content using brand RAG context.
"""

import json
import logging
from agent.state import AgentState
from agent.llm import generate_completion, generate_json
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

PLATFORM_RULES = {
    "linkedin": {
        "max_chars": 3000, "optimal_chars": "150-300",
        "hashtags": "3-5", "tone_default": "professional, authoritative",
        "format_tip": "Use line breaks every 2-3 sentences. Strong opening hook. End with CTA or question.",
    },
    "facebook": {
        "max_chars": 63206, "optimal_chars": "100-250",
        "hashtags": "1-3", "tone_default": "conversational, relatable",
        "format_tip": "Emotional hook. Short paragraphs. Use emojis sparingly.",
    },
    "twitter": {
        "max_chars": 280, "optimal_chars": "240",
        "hashtags": "1-2", "tone_default": "punchy, bold, direct",
        "format_tip": "Pack value in every word. Use numbers. Question or bold statement.",
    },
    "tiktok": {
        "max_chars": 2200, "optimal_chars": "150-300",
        "hashtags": "3-6", "tone_default": "energetic, relatable, trendy",
        "format_tip": "Hook in first 3 words. Use trending sounds reference. Video description.",
    },
    "instagram": {
        "max_chars": 2200, "optimal_chars": "138-150",
        "hashtags": "10-15", "tone_default": "visual, inspiring, lifestyle",
        "format_tip": "Punchy first line (shown before 'more'). Hashtag block at end.",
    },
    "youtube": {
        "max_chars": 5000, "optimal_chars": "200-500",
        "hashtags": "5-10", "tone_default": "informative, engaging",
        "format_tip": "Include keywords naturally. Timestamps if applicable. CTA at end.",
    },
}


async def _fetch_brand_context(prompt: str, platform: str) -> str:
    """Query RAG memory for brand voice and relevant past content."""
    try:
        from rag.retriever import retrieve
        results = await retrieve(query=f"{platform} content: {prompt}", collection="brand", top_k=3)
        if results:
            return "\n".join([r.get("text", "") for r in results])
    except Exception as e:
        logger.warning(f"RAG retrieval failed: {e}")
    return ""


async def content_director_node(state: AgentState) -> dict:
    """
    Processes the current task's content brief and writes platform-optimized content.
    Called once per content generation task.
    """
    tasks = state.get("tasks", [])
    completed = state.get("completed_task_ids", [])

    # Find next content task to execute
    pending_task = next(
        (t for t in tasks if t.get("task_type") == "generate_content" and t.get("id") not in completed),
        None
    )

    if not pending_task:
        return {"next_agent": "publisher", "messages": [{"role": "content_director", "content": "All content tasks complete."}]}

    platform = pending_task.get("platform", "linkedin")
    brief = pending_task.get("content_brief", {})
    rules = PLATFORM_RULES.get(platform, PLATFORM_RULES["linkedin"])

    # Fetch brand voice from RAG
    brand_context = await _fetch_brand_context(state["goal_description"], platform)

    system_prompt = f"""You are an elite social media copywriter specializing in {platform}.

PLATFORM RULES:
- Optimal length: {rules['optimal_chars']} characters
- Hashtags: {rules['hashtags']} (relevant, not spammy)
- Tone: {brief.get('tone', rules['tone_default'])}
- Format tip: {rules['format_tip']}

BRAND VOICE CONTEXT:
{brand_context if brand_context else 'Use a professional, authoritative, inspiring voice.'}

OUTPUT JSON:
{{
  "caption": "Main post body",
  "hook": "First 10-15 words (the attention grabber)",
  "hashtags": ["tag1", "tag2"],
  "cta": "Call to action",
  "alt_text": "Image description for accessibility",
  "character_count": 0
}}"""

    user_prompt = f"""
CAMPAIGN: {state.get('campaign_plan', {}).get('campaign_name', 'Campaign')}
TASK: {pending_task.get('description')}
KEY MESSAGE: {brief.get('key_message', state['goal_description'])}
CONTENT TYPE: {brief.get('content_type', 'thought_leadership')}
PLATFORM: {platform}
RESEARCH CONTEXT: {json.dumps(state.get('research_findings', {}).get('content_angles', [])[:2])}

Write compelling, {platform}-native content that drives real engagement.
"""

    try:
        result = await generate_json(user_prompt, system_prompt)
        result["platform"] = platform
        result["task_id"] = pending_task.get("id", "")

        logger.info(f"[ContentDirector] Generated content for {platform}: {result.get('hook', '')[:50]}...")

        return {
            "messages": [{"role": "content_director", "content": f"Content written for {platform}: {result.get('hook', '')[:60]}..."}],
            "completed_task_ids": completed + [pending_task.get("id", "")],
            "next_agent": "visual_designer",
            "current_task_id": pending_task.get("id"),
        }

    except Exception as e:
        logger.error(f"[ContentDirector] Error: {e}")
        return {
            "error": str(e),
            "next_agent": "visual_designer",
        }
