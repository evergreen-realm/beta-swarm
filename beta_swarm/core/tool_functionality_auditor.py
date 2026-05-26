import os
import shutil
import json
import subprocess
import re
from datetime import datetime
from typing import Dict, List, Any

class ToolFunctionalityAuditor:
    def __init__(self, project_path: str = "C:/Users/Admin/Documents/Beta Swarnv2"):
        self.project_path = os.path.abspath(project_path)
        self.results_path = os.path.join(self.project_path, "tool_audit_results.json")
        self.vault_dir = os.path.join(self.project_path, "obsidian-vault")
        self.agents_dir = os.path.join(self.project_path, "beta_swarm/agents")
        self.orchestrator_path = os.path.join(self.project_path, "beta_swarm/orchestrator.py")

    def _search_files(self, directory: str, file_pattern: str, keyword: str) -> List[str]:
        matches = []
        if not os.path.exists(directory):
            return matches
        regex = re.compile(file_pattern)
        for root, _, files in os.walk(directory):
            for f in files:
                if regex.match(f):
                    path = os.path.join(root, f)
                    try:
                        with open(path, "r", encoding="utf-8", errors="ignore") as file:
                            if keyword.lower() in file.read().lower():
                                matches.append(f)
                    except Exception:
                        pass
        return sorted(list(set(matches)))

    def _check_orchestrator(self, keyword: str) -> bool:
        if os.path.exists(self.orchestrator_path):
            try:
                with open(self.orchestrator_path, "r", encoding="utf-8", errors="ignore") as f:
                    return keyword.lower() in f.read().lower()
            except Exception:
                pass
        return False

    def test_bitnet(self) -> Dict[str, Any]:
        binary = shutil.which("bitnet") or shutil.which("bitnet-cli") or "not found"
        if binary == "not found":
            for loc in [os.path.join(self.project_path, "bitnet"), "C:/BitNet", "C:/Program Files/BitNet"]:
                for ext in ["bitnet.exe", "bitnet-cli.exe"]:
                    path = os.path.join(loc, ext)
                    if os.path.exists(path):
                        binary = path
                        break
        
        models = []
        bitnet_dir = os.path.join(self.project_path, "bitnet")
        if os.path.exists(bitnet_dir):
            for root, _, files in os.walk(bitnet_dir):
                for f in files:
                    if f.endswith(".bin") or f.endswith(".gguf"):
                        models.append(os.path.join(root, f))

        help_works = False
        if binary != "not found":
            try:
                res = subprocess.run([binary, "--help"], capture_output=True, timeout=15, text=True)
                help_works = (res.returncode == 0)
            except Exception:
                pass

        inference_works = False
        if binary != "not found" and models:
            try:
                res = subprocess.run(
                    f'echo Hello | "{binary}" -m "{models[0]}" -p "Say hello"',
                    shell=True, capture_output=True, timeout=15, text=True
                )
                inference_works = (res.returncode == 0)
            except Exception:
                pass

        called = self._search_files(os.path.join(self.agents_dir, "stage"), r"s(1|4|8)_.*\.py", "bitnet")
        installed = (binary != "not found")
        
        status = "not_installed"
        if installed:
            status = "fully_functional" if (help_works and (inference_works or not models)) else "installed_not_used"
        if not installed and called:
            status = "broken_pipeline"
        elif installed and not called:
            status = "installed_not_used"

        return {
            "installed": installed, "binary_found": binary, "models_found": models,
            "help_works": help_works, "inference_works": inference_works,
            "called_by_agents": called, "status": status
        }

    def test_levelcode(self) -> Dict[str, Any]:
        cli_installed = False
        version = "unknown"
        binary = shutil.which("levelcode")
        if binary:
            try:
                res = subprocess.run([binary, "--version"], capture_output=True, timeout=15, text=True)
                if res.returncode == 0:
                    cli_installed = True
                    version = res.stdout.strip() or res.stderr.strip()
            except Exception:
                pass

        adapter = os.path.join(self.project_path, "beta_swarm/adapters/levelcode.py")
        manager = os.path.join(self.project_path, "beta_swarm/orchestration/levelcode_manager.py")
        
        edit_works = False
        if cli_installed and binary:
            test_file = os.path.join(self.project_path, "test_levelcode_temp.py")
            try:
                with open(test_file, "w") as f:
                    f.write("# dummy file\n")
                res = subprocess.run([binary, "--file", test_file, "--prompt", "Add a comment"], capture_output=True, timeout=15)
                edit_works = (res.returncode == 0)
            except Exception:
                pass
            finally:
                if os.path.exists(test_file):
                    try: os.remove(test_file)
                    except Exception: pass

        called = self._search_files(os.path.join(self.agents_dir, "stage"), r"s5.*\.py", "levelcode")
        if self._check_orchestrator("levelcode"):
            called.append("orchestrator.py")

        status = "not_installed"
        if cli_installed:
            status = "fully_functional" if edit_works else "installed_not_wired"
        if not cli_installed and called:
            status = "broken_pipeline"

        return {
            "cli_installed": cli_installed, "version": version,
            "adapter_exists": os.path.exists(adapter), "manager_exists": os.path.exists(manager),
            "edit_test_works": edit_works, "called_by_agents": called, "status": status
        }

    def test_opencode(self) -> Dict[str, Any]:
        cli_installed = False
        version = "unknown"
        binary = shutil.which("opencode") or shutil.which("opencode-ai")
        if binary:
            try:
                res = subprocess.run([binary, "--version"], capture_output=True, timeout=15, text=True)
                if res.returncode == 0:
                    cli_installed = True
                    version = res.stdout.strip() or res.stderr.strip()
            except Exception:
                pass

        adapter = os.path.join(self.project_path, "beta_swarm/adapters/opencode.py")
        
        suggest_works = False
        if cli_installed and binary:
            try:
                res = subprocess.run([binary, "suggest"], input="print('test')", capture_output=True, timeout=15, text=True)
                suggest_works = (res.returncode == 0)
            except Exception:
                pass

        called = self._search_files(self.agents_dir, r".*\.py", "opencode")
        if self._check_orchestrator("opencode"):
            called.append("orchestrator.py")

        status = "not_installed"
        if cli_installed:
            status = "fully_functional" if suggest_works else "installed_not_wired"
        if not cli_installed and called:
            status = "broken_pipeline"

        return {
            "cli_installed": cli_installed, "version": version,
            "adapter_exists": os.path.exists(adapter), "suggest_works": suggest_works,
            "called_by_agents": called, "status": status
        }

    def test_aider(self) -> Dict[str, Any]:
        installed = False
        version = "unknown"
        binary = shutil.which("aider")
        if binary:
            try:
                res = subprocess.run([binary, "--version"], capture_output=True, timeout=15, text=True)
                if res.returncode == 0:
                    installed = True
                    version = res.stdout.strip() or res.stderr.strip()
            except Exception:
                pass

        adapter = os.path.join(self.project_path, "beta_swarm/adapters/aider.py")
        manager = os.path.join(self.project_path, "beta_swarm/orchestration/aider_manager.py")
        
        git_version = "not available"
        try:
            res = subprocess.run(["git", "--version"], capture_output=True, timeout=5, text=True)
            if res.returncode == 0:
                git_version = res.stdout.strip()
        except Exception:
            pass

        dry_run_works = False
        if installed and binary and git_version != "not available":
            temp_dir = os.path.join(self.project_path, "test_aider_temp")
            try:
                os.makedirs(temp_dir, exist_ok=True)
                subprocess.run(["git", "init"], cwd=temp_dir, capture_output=True, timeout=5)
                with open(os.path.join(temp_dir, "test.py"), "w") as f:
                    f.write("print('test')\n")
                res = subprocess.run([binary, "--dry-run", "test.py"], cwd=temp_dir, capture_output=True, timeout=15)
                dry_run_works = (res.returncode == 0)
            except Exception:
                pass
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

        called = self._search_files(os.path.join(self.agents_dir, "stage"), r"s(5|6|7).*\.py", "aider")
        if self._check_orchestrator("aider"):
            called.append("orchestrator.py")

        status = "not_installed"
        if installed:
            status = "fully_functional" if dry_run_works else "installed_not_wired"
        if not installed and called:
            status = "broken_pipeline"

        return {
            "installed": installed, "version": version,
            "adapter_exists": os.path.exists(adapter), "manager_exists": os.path.exists(manager),
            "git_available": (git_version != "not available"), "dry_run_works": dry_run_works,
            "called_by_agents": called, "status": status
        }

    def test_goose(self) -> Dict[str, Any]:
        installed = False
        version = "unknown"
        binary = shutil.which("goose")
        if binary:
            try:
                res = subprocess.run([binary, "--version"], capture_output=True, timeout=15, text=True)
                if res.returncode == 0:
                    installed = True
                    version = res.stdout.strip() or res.stderr.strip()
            except Exception:
                pass

        adapter = os.path.join(self.project_path, "beta_swarm/adapters/goose.py")
        manager = os.path.join(self.project_path, "beta_swarm/orchestration/goose_manager.py")
        
        help_works = False
        if installed and binary:
            try:
                res = subprocess.run([binary, "--help"], capture_output=True, timeout=15)
                help_works = (res.returncode == 0)
            except Exception:
                pass

        called = self._search_files(self.agents_dir, r".*\.py", "goose")
        if self._check_orchestrator("goose"):
            called.append("orchestrator.py")

        status = "not_installed"
        if installed:
            status = "fully_functional" if help_works else "installed_not_wired"
        if not installed and called:
            status = "broken_pipeline"

        return {
            "installed": installed, "version": version,
            "adapter_exists": os.path.exists(adapter), "manager_exists": os.path.exists(manager),
            "help_works": help_works, "called_by_agents": called, "status": status
        }


    def test_all(self) -> Dict[str, Any]:
        results = {
            "bitnet": self.test_bitnet(),
            "levelcode": self.test_levelcode(),
            "opencode": self.test_opencode(),
            "aider": self.test_aider(),
            "goose": self.test_goose()
        }
        
        strategy = "None"
        strategy_detected = False
        if os.path.exists(self.orchestrator_path):
            try:
                with open(self.orchestrator_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().lower()
                    if "select_tool" in content or "choose_tool" in content or ("aider" in content and "opencode" in content):
                        strategy_detected = True
                        strategy = "Tool selection based on task type (Aider, OpenCode, LevelCode)"
            except Exception:
                pass
                
        results["orchestrator_integration"] = {
            "strategy_detected": strategy_detected,
            "strategy_details": strategy
        }
        
        try:
            with open(self.results_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
        except Exception:
            pass
            
        self.generate_functional_report(results)
        return results

    def generate_functional_report(self, results: Dict[str, Any]) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        
        report = f"# Tool Functionality Audit Report - {today}\n\n"
        
        for name, data in results.items():
            if name == "orchestrator_integration":
                continue
                
            status_str = str(data.get("status", "unknown")).upper().replace("_", " ")
            report += f"## {name.title()}\n"
            report += f"- **Status**: {status_str}\n"
            
            if name == "bitnet":
                report += f"- **Binary**: {data.get('binary_found')}\n"
                report += f"- **Models**: {len(data.get('models_found', []))} found\n"
                report += f"- **Inference Test**: {'PASS' if data.get('inference_works') else 'FAIL'}\n"
            else:
                report += f"- **CLI Installed**: {data.get('cli_installed') or data.get('installed')}\n"
                report += f"- **Version**: {data.get('version')}\n"
                
            report += f"- **Wired to Agents**: {', '.join(data.get('called_by_agents', [])) or 'None'}\n"
            report += f"- **Verdict**: Tool status evaluated as {status_str}.\n\n"
            
        integ = results.get("orchestrator_integration", {})
        report += "## Orchestration Integration\n"
        report += f"- **Tool Selection Strategy**: {'Yes' if integ.get('strategy_detected') else 'No'}\n"
        report += f"- **Strategy Details**: {integ.get('strategy_details')}\n\n"
        report += "*Generated by ToolFunctionalityAuditor*\n"
        
        try:
            report_dir = os.path.join(self.vault_dir, "Tool-Audit-Reports")
            os.makedirs(report_dir, exist_ok=True)
            with open(os.path.join(report_dir, f"{today}.md"), "w", encoding="utf-8") as f:
                f.write(report)
        except Exception:
            pass
            
        return report
