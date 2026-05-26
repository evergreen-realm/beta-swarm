import os
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

HAS_CREWAI = False
try:
    from crewai import Agent, Task, Crew, Process
    HAS_CREWAI = True
except ImportError:
    pass

try:
    from langchain_core.language_models.llms import LLM
    from pydantic import Field

    class CrewAILLM(LLM):
        api_router: Any = None

        def _call(self, prompt: str, stop: Optional[List[str]] = None, **kwargs: Any) -> str:
            try:
                if self.api_router:
                    if hasattr(self.api_router, "generate"):
                        return self.api_router.generate([{"role": "user", "content": prompt}])
                    elif hasattr(self.api_router, "call"):
                        res = self.api_router.call([{"role": "user", "content": prompt}])
                        if res.get("status") == "complete":
                            resp = res.get("response", {})
                            if "choices" in resp:
                                return resp["choices"][0]["message"]["content"]
                            elif "candidates" in resp:
                                return resp["candidates"][0]["content"]["parts"][0]["text"]
                            return str(resp)
                        return f"Error: {res.get('message', 'No complete response')}"
                return "Mock Response: API Router not configured."
            except Exception as e:
                return f"Error generating content: {e}"

        @property
        def _llm_type(self) -> str:
            return "custom_apirouter"
except Exception:
    class CrewAILLM:
        def __init__(self, api_router=None):
            self.api_router = api_router

AGENT_MAPPINGS = {
    "s2_research": {"role": "Research Analyst", "goal": "Find comprehensive information", "backstory": "Expert at web research and synthesis"},
    "s3_prd": {"role": "Product Manager", "goal": "Write clear requirements", "backstory": "Experienced at translating research into specs"},
    "s4_architecture": {"role": "System Architect", "goal": "Design scalable systems", "backstory": "Designs robust architectures"},
    "s5_backend": {"role": "Backend Developer", "goal": "Build API services", "backstory": "Writes clean, tested backend code"},
    "s6_frontend": {"role": "Frontend Developer", "goal": "Build user interfaces", "backstory": "Creates responsive, accessible UIs"},
    "s8_testing": {"role": "QA Engineer", "goal": "Ensure code quality", "backstory": "Finds bugs before users do"},
    "x1_code_review": {"role": "Code Reviewer", "goal": "Catch issues early", "backstory": "Eagle-eyed reviewer"},
    "x2_security": {"role": "Security Auditor", "goal": "Identify vulnerabilities", "backstory": "Security-first mindset"},
    "x3_performance": {"role": "Performance Analyst", "goal": "Optimize system performance", "backstory": "Performance-first mindset"}
}

