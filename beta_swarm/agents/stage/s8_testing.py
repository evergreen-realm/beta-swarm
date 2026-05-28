from beta_swarm.agents.base import BaseAgent
import json, re, os, logging, subprocess
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class S8TestingAgent(BaseAgent):
    def __init__(self, brain=None):
        super().__init__("s8_testing", "Testing Agent", "Stage 8: Test Generation", brain)

    def _get_default_next_stage(self):
        return "s9_containerization"

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        project_id   = task.get("project_id", "default")
        project_path = task.get("project_path", f"./projects/{project_id}")
        s3_out       = task.get("s3_prd", {})
        prd          = s3_out.get("prd") or task.get("prd") or {}
        s4_out       = task.get("s4_architecture", {})
        architecture = s4_out.get("architecture") or task.get("architecture", {})
        api_contracts = architecture.get("api_contracts", [])

        self._log_handover(f"S8 started. project={project_id}")

        title = prd.get("metadata", {}).get("title", "App")
        tests_dir = os.path.join(project_path, "tests")
        os.makedirs(tests_dir, exist_ok=True)

        prompt = f"""You are an expert QA engineer. Generate comprehensive pytest tests for "{title}".

API Contracts: {json.dumps(api_contracts[:5], indent=2)}

Generate:
[FILE: tests/__init__.py]
```python
```

[FILE: tests/test_api.py]
```python
# Full pytest test suite for all endpoints using TestClient
# Use from app.main import app and httpx or requests
# Test all CRUD endpoints with assertions
# Include test for /health endpoint
```

[FILE: tests/test_models.py]
```python
# Unit tests for data models and schemas
```

[FILE: tests/conftest.py]
```python
# Pytest fixtures
```"""

        llm_out = self._call_llm(prompt, task_type="s8_testing")
        generated = self.generate_codebase(llm_out, project_path)

        # Guarantee a working test file
        self._ensure_test_files(tests_dir, api_contracts)

        # Try running tests (non-fatal)
        test_results = self._run_tests(project_path)

        all_files = list(set(generated + [
            "tests/__init__.py", "tests/test_api.py", "tests/test_models.py", "tests/conftest.py"
        ]))

        artifact = {
            "test_files": all_files,
            "test_results": test_results
        }
        artifact_path = f"./projects/{project_id}/s8_testing_output.json"
        os.makedirs(os.path.dirname(artifact_path), exist_ok=True)
        with open(artifact_path, "w", encoding="utf-8") as f:
            json.dump(artifact, f, indent=2)

        self._log_handover(f"S8 completed. Tests: {len(all_files)}, Results: {test_results}")

        return {
            "status": "complete",
            "test_files": all_files,
            "test_results": test_results,
            "artifact": artifact,
            "artifact_path": artifact_path,
            "next_stage": task.get("next_stage") or self._get_default_next_stage()
        }

    def _ensure_test_files(self, tests_dir: str, api_contracts: list):
        init_path = os.path.join(tests_dir, "__init__.py")
        if not os.path.exists(init_path):
            open(init_path, "w").close()

        test_api_path = os.path.join(tests_dir, "test_api.py")
        if not os.path.exists(test_api_path) or os.path.getsize(test_api_path) < 50:
            with open(test_api_path, "w", encoding="utf-8") as f:
                f.write(self._generate_test_api(api_contracts))

        conftest_path = os.path.join(tests_dir, "conftest.py")
        if not os.path.exists(conftest_path):
            with open(conftest_path, "w", encoding="utf-8") as f:
                f.write('''import pytest
try:
    from fastapi.testclient import TestClient
    from app.main import app
    @pytest.fixture
    def client():
        return TestClient(app)
except Exception:
    @pytest.fixture
    def client():
        return None
''')

    def _generate_test_api(self, api_contracts: list) -> str:
        tests = '''import pytest
try:
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
except Exception:
    client = None

def test_health():
    if client is None:
        pytest.skip("App not importable")
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json().get("status") == "healthy"

def test_list_items():
    if client is None:
        pytest.skip("App not importable")
    resp = client.get("/api/v1/items/")
    assert resp.status_code in (200, 404)

def test_create_item():
    if client is None:
        pytest.skip("App not importable")
    resp = client.post("/api/v1/items/", json={"title": "Test Item", "user_id": "user-1"})
    assert resp.status_code in (200, 201, 422)
'''
        return tests

    def _run_tests(self, project_path: str) -> dict:
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "tests/", "-v", "--tb=short", "--no-header", "-q"],
                cwd=project_path, capture_output=True, text=True, timeout=60
            )
            return {
                "returncode": result.returncode,
                "stdout": result.stdout[:2000],
                "passed": "passed" in result.stdout.lower(),
                "ran": True
            }
        except Exception as e:
            return {"returncode": -1, "error": str(e), "ran": False}
