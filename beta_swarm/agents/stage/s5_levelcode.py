import os
import logging
import time
from beta_swarm.agents.base import BaseAgent
from beta_swarm.tools.api_stack.router import router
from beta_swarm.brain.neo4j_manager import Neo4jBrain
from beta_swarm.brain.kuzu_manager import KuzuBrain
from beta_swarm.brain.letta_client import LettaClient
from beta_swarm.brain.cognee_client import CogneeClient
from beta_swarm.brain.graphiti_manager import GraphitiManager

logger = logging.getLogger(__name__)


class S5LevelCodeAgent(BaseAgent):
    def __init__(self, complexity: str = "medium"):
        super().__init__(agent_id="S5", name="S5_LevelCode", stage="Coding")
        self.complexity = complexity
        try:
            self.neo4j = Neo4jBrain()
            self.kuzu = KuzuBrain()
            self.letta = LettaClient()
            self.cognee = CogneeClient()
            self.graphiti = GraphitiManager()
        except Exception as e:
            logger.warning(f"Could not initialize all brain managers: {e}")
            self.neo4j = None
            self.kuzu = None
            self.letta = None
            self.cognee = None
            self.graphiti = None

    def execute(self, prd_markdown: str = "", architecture_markdown: str = "", **kwargs) -> dict:
        logger.info("Starting LevelCode (S5) Generation...")

        # Support being called with a task dict (by orchestrator) or positional args
        if not prd_markdown and "task" in kwargs:
            task = kwargs["task"]
            prd_markdown = str(task.get("s3_prd", {}).get("prd", {}).get("full_content", ""))
            architecture_markdown = str(task.get("s4_architecture", {}).get("architecture", {}))

        system_prompt = (
            "You are an expert frontend developer. "
            "Generate a sleek, dark-mode Uber clone. Return ONLY the raw code for the requested file, no markdown formatting blocks."
        )

        files_to_generate = {
            "index.html": "Create the index.html for the Uber clone with a Leaflet map div and a glassmorphism ride request panel.",
            "style.css": "Create the style.css with dark mode, glowing accents, and micro-animations for the UI panel.",
            "app.js": "Create app.js that initializes a basic map and handles the 'Request Ride' button click event."
        }

        output_dir = os.path.join(os.getcwd(), "uber_clone_output")
        os.makedirs(output_dir, exist_ok=True)

        generated_files = []

        for filename, instruction in files_to_generate.items():
            logger.info(f"Generating {filename} [Complexity: {self.complexity}]")
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context: {prd_markdown}\n\nTask: {instruction}"}
            ]

            code = router.generate(messages)

            if code.startswith("```"):
                lines = code.split("\n")
                if len(lines) > 2:
                    code = "\n".join(lines[1:-1])

            file_path = os.path.join(output_dir, filename)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)

            generated_files.append(file_path)
            logger.info(f"Saved {filename} to {file_path}")

        self._update_brain_vault(generated_files)

        return {"files": generated_files, "status": "success"}

    def _update_brain_vault(self, generated_files: list):
        logger.info("Syncing generated code to Brain Vault...")
        try:
            if self.kuzu:
                self.kuzu.add_agent("S5", "LevelCode_Agent", "Coding")
                self.kuzu.store_agent_memory(
                    "S5",
                    f"Generated {len(generated_files)} files.",
                    "code_generation"
                )
            if self.neo4j:
                self.neo4j.add_global_knowledge(
                    "Uber Clone Project",
                    f"Files created: {', '.join(generated_files)}"
                )
            if self.letta:
                agent_data = self.letta.create_agent(
                    "S5_Coder",
                    "I am the S5 frontend developer.",
                    "A user who needs frontend code generated."
                )
                if agent_data and "id" in agent_data:
                    self.letta.send_message(agent_data["id"], "I just built the Uber clone website.")
            if self.graphiti:
                self.graphiti.add_temporal_edge(
                    source_id="S5",
                    target_id="UberCloneCode",
                    relation="generated",
                    timestamp=int(time.time())
                )
        except Exception as e:
            logger.error(f"Brain vault sync failed (non-fatal): {e}")
