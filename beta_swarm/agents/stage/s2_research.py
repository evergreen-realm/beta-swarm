from beta_swarm.agents.base import BaseAgent
import json, re, os, logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class S2ResearchAgent(BaseAgent):
    def __init__(self, brain=None):
        super().__init__("s2_research", "Research Agent", "Stage 2: Deep Research", brain)

    def _get_default_next_stage(self):
        return "s3_prd"

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        project_id = task.get("project_id", "default")
        # Input from S1
        s1_out = task.get("s1_ideation", {})
        concept = s1_out.get("concept") or task.get("concept") or {}
        query = task.get("query", "") or concept.get("title", "") or str(concept)[:200] or "software best practices"
        depth = task.get("depth", "simple")

        self._log_handover(f"S2 started. Query='{query}', depth={depth}")

        raw_results = []
        sources = []

        # Three-tier research based on depth
        if depth in ("simple", "standard"):
            raw_results, sources = self._ddg_search(query)
        elif depth == "medium":
            raw_results, sources = self._openclaw_search(query)
        elif depth == "edge":
            raw_results, sources = self._hermes_search(query)
        else:  # deep
            raw_results, sources = self._parallel_web_search(query, concept)

        # Fallback chain
        if not raw_results:
            raw_results, sources = self._hermes_search(query)
        if not raw_results:
            raw_results, sources = self._ddg_search(query)
        if not raw_results:
            raw_results = [{"title": query, "snippet": f"Research on: {query}", "url": ""}]

        # Summarise via LLM
        context_text = "\n".join([
            f"Source: {r.get('url','')}\nTitle: {r.get('title','')}\nSnippet: {r.get('snippet','')}"
            for r in raw_results[:10]
        ])
        summary_prompt = f"""You are a technical research analyst.
Summarise the following research into a concise technical overview for: "{query}"

Research Data:
{context_text}

Return a JSON object:
{{
  "research_summary": "Multi-paragraph technical summary",
  "key_findings": ["finding 1", "finding 2"],
  "technologies": ["tech1", "tech2"],
  "architecture_patterns": ["pattern1"],
  "sources": []
}}"""

        llm_output = self._call_llm(summary_prompt, task_type="s2_research")
        parsed = self._safe_parse_json(llm_output)
        if not parsed:
            parsed = {
                "research_summary": "\n".join([r.get("snippet", "") for r in raw_results[:5]]),
                "key_findings": [],
                "technologies": [],
                "architecture_patterns": [],
                "sources": sources
            }
        parsed["sources"] = sources

        # Save artifact + Obsidian
        os.makedirs(f"./projects/{project_id}", exist_ok=True)
        artifact_path = f"./projects/{project_id}/s2_research_output.json"
        with open(artifact_path, "w", encoding="utf-8") as f:
            json.dump(parsed, f, indent=2)

        # Write Markdown report
        md_path = f"./projects/{project_id}/research.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# Research Report: {query}\n\n")
            f.write(parsed.get("research_summary", ""))
            f.write("\n\n## Sources\n")
            for s in sources[:20]:
                f.write(f"- {s}\n")

        self._save_to_obsidian(query, parsed.get("research_summary", ""), sources)
        self._log_handover(f"S2 completed. {len(sources)} sources. Artifact: {artifact_path}")

        return {
            "status": "complete",
            "research_summary": parsed.get("research_summary", ""),
            "sources": sources,
            "key_findings": parsed.get("key_findings", []),
            "technologies": parsed.get("technologies", []),
            "artifact": parsed,
            "artifact_path": artifact_path,
            "next_stage": task.get("next_stage") or self._get_default_next_stage()
        }

    def _ddg_search(self, query: str) -> tuple:
        results, sources = [], []
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                hits = list(ddgs.text(query, max_results=8))
            for r in hits:
                results.append({"title": r.get("title",""), "snippet": r.get("body",""), "url": r.get("href","")})
                if r.get("href"):
                    sources.append(r["href"])
            logger.info(f"[S2] DuckDuckGo: {len(results)} results")
        except Exception as e:
            logger.warning(f"[S2] DuckDuckGo failed: {e}")
        return results, sources

    def _openclaw_search(self, query: str) -> tuple:
        try:
            from beta_swarm.orchestration.openclaw import OpenClaw
            oc = OpenClaw()
            res = oc.search_and_navigate(query, max_results=5)
            if res.get("status") == "complete":
                results = [{"title": r.get("title",""), "snippet": r.get("description",""), "url": r.get("url","")} for r in res.get("results", [])]
                sources = [r.get("url","") for r in res.get("results", []) if r.get("url")]
                logger.info(f"[S2] OpenClaw: {len(results)} results")
                return results, sources
        except Exception as e:
            logger.warning(f"[S2] OpenClaw failed: {e}")
        return self._ddg_search(query)

    def _parallel_web_search(self, query: str, concept: dict) -> tuple:
        all_results, all_sources = [], []
        # Generate subtopics from concept
        features = concept.get("key_features", [])
        subtopics = [query] + [f"{query} {feat}" for feat in features[:3]]
        try:
            from beta_swarm.tools.web.parallel_web_client import ParallelWebClient
            client = ParallelWebClient()
            for topic in subtopics:
                res = client.search(topic)
                all_results.extend(res.get("results", []))
                all_sources.extend(res.get("sources", []))
            logger.info(f"[S2] Parallel Web: {len(all_results)} results from {len(subtopics)} subtopics")
        except Exception as e:
            logger.warning(f"[S2] ParallelWebClient failed: {e}. Falling back to Gumloop.")
            try:
                from beta_swarm.orchestration.gumloop_web import GumloopWebManager
                gm = GumloopWebManager()
                tasks = [{"query": t, "depth": "deep"} for t in subtopics]
                for t in tasks:
                    res = gm.run_research(t["query"], t["depth"])
                    if res.get("findings"):
                        all_results.append({"title": t["query"], "snippet": res["findings"][:500], "url": ""})
                        all_sources.extend(res.get("sources", []))
            except Exception as e2:
                logger.warning(f"[S2] Gumloop also failed: {e2}")
                return self._ddg_search(query)
        return all_results, list(set(all_sources))

    def _save_to_obsidian(self, query: str, summary: str, sources: list):
        try:
            vault_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "obsidian-vault", "04-Research")
            os.makedirs(vault_path, exist_ok=True)
            safe_name = re.sub(r'[^\w\s-]', '', query)[:50].strip()
            note_path = os.path.join(vault_path, f"{safe_name}.md")
            with open(note_path, "w", encoding="utf-8") as f:
                f.write(f"# {query}\n\n{summary}\n\n## Sources\n")
                for s in sources[:10]:
                    f.write(f"- {s}\n")
        except Exception as e:
            logger.warning(f"[S2] Obsidian save failed (non-fatal): {e}")

    def _safe_parse_json(self, text: str) -> dict:
        m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1).strip())
            except Exception:
                pass
        m2 = re.search(r'\{.*\}', text, re.DOTALL)
        if m2:
            try:
                return json.loads(m2.group(0))
            except Exception:
                pass
        return {}

    def _hermes_search(self, query: str) -> tuple:
        results, sources = [], []
        try:
            from beta_swarm.orchestration.hermes_daemon import HermesDaemon
            daemon = HermesDaemon()
            task_id = daemon.delegate_task(query)
            res = daemon.poll_task(task_id, timeout=30)
            if res.get("status") == "completed":
                results.append({
                    "title": f"Hermes Research on {query}",
                    "snippet": res.get("result", ""),
                    "url": "http://localhost:3000"
                })
                sources.append("http://localhost:3000")
                logger.info(f"[S2] HermesDaemon completed task {task_id}")
            daemon.shutdown()
        except Exception as e:
            logger.warning(f"[S2] HermesDaemon research failed: {e}")
        return results, sources
