"""
Digital Force — SkillForge Agent Node
Creates new Python skills on-demand using E2B sandboxed execution.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from agent.state import AgentState
from agent.llm import generate_completion
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

SKILLS_DIR = Path(__file__).parent.parent / "skills" / "generated"
SKILLS_DIR.mkdir(parents=True, exist_ok=True)

SKILL_SYSTEM_PROMPT = """You are SkillForge — an expert Python developer creating reusable tool functions for a social media AI agent.

Rules for generated skills:
1. Write a single async Python function
2. Include all imports at the top of the function
3. Handle all exceptions and return sensible defaults
4. Add a docstring explaining what the function does
5. The function must be fully self-contained (no external state)
6. Return a dict with a "success" key always

Example skill structure:
```python
async def check_hashtag_trend(hashtag: str, platform: str) -> dict:
    \"\"\"Check if a hashtag is currently trending on the given platform.\"\"\"
    import httpx
    try:
        # implementation
        return {"success": True, "is_trending": True, "rank": 5}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

Write clean, production-ready Python. No placeholder code."""


async def _run_in_e2b(code: str, function_name: str, test_args: dict) -> dict:
    """Execute generated code in E2B sandbox."""
    if not settings.e2b_api_key:
        logger.warning("[SkillForge] E2B not configured. Running in restricted local mode.")
        return await _run_local_test(code, function_name, test_args)

    try:
        from e2b_code_interpreter import Sandbox
        async with Sandbox(api_key=settings.e2b_api_key) as sbx:
            # Install common deps
            await sbx.commands.run("pip install httpx requests beautifulsoup4 -q")

            # Inject test runner
            test_code = f"""
import asyncio
{code}

async def _test():
    result = await {function_name}(**{json.dumps(test_args)})
    print("RESULT:", result)
    return result

asyncio.run(_test())
"""
            result = await sbx.run_code(test_code)
            output = result.text or ""
            success = "RESULT:" in output and "error" not in output.lower()
            return {"success": success, "output": output, "sandbox": "e2b"}
    except Exception as e:
        logger.error(f"[SkillForge] E2B execution failed: {e}")
        return {"success": False, "error": str(e)}


async def _run_local_test(code: str, function_name: str, test_args: dict) -> dict:
    """
    Restricted local test — only validates syntax, does NOT execute.
    Safe fallback when E2B is not configured.
    """
    import ast
    try:
        ast.parse(code)
        return {"success": True, "output": "Syntax valid (local mode — no execution)", "sandbox": "local_syntax_check"}
    except SyntaxError as e:
        return {"success": False, "error": f"Syntax error: {e}"}


async def skillforge_node(state: AgentState) -> dict:
    """
    Identifies skill gaps from failed tasks, generates new Python skills,
    validates them in sandbox, and registers them for future use.
    """
    logger.info(f"[SkillForge] Checking for skill gaps in goal {state['goal_id']}")

    failed_tasks = state.get("failed_task_ids", [])
    tasks = state.get("tasks", [])

    failed_task_details = [t for t in tasks if t.get("id") in failed_tasks]

    if not failed_task_details:
        return {
            "next_agent": "monitor",
            "messages": [{"role": "skillforge", "content": "No skill gaps identified."}]
        }

    # Analyze what new capability is needed
    analysis_prompt = f"""
A social media AI agent encountered failures while executing these tasks:
{json.dumps(failed_task_details, indent=2)}

What new Python function/skill or alternative approach would prevent these failures?
Respond with JSON:
{{
  "skill_name": "snake_case_function_name",
  "display_name": "Human Readable Name",
  "description": "Technical description of what this skill does",
  "input_params": {{"param_name": "type"}},
  "test_args": {{"param_name": "test_value"}},
  "risk_level": "low" | "medium" | "high",
  "non_technical_summary": "A 1-2 sentence simple explanation of what went wrong and how you are fixing it, suitable for a non-technical manager."
}}

Risk level guidelines:
- low: simple syntax fixes, using backup APIs, changing hashtags
- medium: scraping alternative sites, changing content formats
- high: brute forcing, deleting data, spending money, or violating rate limits
"""

    try:
        skill_spec = await generate_json(analysis_prompt)
    except Exception as e:
        logger.error(f"[SkillForge] Could not analyze skill gap: {e}")
        return {"next_agent": "monitor"}

    skill_name = skill_spec.get("skill_name", "new_skill")
    risk_level = skill_spec.get("risk_level", "high").lower()
    summary = skill_spec.get("non_technical_summary", "Implemented a new skill to bypass the error.")
    logger.info(f"[SkillForge] Forging new skill: {skill_name} (Risk: {risk_level})")

    # Generate the skill code
    code_prompt = f"""
Create a Python async function called '{skill_name}' that:
{skill_spec.get('description')}

Input parameters: {json.dumps(skill_spec.get('input_params', {}))}

Context: This is for a social media AI agent that manages content across LinkedIn, Facebook, TikTok, Instagram, X, YouTube.
"""

    raw_code = await generate_completion(code_prompt, SKILL_SYSTEM_PROMPT)

    # Extract just the Python code
    code_match = re.search(r'```python\n(.*?)```', raw_code, re.DOTALL)
    clean_code = code_match.group(1) if code_match else raw_code

    # Test in sandbox
    test_result = await _run_in_e2b(
        clean_code,
        skill_name,
        skill_spec.get("test_args", {})
    )

    from agent.chat_push import chat_push
    new_skills = state.get("new_skills_created", [])

    if test_result.get("success"):
        # Save the skill file
        skill_file = SKILLS_DIR / f"{skill_name}.py"
        skill_file.write_text(f'"""\nGenerated by SkillForge — {datetime.utcnow().isoformat()}\n{skill_spec.get("description")}\n"""\n\n{clean_code}')

        logger.info(f"[SkillForge] ✅ Skill '{skill_name}' created and saved")

        user_id = state.get("created_by")
        # Route based on risk
        if risk_level in ["low", "medium"]:
            msg = f"I encountered a roadblock, but I've forged a solution: {summary}. Since this is low-risk, I have applied the fix and am retrying the tasks now."
            if user_id:
                await chat_push(user_id, msg, "skillforge", state.get("goal_id"))
            
            # Remove the failed tasks so Publisher tries them again
            current_failed = state.get("failed_task_ids", [])
            fixed_failed = [t for t in current_failed if t not in failed_tasks]
            
            return {
                "new_skills_created": new_skills + [skill_name],
                "failed_task_ids": fixed_failed,  # Clear the ones we just fixed
                "messages": [{"role": "skillforge", "content": f"Auto-applied fix: {skill_name}"}],
                "next_agent": "publisher",  # Loop back to retry!
            }
        else:
            # High risk — pause for human approval
            msg = f"I hit a roadblock. I've forged a potential solution: {summary}. However, because this is a **HIGH RISK** operation, I need your approval. Shall I apply this fix and proceed?"
            if user_id:
                await chat_push(user_id, msg, "skillforge", state.get("goal_id"))

            from langgraph.graph import END
            return {
                "new_skills_created": new_skills + [skill_name],
                "messages": [{"role": "skillforge", "content": f"Paused for approval of fix: {skill_name}"}],
                # We do NOT clear failed tasks yet; chat_agent will clear them upon approval
                "next_agent": END,  
            }
    else:
        logger.warning(f"[SkillForge] Skill validation failed: {test_result.get('error')}")
        if state.get("created_by"):
            from agent.chat_push import chat_push
            await chat_push(state.get("created_by"), f"I attempted to code a workaround for an error, but tests failed. ({test_result.get('error', 'unknown')}). Campaign stalled.", "skillforge", state.get("goal_id"))
        
        return {
            "messages": [{"role": "skillforge", "content": f"Skill forge attempted but validation failed."}],
            "next_agent": "monitor",
        }
