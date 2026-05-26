"""OpenClaw Browser Automation — Playwright -> Selenium -> Requests fallback chain."""

import subprocess
import tempfile
import os
from typing import Dict, Any, List
import requests


class OpenClaw:
    """Browser automation tool with 3-tier fallback for maximum reliability."""

    def __init__(self, headless: bool = True, timeout: int = 30):
        self.headless = headless
        self.timeout = timeout
        self.user_agent = "BetaSwarmBot/1.0 (Research Agent; +https://beta-swarm.local)"

    def browse(self, url: str, task: str = "extract_text",
               actions: List[Dict] = None) -> Dict:
        """Browse URL with automatic fallback chain."""
        for tool in ["playwright", "selenium", "requests"]:
            try:
                if tool == "playwright":
                    return self._use_playwright(url, task, actions)
                elif tool == "selenium":
                    return self._use_selenium(url, task, actions)
                else:
                    return self._use_requests(url, task)
            except Exception as e:
                print(f"[OpenClaw] {tool} failed: {e}, trying fallback...")
                continue
        return {"status": "error", "message": "All browser tools failed"}

    def search_and_navigate(self, query: str, depth: int = 3) -> List[Dict]:
        """Search DuckDuckGo and navigate to top results."""
        from duckduckgo_search import DDGS
        results = []
        try:
            with DDGS() as ddgs:
                search_results = list(ddgs.text(query, max_results=depth))
                for r in search_results:
                    page = self.browse(r["href"], "extract_text")
                    results.append({
                        "title": r["title"],
                        "url": r["href"],
                        "snippet": r["body"],
                        "content": page.get("content", "")[:5000] if page.get("status") == "complete" else "",
                        "tool_used": page.get("tool", "unknown")
                    })
        except Exception as e:
            return [{"error": str(e), "query": query}]
        return results

    def _use_playwright(self, url: str, task: str, actions: List[Dict] = None) -> Dict:
        """Use Playwright for full browser automation."""
        headless_flag = "True" if self.headless else "False"
        script = f'''
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless={headless_flag})
        page = await browser.new_page(user_agent="{self.user_agent}")
        await page.goto("{url}", timeout={self.timeout * 1000})
        await page.wait_for_load_state("networkidle")

        title = await page.title()
        text = await page.inner_text("body")
        links = await page.eval_on_selector_all("a[href]", "elements => elements.map(e => e.href)")

        await browser.close()
        print("TITLE: " + title)
        print("LINKS: " + "|".join(links[:20]))
        print("TEXT: " + text[:8000])

asyncio.get_event_loop().run_until_complete(main())
'''
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(script)
            script_path = f.name

        try:
            result = subprocess.run(
                ["python", script_path],
                capture_output=True,
                text=True,
                timeout=self.timeout + 10
            )

            if result.returncode != 0:
                raise RuntimeError(f"Playwright error: {result.stderr[:500]}")

            lines = result.stdout.split("\n")
            title = ""
            links = []
            text = ""
            for line in lines:
                if line.startswith("TITLE: "):
                    title = line[7:]
                elif line.startswith("LINKS: "):
                    links = line[7:].split("|") if line[7:] else []
                elif line.startswith("TEXT: "):
                    text = line[6:]

            return {
                "status": "complete",
                "tool": "playwright",
                "url": url,
                "title": title,
                "content": text,
                "links": links[:20],
                "html_length": len(result.stdout)
            }
        except Exception as e:
            raise RuntimeError(f"Playwright execution failed: {e}")
        finally:
            if os.path.exists(script_path):
                os.unlink(script_path)

    def _use_selenium(self, url: str, task: str, actions: List[Dict] = None) -> Dict:
        """Use Selenium as fallback."""
        headless_line = "options.add_argument('--headless')" if self.headless else "# headless disabled"
        script = f'''
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

options = Options()
{headless_line}
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--user-agent={self.user_agent}')

driver = webdriver.Chrome(options=options)
try:
    driver.get("{url}")
    title = driver.title
    text = driver.find_element(By.TAG_NAME, "body").text
    links = [a.get_attribute("href") for a in driver.find_elements(By.TAG_NAME, "a") if a.get_attribute("href")]
    print("TITLE: " + title)
    print("LINKS: " + "|".join(links[:20]))
    print("TEXT: " + text[:8000])
finally:
    driver.quit()
'''
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(script)
            script_path = f.name

        try:
            result = subprocess.run(
                ["python", script_path],
                capture_output=True,
                text=True,
                timeout=self.timeout + 10
            )

            if result.returncode != 0:
                raise RuntimeError(f"Selenium error: {result.stderr[:500]}")

            lines = result.stdout.split("\n")
            title = ""
            links = []
            text = ""
            for line in lines:
                if line.startswith("TITLE: "):
                    title = line[7:]
                elif line.startswith("LINKS: "):
                    links = line[7:].split("|") if line[7:] else []
                elif line.startswith("TEXT: "):
                    text = line[6:]

            return {
                "status": "complete",
                "tool": "selenium",
                "url": url,
                "title": title,
                "content": text,
                "links": links[:20]
            }
        except Exception as e:
            raise RuntimeError(f"Selenium execution failed: {e}")
        finally:
            if os.path.exists(script_path):
                os.unlink(script_path)

    def _use_requests(self, url: str, task: str) -> Dict:
        """Use Requests as final fallback."""
        try:
            resp = requests.get(
                url,
                timeout=self.timeout,
                headers={"User-Agent": self.user_agent},
                allow_redirects=True
            )
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
            title = soup.title.string if soup.title else "No title"
            text = soup.get_text(separator="\n", strip=True)
            links = [a["href"] for a in soup.find_all("a", href=True)[:20]]

            return {
                "status": "complete",
                "tool": "requests",
                "url": url,
                "title": title,
                "content": text[:8000],
                "links": links,
                "status_code": resp.status_code
            }
        except Exception as e:
            raise RuntimeError(f"Requests failed: {e}")

    def extract_structured(self, url: str, selectors: Dict[str, str]) -> Dict:
        """Extract structured data using CSS selectors."""
        page = self.browse(url, "extract_structured")
        if page.get("status") != "complete":
            return page

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(page.get("content", ""), "html.parser")
        data = {"url": url, "status": "complete"}
        for key, selector in selectors.items():
            elements = soup.select(selector)
            data[key] = [el.get_text(strip=True) for el in elements]
        return data
