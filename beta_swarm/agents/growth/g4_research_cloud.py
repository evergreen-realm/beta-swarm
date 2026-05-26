import logging
import os
import requests
from typing import Dict, Any, List
from beta_swarm.agents.base import BaseAgent

logger = logging.getLogger(__name__)

class G4CloudResearchAgent(BaseAgent):
    """
    G4: Cloud Research Agent
    Growth: Cloud Offload Research
    Performs web searches using DuckDuckGo and optional APIs (like Gumloop).
    Can scrape URLs and synthesize findings.
    """
    def __init__(self, brain=None):
        super().__init__("g4_cloud", "Cloud Research Agent", "growth", brain)
        self.gumloop_api = os.getenv("GUMLOOP_API_URL", "")
        self.gumloop_key = os.getenv("GUMLOOP_API_KEY", "")

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        query = task.get("query", "")
        depth = task.get("depth", "standard")
        operation = task.get("operation", "research")

        if operation == "research":
            result = self._call_gumloop(query, depth)
            
            # If deep research, try to scrape contents for better context
            if depth == "deep" and result.get("results"):
                result["results"] = self._scrape_contents(result["results"])
                
            return result
        elif operation == "synthesize":
            return self._synthesize(task.get("sources", []))
        else:
            return {"status": "error", "message": f"Unknown operation: {operation}"}

    def _call_gumloop(self, query: str, depth: str) -> Dict[str, Any]:
        logger.info(f"[G4] Starting research for query: '{query}', depth: {depth}")
        
        # 1. Try to trigger the Gumloop pipeline via OpenClaw browser automation
        try:
            from beta_swarm.orchestration.openclaw import OpenClaw
            openclaw = OpenClaw()
            gumloop_url = os.getenv("GUMLOOP_PIPELINE_URL", "https://www.gumloop.com/pipeline?pipeline_id=beta_swarm_research")
            logger.info(f"[G4] Initiating Gumloop workflow via OpenClaw browser automation at: {gumloop_url}")
            
            # Formulate the target actions in the browser to automate Gumloop pipeline execution
            actions = [
                {"action": "click", "selector": "#run-pipeline-btn"},
                {"action": "type", "selector": "#query-input", "value": query}
            ]
            openclaw_res = openclaw.browse(
                url=gumloop_url,
                task=f"Trigger Gumloop research pipeline for query: {query}",
                actions=actions
            )
            logger.info(f"[G4] OpenClaw Gumloop browser initiation status: {openclaw_res.get('status')}")
            
            if openclaw_res.get("status") == "complete":
                if self.brain:
                    self.brain.store_fact(self.agent_id, f"Initiated Gumloop research pipeline via OpenClaw browser automation for: {query}", "openclaw_gumloop")
        except Exception as e:
            logger.warning(f"[G4] OpenClaw Gumloop browser automation initiation skipped/failed: {e}")

        # 2. Try Gumloop API first if configured
        if self.gumloop_api and self.gumloop_key:
            try:
                resp = requests.post(
                    self.gumloop_api,
                    headers={
                        "Authorization": f"Bearer {self.gumloop_key}", 
                        "Content-Type": "application/json"
                    },
                    json={"query": query, "depth": depth},
                    timeout=60
                )
                if resp.status_code == 200:
                    data = resp.json()
                    logger.info("[G4] Successfully retrieved data from Gumloop.")
                    results = data.get("results", [])
                    if self.brain:
                        self.brain.store_fact(self.agent_id, f"Researched via Gumloop: {query}. Found {len(results)} results.", "research")
                    return {
                        "status": "complete", 
                        "source": "gumloop", 
                        "results": results, 
                        "query": query
                    }
            except Exception as e:
                logger.warning(f"[G4] Gumloop API failed: {e}. Falling back to DuckDuckGo.")

        # Fallback: Use DuckDuckGo locally
        logger.info("[G4] Using DuckDuckGo fallback.")
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                max_res = 10 if depth == "deep" else 5
                results = list(ddgs.text(query, max_results=max_res))
                
                formatted_results = [
                    {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")} 
                    for r in results
                ]
                
                if self.brain:
                    self.brain.store_fact(self.agent_id, f"Researched via DDG: {query}. Found {len(formatted_results)} results.", "research")
                
                return {
                    "status": "complete",
                    "source": "duckduckgo_fallback",
                    "results": formatted_results,
                    "query": query
                }
        except ImportError:
            logger.error("[G4] duckduckgo_search is not installed.")
            return {
                "status": "complete", 
                "source": "none", 
                "results": [], 
                "query": query, 
                "note": "DuckDuckGo not installed. Run `pip install duckduckgo-search`"
            }
        except Exception as e:
            logger.error(f"[G4] DuckDuckGo search failed: {e}")
            return {"status": "error", "message": f"DDG search failed: {e}"}

    def _scrape_contents(self, results: List[Dict]) -> List[Dict]:
        """Attempt to fetch deeper content from the URLs using BeautifulSoup."""
        try:
            import requests
            from bs4 import BeautifulSoup
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            for res in results[:3]: # Only scrape top 3 to save time
                url = res.get("url")
                if not url:
                    continue
                try:
                    page = requests.get(url, headers=headers, timeout=10)
                    if page.status_code == 200:
                        soup = BeautifulSoup(page.content, 'html.parser')
                        # Extract paragraphs
                        paragraphs = soup.find_all('p')
                        text = " ".join([p.get_text() for p in paragraphs])
                        # Store a truncated version of the full text
                        res["full_text"] = text[:2000].strip()
                except Exception as e:
                    logger.debug(f"[G4] Scrape failed for {url}: {e}")
                    pass
        except ImportError:
            logger.warning("[G4] beautifulsoup4 or requests not installed. Skipping deep scrape.")
        
        return results

    def _synthesize(self, sources: List[Dict]) -> Dict[str, Any]:
        logger.info(f"[G4] Synthesizing {len(sources)} sources.")
        if not sources:
            return {"status": "complete", "synthesis": "", "key_points": [], "confidence": 0.0}

        # Combine snippets and full text
        all_text = ""
        for s in sources:
            all_text += s.get("snippet", "") + ". "
            if s.get("full_text"):
                all_text += s.get("full_text") + " "
                
        sentences = all_text.split(". ")
        key_points = []
        for s in sentences:
            clean = s.strip()
            if len(clean) > 30 and clean not in key_points:
                key_points.append(clean)
            if len(key_points) >= 20: # Limit processing
                break

        synthesis_text = " ".join(key_points[:5])
        confidence = min(1.0, len(sources) / 5.0) # Higher confidence if more sources

        if self.brain:
            self.brain.store_fact(self.agent_id, f"Synthesized research. Confidence: {confidence}", "synthesis")

        return {
            "status": "complete",
            "synthesis": synthesis_text,
            "key_points": key_points[:10],
            "confidence": round(confidence, 2),
            "sources_used": len(sources)
        }
