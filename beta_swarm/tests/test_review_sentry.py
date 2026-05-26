"""
Beta Swarm -- Review & Sentry Layer Integration Tests
Run standalone : python beta_swarm/tests/test_review_sentry.py
Run via pytest  : python -m pytest beta_swarm/tests/test_review_sentry.py -v
"""
import sys
import os
import shutil
import tempfile
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from beta_swarm.agents.review.x1_code_review import X1CodeReviewAgent
from beta_swarm.agents.review.x2_security_review import X2SecurityReviewAgent
from beta_swarm.agents.review.x3_performance_review import X3PerformanceReviewAgent
from beta_swarm.agents.review.x4_review_board import X4ReviewBoardAgent
from beta_swarm.agents.sentry.sentry_layer import SentryLayerAgent

CHECKPOINT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "checkpoints")


def _clean():
    shutil.rmtree(CHECKPOINT_DIR, ignore_errors=True)


# ---------------------------------------------------------------------------
# Helpers: write test fixtures to a temp project
# ---------------------------------------------------------------------------

def _make_test_project(tmpdir: str):
    """Create a small project with intentional issues for the scanners."""
    app_dir = os.path.join(tmpdir, "app")
    os.makedirs(app_dir, exist_ok=True)

    # Clean code
    with open(os.path.join(app_dir, "__init__.py"), "w") as f:
        f.write("")

    with open(os.path.join(app_dir, "main.py"), "w") as f:
        f.write("""\
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "ok"}
""")

    # Code with issues
    with open(os.path.join(app_dir, "risky.py"), "w") as f:
        f.write("""\
import os
import requests

# dead code
def _unused_helper():
    pass

def fetch_data():
    # blocking I/O (not async)
    resp = requests.get("http://example.com")
    return resp.json()

def process():
    # bare except
    try:
        x = 1 / 0
    except:
        pass
""")

    # JS with XSS risk
    os.makedirs(os.path.join(tmpdir, "frontend"), exist_ok=True)
    with open(os.path.join(tmpdir, "frontend", "app.js"), "w") as f:
        f.write("""\
document.getElementById('out').innerHTML = userInput;
""")


# ---------------------------------------------------------------------------
# Individual agent tests
# ---------------------------------------------------------------------------

def test_x1_code_review():
    _clean()
    with tempfile.TemporaryDirectory() as tmpdir:
        _make_test_project(tmpdir)
        agent = X1CodeReviewAgent()
        result = agent.run({"project_path": tmpdir})

        assert result["status"] == "complete"
        assert isinstance(result["issues"], list)
        assert isinstance(result["passed"], bool)

        # Should find _unused_helper as dead code
        dead = [i for i in result["issues"] if i["type"] == "dead_code"]
        assert len(dead) > 0, "Expected dead code detection for _unused_helper"
        assert any("_unused_helper" in i["message"] for i in dead)

        print(f"X1 PASS: {len(result['issues'])} issues, passed={result['passed']}")


def test_x2_security_review():
    _clean()
    with tempfile.TemporaryDirectory() as tmpdir:
        _make_test_project(tmpdir)

        # Add a file with a hardcoded secret
        with open(os.path.join(tmpdir, "app", "config.py"), "w") as f:
            f.write("""\
API_KEY = "sk_live_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij"
DATABASE_URL = "postgresql://user:pass@localhost/db"
""")

        agent = X2SecurityReviewAgent()
        result = agent.run({"project_path": tmpdir})

        assert result["status"] == "complete"
        assert isinstance(result["findings"], list)
        assert isinstance(result["passed"], bool)

        # Should detect hardcoded secret
        secrets = [f for f in result["findings"] if f["type"] == "hardcoded_secret"]
        assert len(secrets) > 0, "Expected hardcoded secret detection"

        # Should detect XSS in frontend
        xss = [f for f in result["findings"] if f["type"] == "xss"]
        assert len(xss) > 0, "Expected XSS detection for innerHTML"

        print(f"X2 PASS: {len(result['findings'])} findings, passed={result['passed']}")


def test_x3_performance_review():
    _clean()
    with tempfile.TemporaryDirectory() as tmpdir:
        _make_test_project(tmpdir)
        agent = X3PerformanceReviewAgent()
        result = agent.run({"project_path": tmpdir})

        assert result["status"] == "complete"
        assert isinstance(result["findings"], list)
        assert isinstance(result["passed"], bool)

        print(f"X3 PASS: {len(result['findings'])} findings, passed={result['passed']}")


def test_x4_review_board_pass():
    """All reviews pass -> unanimous PASS."""
    _clean()
    reviews = [
        {"passed": True, "issues": []},
        {"passed": True, "findings": []},
        {"passed": True, "findings": []},
    ]
    agent = X4ReviewBoardAgent()
    result = agent.run({"individual_reviews": reviews})

    assert result["status"] == "complete"
    assert result["verdict"]["decision"] == "PASS"
    assert result["verdict"]["consensus"] is True
    print(f"X4 PASS (unanimous): {result['verdict']}")


