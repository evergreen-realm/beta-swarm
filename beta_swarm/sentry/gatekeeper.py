# gatekeeper.py - Security gate check maps and pipeline blocking locks
import os
import json
import logging

logger = logging.getLogger("beta_swarm.gatekeeper")

class Gatekeeper:
    def __init__(self, state_file=None):
        self.state_file = state_file or os.path.join(os.path.dirname(__file__), "gates_state.json")
        self.gates = {
            "gate_static": "secure",
            "gate_semantic": "secure",
            "gate_runtime": "secure"
        }
        self.load_state()

    def load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    self.gates.update(json.load(f))
            except Exception as e:
                logger.error(f"Failed to load gates state: {e}")

    def save_state(self):
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, "w") as f:
                json.dump(self.gates, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save gates state: {e}")

    def get_gate_status(self, gate_id):
        return self.gates.get(gate_id, "unknown")

    def set_gate_status(self, gate_id, status):
        if gate_id in self.gates:
            self.gates[gate_id] = status
            self.save_state()
            return True
        return False

    def is_pipeline_safe(self):
        # All gates must be "secure" for compilation/deployment pipeline safety
        return all(status == "secure" for status in self.gates.values())

# Global Gatekeeper Instance
gatekeeper = Gatekeeper()
