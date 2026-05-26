import logging
from typing import Dict, Any
from beta_swarm.agents.base import BaseAgent

logger = logging.getLogger(__name__)

class S10MonitoringAgent(BaseAgent):
    """
    S10: Monitoring Agent
    Instruments the application for monitoring and generates dashboards.
    """
    def __init__(self, brain=None):
        super().__init__("s10_monitoring", "Monitoring Agent", "Stage 10: Observability", brain)

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Setting up monitoring and instrumentation.")
        
        instrumentation = self._instrument_app(task)
        prom_config = self._generate_prometheus_config(task)
        grafana_dash = self._generate_grafana_dashboard(task)
        
        return {
            "status": "complete",
            "monitoring_config": {
                "instrumentation": instrumentation,
                "prometheus": prom_config,
                "grafana": grafana_dash
            },
            "next_stage": "s11_documentation"
        }

    def _instrument_app(self, task: Dict[str, Any]) -> str:
        """Adds prometheus_client instrumentation to the backend code."""
        prompt = "Add prometheus metrics to a FastAPI app."
        return self.call_llm([{"role": "user", "content": prompt}])

    def _generate_prometheus_config(self, task: Dict[str, Any]) -> str:
        """Generates prometheus.yml configuration."""
        prompt = "Generate a prometheus.yml for scraping a FastAPI service."
        return self.call_llm([{"role": "user", "content": prompt}])

    def _generate_grafana_dashboard(self, task: Dict[str, Any]) -> str:
        """Generates a JSON dashboard for Grafana."""
        prompt = "Generate a Grafana dashboard JSON for a FastAPI app."
        return self.call_llm([{"role": "user", "content": prompt}])
