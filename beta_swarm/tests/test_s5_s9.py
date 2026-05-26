"""
Beta Swarm — S5-S9 Pipeline Integration Tests
Run standalone : python beta_swarm/tests/test_s5_s9.py
Run via pytest  : python -m pytest beta_swarm/tests/test_s5_s9.py -v

Improvements over the original reference:
  - sys.path points at the real project root (two levels up from tests/)
  - S6 key assertion corrected to 'api_client_code'
  - React scaffold checks src/App.js (not bare App.js)
  - Content-level checks so hollow files don't silently pass
  - Informative FAIL output: exception type + message printed per test
  - Full pipeline chain test as the final integration smoke-test
  - Checkpoint dir cleaned before each run
"""
import sys
import os
import shutil
import tempfile
import traceback
from dotenv import load_dotenv

# Two levels up from tests/ → project root (Beta_Swarnv2/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# Load .env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from beta_swarm.agents.stage.s5_backend import S5BackendAgent
from beta_swarm.agents.stage.s6_api import S6APIAgent
from beta_swarm.agents.stage.s7_frontend import S7FrontendAgent
from beta_swarm.agents.stage.s8_testing import S8TestingAgent
from beta_swarm.agents.stage.s9_deployment import S9DeploymentAgent

# ---------------------------------------------------------------------------
# Shared test context
# ---------------------------------------------------------------------------

MINIMAL_PRD = {
    "metadata": {"title": "Test App"},
    "functional_requirements": ["Track items"],
    "user_stories": ["As a user I can create an item"],
    "tech_stack_recommendation": {"backend": "FastAPI", "frontend": "html"},
}

MINIMAL_ARCH = {
    "components": [{"name": "Core API", "tech": "FastAPI"}],
    "data_flow": ["User -> API -> DB"],
    "database_schema": "items(id, title, user_id)",
    "api_contracts": "GET /api/v1/items, POST /api/v1/items",
    "title": "Test App",
}

CHECKPOINT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "checkpoints")


def _clean_checkpoints():
    shutil.rmtree(CHECKPOINT_DIR, ignore_errors=True)


# ---------------------------------------------------------------------------
# Individual stage tests
# ---------------------------------------------------------------------------

def test_s5_backend():
    _clean_checkpoints()
    with tempfile.TemporaryDirectory() as tmpdir:
        s5 = S5BackendAgent()
        result = s5.run({
            "project_path": tmpdir,
            "architecture": MINIMAL_ARCH,
            "prd": MINIMAL_PRD,
        })
        assert result["status"] == "complete", f"Expected 'complete', got {result['status']}"
        assert result["next_stage"] == "s6_api"

        # File existence
        for rel in ["app/main.py", "app/models.py", "app/routers.py",
                    "app/__init__.py", "Dockerfile", "requirements.txt"]:
            assert os.path.exists(os.path.join(tmpdir, rel)), f"Missing: {rel}"

        # Content checks
        main = open(os.path.join(tmpdir, "app/main.py")).read()
        assert "FastAPI" in main, "main.py missing FastAPI import"
        assert "health_check" in main, "main.py missing /health endpoint"

        routers = open(os.path.join(tmpdir, "app/routers.py")).read()
        assert "APIRouter" in routers
        assert "/api/v1/items" in routers

        reqs = open(os.path.join(tmpdir, "requirements.txt")).read()
        assert "fastapi" in reqs
        assert "uvicorn" in reqs

        print("S5 PASS: Backend files generated")


