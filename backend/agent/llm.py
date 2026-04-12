"""
Digital Force — Agent LLM Client
Groq primary, OpenAI fallback. Smart routing for reasoning vs speed.
"""

import json
import re
import logging
from typing import Optional
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def get_groq_llm(model: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 4096):
    from langchain_groq import ChatGroq
    return ChatGroq(
        model=model or settings.groq_primary_model,
        api_key=settings.groq_api_key,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def get_openai_llm(model: Optional[str] = None, temperature: float = 0.7):
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=model or settings.openai_reasoning_model,
        api_key=settings.openai_api_key,
        temperature=temperature,
    )


def get_primary_llm(prefer_reasoning: bool = False, temperature: float = 0.7):
    """Smart LLM selector — reasoning → GPT-4o, speed → Groq."""
    if prefer_reasoning and settings.openai_api_key:
        return get_openai_llm(temperature=temperature)
    elif settings.groq_api_key:
        return get_groq_llm(temperature=temperature)
    elif settings.openai_api_key:
        return get_openai_llm(temperature=temperature)
    else:
        raise ValueError("No LLM API key. Set GROQ_API_KEY or OPENAI_API_KEY in .env")


async def generate_completion(
    prompt: str,
    system_prompt: str = "",
    prefer_reasoning: bool = False,
    temperature: float = 0.7,
) -> str:
    from langchain_core.messages import SystemMessage, HumanMessage
    llm = get_primary_llm(prefer_reasoning=prefer_reasoning, temperature=temperature)
    messages = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=prompt))
    try:
        response = await llm.ainvoke(messages)
        return response.content
    except Exception as e:
        logger.warning(f"Primary LLM failed ({e}), trying fallback...")
        if settings.groq_api_key and prefer_reasoning:
            response = await get_groq_llm().ainvoke(messages)
            return response.content
        raise


async def generate_json(
    prompt: str,
    system_prompt: str = "",
    prefer_reasoning: bool = False,
) -> dict:
    """Generate and parse a JSON object from the LLM."""
    sys = (system_prompt or "") + "\n\nRESPOND WITH VALID JSON ONLY. No markdown fences, no explanation."
    raw = await generate_completion(prompt, sys, prefer_reasoning=prefer_reasoning, temperature=0.3)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"LLM did not return valid JSON: {raw[:300]}")
