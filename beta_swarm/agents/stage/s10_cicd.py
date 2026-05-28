"""
S10 — CI/CD + Monitoring (merged).
Absorbs: s10_cicd.py (GitHub Actions, Makefile) + s10_monitoring.py (Prometheus, Grafana).
s10_monitoring.py is deleted after this file.
"""
from beta_swarm.agents.base import BaseAgent
import json, os, re, logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class S10CICDAgent(BaseAgent):
    """
    Stage 10 — CI/CD pipelines + Observability stack.
    Generates GitHub Actions workflows, Makefile, Prometheus config,
    Grafana dashboard JSON, and a health-poller script.
    """

    def __init__(self, brain=None):
        super().__init__("s10_cicd", "CI/CD & Monitoring Agent",
                         "Stage 10: CI/CD + Observability", brain)

    def _get_default_next_stage(self):
        return "s11_docs"

    # ------------------------------------------------------------------ #
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        project_id   = task.get("project_id", "default")
        project_path = task.get("project_path", f"./projects/{project_id}")
        s3_out       = task.get("s3_prd", {})
        prd          = s3_out.get("prd") or task.get("prd") or {}
        title        = prd.get("metadata", {}).get("title", "App")
        safe         = title.lower().replace(" ", "-")
        preview_url  = task.get("preview_url", "http://localhost:8000")

        self._log_handover(f"S10 started. title={title}")
        os.makedirs(project_path, exist_ok=True)

        files_written: List[str] = []

        # ── CI/CD ────────────────────────────────────────────────────── #
        ci_content = self._generate_ci(title, safe)
        self._write(project_path, ".github/workflows/ci.yml", ci_content, files_written)
        self._write(project_path, ".github/workflows/cd.yml", self._cd_yaml(title), files_written)
        self._write(project_path, "Makefile", self._makefile(), files_written)

        # ── Monitoring (from s10_monitoring) ─────────────────────────── #
        prom = self._generate_prometheus(safe, preview_url)
        self._write(project_path, "monitoring/prometheus.yml", prom, files_written)
        self._write(project_path, "monitoring/grafana_dashboard.json",
                    self._grafana_dashboard(title), files_written)
        self._write(project_path, "monitoring/docker-compose.monitoring.yml",
                    self._monitoring_compose(), files_written)
        self._write(project_path, "monitoring/health_check.py",
                    self._health_poller(preview_url), files_written)

        artifact = {"cicd_monitoring_files": files_written}
        artifact_path = f"./projects/{project_id}/s10_cicd_output.json"
        os.makedirs(os.path.dirname(artifact_path), exist_ok=True)
        with open(artifact_path, "w", encoding="utf-8") as f:
            json.dump(artifact, f, indent=2)

        self._log_handover(f"S10 completed. {len(files_written)} files.")

        return {
            "status": "complete",
            "cicd_monitoring_files": files_written,
            "artifact": artifact,
            "artifact_path": artifact_path,
            "next_stage": task.get("next_stage") or self._get_default_next_stage()
        }

    # ── CI/CD generators ──────────────────────────────────────────────── #
    def _generate_ci(self, title: str, safe: str) -> str:
        prompt = (f"Generate a GitHub Actions CI workflow for \"{title}\" FastAPI+React project. "
                  "Include: checkout, python setup, pip install, pytest, docker build steps. "
                  "Output ONLY valid YAML.")
        raw = self._call_llm(prompt, task_type="s10_cicd")
        m = re.search(r'```(?:yaml|yml)?\s*\n?(.*?)\n?```', raw, re.DOTALL)
        if m:
            raw = m.group(1).strip()
        return raw if len(raw) > 80 else f"""name: CI — {title}
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - name: Install
        run: pip install -r requirements.txt pytest httpx fastapi
      - name: Test
        run: python -m pytest tests/ -v --tb=short

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build image
        run: docker build -t {safe}:${{{{ github.sha }}}} .
"""

    def _cd_yaml(self, title: str) -> str:
        return f"""name: CD — {title}
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy
        run: |
          docker-compose pull || true
          docker-compose up -d --build
          docker-compose ps
"""

    def _makefile(self) -> str:
        return """.PHONY: dev test build deploy clean logs

dev:
\tdocker-compose up --build

test:
\tpython -m pytest tests/ -v --tb=short

build:
\tdocker-compose build

deploy:
\tdocker-compose up -d

clean:
\tdocker-compose down -v --rmi all

logs:
\tdocker-compose logs -f

lint:
\tpython -m flake8 app/ --max-line-length=120
"""

    # ── Monitoring generators ────────────────────────────────────────── #
    def _generate_prometheus(self, safe: str, preview_url: str) -> str:
        host = preview_url.replace("http://", "").replace("https://", "").split("/")[0]
        return f"""global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: '{safe}-backend'
    static_configs:
      - targets: ['{host}']
    metrics_path: /metrics
"""

    def _grafana_dashboard(self, title: str) -> str:
        return json.dumps({
            "title": f"{title} — Beta Swarm Dashboard",
            "uid": "betaswarm-main",
            "panels": [
                {"id": 1, "title": "Request Rate", "type": "graph",
                 "targets": [{"expr": "rate(http_requests_total[5m])"}]},
                {"id": 2, "title": "Error Rate", "type": "graph",
                 "targets": [{"expr": "rate(http_requests_total{status=~'5..'}[5m])"}]},
                {"id": 3, "title": "Response Time p95", "type": "graph",
                 "targets": [{"expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"}]}
            ],
            "schemaVersion": 36,
            "version": 1
        }, indent=2)

    def _monitoring_compose(self) -> str:
        return """version: '3.8'
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    ports: ["9090:9090"]
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    ports: ["3001:3000"]
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    depends_on: [prometheus]
    restart: unless-stopped
"""

    def _health_poller(self, base_url: str) -> str:
        return f"""#!/usr/bin/env python3
import time, logging
import urllib.request, urllib.error

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
BASE_URL = "{base_url}"
INTERVAL = 30

def check():
    try:
        with urllib.request.urlopen(f"{{BASE_URL}}/health", timeout=5) as r:
            logging.info(f"HEALTHY: {{r.read().decode()[:100]}}")
    except Exception as e:
        logging.error(f"DOWN: {{e}}")

if __name__ == "__main__":
    logging.info(f"Health poller started → {{BASE_URL}}")
    while True:
        check()
        time.sleep(INTERVAL)
"""

    # ── Helper ───────────────────────────────────────────────────────── #
    def _write(self, base: str, rel: str, content: str, registry: List[str]):
        p = os.path.join(base, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        if rel not in registry:
            registry.append(rel)


# Backward-compat aliases
S10MonitoringAgent = S10CICDAgent