def test_s6_api():
    _clean_checkpoints()
    with tempfile.TemporaryDirectory() as tmpdir:
        s6 = S6APIAgent()
        result = s6.run({
            "backend_url": "http://localhost:8000",  # likely offline; graceful skip
            "architecture": MINIMAL_ARCH,
            "project_path": tmpdir,
        })
        assert result["status"] == "complete"
        assert result["next_stage"] == "s7_frontend"

        # Key name check (api_client_code, not client_code)
        assert "api_client_code" in result, \
            f"Missing 'api_client_code' in result. Keys: {list(result.keys())}"
        assert isinstance(result["tests"], list), "Expected 'tests' to be a list"
        assert len(result["tests"]) == 3, f"Expected 3 test entries, got {len(result['tests'])}"

        # JS client written to disk
        client_path = os.path.join(tmpdir, "frontend", "APIClient.js")
        assert os.path.exists(client_path), "APIClient.js not written to disk"
        client_code = open(client_path).read()
        assert "class APIClient" in client_code
        assert "listItems" in client_code
        assert "createItem" in client_code

        print("S6 PASS: API client generated")


def test_s7_frontend_html():
    """Verify plain-HTML fallback when frontend != react/next."""
    _clean_checkpoints()
    with tempfile.TemporaryDirectory() as tmpdir:
        prd = {**MINIMAL_PRD, "tech_stack_recommendation": {"frontend": "html"}}
        s7 = S7FrontendAgent()
        result = s7.run({
            "project_path": tmpdir,
            "prd": prd,
            "architecture": MINIMAL_ARCH,
        })
        assert result["status"] == "complete"
        assert result["next_stage"] == "s8_testing"

        index = os.path.join(tmpdir, "frontend", "index.html")
        assert os.path.exists(index), "index.html not generated"
        content = open(index).read()
        assert "Test App" in content
        assert "fetch" in content, "index.html missing fetch() calls"

        print("S7 PASS (HTML): Frontend generated")


def test_s7_frontend_react():
    """Verify React CRA scaffold when frontend == react."""
    _clean_checkpoints()
    with tempfile.TemporaryDirectory() as tmpdir:
        prd = {**MINIMAL_PRD, "tech_stack_recommendation": {"frontend": "react"}}
        s7 = S7FrontendAgent()
        result = s7.run({
            "project_path": tmpdir,
            "prd": prd,
            "architecture": MINIMAL_ARCH,
        })
        assert result["status"] == "complete"

        # React scaffold lives under frontend/src/App.js (not bare App.js)
        expected_files = [
            os.path.join("frontend", "package.json"),
            os.path.join("frontend", "public", "index.html"),
            os.path.join("frontend", "src", "App.js"),   # <-- corrected path
            os.path.join("frontend", "src", "App.css"),
        ]
        for rel in expected_files:
            assert os.path.exists(os.path.join(tmpdir, rel)), f"Missing React file: {rel}"

        pkg = open(os.path.join(tmpdir, "frontend", "package.json")).read()
        assert "react" in pkg

        app_js = open(os.path.join(tmpdir, "frontend", "src", "App.js")).read()
        assert "Test App" in app_js
        assert "apiFetch" in app_js

        print("S7 PASS (React): Frontend generated")


def test_s8_testing():
    _clean_checkpoints()
    with tempfile.TemporaryDirectory() as tmpdir:
        s8 = S8TestingAgent()
        result = s8.run({"project_path": tmpdir})
        assert result["status"] == "complete"
        assert result["next_stage"] == "s9_deployment"

        # Files exist
        assert os.path.exists(os.path.join(tmpdir, "tests", "test_api.py")), \
            "test_api.py not generated"
        assert os.path.exists(os.path.join(tmpdir, "tests", "conftest.py")), \
            "conftest.py not generated"

        # Content checks
        code = open(os.path.join(tmpdir, "tests", "test_api.py")).read()
        assert "def test_health_check" in code
        assert "def test_create_item" in code
        assert "def test_full_crud_cycle" in code

        conftest = open(os.path.join(tmpdir, "tests", "conftest.py")).read()
        assert "TestClient" in conftest

        print("S8 PASS: Tests generated")


