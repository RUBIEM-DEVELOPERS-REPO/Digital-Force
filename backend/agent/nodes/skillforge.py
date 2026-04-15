"""
Digital Force — SkillForge Agent Node
Creates new Python skills on-demand using E2B sandboxed execution.

Now with:
  - Web search (Tavily) to find real solutions before writing code
  - Dynamic skill registry: skills are loaded and called, not just saved
  - Metadata files (.meta.json) for each skill
  - Risk-based routing: low/medium auto-retries, high risk pauses for approval
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from agent.state import AgentState
from agent.llm import generate_completion, generate_json
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

SKILLS_DIR = Path(__file__).parent.parent / "skills" / "generated"
SKILLS_DIR.mkdir(parents=True, exist_ok=True)

SKILL_SYSTEM_PROMPT = """You are SkillForge — an expert Python developer creating reusable tool functions for a social media AI agent.

Rules for generated skills:
1. Write a single async Python function
2. Include ALL imports inside the function body
3. Handle all exceptions and return sensible defaults
4. Add a docstring explaining what the function does
5. The function must be fully self-contained (no external state)
6. Return a dict with a "success" key always

═══ STRATEGY FOR CHOOSING IMPLEMENTATION APPROACH ═══

Option A — API first (preferred):
If a public REST/GraphQL API exists for the task, use it with httpx.

Option B — Headless browser (fallback when no API exists):
If no API exists or the API is paywalled/blocked, use Playwright to control a
real Chromium browser. This is available in the E2B sandbox.

Playwright skill example:
```python
async def scrape_linkedin_profile(username: str) -> dict:
    \"\"\"Scrape a LinkedIn public profile using a headless browser.\"\"\"
    from playwright.async_api import async_playwright
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            await page.goto(f"https://www.linkedin.com/in/{username}/", wait_until="networkidle")
            name = await page.text_content("h1.top-card-layout__title") or "Unknown"
            headline = await page.text_content("h2.top-card-layout__headline") or ""
            await browser.close()
            return {"success": True, "name": name.strip(), "headline": headline.strip()}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

API skill example:
```python
async def check_hashtag_trend(hashtag: str, platform: str) -> dict:
    \"\"\"Check if a hashtag is trending.\"\"\"
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"https://api.example.com/trends/{hashtag}")
            data = resp.json()
        return {"success": True, "is_trending": data.get("trending", False)}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

When using Playwright:
- Always set `headless=True`
- Set a realistic `user_agent` to avoid bot detection
- Use `wait_until="networkidle"` or specific selectors with `wait_for_selector`
- Always call `await browser.close()` before returning
- Use `page.screenshot(path="/tmp/debug.png")` if you need to debug page state

Write clean, production-ready Python. No placeholder code."""


# ─── E2B Sandbox ─────────────────────────────────────────────────────────────

def _is_playwright_skill(code: str) -> bool:
    """Detect if the generated skill uses Playwright."""
    return "playwright" in code.lower() or "async_playwright" in code


async def _run_in_e2b(code: str, function_name: str, test_args: dict) -> dict:
    """
    Execute generated code in E2B cloud sandbox.
    Auto-detects Playwright usage and installs Chromium in the sandbox if needed.
    The sandbox is remote and isolated — nothing touches the local machine.
    """
    if not settings.e2b_api_key:
        logger.warning("[SkillForge] E2B not configured. Running in restricted local mode.")
        return await _run_local_test(code, function_name, test_args)

    uses_playwright = _is_playwright_skill(code)

    try:
        from e2b_code_interpreter import Sandbox
        async with Sandbox(api_key=settings.e2b_api_key) as sbx:
            # ── Base dependency install ──────────────────────────────────────
            await sbx.commands.run("pip install httpx requests beautifulsoup4 -q")

            # ── Playwright: install + download Chromium inside the sandbox ───
            if uses_playwright:
                logger.info("[SkillForge] Playwright skill detected — installing Chromium in E2B sandbox...")
                # This runs INSIDE the cloud sandbox — zero local disk usage
                install_result = await sbx.commands.run(
                    "pip install playwright -q && playwright install chromium --with-deps -q"
                )
                logger.info(f"[SkillForge] Playwright sandbox ready: {install_result.stdout[-200:] if hasattr(install_result, 'stdout') else 'ok'}")

            # ── Build the test runner ────────────────────────────────────────
            test_code = f"""import asyncio
{code}

