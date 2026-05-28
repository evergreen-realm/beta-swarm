"""
ParallelWebClient — concurrent web search across multiple subtopics.
Used by S2ResearchAgent (deep research mode).
Falls back gracefully: ThreadPool → DuckDuckGo → Playwright (if installed).
"""
import logging, concurrent.futures, re, time
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class ParallelWebClient:
    """Concurrent multi-topic web search with DuckDuckGo + optional Playwright."""

    def __init__(self, max_workers: int = 4, timeout: int = 20):
        self.max_workers = max_workers
        self.timeout = timeout

    def search(self, query: str, max_results: int = 8) -> Dict[str, Any]:
        """Single-topic search — returns {results: [...], sources: [...]}."""
        results, sources = self._ddg_search(query, max_results)
        if not results:
            results, sources = self._playwright_search(query, max_results)
        return {"results": results, "sources": sources}

    def multi_search(self, queries: List[str], max_results_each: int = 5) -> Dict[str, Any]:
        """Concurrent multi-topic search."""
        all_results: List[Dict] = []
        all_sources: List[str] = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_map = {
                executor.submit(self._ddg_search, q, max_results_each): q
                for q in queries
            }
            for future in concurrent.futures.as_completed(future_map, timeout=self.timeout * len(queries)):
                try:
                    results, sources = future.result(timeout=self.timeout)
                    all_results.extend(results)
                    all_sources.extend(sources)
                except Exception as e:
                    logger.warning(f"[ParallelWeb] subtopic failed: {e}")

        return {
            "results": all_results,
            "sources": list(set(all_sources)),
            "total": len(all_results)
        }

    def search_with_subtopics(self, base_query: str, subtopics: List[str]) -> Dict[str, Any]:
        """Search base query + each subtopic in parallel."""
        all_queries = [base_query] + [f"{base_query} {t}" for t in subtopics[:4]]
        return self.multi_search(all_queries)

    # ── DuckDuckGo ────────────────────────────────────────────────────── #
    def _ddg_search(self, query: str, max_results: int = 8):
        results, sources = [], []
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                hits = list(ddgs.text(query, max_results=max_results))
            for r in hits:
                results.append({
                    "title": r.get("title", ""),
                    "snippet": r.get("body", "")[:500],
                    "url": r.get("href", "")
                })
                if r.get("href"):
                    sources.append(r["href"])
            logger.debug(f"[DDG] '{query[:40]}' → {len(results)} results")
        except Exception as e:
            logger.warning(f"[DDG] '{query[:40]}' failed: {e}")
        return results, sources

    # ── Playwright fallback ───────────────────────────────────────────── #
    def _playwright_search(self, query: str, max_results: int = 5):
        results, sources = [], []
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(f"https://duckduckgo.com/?q={query.replace(' ', '+')}&ia=web", timeout=15000)
                page.wait_for_selector("[data-result='web']", timeout=8000)
                items = page.query_selector_all("[data-result='web']")[:max_results]
                for item in items:
                    try:
                        title_el = item.query_selector("h2")
                        link_el  = item.query_selector("a[href]")
                        body_el  = item.query_selector("[data-result='snippet']")
                        title   = title_el.inner_text() if title_el else ""
                        url     = link_el.get_attribute("href") if link_el else ""
                        snippet = body_el.inner_text() if body_el else ""
                        if title or url:
                            results.append({"title": title, "snippet": snippet[:400], "url": url})
                            if url: sources.append(url)
                    except Exception:
                        pass
                browser.close()
            logger.debug(f"[Playwright] '{query[:40]}' → {len(results)} results")
        except Exception as e:
            logger.warning(f"[Playwright] '{query[:40]}' failed: {e}")
        return results, sources
