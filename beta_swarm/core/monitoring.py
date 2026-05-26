from prometheus_client import Counter, Gauge, Histogram, start_http_server
import logging
import time

logger = logging.getLogger(__name__)

# Define Metrics
STAGE_EXECUTIONS = Counter('beta_swarm_stage_executions_total', 'Total number of stage executions', ['stage', 'status'])
STAGE_DURATION = Histogram('beta_swarm_stage_duration_seconds', 'Duration of stage execution in seconds', ['stage'])
ACTIVE_AGENTS = Gauge('beta_swarm_active_agents', 'Number of currently active agents')
SYSTEM_LOAD = Gauge('beta_swarm_system_load', 'System load as perceived by the swarm')

def start_metrics_server(port: int = 8000):
    """Starts the Prometheus metrics server."""
    try:
        start_http_server(port)
        logger.info(f"Prometheus metrics server started on port {port}")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")

class MetricsTracker:
    """Helper to track metrics within the orchestrator."""
    @staticmethod
    def record_stage(stage_name: str, duration: float, success: bool):
        status = "success" if success else "error"
        STAGE_EXECUTIONS.labels(stage=stage_name, status=status).inc()
        STAGE_DURATION.labels(stage=stage_name).observe(duration)