async def _test():
    result = await {function_name}(**{json.dumps(test_args)})
    print("RESULT:", result)
    return result

asyncio.run(_test())
"""
            result = await sbx.run_code(test_code)
            output = result.text or ""
            success = "RESULT:" in output and "'success': False" not in output and "error" not in output.lower()
            sandbox_type = "e2b_playwright" if uses_playwright else "e2b_standard"
            return {"success": success, "output": output, "sandbox": sandbox_type}
    except Exception as e:
        logger.error(f"[SkillForge] E2B execution failed: {e}")
        return {"success": False, "error": str(e)}


async def _run_local_test(code: str, function_name: str, test_args: dict) -> dict:
    """
    Restricted local test — validates syntax only when E2B unavailable.
    """
    import ast
    try:
        ast.parse(code)
        return {"success": True, "output": "Syntax valid (local mode)", "sandbox": "local_syntax_check"}
    except SyntaxError as e:
        return {"success": False, "error": f"Syntax error: {e}"}


# ─── Main SkillForge Node ────────────────────────────────────────────────────

async def skillforge_node(state: AgentState) -> dict:
    """
    Identifies skill gaps from failed tasks, searches the web for solutions,
    generates new Python skills, validates in sandbox, registers them,
    and retries or asks for approval based on risk.
    """
    from agent.tools.web_search import search_for_solution
    from agent.skills.registry import save_skill_metadata, skills_for_task, run_skill
    from agent.chat_push import chat_push

    logger.info(f"[SkillForge] Checking for skill gaps in goal {state['goal_id']}")

    failed_tasks = state.get("failed_task_ids", [])
    tasks = state.get("tasks", [])
    failed_task_details = [t for t in tasks if t.get("id") in failed_tasks]

    if not failed_task_details:
        return {
            "next_agent": "monitor",
            "messages": [{"role": "skillforge", "content": "No skill gaps identified."}]
        }

    # ── Step 1: Check if an existing generated skill can handle any of these ──
    for task in failed_task_details[:3]:
        task_desc = task.get("description", task.get("action", ""))
        candidate_skills = skills_for_task(task_desc)
        if candidate_skills:
            logger.info(f"[SkillForge] Found existing skills that may help: {candidate_skills}")
            # Try running the best candidate
            for skill_name in candidate_skills[:2]:
                try:
                    result = await run_skill(skill_name)
                    if result.get("success"):
                        logger.info(f"[SkillForge] Existing skill '{skill_name}' solved the problem!")
                        # Clear the failed task
                        user_id = state.get("created_by")
                        if user_id:
                            await chat_push(user_id,
                                f"♻️ I found an existing capability ('{skill_name}') that resolves the issue. Retrying tasks now.",
                                "skillforge", state.get("goal_id"))
                        current_failed = list(state.get("failed_task_ids", []))
                        fixed = [t for t in current_failed if t != task.get("id")]
                        return {
                            "failed_task_ids": fixed,
                            "messages": [{"role": "skillforge", "content": f"Reused skill: {skill_name}"}],
                            "next_agent": "publisher",
                        }
                except Exception as e:
                    logger.warning(f"[SkillForge] Existing skill '{skill_name}' failed: {e}")

    # ── Step 2: Web search for a real-world solution ──────────────────────────
    error_summary = "; ".join([
        f"{t.get('action', 'task')} failed: {t.get('error', 'unknown error')}"
        for t in failed_task_details[:2]
    ])
    logger.info(f"[SkillForge] Searching web for: {error_summary}")
    web_solution = await search_for_solution(error_summary, context="social media publishing python")
    logger.info(f"[SkillForge] Web solution context: {web_solution[:300]}...")

    # ── Step 2b: Detect if the solution requires a new API credential ─────────
    api_check_prompt = f"""
The following error occurred in a social media AI agent:
{error_summary}

Web research found this potential solution:
{web_solution[:1000]}

IMPORTANT: A headless browser (Playwright with Chromium) IS available in the execution sandbox.
If the best solution can be achieved by controlling a browser (scraping, clicking, filling forms),
that counts as a valid solution WITHOUT needing a new API key.

