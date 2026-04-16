"""
Digital Force — Agent LLM Client
9-Model Cascading Router (3 API Keys × 3 Models).
Strictly uses Groq for massive speed and hyper-resilience against rate-limits.
"""

import json
import re
import logging
from typing import Optional, AsyncGenerator
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_cascade_configs():
    """Return list of (api_key, model_name) tightly ordered for the fallback cascade."""
    keys = [k for k in [settings.groq_api_key_1, settings.groq_api_key_2, settings.groq_api_key_3] if k]
    if not keys:
        raise ValueError("No Groq API keys configured. Set GROQ_API_KEY_1, 2, or 3 in .env")
        
    models = [
        settings.groq_primary_model,      # llama-3.3-70b-versatile
        settings.groq_secondary_model,    # mixtral-8x7b-32768
        settings.groq_fallback_model      # groq/compound
    ]
    
    configs = []
    # Rotate: Key 1 tests all 3 models, then Key 2 tests all 3, then Key 3...
    for key in keys:
        for model in models:
            if model:
                configs.append((key, model))
    
    return configs


async def generate_completion(
    prompt: str,
    system_prompt: str = "",
    prefer_reasoning: bool = False, # Maintained for function signature compatibility with existing Graph Nodes
    temperature: float = 0.7,
) -> str:
    """Invokes the LangChain LLM, rotating automatically across 9 models if rate-limits or errors hit."""
    from langchain_core.messages import SystemMessage, HumanMessage
    from langchain_groq import ChatGroq
    
    messages = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=prompt))
    
    configs = _get_cascade_configs()
    last_error = None
    
    for attempt, (api_key, model) in enumerate(configs, 1):
        try:
            llm = ChatGroq(
                model=model,
                api_key=api_key,
                temperature=temperature,
                max_tokens=settings.groq_max_tokens,
                max_retries=0, # We handle the retries inside this pure Python loop
            )
            response = await llm.ainvoke(messages)
            return response.content
            
        except Exception as e:
            last_error = e
            logger.warning(f"[LLM Cascade] Attempt {attempt}/{len(configs)} failed (Key: ...{api_key[-4:]}, Model: {model}): {e}")
            
    logger.error(f"[LLM Cascade] CRITICAL: ALL {len(configs)} models failed. Agents are halted. Final error: {last_error}")
    raise last_error


async def generate_json(
    prompt: str,
    system_prompt: str = "",
    prefer_reasoning: bool = False,
) -> dict:
    """Generate and natively parse a JSON object from the AI."""
    sys = (system_prompt or "") + "\n\nRESPOND WITH VALID JSON ONLY. No markdown fences, no explanation."
    # Use low temperature for deterministic JSON structuring
    raw = await generate_completion(prompt, sys, prefer_reasoning=prefer_reasoning, temperature=0.3)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"LLM did not return valid JSON: {raw[:300]}")


async def stream_chat_response(
    system: str,
    user: str,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> AsyncGenerator[str, None]:
    """
    Legacy single-turn stream (kept for compatibility). Prefer stream_chat_with_history.
    """
    async for token in stream_chat_with_history(
        system=system,
        messages=[{"role": "user", "content": user}],
        temperature=temperature,
        max_tokens=max_tokens,
    ):
        yield token


async def stream_chat_with_history(
    system: str,
    messages: list,
    temperature: float = 0.7,
    max_tokens: int = 1500,
) -> AsyncGenerator[str, None]:
    """
    Memory-aware chat streaming. Passes the FULL conversation history to Groq
    as a proper multi-turn messages[] array so the model has context.

    messages format: [{"role": "user"|"assistant"|"agent", "content": "..."}]
    "agent" roles are remapped to "assistant" for the Groq API.
    """
    from groq import AsyncGroq
    configs = _get_cascade_configs()
    last_error = None

    # Normalise roles: Groq only accepts "user" | "assistant" | "system"
    groq_messages = [{"role": "system", "content": system}]
    for m in messages:
        role = m.get("role", "user")
        if role not in ("user", "assistant"):
            role = "assistant"  # agent messages appear as assistant context
        groq_messages.append({"role": role, "content": m.get("content", "")})

    for attempt, (api_key, model) in enumerate(configs, 1):
        try:
            client = AsyncGroq(api_key=api_key, max_retries=0)
            stream = await client.chat.completions.create(
                model=model,
                messages=groq_messages,
                stream=True,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
            return

        except Exception as e:
            last_error = e
            logger.warning(f"[LLM Stream History Cascade] Attempt {attempt}/{len(configs)} failed: {e}")

    logger.error("[LLM Stream History] All Groq API connections failed. Falling back to non-streaming.")
    full = await generate_completion(
        prompt=messages[-1].get("content", "") if messages else "",
        system_prompt=system,
        temperature=temperature,
    )
    for word in full.split(" "):
        yield word + " "


def get_llm_client():
    from config import get_settings
    s = get_settings()
    return {
        "groq_1": bool(s.groq_api_key_1),
        "groq_2": bool(s.groq_api_key_2),
        "groq_3": bool(s.groq_api_key_3),
        "stream_chat": stream_chat_response,
    }


async def heal_dom_selector(screenshot_path: str, failed_selector: str) -> Optional[str]:
    """Uses Groq Llama-3.2-Vision to hot-patch broken CSS selectors from a DOM snapshot."""
    key = settings.groq_api_key_1 or settings.groq_api_key_2 or settings.groq_api_key_3
    if not key:
        logger.warning("[Vision Healer] No Groq API key available for Vision Healing.")
        return None
        
    try:
        import base64
        import os
        from groq import AsyncGroq
        
        if not os.path.exists(screenshot_path):
            return None
            
        client = AsyncGroq(api_key=key, max_retries=1)
        
        with open(screenshot_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
            
        prompt = (
            f"The CSS selector '{failed_selector}' timed out and failed acting on this page. "
            "Examine this screenshot of the page at the time of failure. Identify the UI element "
            "that the script was trying to interact with using that old selector. "
            "Return ONLY the new valid CSS selector string that targets that element. No markdown, no explanations."
        )
        
        resp = await client.chat.completions.create(
            model="llama-3.2-90b-vision-preview",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
                ]
            }],
            max_tokens=50,
            temperature=0.1
        )
        new_selector = resp.choices[0].message.content.strip().strip("'\"`")
        if new_selector and len(new_selector) < 100:
            return new_selector
    except Exception as e:
        logger.error(f"[Vision Healer] Failed to heal DOM selector: {e}")
    return None
