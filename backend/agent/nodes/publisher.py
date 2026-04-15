"""
Digital Force — Publisher Agent Node
Posts content to all platforms via Buffer API + Facebook Graph API.
"""

import json
import logging
import httpx
from datetime import datetime
from agent.state import AgentState
from agent.chat_push import chat_push
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

BUFFER_API = "https://api.bufferapp.com/1"
FB_API = f"https://graph.facebook.com/{settings.facebook_api_version}"

# Platform → Buffer profile lookup (set via Settings in DB)
BUFFER_PLATFORMS = {"linkedin", "twitter", "tiktok", "instagram", "youtube", "pinterest", "threads"}
FACEBOOK_PLATFORMS = {"facebook"}


# ─── Buffer Publisher ─────────────────────────────────────

async def _get_buffer_profiles() -> dict:
    """Get all connected Buffer profile IDs keyed by service."""
    if not settings.buffer_access_token:
        return {}
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BUFFER_API}/profiles.json",
            params={"access_token": settings.buffer_access_token}
        )
        if resp.status_code == 200:
            profiles = resp.json()
            return {p["service"]: p["id"] for p in profiles if p.get("id")}
    return {}


async def _buffer_post(
    profile_id: str,
    text: str,
    media_urls: list[str] = None,
    scheduled_at: str = None,
) -> dict:
    """Post to a Buffer profile."""
    payload = {
        "access_token": settings.buffer_access_token,
        "profile_ids[]": profile_id,
        "text": text,
        "now": scheduled_at is None,
    }
    if scheduled_at:
        payload["scheduled_at"] = scheduled_at
    if media_urls:
        for i, url in enumerate(media_urls[:4]):
            payload[f"media[picture]"] = url  # Buffer supports single image this way

    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BUFFER_API}/updates/create.json", data=payload)
        data = resp.json()
        if resp.status_code in (200, 201) and data.get("success"):
            updates = data.get("updates", [{}])
            return {"success": True, "platform_post_id": updates[0].get("id"), "platform_url": None}
        return {"success": False, "error": data.get("message", "Buffer API error")}


# ─── Facebook Graph Publisher ──────────────────────────────

async def _facebook_post(
    text: str,
    media_urls: list[str] = None,
    scheduled_at: str = None,
) -> dict:
    """Post to Facebook Page via Graph API."""
    if not settings.facebook_access_token or not settings.facebook_page_id:
        return {"success": False, "error": "Facebook not configured"}

    page_id = settings.facebook_page_id
    token = settings.facebook_access_token

    async with httpx.AsyncClient() as client:
        if media_urls:
            # Photo post
            endpoint = f"{FB_API}/{page_id}/photos"
            payload = {"message": text, "url": media_urls[0], "access_token": token}
        else:
            # Text/link post
            endpoint = f"{FB_API}/{page_id}/feed"
            payload = {"message": text, "access_token": token}

        if scheduled_at:
            from datetime import datetime
            dt = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
            payload["published"] = "false"
            payload["scheduled_publish_time"] = int(dt.timestamp())

        resp = await client.post(endpoint, data=payload)
        data = resp.json()

        if "id" in data:
            post_id = data["id"]
            return {
                "success": True,
                "platform_post_id": post_id,
                "platform_url": f"https://facebook.com/{post_id}"
            }
        return {"success": False, "error": data.get("error", {}).get("message", "Facebook API error")}


# ─── Main Publisher Node ───────────────────────────────────

async def publisher_node(state: AgentState) -> dict:
    """
    Takes approved tasks marked as 'post_content', resolves content + assets,
    and publishes to the appropriate platform.
    """
    goal_id = state['goal_id']
    user_id = state.get('created_by', '')
    logger.info(f"[Publisher] Processing publish tasks for goal {goal_id}")

    tasks = state.get("tasks", [])
    completed = set(state.get("completed_task_ids", []))
    failed = set(state.get("failed_task_ids", []))

    publish_tasks = [
        t for t in tasks
        if t.get("task_type") == "post_content" and t.get("id") not in completed | failed
    ]

    if not publish_tasks:
        return {
            "next_agent": "monitor",
            "messages": [{"role": "publisher", "content": "No pending publish tasks."}]
        }

    await chat_push(
        user_id=user_id,
        content=f"📤 Publishing {len(publish_tasks)} post(s) to your platforms...",
        agent_name="publisher",
        goal_id=goal_id,
    )

    buffer_profiles = await _get_buffer_profiles()
    newly_completed = []
    newly_failed = []
    messages = []

    for task in publish_tasks[:5]:  # Process up to 5 at a time
        platform = task.get("platform", "").lower()
        content = task.get("result", {})
        caption = content.get("caption", task.get("description", ""))
        hashtags = " ".join([f"#{h.lstrip('#')}" for h in content.get("hashtags", [])])
        full_text = f"{caption}\n\n{hashtags}".strip()
        media_urls = content.get("media_urls", [])
        scheduled_for = task.get("scheduled_for")

        try:
            if platform in FACEBOOK_PLATFORMS:
                result = await _facebook_post(full_text, media_urls, scheduled_for)
            elif platform in BUFFER_PLATFORMS and buffer_profiles.get(platform):
                profile_id = buffer_profiles[platform]
                result = await _buffer_post(profile_id, full_text, media_urls, scheduled_for)
            else:
                # Simulation mode — log but don't actually post
                result = {
                    "success": True,
                    "platform_post_id": f"sim_{platform}_{datetime.utcnow().timestamp():.0f}",
                    "simulation": True,
                }
                logger.info(f"[Publisher] SIMULATION: Would post to {platform}: {full_text[:80]}...")

            if result["success"]:
                newly_completed.append(task.get("id", ""))
                sim_note = " (simulated — connect platforms in Settings)" if result.get("simulation") else ""
                await chat_push(
                    user_id=user_id,
                    content=f"✅ Published to **{platform.capitalize()}**{sim_note}: \"{caption[:60]}...\"",
                    agent_name="publisher",
                    goal_id=goal_id,
                    metadata={"platform": platform, "post_id": result.get("platform_post_id")},
                )
                messages.append({"role": "publisher", "content": f"✅ Posted to {platform}: {caption[:50]}..."})
            else:
                newly_failed.append(task.get("id", ""))
                await chat_push(
                    user_id=user_id,
                    content=f"❌ Failed to publish to **{platform.capitalize()}**: {result.get('error', 'Unknown error')}",
                    agent_name="publisher",
                    goal_id=goal_id,
                )
                messages.append({"role": "publisher", "content": f"❌ Failed {platform}: {result.get('error')}"})

        except Exception as e:
            logger.error(f"[Publisher] Error posting to {platform}: {e}")
            newly_failed.append(task.get("id", ""))

    return {
        "completed_task_ids": list(completed) + newly_completed,
        "failed_task_ids": list(failed) + newly_failed,
        "messages": messages,
        "next_agent": "skillforge" if newly_failed else "monitor",
    }
