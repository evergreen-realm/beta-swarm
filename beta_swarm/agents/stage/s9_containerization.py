"""
S9 — Containerization + Deployment (merged).
Absorbs: s9_containerization.py + s9_deployment.py (KuzuDB/Obsidian sync).
s9_deployment.py is deleted after this file.
"""
from beta_swarm.agents.base import BaseAgent
import json, os, re, logging, socket, subprocess, time
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class S9ContainerizationAgent(BaseAgent):
    """
    Stage 9 — Docker + Deployment synthesis.
    Generates docker-compose, Dockerfiles, nginx.conf, .env.example, deploy.sh.
    Syncs artefacts to KuzuDB brain and Obsidian daily note.
    """

    def __init__(self, brain=None):
        super().__init__("s9_containerization", "Containerization & Deployment Agent",
                         "Stage 9: Docker + Deploy", brain)

    def _get_default_next_stage(self):
        return "s10_cicd"

    # ------------------------------------------------------------------ #
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        project_id   = task.get("project_id", "default")
        project_path = task.get("project_path", f"./projects/{project_id}")
        deploy_mode  = task.get("deploy_mode", "local")

        s3_out = task.get("s3_prd", {})
        prd    = s3_out.get("prd") or task.get("prd") or {}
        title  = prd.get("metadata", {}).get("title", "App")
        safe   = title.lower().replace(" ", "-")

        self._log_handover(f"S9 started. title={title}, mode={deploy_mode}")
        os.makedirs(project_path, exist_ok=True)

        files_written: List[str] = []

        # 1. docker-compose.yml (LLM → fallback)
        dc_content = self._generate_compose(title, safe, prd)
        self._write(project_path, "docker-compose.yml", dc_content, files_written)

        # 2. Backend Dockerfile (guarantee)
        bd = os.path.join(project_path, "Dockerfile")
        if not os.path.exists(bd) or os.path.getsize(bd) < 20:
            self._write(project_path, "Dockerfile", self._backend_dockerfile(), files_written)

        # 3. Frontend nginx config + Dockerfile
        fe_df = os.path.join(project_path, "frontend", "Dockerfile")
        if not os.path.exists(fe_df) or os.path.getsize(fe_df) < 20:
            self._write(project_path, "frontend/Dockerfile", self._frontend_dockerfile(), files_written)
        fe_ng = os.path.join(project_path, "frontend", "nginx.conf")
        if not os.path.exists(fe_ng):
            self._write(project_path, "frontend/nginx.conf", self._nginx_conf(), files_written)

        # 4. .env.example
        self._write(project_path, ".env.example",
                    f"DATABASE_URL=postgresql://postgres:postgres@db:5432/{safe}\n"
                    f"SECRET_KEY=change-me\nBACKEND_PORT=8000\nFRONTEND_PORT=80\n",
                    files_written)

        # 5. deploy.sh (from s9_deployment)
        self._write(project_path, "deploy.sh",
                    "#!/bin/bash\nset -euo pipefail\n"
                    'echo "Starting deployment..."\n'
                    "docker-compose up -d --build\n"
                    'echo "Deployment complete."\n',
                    files_written)
        # make executable (best-effort)
        try:
            os.chmod(os.path.join(project_path, "deploy.sh"), 0o755)
        except Exception:
            pass

        # 6. GitHub Actions CI skeleton (from s9_deployment)
        ci_dir = os.path.join(project_path, ".github", "workflows")
        os.makedirs(ci_dir, exist_ok=True)
        ci_path = os.path.join(ci_dir, "ci.yml")
        if not os.path.exists(ci_path):
            self._write(project_path, ".github/workflows/ci.yml",
                        f"name: Swarm CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n"
                        f"    steps:\n      - uses: actions/checkout@v4\n"
                        f"      - run: pip install -r requirements.txt && pytest\n",
                        files_written)

        # 7. Optional live deploy (local uvicorn)
        preview_url = "http://localhost:8000"
        if deploy_mode in ("local", "auto"):
            preview_url = self._maybe_start_local(project_path)

        # 8. KuzuDB + Obsidian sync (from s9_deployment)
        artifact_id = self._sync_brain(project_id, title, files_written)

        artifact = {
            "containerization_files": files_written,
            "preview_url": preview_url,
            "artifact_id": artifact_id,
        }
        artifact_path = f"./projects/{project_id}/s9_containerization_output.json"
        os.makedirs(os.path.dirname(artifact_path), exist_ok=True)
        with open(artifact_path, "w", encoding="utf-8") as f:
            json.dump(artifact, f, indent=2)

        self._log_handover(f"S9 completed. {len(files_written)} files. preview={preview_url}")

        return {
            "status": "complete",
            "containerization_files": files_written,
            "preview_url": preview_url,
            "artifact": artifact,
            "artifact_path": artifact_path,
            "next_stage": task.get("next_stage") or self._get_default_next_stage()
        }

    # ------------------------------------------------------------------ #
    # Compose generation
    # ------------------------------------------------------------------ #
    def _generate_compose(self, title: str, safe: str, prd: dict) -> str:
        prompt = (f"Generate a production-ready docker-compose.yml for \"{title}\" with services: "
                  "backend(FastAPI port 8000), frontend(Nginx port 80), db(PostgreSQL port 5432). "
                  "Include healthchecks, volumes, depends_on. Output ONLY valid YAML.")
        raw = self._call_llm(prompt, task_type="s9_containerization")
        m = re.search(r'```(?:yaml|yml)?\s*\n?(.*?)\n?```', raw, re.DOTALL)
        if m:
            raw = m.group(1).strip()
        if len(raw) < 80:
            return self._fallback_compose(safe)
        return raw

    def _fallback_compose(self, safe: str) -> str:
        return f"""version: '3.8'
services:
  backend:
    build: .
    container_name: {safe}-backend
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/{safe}
      - SECRET_KEY=${{SECRET_KEY:-dev-secret}}
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build: ./frontend
    container_name: {safe}-frontend
    ports: ["80:80"]
    depends_on: [backend]
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    container_name: {safe}-db
    environment:
      POSTGRES_DB: {safe}
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  postgres_data:
"""

    def _backend_dockerfile(self) -> str:
        return ("FROM python:3.10-slim\nWORKDIR /app\nCOPY requirements.txt .\n"
                "RUN pip install --no-cache-dir -r requirements.txt\nCOPY . .\n"
                "EXPOSE 8000\nCMD [\"uvicorn\",\"app.main:app\",\"--host\",\"0.0.0.0\",\"--port\",\"8000\"]\n")

    def _frontend_dockerfile(self) -> str:
        return ("FROM nginx:alpine\nCOPY . /usr/share/nginx/html\n"
                "COPY nginx.conf /etc/nginx/conf.d/default.conf\n"
                "EXPOSE 80\nCMD [\"nginx\",\"-g\",\"daemon off;\"]\n")

    def _nginx_conf(self) -> str:
        return ("server {\n    listen 80;\n    root /usr/share/nginx/html;\n    index index.html;\n"
                "    location / { try_files $uri $uri/ /index.html; }\n"
                "    location /api/ {\n        proxy_pass http://backend:8000;\n"
                "        proxy_set_header Host $host;\n    }\n}\n")

    # ------------------------------------------------------------------ #
    # Local uvicorn start (best-effort)
    # ------------------------------------------------------------------ #
    def _maybe_start_local(self, project_path: str) -> str:
        port = self._free_port(8000, 8099)
        try:
            subprocess.Popen(
                ["python", "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                cwd=project_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            logger.info(f"[S9] Uvicorn started on port {port}")
        except Exception as e:
            logger.warning(f"[S9] Could not start uvicorn (non-fatal): {e}")
        return f"http://127.0.0.1:{port}"

    def _free_port(self, start: int, end: int) -> int:
        for p in range(start, end):
            with socket.socket() as s:
                if s.connect_ex(("127.0.0.1", p)) != 0:
                    return p
        return start

    # ------------------------------------------------------------------ #
    # Brain sync (from s9_deployment)
    # ------------------------------------------------------------------ #
    def _sync_brain(self, project_id: str, title: str, files: List[str]) -> str:
        artifact_id = f"art_s9_{int(time.time())}"
        # SQLiteBrain
        try:
            from beta_swarm.brain.sqlite_brain import SQLiteBrain
            db = SQLiteBrain.get_instance(mode="auto")
            db.register_agent("s9_containerization", "Containerization Agent", "Stage 9")
            result = db.store_artifact(
                agent_id="s9_containerization", project=title, stage="S9",
                data=f"Docker compose + deploy for {project_id}: {len(files)} files."
            )
            if isinstance(result, dict):
                artifact_id = result.get("artifact_id", artifact_id)
        except Exception as e:
            logger.warning(f"[S9] SQLiteBrain sync (non-fatal): {e}")
        # Obsidian
        try:
            from beta_swarm.brain.obsidian_sync import obsidian_sync
            obsidian_sync.sync_to_daily_note(
                f"S9 containerized {title}: {len(files)} files generated.",
                agent_id="s9_containerization"
            )
        except Exception as e:
            logger.warning(f"[S9] Obsidian sync (non-fatal): {e}")
        return artifact_id

    # ------------------------------------------------------------------ #
    def _write(self, base: str, rel: str, content: str, registry: List[str]):
        p = os.path.join(base, rel)
        os.makedirs(os.path.dirname(p) if os.path.dirname(p) != base else base, exist_ok=True)
        if os.path.dirname(p):
            os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        if rel not in registry:
            registry.append(rel)


# Backward-compat aliases
Stage9DeploymentAgent = S9ContainerizationAgent
S9DeploymentAgent     = S9ContainerizationAgent