class CrewAIBackend:
    def __init__(self, project_id: str, api_router=None, brain=None):
        self.project_id = project_id
        self.api_router = api_router
        self.brain = brain

    def _create_crewai_agent(self, swarm_agent_id: str, role: str, goal: str, backstory: str) -> Optional[Any]:
        try:
            if not HAS_CREWAI:
                return None
            llm = CrewAILLM(api_router=self.api_router) if self.api_router else None
            return Agent(role=role, goal=goal, backstory=backstory, llm=llm, verbose=True, allow_delegation=True)
        except Exception as e:
            logger.error(f"Failed to create CrewAI agent for {swarm_agent_id}: {e}")
            return None

    def _get_agent(self, aid: str) -> Optional[Any]:
        m = AGENT_MAPPINGS.get(aid, {"role": f"{aid} Swarm Agent", "goal": "Collaborate and achieve project objectives", "backstory": "Expert swarm collaborator"})
        return self._create_crewai_agent(aid, m["role"], m["goal"], m["backstory"])

    def _get_raw_out(self, task: Any, fallback: str = "") -> str:
        if not task or not hasattr(task, 'output') or not task.output:
            return fallback
        for attr in ['raw', 'raw_output']:
            if hasattr(task.output, attr):
                val = getattr(task.output, attr)
                if val:
                    return str(val)
        return fallback

    def run_research_crew(self, query: str, depth: str = "standard") -> Dict[str, Any]:
        if not HAS_CREWAI:
            return {"status": "error", "message": "pip install crewai"}
        try:
            a1, a2 = self._get_agent("s2_research"), self._get_agent("s3_prd")
            t1 = Task(description=f"Conduct thorough research on: '{query}'. Depth parameter is: {depth}.", expected_output="A detailed research synthesis.", agent=a1)
            t2 = Task(description="Write detailed PRD based on research.", expected_output="A formal Product Requirements Document.", agent=a2, context=[t1])
            crew = Crew(agents=[a1, a2], tasks=[t1, t2], process=Process.sequential, verbose=True)
            res = str(crew.kickoff())
            return {
                "research": self._get_raw_out(t1, res),
                "prd": self._get_raw_out(t2, res),
                "crew_result": res
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def run_code_crew(self, project_path: str, stack: Dict[str, Any]) -> Dict[str, Any]:
        if not HAS_CREWAI:
            return {"status": "error", "message": "pip install crewai"}
        try:
            a1, a2, a3 = self._get_agent("s4_architecture"), self._get_agent("s5_backend"), self._get_agent("s8_testing")
            t1 = Task(description=f"Design architecture at {project_path}. Stack: {stack}.", expected_output="Architecture doc.", agent=a1)
            t2 = Task(description=f"Implement backend at {project_path}.", expected_output="Backend implementation.", agent=a2, context=[t1])
            t3 = Task(description=f"Write tests under {project_path}.", expected_output="Backend tests.", agent=a3, context=[t2])
            crew = Crew(agents=[a1, a2, a3], tasks=[t1, t2, t3], process=Process.sequential, verbose=True)
            res = str(crew.kickoff())
            return {
                "architecture": self._get_raw_out(t1, res),
                "code": self._get_raw_out(t2, res),
                "tests": self._get_raw_out(t3, res)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def run_review_crew(self, code_path: str) -> Dict[str, Any]:
        if not HAS_CREWAI:
            return {"status": "error", "message": "pip install crewai"}
        try:
            a1, a2, a3 = self._get_agent("x1_code_review"), self._get_agent("x2_security"), self._get_agent("x3_performance")
            t1 = Task(description=f"Review code quality at {code_path}.", expected_output="Code review feedback.", agent=a1)
            t2 = Task(description=f"Security audit at {code_path}.", expected_output="Security audit report.", agent=a2)
            t3 = Task(description=f"Analyze performance of {code_path}.", expected_output="Performance analysis report.", agent=a3)
            crew = Crew(agents=[a1, a2, a3], tasks=[t1, t2, t3], process=Process.sequential, verbose=True)
            res = str(crew.kickoff())
            return {
                "code_review": self._get_raw_out(t1, res),
                "security": self._get_raw_out(t2, res),
                "performance": self._get_raw_out(t3, res),
                "consensus": res
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def run_custom_crew(self, agent_ids: List[str], tasks: List[Dict[str, Any]], process: str = "sequential") -> Dict[str, Any]:
        if not HAS_CREWAI:
            return {"status": "error", "message": "pip install crewai"}
        try:
            agents = {aid: self._get_agent(aid) for aid in agent_ids}
            ctasks = []
            for t_def in tasks:
                agent = agents.get(t_def.get("agent_id"))
                ctx = [ctasks[dep] for dep in t_def.get("dependencies", []) if dep < len(ctasks)]
                ctasks.append(Task(description=t_def.get("description", ""), expected_output=t_def.get("expected_output", ""), agent=agent, context=ctx if ctx else None))
            proc = Process.sequential if process == "sequential" else Process.hierarchical
            crew = Crew(agents=list(agents.values()), tasks=ctasks, process=proc, verbose=True)
            res = str(crew.kickoff())
            return {"status": "complete", "crew_result": res, "tasks_outputs": [self._get_raw_out(t, "") for t in ctasks]}
        except Exception as e:
            return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    cb = CrewAIBackend("test-project")
    try:
        print(cb.run_research_crew("AI agent memory systems 2026").keys())
    except Exception as e:
        print(f"CrewAI test: {e}")
