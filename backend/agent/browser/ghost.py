"""
Digital Force — Ghost Browser
Persistent headless Playwright session that holds authenticated state
to allow agents to bypass CAPTCHAs and login walls seamlessly.
"""

import asyncio
import logging
from pathlib import Path
from playwright.async_api import async_playwright, Playwright, Browser, BrowserContext, Page
from typing import Optional

logger = logging.getLogger(__name__)

# Where we store persistent cookies/session state
SESSION_DIR = Path(__file__).parent.parent.parent / "ghost_session_data"

class GhostBrowser:
    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[BrowserContext] = None
        self._lock = asyncio.Lock()
        
    async def start(self):
        """Initialise the persistent browser context."""
        SESSION_DIR.mkdir(parents=True, exist_ok=True)
        try:
            self._playwright = await async_playwright().start()
            
            # Using launch_persistent_context to natively preserve cookies
            # across restarts, acting exactly like a real browser profile.
            self._browser = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(SESSION_DIR),
                headless=True,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                timezone_id="UTC",
                args=[
                    "--disable-blink-features=AutomationControlled", # Anti-bot mitigation
                    "--disable-infobars",
                ]
            )
            logger.info("👻 Ghost Browser initialized with persistent context.")
            
        except Exception as e:
            logger.error(f"Failed to start Ghost Browser: {e}")
            raise
            
    async def stop(self):
        """Cleanly shutdown the browser context."""
        logger.info("👻 Ghost Browser shutting down...")
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
            
    async def get_page(self) -> Page:
        """
        Retrieves a new tab in the persistent context.
        Callers MUST ensure they close the page when done: `await page.close()`
        """
        async with self._lock:
            if not self._browser:
                raise RuntimeError("GhostBrowser is not running.")
            page = await self._browser.new_page()
            # Anti-bot bypass injection
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            return page

# Global instance managed by FastAPI Lifespan
ghost = GhostBrowser()