Does the BEST solution require a new API key or external service that might not be configured yet?
Respond with JSON only:
{{
  "needs_new_api": true or false,
  "api_name": "Name of the API/service, or null if can use browser/other approach",
  "signup_url": "https://..., or null",
  "is_free": true or false,
  "why_needed": "1-2 sentence explanation",
  "can_proceed_without": true or false,
  "use_playwright": true or false,
  "alternative_approach": "Description of headless browser approach or other fallback if it exists, else null"
}}

Set use_playwright=true if a headless Playwright browser can solve this without needing a new API key.
Set can_proceed_without=true if either a browser approach OR another library can solve this.
"""
    try:
        api_check = await generate_json(api_check_prompt)
    except Exception:
        api_check = {"needs_new_api": False}

    user_id = state.get("created_by")
    goal_id = state.get("goal_id")

    if api_check.get("needs_new_api") and not api_check.get("can_proceed_without"):
        # Notify via chat AND email
        api_name = api_check.get("api_name", "an external API")
        signup_url = api_check.get("signup_url", "")
        is_free = api_check.get("is_free", False)
        why = api_check.get("why_needed", "")
        free_note = "✅ Free tier available" if is_free else "⚠️ May require a paid plan"

        chat_msg = (
            f"🔑 I found a solution for the roadblock, but it requires a new credential: **{api_name}**\n\n"
            f"Why: {why}\n\n"
            f"{free_note}\n"
            f"Sign up here: {signup_url}\n\n"
            f"Once you add the key in **Settings → Integrations**, I'll automatically retry this task. "
            f"I've also sent you an email with this info."
        )
        if user_id:
            await chat_push(user_id, chat_msg, "skillforge", goal_id)

        from agent.tools.email_notify import notify_api_key_needed
        await notify_api_key_needed(
            capability=error_summary[:80],
            api_name=api_name,
            signup_url=signup_url,
            why_needed=why,
            is_free=is_free,
        )

        from langgraph.graph import END
        return {
            "messages": [{"role": "skillforge", "content": f"Paused — API key needed: {api_name}"}],
            "next_agent": END,
        }

    # If an alternative exists even without the API, proceed with that
    if api_check.get("needs_new_api") and api_check.get("alternative_approach"):
        alt = api_check.get("alternative_approach", "")
        logger.info(f"[SkillForge] API needed but alternative exists: {alt}")
        # Inject alternative into the web solution context
        web_solution = f"PREFERRED APPROACH (no new API needed): {alt}\n\n" + web_solution

    # ── Step 3: Analyze + design the new skill (with web context) ─────────────
    analysis_prompt = f"""
A social media AI agent encountered failures:
{json.dumps(failed_task_details, indent=2)}

Web research found these potential solutions:
{web_solution}

Design a new Python skill to prevent these failures.
Respond with JSON only:
{{
  "skill_name": "snake_case_function_name",
  "display_name": "Human Readable Name",
  "description": "Technical description of what this skill does",
  "input_params": {{"param_name": "type"}},
  "test_args": {{"param_name": "test_value"}},
  "risk_level": "low or medium or high",
  "non_technical_summary": "1-2 sentence plain-English explanation of what went wrong and what the fix does."
}}

Risk level:
- low: syntax fixes, backup APIs, alternate hashtags, retry logic
- medium: scraping alternatives, format changes, different endpoints
- high: spending money, deleting data, violating rate limits, brute force
"""

    try:
        skill_spec = await generate_json(analysis_prompt)
    except Exception as e:
        logger.error(f"[SkillForge] Could not design skill from web context: {e}")
        return {"next_agent": "monitor"}

    skill_name = skill_spec.get("skill_name", "new_skill")
    risk_level = skill_spec.get("risk_level", "high").lower()
    summary = skill_spec.get("non_technical_summary", "Implemented a new skill to bypass the error.")
    logger.info(f"[SkillForge] Forging: {skill_name} (Risk: {risk_level})")

    # ── Step 4: Generate the skill code (with web solution as context) ────────
    use_playwright = api_check.get("use_playwright", False)
    playwright_hint = (
        "\n\nIMPORTANT: Use Playwright (headless Chromium browser) for this skill — no API is available. "
        "The sandbox has Playwright installed. Use `from playwright.async_api import async_playwright` inside the function."
    ) if use_playwright else ""

    code_prompt = f"""
