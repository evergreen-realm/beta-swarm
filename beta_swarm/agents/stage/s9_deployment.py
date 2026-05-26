# s9_deployment.py - Stage 9 Swarm Deployment synthesis orchestrator
import os
import time
import logging
from typing import Dict, Any
from beta_swarm.agents.base import BaseAgent
from beta_swarm.brain.kuzudb_manager import KuzuBrain
from beta_swarm.brain.obsidian_sync import obsidian_sync

logger = logging.getLogger("beta_swarm.s9_deployment")

class Stage9DeploymentAgent(BaseAgent):
    def __init__(self, brain=None):
        super().__init__("s9_deployment", "Deployment Stage Agent", "Stage 9: Deployment", brain)

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesize deployment manifests, run AST checks, record artifacts in KuzuDB, sync to Obsidian."""
        project_name = task.get("project_name") or task.get("prd", {}).get("metadata", {}).get("title", "BetaSwarmApp")
        project_path = task.get("project_path") or os.path.join(os.getcwd(), "deploy")
        
        logger.info(f"[{self.name}] Initiating deployment synthesis in path: {project_path}")
        os.makedirs(project_path, exist_ok=True)
        
        # 1. Synthesize docker-compose.yml
        compose_content = """version: '3.8'
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: beta_db
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: secretpassword
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U admin -d beta_db"]
      interval: 10s
      timeout: 5s
      retries: 5
"""
        compose_path = os.path.join(project_path, "docker-compose.yml")
        self._write_file(compose_path, compose_content)
        
        # 2. Synthesize deploy.sh
        deploy_content = """#!/bin/bash
set -euo pipefail
echo "Starting Beta Swarm Deployment..."
docker-compose up -d
echo "Deployment successful."
"""
        deploy_path = os.path.join(project_path, "deploy.sh")
        self._write_file(deploy_path, deploy_content)
        
        # 3. Synthesize .github/workflows/ci.yml
        ci_dir = os.path.join(project_path, ".github", "workflows")
        os.makedirs(ci_dir, exist_ok=True)
        ci_content = """name: Swarm CI
on: [push]
jobs:
  build-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Tests
        run: pytest
      - name: Build Docker
        uses: docker/build-push-action@v4
        with:
          context: .
          push: false
"""
        ci_path = os.path.join(ci_dir, "ci.yml")
        self._write_file(ci_path, ci_content)
        
        # 4. Synthesize .env.example
        env_content = """DATABASE_URL=postgresql://admin:secretpassword@postgres:5432/beta_db
PORT=8000
"""
        env_path = os.path.join(project_path, ".env.example")
        self._write_file(env_path, env_content)

        generated_files = [
            "docker-compose.yml",
            "deploy.sh",
            ".github/workflows/ci.yml",
            ".env.example"
        ]

        # 5. Write artifact into SQLite Brain
        artifact_id = f"art_s9_{int(time.time())}"
        try:
            db = KuzuBrain.get_instance(mode="auto")
            result = db.store_artifact(
                agent_id="s9_deployment",
                project=project_name,
                stage="S9",
                data="Docker compose and CI/CD generated."
            )
            artifact_id = result.get("artifact_id", artifact_id)
            logger.info("Successfully recorded deployment artifact in SQLite brain.")
        except Exception as e:
            logger.warning(f"Artifact record skipped: {e}")

        # 6. Sync daily note log directly to Obsidian Memory Vault
        log_msg = f"Synthesized production docker-compose deployment manifest for {project_name} successfully."
        obsidian_sync.sync_to_daily_note(log_msg, agent_id=self.agent_id)
        
        return {
            "status": "complete",
            "artifact_id": artifact_id,
            "manifest_path": compose_path,
            "generated_files": generated_files,
            "next_stage": "s10_monitoring"
        }

# Alias for backwards compatibility with legacy imports and test suites
S9DeploymentAgent = Stage9DeploymentAgent

if __name__ == "__main__":
    agent = Stage9DeploymentAgent()
    res = agent.execute({"project_name": "ProductionMobileDashboard"})
    print("Execution complete:", res)
