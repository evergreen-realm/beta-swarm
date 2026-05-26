from beta_swarm.agents.base import BaseAgent
from typing import Dict, Any
import os

class S10MonitoringAgent(BaseAgent):
    def __init__(self, brain=None):
        super().__init__("s10_monitoring", "Monitoring Agent", "Stage 10: Observability", brain)

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        project_path = task.get("project_path", "./projects/new_project")

        # IMPROVEMENT: Ensure the project_path exists before trying to write files
        os.makedirs(project_path, exist_ok=True)

        self._generate_prometheus_config(project_path)
        self._generate_grafana_dashboard(project_path)
        self._generate_alert_rules(project_path)

        if self.brain:
            self.brain.store_fact(self.agent_id, f"Monitoring configured for {project_path}", "deployment")

        return {"status": "complete", "path": project_path, "next_stage": "s11_documentation"}

    def _generate_prometheus_config(self, path: str):
        config = '''global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'beta-swarm'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: /metrics

  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']
'''
        with open(os.path.join(path, "prometheus.yml"), "w", encoding="utf-8") as f:
            f.write(config)

    def _generate_grafana_dashboard(self, path: str):
        dashboard = '''{
  "dashboard": {
    "title": "Beta Swarm Overview",
    "panels": [
      {"title": "Agent Count", "type": "stat", "targets": [{"expr": "swarm_agents_total"}]},
      {"title": "Task Success Rate", "type": "gauge", "targets": [{"expr": "swarm_tasks_completed / (swarm_tasks_completed + swarm_tasks_failed)"}]},
      {"title": "RAM Usage", "type": "graph", "targets": [{"expr": "swarm_ram_usage_percent"}]},
      {"title": "CPU Usage", "type": "graph", "targets": [{"expr": "swarm_cpu_usage_percent"}]}
    ]
  }
}'''
        dash_dir = os.path.join(path, "grafana", "dashboards")
        os.makedirs(dash_dir, exist_ok=True)
        with open(os.path.join(dash_dir, "swarm.json"), "w", encoding="utf-8") as f:
            f.write(dashboard)

    def _generate_alert_rules(self, path: str):
        rules = '''groups:
- name: swarm_alerts
  rules:
  - alert: HighRAMUsage
    expr: swarm_ram_usage_percent > 85
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "Swarm RAM usage high"

  - alert: AgentCrash
    expr: swarm_tasks_failed > 10
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Multiple agent failures detected"
'''
        with open(os.path.join(path, "alert_rules.yml"), "w", encoding="utf-8") as f:
            f.write(rules)
