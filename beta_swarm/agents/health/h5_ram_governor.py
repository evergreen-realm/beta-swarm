import os
import json
import time
import subprocess
import psutil
import logging
from typing import Dict, Any, List, Optional
from beta_swarm.agents.base import BaseAgent

logger = logging.getLogger(__name__)

class H5RamGovernorAgent(BaseAgent):
    def __init__(self, agent_id: str = "h5_ram_governor", name: str = "RAM Governor", stage: str = "all"):
        super().__init__(agent_id, name, stage)
        
        # Load config
        config_path = os.path.join(os.path.dirname(__file__), "../../config/ram_governor.json")
        try:
            with open(config_path, "r") as f:
                self.config = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load RAM Governor config: {e}")
            self.config = {}

        self.budgets = self.config.get("machines", {})
        
        # Service footprints (MB)
        self.container_footprints = {
            "neo4j": {"mb": 2048, "machine": "production", "stage_needed": ["S2", "S3", "S4", "S5", "S6", "S7"], "essential": False, "container": "neo4j"},
            "letta": {"mb": 1024, "machine": "t490", "stage_needed": "all", "essential": True, "container": "beta-letta"},
            "letta-postgres": {"mb": 256, "machine": "t490", "stage_needed": "all", "essential": True, "container": "letta-postgres"},
            "cognee": {"mb": 1024, "machine": "production", "stage_needed": ["S2"], "essential": False, "container": "beta-cognee"},
            "cognee-qdrant": {"mb": 256, "machine": "production", "stage_needed": ["S2"], "essential": False, "container": "cognee-qdrant"},
            "graphiti": {"mb": 512, "machine": "production", "stage_needed": ["S2", "S3"], "essential": False, "container": "graphiti"},
            "gitnexus-mcp": {"mb": 1024, "machine": "production", "stage_needed": ["S5", "S6", "S7", "X1", "X2", "X3", "X4"], "essential": False, "container": "gitnexus-mcp"},
            "traefik": {"mb": 128, "machine": "t490", "stage_needed": "all", "essential": True, "container": "traefik"},
            "beta-swarm-core": {"mb": 512, "machine": "t490", "stage_needed": "all", "essential": True, "container": "beta-swarm-core"},
            # Monitoring Batch
            "prometheus": {"mb": 512, "machine": "production", "stage_needed": ["S10", "S12"], "essential": False, "batch": "monitoring"},
            "grafana": {"mb": 512, "machine": "production", "stage_needed": ["S10", "S12"], "essential": False, "batch": "monitoring"},
            "node-exporter": {"mb": 64, "machine": "production", "stage_needed": ["S10", "S12"], "essential": False, "batch": "monitoring"},
            "uptime-kuma": {"mb": 256, "machine": "production", "stage_needed": ["S10", "S12"], "essential": False, "batch": "monitoring"},
            "bugsink": {"mb": 512, "machine": "production", "stage_needed": ["S10", "S12"], "essential": False, "batch": "monitoring"},
            "alertmanager": {"mb": 128, "machine": "production", "stage_needed": ["S10", "S12"], "essential": False, "batch": "monitoring"}
        }

        self.model_footprints = {
            "bitnet-2b": {"mb": 400, "machine": "t490", "stage_needed": ["S1"]},
            "bitnet-7b": {"mb": 1200, "machine": "t490", "stage_needed": ["S4", "S8"]},
            "bitnet-13b": {"mb": 2200, "machine": "t490", "stage_needed": ["S9", "S11"]},
            "qwen-2b": {"mb": 1536, "machine": "production", "stage_needed": ["S1"]},
            "qwen-7b": {"mb": 4608, "machine": "production", "stage_needed": ["S3"]},
            "qwen-14b": {"mb": 9216, "machine": "production", "stage_needed": ["S2"]},
            "qwen-32b": {"mb": 20480, "machine": "production", "stage_needed": ["S5", "S6", "S7"]},
            "deepseek-14b": {"mb": 9216, "machine": "production", "stage_needed": ["X1", "X2", "X3", "X4"]},
            "llama-70b": {"mb": 40960, "machine": "production", "stage_needed": ["S13"]}
        }

        self.tool_footprints = {
            "aider": {"mb": 1024, "machine": "t490", "stage_needed": ["S5", "S6", "S7"]},
            "whisper-cpp": {"mb": 512, "machine": "t490", "stage_needed": ["S1"]},
            "bitnet-runtime": {"mb": 512, "machine": "t490", "stage_needed": ["S1", "S4", "S8", "S9", "S11"]},
            "obsidian": {"mb": 512, "machine": "t490", "stage_needed": "all"},
            "lm-studio-server": {"mb": 512, "machine": "production", "stage_needed": "all"}
        }

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        action = payload.get("action")
        stage = payload.get("stage")

        if action == "transition_to_stage":
            return self._transition_to_stage(stage)
        elif action == "check_capacity":
            return self._check_capacity()
        elif action == "offload_to_production":
            return self._offload_container_to_production(payload.get("container"))
        elif action == "emergency_purge":
            return self._emergency_purge()
        else:
            raise ValueError(f"Unknown action: {action}")

    def _check_capacity(self) -> Dict[str, Any]:
        t490_ram = psutil.virtual_memory()
        prod_ram = self._ssh_check_ram()
        
        return {
            "t490": {
                "free_mb": t490_ram.available // (1024 * 1024),
                "total_mb": t490_ram.total // (1024 * 1024),
                "percent": t490_ram.percent
            },
            "production": prod_ram
        }

    def _transition_to_stage(self, stage: str) -> Dict[str, Any]:
        logger.info(f"Transitioning to stage: {stage}")
        
        # 1. Identify needs (container names)
        target_container_names = []
        for k, v in self.container_footprints.items():
            if v["stage_needed"] == "all" or stage in v["stage_needed"]:
                target_container_names.append(v.get("container", k))
        
        target_models = [k for k, v in self.model_footprints.items() if stage in v["stage_needed"]]
        target_tools = [k for k, v in self.tool_footprints.items() if v["stage_needed"] == "all" or stage in v["stage_needed"]]

        # 2. Identify currently running
        current_container_names = self._get_running_containers()
        current_models = self._get_loaded_models()
        current_tools = self._get_active_tools()

        # 3. Stop unneeded
        for c_name in current_container_names:
            # Find which footprint entry matches this container name
            footprint_key = next((k for k, v in self.container_footprints.items() if v.get("container", k) == c_name), None)
            
            if c_name not in target_container_names:
                if footprint_key and self.container_footprints[footprint_key].get("essential"):
                    continue # Never stop essential
                self._stop_container(footprint_key or c_name)
                time.sleep(self.config.get("stagger", {}).get("container_stop_delay_sec", 2))

        for model in current_models:
            if model not in target_models:
                self._unload_model(model)

        for tool in current_tools:
            if tool not in target_tools:
                self._stop_tool(tool)

        # 4. Start needed
        for k, v in self.container_footprints.items():
            c_name = v.get("container", k)
            if c_name in target_container_names and c_name not in current_container_names:
                self._start_container(k)
                time.sleep(self.config.get("stagger", {}).get("container_start_delay_sec", 3))

        for model in target_models:
            if model not in current_models:
                self._load_model(model)

        for tool in target_tools:
            if tool not in current_tools:
                self._start_tool(tool)

        return {"status": "success", "stage": stage, "active": self._verify_state()}

    def _start_container(self, name: str):
        logger.info(f"Starting container: {name}")
        try:
            # Use the absolute path to the consolidated deploy directory
            deploy_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../deploy"))
            subprocess.run(["docker-compose", "-f", "master-docker-compose.yml", "up", "-d", name], cwd=deploy_dir, check=True)
        except Exception as e:
            logger.error(f"Failed to start via compose: {e}. Trying direct docker start...")
            container_name = self.container_footprints.get(name, {}).get("container", name)
            subprocess.run(["docker", "start", container_name])

    def _stop_container(self, name: str):
        logger.info(f"Stopping container: {name}")
        container_name = self.container_footprints.get(name, {}).get("container", name)
        subprocess.run(["docker", "stop", container_name])

    def _load_model(self, model_name: str):
        logger.info(f"Loading model: {model_name}")
        meta = self.model_footprints[model_name]
        if meta["machine"] == "t490":
            # BitNet local load logic
            pass
        else:
            # LM Studio SSH load logic
            pass

    def _unload_model(self, model_name: str):
        logger.info(f"Unloading model: {model_name}")
        # Similar to _load_model but for unload

    def _start_tool(self, tool_name: str):
        logger.info(f"Starting tool: {tool_name}")
        # subprocess.Popen(...) logic

    def _stop_tool(self, tool_name: str):
        logger.info(f"Stopping tool: {tool_name}")
        if os.name == 'nt':
            # Windows: use taskkill
            subprocess.run(["taskkill", "/IM", f"{tool_name}*", "/F"],
                           capture_output=True, timeout=10)
        else:
            subprocess.run(["pkill", "-f", tool_name],
                           capture_output=True, timeout=10)

    def _emergency_purge(self):
        logger.warning("EMERGENCY PURGE TRIGGERED")
        # Phase 1: Stop monitoring batch
        for name, meta in self.container_footprints.items():
            if meta.get("batch") == "monitoring":
                self._stop_container(name)
        
        # Phase 2: Unload models
        current_models = self._get_loaded_models()
        for model in current_models:
            self._unload_model(model)

        # Phase 3: Stop on-demand brain
        for name, meta in self.container_footprints.items():
            if not meta.get("essential") and not meta.get("batch"):
                self._stop_container(name)

        return {"status": "purged"}

    def _ssh_check_ram(self) -> Dict[str, Any]:
        # Mock SSH logic
        return {"free_mb": 20000, "total_mb": 40960, "percent": 50}

    def _get_running_containers(self) -> List[str]:
        result = subprocess.run(["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True)
        return result.stdout.splitlines()

    def _get_loaded_models(self) -> List[str]:
        loaded = []
        try:
            import requests
            url = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
            resp = requests.get(f"{url}/models", timeout=2)
            if resp.status_code == 200:
                data = resp.json()
                for m in data.get("data", []):
                    loaded.append(m.get("id"))
        except Exception:
            pass

        try:
            import requests
            resp = requests.get("http://localhost:11434/api/ps", timeout=1)
            if resp.status_code == 200:
                for m in resp.json().get("models", []):
                    loaded.append(m.get("name"))
        except Exception:
            pass

        try:
            import psutil
            for proc in psutil.process_iter(['name', 'cmdline']):
                try:
                    name = proc.info['name'] or ""
                    cmdline = proc.info['cmdline'] or []
                    cmd_str = " ".join(cmdline).lower()
                    if "llama" in cmd_str or "ollama" in cmd_str or "bitnet" in cmd_str:
                        for word in cmdline:
                            if ".gguf" in word or "model" in word:
                                loaded.append(os.path.basename(word))
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        except Exception:
            pass

        return list(set(loaded))

    def _get_active_tools(self) -> List[str]:
        active = []
        try:
            import psutil
            for proc in psutil.process_iter(['name', 'cmdline']):
                try:
                    name = proc.info['name'] or ""
                    cmdline = proc.info['cmdline'] or []
                    cmd_str = " ".join(cmdline).lower()
                    for tool in ["aider", "goose", "opencode", "levelcode", "git", "docker", "obsidian", "whisper"]:
                        if tool in name.lower() or tool in cmd_str:
                            active.append(tool)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        except Exception:
            pass
        return list(set(active))

    def _verify_state(self) -> Dict[str, List[str]]:
        return {
            "containers": self._get_running_containers(),
            "models": self._get_loaded_models(),
            "tools": self._get_active_tools()
        }

# Alias for compatibility with compliance checks and testing
H5RAMGovernorAgent = H5RamGovernorAgent

