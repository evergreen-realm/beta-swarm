import logging
from typing import Dict, Any, List

from beta_swarm.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class X4ReviewBoardAgent(BaseAgent):
    """
    X4: Review Board Agent
    Review: Multi-Agent Consensus
    Aggregates individual review results from X1/X2/X3 (and optionally Sentry),
    runs a consensus vote, and falls back to adversarial debate when there
    is no majority agreement.
    """

    def __init__(self, brain=None):
        super().__init__("x4_board", "Review Board", "review", brain)

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        # Extract individual reviews from either 'individual_reviews' list or flattened context keys
        reviews = []
        individual_reviews = task.get("individual_reviews")
        if individual_reviews and isinstance(individual_reviews, list):
            reviews = [r.get("output", r) if isinstance(r, dict) else r for r in individual_reviews]
        else:
            for stage in ["x1_code_review", "x2_security_review", "x3_performance_review"]:
                res = task.get(stage)
                if res:
                    # Some stages might return result in 'output' or root
                    review_data = res.get("output", res) if isinstance(res, dict) else res
                    if review_data:
                        reviews.append(review_data)

        if not reviews:
            logger.warning("[X4] No individual reviews provided — auto-failing.")
            return {
                "status": "complete",
                "verdict": {
                    "consensus": False,
                    "decision": "FAIL",
                    "reason": "No reviews to evaluate",
                    "votes": "0/0",
                },
            }

        # Phase 1: Consensus vote
        verdict = self._consensus_vote(reviews)

        # Phase 2: Adversarial debate only if no consensus
        if not verdict["consensus"]:
            verdict = self._adversarial_debate(reviews, verdict)

        logger.info(
            f"[X4] Board verdict: {verdict['decision']}  "
            f"(votes={verdict.get('votes', '?')})"
        )

        if self.brain:
            self.brain.store_fact(
                self.agent_id,
                f"Board verdict: {verdict['decision']}",
                "consensus",
            )

        return {"status": "complete", "verdict": verdict}

    # ------------------------------------------------------------------
    # Phase 1 — Consensus Vote
    # ------------------------------------------------------------------

    def _consensus_vote(self, reviews: List[Dict]) -> Dict:
        """
        Each review dict may carry a ``passed`` boolean.
        - Unanimous PASS  → PASS
        - Majority PASS   → PASS_WITH_NOTES
        - Minority PASS   → no consensus → triggers debate
        """
        passes = sum(1 for r in reviews if r.get("passed", False))
        total = len(reviews)
        votes_str = f"{passes}/{total}"

        # Collect all issues across reviews
        all_issues = self._collect_all_issues(reviews)
        critical = [i for i in all_issues if i.get("severity") == "critical"]
        errors = [i for i in all_issues if i.get("severity") == "error"]
        warnings = [i for i in all_issues if i.get("severity") == "warning"]

        summary = {
            "critical_count": len(critical),
            "error_count": len(errors),
            "warning_count": len(warnings),
            "total_issues": len(all_issues),
        }

        if passes == total:
            return {
                "consensus": True,
                "decision": "PASS",
                "votes": votes_str,
                "summary": summary,
            }
        elif passes > total / 2:
            return {
                "consensus": True,
                "decision": "PASS_WITH_NOTES",
                "votes": votes_str,
                "summary": summary,
                "notes": [i["message"] for i in errors + critical],
            }
        else:
            return {
                "consensus": False,
                "decision": "PENDING",
                "votes": votes_str,
                "summary": summary,
            }

    # ------------------------------------------------------------------
    # Phase 2 — Adversarial Debate
    # ------------------------------------------------------------------

    def _adversarial_debate(self, reviews: List[Dict], initial: Dict) -> Dict:
        """
        When consensus is not reached, inspect the combined issue pool
        more carefully:
        - If there are zero critical issues → PASS_AFTER_DEBATE
        - If there are critical issues → FAIL with reasoning
        """
        all_issues = self._collect_all_issues(reviews)
        critical = [i for i in all_issues if i.get("severity") == "critical"]
        errors = [i for i in all_issues if i.get("severity") == "error"]

        votes_str = initial.get("votes", "?")

        if len(critical) == 0 and len(errors) == 0:
            return {
                "consensus": True,
                "decision": "PASS_AFTER_DEBATE",
                "votes": votes_str,
                "reason": "No critical or error-level issues found after adversarial review",
                "summary": initial.get("summary", {}),
            }
        elif len(critical) == 0:
            # Errors exist but no criticals — conditional pass
            return {
                "consensus": True,
                "decision": "PASS_WITH_NOTES",
                "votes": votes_str,
                "reason": f"{len(errors)} error(s) remain but no criticals — conditional pass",
                "notes": [i.get("message", "") for i in errors[:10]],
                "summary": initial.get("summary", {}),
            }
        else:
            return {
                "consensus": True,
                "decision": "FAIL",
                "votes": votes_str,
                "reason": f"{len(critical)} critical issue(s) remain unresolved",
                "critical_issues": [i.get("message", "") for i in critical[:10]],
                "summary": initial.get("summary", {}),
            }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _collect_all_issues(reviews: List[Dict]) -> List[Dict]:
        """
        Reviews may store issues in 'issues' (X1) or 'findings' (X2/X3)
        or nested under 'gates' (Sentry). Merge them all.
        """
        all_issues: List[Dict] = []
        for r in reviews:
            all_issues.extend(r.get("issues", []))
            all_issues.extend(r.get("findings", []))
            # Sentry gate-level issues
            gates = r.get("gates", {})
            if isinstance(gates, dict):
                for gate in gates.values():
                    if isinstance(gate, dict):
                        all_issues.extend(gate.get("issues", []))
            elif isinstance(gates, list):
                for gate in gates:
                    if isinstance(gate, dict):
                        all_issues.extend(gate.get("issues", []))
        return all_issues