def test_x4_review_board_fail():
    """Critical issues -> FAIL after debate."""
    _clean()
    reviews = [
        {"passed": False, "issues": [
            {"severity": "critical", "message": "SQL injection found"}
        ]},
        {"passed": False, "findings": [
            {"severity": "critical", "message": "Hardcoded secret"}
        ]},
        {"passed": True, "findings": []},
    ]
    agent = X4ReviewBoardAgent()
    result = agent.run({"individual_reviews": reviews})

    assert result["status"] == "complete"
    assert result["verdict"]["decision"] == "FAIL"
    print(f"X4 PASS (fail case): {result['verdict']}")


def test_x4_review_board_debate():
    """Minority pass, no criticals -> PASS_AFTER_DEBATE."""
    _clean()
    reviews = [
        {"passed": False, "issues": [
            {"severity": "warning", "message": "Dead code found"}
        ]},
        {"passed": False, "findings": [
            {"severity": "warning", "message": "Missing cache"}
        ]},
        {"passed": True, "findings": []},
    ]
    agent = X4ReviewBoardAgent()
    result = agent.run({"individual_reviews": reviews})

    assert result["status"] == "complete"
    # No criticals, no errors -> should pass after debate
    assert result["verdict"]["decision"] in ("PASS_AFTER_DEBATE", "PASS_WITH_NOTES")
    print(f"X4 PASS (debate): {result['verdict']}")


def test_sentry_clean_code():
    """Clean Python code should pass all three gates."""
    _clean()
    clean_code = """\
def greet(name: str) -> str:
    return f"Hello, {name}!"

if __name__ == "__main__":
    print(greet("world"))
"""
    agent = SentryLayerAgent()
    result = agent.run({"code": clean_code, "file_path": "greet.py"})

    assert result["status"] == "approved"
    assert result["can_merge"] is True
    assert result["gates"]["static"]["passed"] is True
    assert result["gates"]["semantic"]["passed"] is True
    assert result["gates"]["runtime"]["passed"] is True

    print(f"Sentry PASS (clean): status={result['status']}")


def test_sentry_syntax_error():
    """Code with a syntax error should fail the static gate."""
    _clean()
    bad_code = """\
def broken(
    return 42
"""
    agent = SentryLayerAgent()
    result = agent.run({"code": bad_code, "file_path": "broken.py"})

    assert result["status"] == "blocked"
    assert result["can_merge"] is False
    assert result["gates"]["static"]["passed"] is False

    print(f"Sentry PASS (syntax error detected): status={result['status']}")


def test_sentry_dangerous_patterns():
    """Code with eval/exec should get semantic warnings."""
    _clean()
    risky_code = """\
def risky(user_input):
    result = eval(user_input)
    return result
"""
    agent = SentryLayerAgent()
    result = agent.run({"code": risky_code, "file_path": "risky.py"})

    # eval() is a warning, not error, so semantic gate still passes
    semantic = result["gates"]["semantic"]
    assert len(semantic["issues"]) > 0
    assert any("eval" in i["message"] for i in semantic["issues"])

    print(f"Sentry PASS (semantic warnings): {len(semantic['issues'])} issues")


# ---------------------------------------------------------------------------
# Full pipeline: X1 + X2 + X3 -> X4 Review Board
# ---------------------------------------------------------------------------

def test_full_review_pipeline():
    """Run X1, X2, X3 on a test project, then feed results into X4."""
    _clean()
    with tempfile.TemporaryDirectory() as tmpdir:
        _make_test_project(tmpdir)
        task = {"project_path": tmpdir}

        r1 = X1CodeReviewAgent().run(task)
        assert r1["status"] == "complete"
        print(f"  X1 OK: {len(r1['issues'])} issues")

        r2 = X2SecurityReviewAgent().run(task)
        assert r2["status"] == "complete"
        print(f"  X2 OK: {len(r2['findings'])} findings")

        r3 = X3PerformanceReviewAgent().run(task)
        assert r3["status"] == "complete"
        print(f"  X3 OK: {len(r3['findings'])} findings")

        # Feed into X4
        r4 = X4ReviewBoardAgent().run({
            "individual_reviews": [r1, r2, r3],
        })
        assert r4["status"] == "complete"
        verdict = r4["verdict"]
        print(f"  X4 OK: decision={verdict['decision']}, votes={verdict.get('votes', '?')}")

        print("\nFull Review Pipeline: ALL PASS")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_x1_code_review,
        test_x2_security_review,
        test_x3_performance_review,
        test_x4_review_board_pass,
        test_x4_review_board_fail,
        test_x4_review_board_debate,
        test_sentry_clean_code,
        test_sentry_syntax_error,
        test_sentry_dangerous_patterns,
        test_full_review_pipeline,
    ]

    passed, failed = 0, 0
    for t in tests:
        print(f"\n[TEST] {t.__name__}")
        try:
            t()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"  FAIL ({type(e).__name__}): {e}")
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
