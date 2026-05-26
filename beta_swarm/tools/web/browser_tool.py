import asyncio
import logging
from typing import Dict, List, Optional
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

class BrowserTool:
    """
    A tool for autonomous agents to interact with the web using Playwright.
    Supports fetching page content, taking screenshots, and basic interaction.
    """
    
    def __init__(self, headless: bool = True):
        self.headless = headless

    async def fetch_page_content(self, url: str) -> Dict[str, str]:
        """Fetch the text content and title of a given URL."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page = await browser.new_page()
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                content = await page.content()
                text = await page.evaluate("() => document.body.innerText")
                title = await page.title()
                return {
                    "url": url,
                    "title": title,
                    "text": text[:10000],  # Truncate for efficiency
                    "html": content[:5000] # Snippet of HTML
                }
            except Exception as e:
                logger.error(f"Error fetching page {url}: {e}")
                return {"error": str(e), "url": url}
            finally:
                await browser.close()

    async def take_screenshot(self, url: str, path: str) -> bool:
        """Take a screenshot of a page and save it to path."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page = await browser.new_page()
            try:
                await page.goto(url, wait_until="networkidle")
                await page.screenshot(path=path)
                return True
            except Exception as e:
                logger.error(f"Error taking screenshot of {url}: {e}")
                return False
            finally:
                await browser.close()

    def sync_fetch_page_content(self, url: str) -> Dict[str, str]:
        """Synchronous wrapper for fetch_page_content.
        
        Handles the case where an asyncio event loop is already running
        (e.g., when called from the orchestrator pipeline).
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # We're inside an existing async context — run in a thread to avoid
            # "cannot call asyncio.run() while another loop is running"
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, self.fetch_page_content(url))
                return future.result(timeout=45)
        else:
            return asyncio.run(self.fetch_page_content(url))

if __name__ == "__main__":
    # Quick test
    tool = BrowserTool()
    result = tool.sync_fetch_page_content("https://example.com")
    print(f"Title: {result.get('title')}")
    print(f"Content Length: {len(result.get('text', ''))}")
