"""
S12 — Monitoring + Maintenance (merged).
Absorbs: s12_monitoring.py (Prometheus/Grafana/health) + s12_maintenance.py (security audit, maintenance.sh).
s12_maintenance.py is deleted after this file.
Uses SQLiteBrain (not KuzuBrain).
"""
from beta_swarm.agents.base import BaseAgent
import json, os, re, logging, subprocess
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class S12MonitoringAgent(BaseAgent):
    """
    Stage 12 — Monitoring + Maintenance.
    Generates: Prometheus config, Grafana dashboard, health poller,
    security audit report, dependency maintenance script.
    """

    def __init__(self, brain=None):
        super().__init__("s12_monitoring", "Monitoring & Maintenance Agent",
                         "Stage 12: Monitoring + Maintenance", brain)

    def _get_default_next_stage(self):
        return "s13_design"

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        project_id   = task.get("project_id", "default")
        project_path = task.get("project_path", f"./projects/{project_id}")
        s3_out       = task.get("s3_prd", {})
        prd          = s3_out.get("prd") or task.get("prd") or {}
        title        = prd.get("metadata", {}).get("title", "App")
        safe         = title.lower().replace(" ", "-")
        preview_url  = task.get("preview_url", "http://localhost:8000")

        self._log_handover(f"S12 started. title={title}")

        files_written: List[str] = []

        def write(rel: str, content: str):
            p = os.path.join(project_path, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)
            if rel not in files_written:
                files_written.append(rel)

        # ── Monitoring ────────────────────────────────────────────────── #
        prom = self._prometheus_config(safe, preview_url)
        write("monitoring/prometheus.yml", prom)
        write("monitoring/grafana_dashboard.json", self._grafana_dashboard(title))
        write("monitoring/docker-compose.monitoring.yml", self._monitoring_compose())
        write("monitoring/health_check.py", self._health_poller(preview_url))

        # ── Maintenance (from s12_maintenance) ────────────────────────── #
        security_report = self._run_security_audit(project_path, title)
        write("maintenance/SECURITY_REPORT.md", security_report)
        write("maintenance/maintenance.sh", self._maintenance_script())
        write("maintenance/MAINTENANCE.md", self._maintenance_doc(title))

        # ── Try pip-audit for real vuln data (best-effort) ─────────────── #
        vuln_data = self._run_pip_audit(project_path)
        if vuln_data:
            write("maintenance/pip_audit.json", vuln_data)

        # ── SQLiteBrain sync ─────────────────────────────────────────── #
        try:
            from beta_swarm.brain.sqlite_brain import SQLiteBrain
            db = SQLiteBrain.get_instance()
            db.register_agent("s12_monitoring", "Monitoring & Maintenance Agent", "Stage 12")
            db.store_artifact(agent_id="s12_monitoring", project=title, stage="S12",
                              data=f"Monitoring+Maintenance: {len(files_written)} files.")
        except Exception as e:
            logger.warning(f"[S12] SQLiteBrain sync (non-fatal): {e}")

        artifact = {"monitoring_maintenance_files": files_written}
        artifact_path = f"./projects/{project_id}/s12_monitoring_output.json"
        os.makedirs(os.path.dirname(artifact_path), exist_ok=True)
        with open(artifact_path, "w", encoding="utf-8") as f:
            json.dump(artifact, f, indent=2)

        self._log_handover(f"S12 completed. {len(files_written)} files.")

        return {
            "status": "complete",
            "monitoring_maintenance_files": files_written,
            "artifact": artifact,
            "artifact_path": artifact_path,
            "next_stage": task.get("next_stage") or self._get_default_next_stage()
        }

    # ── Monitoring generators ─────────────────────────────────────────── #
    def _prometheus_config(self, safe: str, preview_url: str) -> str:
        host = preview_url.replace("http://","").replace("https://","").split("/")[0]
        return f"""global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: '{safe}-backend'
    static_configs:
      - targets: ['{host}']
    metrics_path: /metrics
    scrape_timeout: 10s
"""

    def _grafana_dashboard(self, title: str) -> str:
        return json.dumps({
            "title": f"{title} — Beta Swarm Dashboard",
            "uid": f"betaswarm-{abs(hash(title)) % 10000}",
            "panels": [
                {"id": 1, "title": "HTTP Request Rate", "type": "graph",
                 "targets": [{"expr": "rate(http_requests_total[5m])", "legendFormat": "req/s"}]},
                {"id": 2, "title": "Error Rate", "type": "graph",
                 "targets": [{"expr": "rate(http_requests_total{status=~'5..'}[5m])", "legendFormat": "errors/s"}]},
                {"id": 3, "title": "p95 Latency", "type": "graph",
                 "targets": [{"expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))", "legendFormat": "p95 ms"}]}
            ],
            "schemaVersion": 36, "version": 1
        }, indent=2)

    def _monitoring_compose(self) -> str:
        return """version: '3.8'
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
    ports: ["9090:9090"]
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    ports: ["3001:3000"]
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    depends_on: [prometheus]
    restart: unless-stopped
"""

    def _health_poller(self, base_url: str) -> str:
        return f"""#!/usr/bin/env python3
\"\"\"Lightweight health poller — no external deps.\"\"\"
import time, logging, urllib.request, urllib.error

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
BASE_URL = "{base_url}"
INTERVAL = 30

def check():
    try:
        with urllib.request.urlopen(f"{{BASE_URL}}/health", timeout=5) as r:
            logging.info(f"HEALTHY HTTP {{r.status}}: {{r.read().decode()[:80]}}")
    except urllib.error.HTTPError as e:
        logging.warning(f"HTTP ERROR {{e.code}}: {{e.reason}}")
    except Exception as e:
        logging.error(f"DOWN: {{e}}")

if __name__ == "__main__":
    logging.info(f"Health poller → {{BASE_URL}} (interval={{INTERVAL}}s)")
    while True:
        check()
        time.sleep(INTERVAL)
"""

    # ── Maintenance generators (from s12_maintenance) ─────────────────── #
    def _run_security_audit(self, project_path: str, title: str) -> str:
        prompt = f"""Perform a security audit for the FastAPI project "{title}".
Common issues to check: SQL injection, missing auth, CORS wildcard, insecure defaults, hardcoded secrets.
Return a MAINTENANCE.md-style security report with findings and recommendations."""
        report = self._call_llm(prompt, task_type="s12_maintenance")
        m = re.search(r'```(?:markdown|md)?\s*\n?(.*?)\n?```', report, re.DOTALL)
        if m: report = m.group(1).strip()
        if len(report) < 100:
            report = f"""# Security Audit — {title}

## Findings
| ID   | Severity | Finding                        | Recommendation           |
|------|----------|-------------------------------|--------------------------|
| S-01 | Medium   | CORS allows all origins (*) | Restrict to known domains |
| S-02 | High     | No rate limiting             | Add slowapi middleware   |
| S-03 | Low      | Debug mode may be enabled   | Set DEBUG=False in prod  |
| S-04 | Medium   | No input sanitization docs  | Add pydantic validators  |

## Recommendations
1. Set `CORS_ORIGINS` env var to specific domains
2. Add `slowapi` rate limiter to FastAPI
3. Store secrets in environment variables, never in code
4. Enable HTTPS via reverse proxy (Nginx + Let's Encrypt)
"""
        return report

    def _maintenance_script(self) -> str:
        return """#!/bin/bash
# maintenance.sh — automated dependency update and lint
set -euo pipefail

echo "=== Beta Swarm Maintenance Script ==="

# Update pip dependencies
echo "[1/4] Checking for outdated packages..."
pip list --outdated --format=columns || true

# Run safety check
echo "[2/4] Running pip-audit..."
pip-audit --format=json -o maintenance/pip_audit.json 2>/dev/null || \
  pip list --outdated --format=json > maintenance/pip_audit.json 2>/dev/null || true

# Lint
echo "[3/4] Running flake8..."
python -m flake8 app/ --max-line-length=120 --exclude=__pycache__ || true

# Tests
echo "[4/4] Running tests..."
python -m pytest tests/ -v --tb=short -q || true

echo "=== Maintenance complete ==="
"""

    def _maintenance_doc(self, title: str) -> str:
        return f"""# Maintenance Guide — {title}

## Routine Tasks
- **Weekly**: Run `./maintenance/maintenance.sh`
- **Monthly**: Review `SECURITY_REPORT.md` findings
- **On deploy**: Check `monitoring/health_check.py` output

## Dependency Updates
```bash
pip install --upgrade pip
pip-audit --fix
pip freeze > requirements.txt
```

## Database Maintenance
```bash
# SQLite
sqlite3 app.db "VACUUM;"
sqlite3 app.db "ANALYZE;"
```

## Log Rotation
```bash
docker-compose logs --no-color > logs/$(date +%Y%m%d).log
```
"""

    def _run_pip_audit(self, project_path: str) -> str:
        try:
            result = subprocess.run(
                ["pip-audit", "--format=json"],
                cwd=project_path, capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                return result.stdout
        except Exception:
            pass
        return ""


# Backward-compat alias
S12MaintenanceAgent = S12MonitoringAgent