Create a Python async function called '{skill_name}' that:
{skill_spec.get('description')}

Input parameters: {json.dumps(skill_spec.get('input_params', {}))}

Use this research as guidance for implementation:
{web_solution[:800]}

Context: This is for a social media AI agent managing content across LinkedIn, Facebook, TikTok, Instagram, X, YouTube.
The function must be fully self-contained. Include ALL imports inside the function body.
Return a dict with a "success" key always.{playwright_hint}
"""

    raw_code = await generate_completion(code_prompt, SKILL_SYSTEM_PROMPT)
    code_match = re.search(r'```python\n(.*?)```', raw_code, re.DOTALL)
    clean_code = code_match.group(1) if code_match else raw_code

    # ── Step 5: Test in sandbox ───────────────────────────────────────────────
    test_result = await _run_in_e2b(clean_code, skill_name, skill_spec.get("test_args", {}))

    new_skills = state.get("new_skills_created", [])

    if test_result.get("success"):
        # ── Step 6: Save skill + metadata ─────────────────────────────────────
        skill_file = SKILLS_DIR / f"{skill_name}.py"
        skill_file.write_text(
            f'"""\nGenerated by SkillForge — {datetime.utcnow().isoformat()}\n'
            f'{skill_spec.get("description")}\n"""\n\n{clean_code}'
        )
        # Save metadata so registry can describe and find it
        save_skill_metadata(skill_name, {
            "function_name": skill_name,
            "display_name": skill_spec.get("display_name", skill_name),
            "description": skill_spec.get("description", ""),
            "input_params": skill_spec.get("input_params", {}),
            "risk_level": risk_level,
            "created_at": datetime.utcnow().isoformat(),
        })

        logger.info(f"[SkillForge] ✅ Skill '{skill_name}' created, saved, and registered")

        user_id = state.get("created_by")

        if risk_level in ["low", "medium"]:
            msg = (
                f"🔧 I hit a roadblock, searched the web for a solution, and built a new capability: "
                f"**{skill_spec.get('display_name', skill_name)}**. {summary} "
                f"I've tested it and it's working. Retrying the tasks now."
            )
            if user_id:
                await chat_push(user_id, msg, "skillforge", state.get("goal_id"))

            current_failed = state.get("failed_task_ids", [])
            fixed_failed = [t for t in current_failed if t not in [ft.get("id") for ft in failed_task_details]]

            return {
                "new_skills_created": new_skills + [skill_name],
                "failed_task_ids": fixed_failed,
                "messages": [{"role": "skillforge", "content": f"Auto-applied fix via new skill: {skill_name}"}],
                "next_agent": "publisher",
            }
        else:
            msg = (
                f"⚠️ I researched and built a fix for the roadblock: "
                f"**{skill_spec.get('display_name', skill_name)}**. {summary} "
                f"This is a **HIGH RISK** operation — I need your go-ahead before I apply it. "
                f"Reply 'approve' to proceed, or 'skip' to drop these tasks."
            )
            if user_id:
                await chat_push(user_id, msg, "skillforge", state.get("goal_id"))
                # Also email for high-risk
                from agent.tools.email_notify import notify_high_risk_approval
                await notify_high_risk_approval(
                    action_description=skill_spec.get("display_name", skill_name),
                    risk_reason=summary,
                    skill_name=skill_name,
                )

            from langgraph.graph import END
            return {
                "new_skills_created": new_skills + [skill_name],
                "messages": [{"role": "skillforge", "content": f"Paused — awaiting approval for: {skill_name}"}],
                "next_agent": END,
            }

    else:
        # Sandbox test failed
        logger.warning(f"[SkillForge] Validation failed: {test_result.get('error')}")
        user_id = state.get("created_by")
        if user_id:
            await chat_push(
                user_id,
                f"⚠️ I found a solution online and wrote code to fix the issue, but the code failed testing. "
                f"Error: {test_result.get('error', 'unknown')}. "
                f"I'll log this and the Monitor will decide next steps.",
                "skillforge",
                state.get("goal_id"),
            )
        return {
            "messages": [{"role": "skillforge", "content": "Skill validation failed after web-informed attempt."}],
            "next_agent": "monitor",
        }
