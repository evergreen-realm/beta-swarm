from beta_swarm.agents.base import BaseAgent
from typing import Dict, Any, List
import requests
import logging

logger = logging.getLogger(__name__)
from beta_swarm.tools.web.browser_tool import BrowserTool
from beta_swarm.tools.web.gumloop_tool import GumloopTool

class S2ResearchAgent(BaseAgent):
    def __init__(self, brain=None):
        super().__init__("s2_research", "Research Agent", "Stage 2: Deep Research", brain)
        self.browser = BrowserTool()
        self.gumloop = GumloopTool(headless=True)

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        concept = task.get("concept", {})
        query = task.get("query", "") or concept.get("title", "") or "AI web applications"
        depth = task.get("depth", "standard")
        
        # Try Gumloop web first
        try:
            from beta_swarm.orchestration.gumloop_web import GumloopWebManager
            gumloop = GumloopWebManager()
            result = gumloop.run_research(query, depth)
            if result.get("findings"):
                # Ingest into brain
                bp = getattr(self, "brain_pipeline", None)
                if not bp:
                    try:
                        from beta_swarm.brain.brain_pipeline import BrainPipeline
                        bp = BrainPipeline()
                    except Exception:
                        pass
                
                if bp:
                    from beta_swarm.brain.brain_pipeline import Artifact
                    artifact = Artifact(
                        artifact_type="research",
                        project_id=task.get("project_id", "unknown"),
                        content=result["findings"],
                        source_agent="s2_research"
                    )
                    bp.ingest(artifact)
                    
                return {
                    "status": "complete",
                    "research_summary": result["findings"],
                    "sources": result.get("sources", []),
                    "technologies": result.get("technologies", []),
                    "confidence": result.get("confidence", 0.8),
                    "via": "gumloop_web",
                    "next_stage": "s3_prd"
                }
        except Exception as e:
            logger.warning(f"GumloopWebManager run_research failed: {e}. Falling back...")
            
        return self._local_research(task)

    def _local_research(self, task: Dict[str, Any]) -> Dict[str, Any]:
        concept = task.get("concept", {})
        queries = self._generate_queries(concept)

        research_results = []
        for query in queries:
            web_results = self._search_web(query)
            research_results.extend(web_results)

        summary = self._summarize(research_results)

        if self.brain:
            self.brain.store_fact(self.agent_id, f"Research: {len(research_results)} sources for {concept.get('title')}", "research")

        return {
            "status": "complete",
            "research_summary": summary,
            "sources": research_results[:20],
            "next_stage": "s3_prd"
        }

    def _generate_queries(self, concept: Dict) -> List[str]:
        title = concept.get("title", "")
        features = concept.get("key_features", [])
        queries = [
            f"{title} best practices 2026",
            f"{title} similar projects open source",
            f"{title} architecture patterns"
        ]
        for feat in features[:3]:
            queries.append(f"{feat} implementation approaches")
        return queries

    def _search_web(self, query: str) -> List[Dict]:
        if query.startswith("http://") or query.startswith("https://"):
            logger.info(f"Directly scraping URL: {query}")
            content = self.browser.sync_fetch_page_content(query)
            return [{"title": content.get("title", "Scraped Page"), "url": query, "snippet": content.get("text", "")[:500]}]

        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
                return [{"title": r["title"], "url": r["href"], "snippet": r["body"]} for r in results]
        except Exception as e:
            logger.warning(f"DuckDuckGo search failed: {e}. Trying OpenClaw fallback...")
            try:
                from beta_swarm.orchestration.openclaw import OpenClaw
                oc = OpenClaw()
                oc_res = oc.search_and_navigate(query)
                if oc_res.get("status") == "complete":
                    return [{"title": r.get("title", "OpenClaw Result"), "url": r.get("url", ""), "snippet": r.get("description", "")} for r in oc_res.get("results", [])]
            except Exception as oc_err:
                logger.warning(f"OpenClaw fallback search failed: {oc_err}")
            return [{"title": f"Search failed: {e}", "url": "", "snippet": f"Query: {query}"}]

    def _summarize(self, results: List[Dict]) -> str:
        """Uses LLM to synthesize search results into a concise technical summary."""
        if not results:
            return "No research results found."
            
        context = "\n".join([f"Source: {r['url']}\nSnippet: {r['snippet']}" for r in results[:10]])
        prompt = f"""
        Summarize the following research snippets into a coherent technical overview.
        
        FOCUS:
        - Common architecture patterns for this type of project.
        - Core API functionalities and data structures used by competitors.
        - Technical challenges and recommended solutions.
        - Suggest exact method/function signatures that would be part of a real implementation.
        
        RESEARCH DATA:
        {context}
        """
        
        return self.call_llm([{"role": "user", "content": prompt}])
