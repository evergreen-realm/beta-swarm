from beta_swarm.agents.base import BaseAgent
from typing import Dict, Any, List
from datetime import datetime

class S3PRDAgent(BaseAgent):
    def __init__(self, brain=None):
        super().__init__("s3_prd", "PRD Agent", "Stage 3: Product Requirements", brain)

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        # Support both direct "concept" (from initial task) or from S1 result
        s1_out = task.get("s1_ideation", {})
        concept = s1_out.get("concept") or task.get("concept") or task.get("idea") or {}
        
        s2_out = task.get("s2_research", {})
        research = s2_out.get("research_summary") or task.get("research_summary", "")
        
        domain = task.get("business_domain", "general")

        prompt = f"""
        Generate a comprehensive PRD (Product Requirements Document) for the following concept and research:
        
        CONCEPT:
        {concept}
        
        RESEARCH:
        {research}
        
        The PRD should include:
        1. Objectives
        2. Detailed User Stories
        3. Functional Requirements (FR-1, FR-2, etc.)
        4. Non-Functional Requirements
        5. Tech Stack Recommendation (Choose between Vanilla JS or React/Next.js)
        6. TECHNICAL BLUEPRINT (CRITICAL):
           - DATA SCHEMA: Detailed table/model names, fields, types, and relationships.
           - API SPECIFICATION: Detailed endpoint paths, methods (GET/POST/etc), function names, parameters, and return types.
           - COMPONENT BLUEPRINT: Frontend component names, their purpose, and their interactions with the API.
        7. Security Requirements
        8. Milestones
        """
        
        llm_response = self.call_llm([{"role": "user", "content": prompt}], max_tokens=2048)
        
        objectives = self._parse_list(llm_response, "Objectives") or self._generate_objectives(concept)
        user_stories = self._parse_list(llm_response, "User Stories") or self._generate_user_stories(concept)
        functional_requirements = self._parse_list(llm_response, "Functional Requirements") or self._generate_functional_reqs(concept)
        
        # Ensure user_stories format is list of dict with 'as_a', 'i_want', 'so_that'
        formatted_stories = []
        for story in user_stories:
            if isinstance(story, dict):
                formatted_stories.append(story)
            else:
                # String format parsing fallback
                formatted_stories.append({
                    "as_a": "user",
                    "i_want": str(story),
                    "so_that": "I can achieve my goal"
                })
        if not formatted_stories:
            formatted_stories = self._generate_user_stories(concept)

        prd = {
            "metadata": {
                "title": concept.get("title"),
                "version": "1.0",
                "date": datetime.now().isoformat(),
                "author": "Beta Swarm S3 Agent",
                "domain": domain
            },
            "full_content": llm_response,
            "objectives": objectives,
            "user_stories": formatted_stories,
            "functional_requirements": functional_requirements,
            "tech_stack_recommendation": self._parse_field(llm_response, "Tech Stack Recommendation") or str(self._recommend_stack(concept, research)),
            "blueprint": {
                "data_schema": self._parse_field(llm_response, "DATA SCHEMA") or "schema: base",
                "api_spec": self._parse_field(llm_response, "API SPECIFICATION") or "spec: base",
                "components": self._parse_field(llm_response, "COMPONENT BLUEPRINT") or "components: base"
            }
        }
        
        if self.brain:
            self.brain.store_fact(self.agent_id, f"Detailed PRD & Blueprint for {concept.get('title')}", "prd")
            
        return {"status": "complete", "prd": prd, "next_stage": "s4_architecture"}

    def _generate_objectives(self, concept: Dict) -> List[str]:
        return [
            f"Solve: {concept.get('problem_statement', '')[:200]}",
            "Deliver MVP within estimated timeline",
            "Ensure code quality via automated review"
        ]

    def _generate_user_stories(self, concept: Dict) -> List[Dict]:
        users = concept.get("target_users", ["user"])
        features = concept.get("key_features", [])
        stories = []
        for user in users[:3]:
            for feat in features[:3]:
                stories.append({
                    "as_a": user,
                    "i_want": feat,
                    "so_that": "I can accomplish my goal efficiently"
                })
        return stories

    def _generate_functional_reqs(self, concept: Dict) -> List[str]:
        features = concept.get("key_features", [])
        return [f"FR-{i+1}: Implement {feat}" for i, feat in enumerate(features)]

    def _generate_non_functional_reqs(self, concept: Dict) -> List[str]:
        return [
            "NFR-1: Response time < 200ms for API calls",
            "NFR-2: 99.9% uptime",
            "NFR-3: Support 1000 concurrent users",
            "NFR-4: Zero-cost infrastructure"
        ]

    def _recommend_stack(self, concept: Dict, research: str) -> Dict:
        tech_hints = concept.get("tech_stack_hints", [])
        return {
            "frontend": "React + TypeScript" if "react" in tech_hints or "web" in tech_hints else "HTML/CSS/JS",
            "backend": "FastAPI + Python" if "python" in tech_hints or "api" in tech_hints else "Node.js",
            "database": "PostgreSQL" if "database" in tech_hints else "SQLite",
            "ai": "Local LLM via LM Studio" if "ai" in tech_hints else None,
            "deployment": "Docker + Self-hosted"
        }

    def _generate_security_reqs(self, domain: str) -> List[str]:
        base = ["SEC-1: Input validation on all endpoints", "SEC-2: No secrets in code"]
        if domain in ["healthcare", "finance"]:
            base.extend(["SEC-3: Encryption at rest", "SEC-4: Audit logging"])
        return base

    def _generate_milestones(self) -> List[Dict]:
        return [
            {"name": "M1: Architecture & Setup", "duration": "2 days"},
            {"name": "M2: Core Backend", "duration": "3 days"},
            {"name": "M3: Frontend & Integration", "duration": "3 days"},
            {"name": "M4: Testing & Deployment", "duration": "2 days"}
        ]
