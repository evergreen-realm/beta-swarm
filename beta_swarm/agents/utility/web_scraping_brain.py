from beta_swarm.agents.base import BaseAgent
from typing import Dict, Any, List
import requests
import logging

logger = logging.getLogger(__name__)

try:
    from bs4 import BeautifulSoup
    _BS4_AVAILABLE = True
except ImportError:
    _BS4_AVAILABLE = False
    logger.warning("beautifulsoup4 not installed — web scraping will use raw text fallback. "
                   "Install with: pip install beautifulsoup4")


class WebScrapingBrainAgent(BaseAgent):
    def __init__(self, brain=None):
        super().__init__("u1_scrape", "Web Scraping Brain", "Utility: Content Extraction", brain)

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        urls = task.get("urls", [])
        depth = task.get("depth", "shallow")
        results = []

        for url in urls:
            try:
                resp = requests.get(url, timeout=15, headers={"User-Agent": "BetaSwarmBot/1.0"})

                if _BS4_AVAILABLE:
                    result = self._parse_with_bs4(url, resp.text, depth)
                else:
                    result = self._parse_raw(url, resp.text)

                results.append(result)

                if self.brain:
                    self.brain.store_fact(self.agent_id, f"Scraped: {result.get('title', 'Unknown')[:50]}", "research")

            except Exception as e:
                results.append({"url": url, "error": str(e)})

        return {"status": "complete", "pages": results, "count": len(results)}

    def _parse_with_bs4(self, url: str, html: str, depth: str) -> Dict[str, Any]:
        """Parse HTML content using BeautifulSoup."""
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string if soup.title else "No title"
        paragraphs = [p.get_text(strip=True) for p in soup.find_all("p")[:10]]
        links = [a["href"] for a in soup.find_all("a", href=True)[:20]]

        content = " ".join(paragraphs)
        if depth == "deep" and len(content) < 500:
            for div in soup.find_all(["div", "article", "section"]):
                text = div.get_text(strip=True)
                if len(text) > 100:
                    content += " " + text
                    if len(content) > 5000:
                        break

        return {
            "url": url,
            "title": title,
            "content": content[:5000],
            "links": links
        }

    @staticmethod
    def _parse_raw(url: str, html: str) -> Dict[str, Any]:
        """Fallback parser using regex when bs4 is unavailable."""
        import re
        # Extract title
        title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else "No title"

        # Strip tags for content
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()

        # Extract links
        links = re.findall(r'href=["\']([^"\']+)["\']', html)[:20]

        return {
            "url": url,
            "title": title,
            "content": text[:5000],
            "links": links
        }

# Alias for compatibility with compliance checks and testing
U1WebScrapingAgent = WebScrapingBrainAgent

