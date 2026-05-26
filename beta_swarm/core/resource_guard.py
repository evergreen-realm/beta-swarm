import time
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ResourceGuard:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance
    
    def _init(self):
        from beta_swarm.agents.health.h5_ram_governor import H5RamGovernorAgent
        self.governor = H5RamGovernorAgent()
        self.last_check = 0
        self.check_interval = 30  # seconds
    
    def check_before_execute(self, agent_id: str, stage: str) -> Dict:
        """Called before ANY agent executes. Returns ok or blocks."""
        # 1. Check if enough time has passed since last check
        if time.time() - self.last_check < self.check_interval:
            return {"ok": True, "cached": True}
        
        self.last_check = time.time()
        
        try:
            # 2. Get current RAM state
            capacity = self.governor.execute({"action": "check_capacity"})
            t490_free = capacity["t490"]["free_mb"]
            t490_percent = capacity["t490"]["percent"]
            
            # 3. Decision logic
            if t490_percent > 95:
                # CRITICAL: Emergency purge + notify
                self._emergency_purge(agent_id)
                return {"ok": False, "reason": "CRITICAL RAM", "action": "emergency_purged"}
            
            if t490_percent > 85:
                # HIGH: Activate health agents, warn but allow
                self._activate_health_agents("high_ram", capacity)
                return {"ok": True, "warning": "HIGH RAM usage", "percent": t490_percent}
            
            if t490_percent > 70:
                # MEDIUM: Log warning, continue
                logger.warning(f"Elevated RAM usage detected: {t490_percent}%")
                return {"ok": True, "notice": "Elevated RAM", "percent": t490_percent}
            
            # 4. Transition to stage (start needed containers/models/tools)
            self.governor.execute({"action": "transition_to_stage", "stage": stage})
            
            return {"ok": True, "free_mb": t490_free, "percent": t490_percent}
        except Exception as e:
            logger.error(f"ResourceGuard check_before_execute error: {e}")
            return {"ok": True, "error": str(e)}
    
    def _emergency_purge(self, triggered_by: str):
        logger.critical(f"EMERGENCY PURGE triggered by {triggered_by}")
        try:
            self.governor.execute({"action": "emergency_purge"})
        except Exception as e:
            logger.error(f"Governor emergency purge failed: {e}")
        self._activate_health_agents("emergency_purge", {})
    
    def _activate_health_agents(self, reason: str, capacity: Dict):
        """Activate health monitoring agents when thresholds breach."""
        # Import health agents
        from beta_swarm.agents.health.h1_resource_monitor import H1ResourceMonitorAgent
        from beta_swarm.agents.health.h2_model_health import H2ModelHealthAgent
        from beta_swarm.agents.health.h3_service_health import H3ServiceHealthAgent
        from beta_swarm.agents.health.h4_auto_reboot import H4AutoRebootAgent
        
        agents_to_activate = []
        
        if reason == "high_ram":
            agents_to_activate = [H1ResourceMonitorAgent, H2ModelHealthAgent]
        elif reason == "emergency_purge":
            agents_to_activate = [H1ResourceMonitorAgent, H2ModelHealthAgent, H3ServiceHealthAgent, H4AutoRebootAgent]
        elif reason == "model_unload":
            agents_to_activate = [H2ModelHealthAgent]
        elif reason == "service_down":
            agents_to_activate = [H3ServiceHealthAgent, H4AutoRebootAgent]
        
        for AgentClass in agents_to_activate:
            try:
                agent = AgentClass()
                agent.execute({"trigger": reason, "capacity": capacity})
            except Exception as e:
                logger.error(f"Health agent {AgentClass.__name__} failed: {e}")
