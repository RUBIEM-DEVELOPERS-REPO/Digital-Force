"""
Digital Force — Sandbox Execution Tool
Provides a secure E2B container runner for all agents to execute Python/Playwright scraping code.
"""

import json
import logging
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

def is_playwright_used(code: str) -> bool:
    """Detect if the generated script uses Playwright."""
    return "playwright" in code.lower() or "async_playwright" in code

async def run_in_e2b(code: str, function_name: str = None, test_args: dict = None) -> dict:
    """
    Execute generated code in the E2B cloud sandbox.
    Auto-detects Playwright usage and installs Chromium in the sandbox if needed.
    """
    if not settings.e2b_api_key:
        logger.warning("[Sandbox] E2B not configured. Simulated execution only.")
        return {"success": False, "error": "E2B_API_KEY not configured. Cannot strictly execute sandbox code."}

    uses_playwright = is_playwright_used(code)

    try:
        from e2b_code_interpreter import Sandbox
        async with Sandbox(api_key=settings.e2b_api_key) as sbx:
            # Base dependency install
            await sbx.commands.run("pip install httpx requests beautifulsoup4 lxml pandas -q")

            # Playwright: install + download Chromium inside the sandbox
            if uses_playwright:
                logger.info("[Sandbox] Playwright detected — installing Chromium in E2B sandbox...")
                install_result = await sbx.commands.run(
                    "pip install playwright -q && playwright install chromium --with-deps -q"
                )
                logger.info(f"[Sandbox] Playwright sandbox ready.")

            # If function_name and test_args are provided, it's a tool-test (like SkillForge)
            # Otherwise, it's an auto-execution script (like Researcher scraping)
            if function_name:
                test_code = f"import asyncio\n{code}\n\nasync def _test():\n    return await {function_name}(**{json.dumps(test_args or {})})\n\nprint('RESULT:', asyncio.run(_test()))"
            else:
                test_code = code

            logger.info("[Sandbox] Running code in E2B container...")
            result = await sbx.run_code(test_code)
            
            output = result.text or ""
            error = result.error.message if result.error else None
            
            success = (error is None) and ("'success': False" not in output)
            sandbox_type = "e2b_playwright" if uses_playwright else "e2b_standard"
            
            if error:
                return {"success": False, "error": error, "output": output, "sandbox": sandbox_type}
            else:
                return {"success": success, "output": output, "sandbox": sandbox_type}

    except Exception as e:
        logger.error(f"[Sandbox] E2B execution failed: {e}")
        return {"success": False, "error": str(e)}