def test_s9_deployment():
    _clean_checkpoints()
    with tempfile.TemporaryDirectory() as tmpdir:
        # Mock KuzuBrain to avoid test hangs on DB locks if server is running
        import unittest.mock
        with unittest.mock.patch("beta_swarm.agents.stage.s9_deployment.KuzuBrain") as MockBrain:
            mock_db = unittest.mock.MagicMock()
            MockBrain.get_instance.return_value = mock_db
            
            s9 = S9DeploymentAgent()
            result = s9.run({
                "project_path": tmpdir,
                "prd": MINIMAL_PRD,
            })
            assert result["status"] == "complete"
            assert result["next_stage"] == "s10_monitoring"

        # Files exist
        assert os.path.exists(os.path.join(tmpdir, "docker-compose.yml"))
        assert os.path.exists(os.path.join(tmpdir, "deploy.sh"))
        assert os.path.exists(os.path.join(tmpdir, ".github", "workflows", "ci.yml"))
        assert os.path.exists(os.path.join(tmpdir, ".env.example"))

        # Content spot-checks
        compose = open(os.path.join(tmpdir, "docker-compose.yml")).read()
        assert "services:" in compose
        assert "healthcheck" in compose
        assert "postgres" in compose

        deploy = open(os.path.join(tmpdir, "deploy.sh")).read()
        assert "docker-compose up" in deploy
        assert "set -euo pipefail" in deploy

        ci = open(os.path.join(tmpdir, ".github", "workflows", "ci.yml")).read()
        assert "pytest" in ci
        assert "docker/build-push-action" in ci

        print("S9 PASS: Deployment artifacts generated")


# ---------------------------------------------------------------------------
# Full pipeline chain S5 -> S6 -> S7 -> S8 -> S9
# ---------------------------------------------------------------------------

def test_full_pipeline():
    """Run all five stages sequentially, piping outputs as inputs."""
    _clean_checkpoints()
    with tempfile.TemporaryDirectory() as tmpdir:
        base = {
            "prd": MINIMAL_PRD,
            "architecture": MINIMAL_ARCH,
            "project_path": tmpdir,
        }

        r5 = S5BackendAgent().run(base)
        assert r5["status"] == "complete"
        print(f"  S5 OK  generated={r5['backend_info']['generated_files']}")

        r6 = S6APIAgent().run({**base, "backend_url": "http://localhost:8000"})
        assert r6["status"] == "complete"
        print(f"  S6 OK  tests={len(r6['tests'])}, client written")

        r7 = S7FrontendAgent().run({**base, "api_client_code": r6["api_client_code"]})
        assert r7["status"] == "complete"
        print(f"  S7 OK  files={r7['files']}")

        r8 = S8TestingAgent().run({"project_path": tmpdir})
        assert r8["status"] == "complete"
        print(f"  S8 OK  rc={r8['test_results'].get('returncode', 'N/A')}")

        import unittest.mock
        with unittest.mock.patch("beta_swarm.agents.stage.s9_deployment.KuzuBrain") as MockBrain:
            mock_db = unittest.mock.MagicMock()
            MockBrain.get_instance.return_value = mock_db
            
            r9 = S9DeploymentAgent().run(base)
            assert r9["status"] == "complete"
            print(f"  S9 OK  files={r9['generated_files']}")

        print("\nS5-S9 Pipeline: ALL PASS")


# ---------------------------------------------------------------------------
# Runner (standalone execution)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_s5_backend,
        test_s6_api,
        test_s7_frontend_html,
        test_s7_frontend_react,
        test_s8_testing,
        test_s9_deployment,
        test_full_pipeline,
    ]

    passed, failed = 0, 0
    for t in tests:
        print(f"\n[TEST] {t.__name__}")
        try:
            t()
            passed += 1
        except Exception as e:
            failed += 1
            # Show the exception type, message, and the exact failing line
            print(f"  FAIL ({type(e).__name__}): {e}")
            # Print the innermost traceback frame for quick diagnosis
            tb = traceback.extract_tb(e.__traceback__)
            if tb:
                last = tb[-1]
                print(f"       -> {os.path.basename(last.filename)}:{last.lineno}  {last.line}")

    sep = "=" * 52
    print(f"\n{sep}")
    print(f"Results: {passed} passed, {failed} failed / {len(tests)} total")
    print(sep)
    if failed:
        sys.exit(1)
