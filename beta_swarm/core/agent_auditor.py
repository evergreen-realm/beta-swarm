import os
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

REGISTERED_AGENTS = [
    ("s1_ideation", "Ideation Agent", "Stage 1: Input Processing"),
    ("s2_research", "Research Agent", "Stage 2: Deep Research"),
    ("s3_prd", "PRD Agent", "Stage 3: Product Requirements"),
    ("s4_architecture", "Architecture Agent", "Stage 4: System Design"),
    ("s5_backend", "Backend Agent", "Stage 5: Backend Development"),
    ("s6_api", "API Integration Agent", "Stage 6: API Integration"),
    ("s7_frontend", "Frontend Agent", "Stage 7: Frontend Generation"),
    ("s8_testing", "Testing Agent", "Stage 8: Quality Assurance"),
    ("s9_deployment", "Deployment Agent", "Stage 9: Deployment"),
    ("s10_monitoring", "Monitoring Agent", "Stage 10: Observability"),
    ("s11_docs", "Documentation Agent", "Stage 11: Documentation"),
    ("s12_maintenance", "Maintenance Agent", "Stage 12: Maintenance"),
    ("s13_design", "Design Agent", "Stage 13: Visual Design"),
    ("x1_review", "Code Review Agent", "Review: Structural Analysis"),
    ("x2_security", "Security Review Agent", "Review: Security Audit"),
    ("x3_performance", "Performance Review Agent", "Review: Performance"),
    ("x4_board", "Review Board", "Review: Multi-Agent Consensus"),
    ("b1_local", "LocalBrainAgent", "Brain: KuzuDB Management"),
    ("b2_global", "GlobalBrainAgent", "Brain: Neo4j Management"),
    ("b3_evolver", "EvolverAgent", "Brain: Self-Evolution"),
    ("b4_intel", "CodeIntelAgent", "Brain: Structural Awareness"),
    ("b5_obsidian", "B5ObsidianAgent", "Brain: Human-Readable Memory"),
    ("g1_health", "HealthMonitorAgent", "Growth: System Health"),
    ("g2_domain", "BusinessDomainAgent", "Growth: Domain Logic"),
    ("g3_reflection", "ReflectionAgent", "Growth: Self-Correction"),
    ("g4_cloud", "CloudResearchAgent", "Growth: Cloud Offload"),
    ("sentry", "SentryLayerAgent", "Security: Triple Gate"),
    ("h1_resource", "H1ResourceMonitorAgent", "Health: Passive Metrics"),
    ("h2_model", "H2ModelHealthAgent", "Health: LLM Status"),
    ("h3_service", "H3ServiceHealthAgent", "Health: Service Status"),
    ("h4_reboot", "H4AutoRebootAgent", "Health: Emergency Recovery"),
    ("h5_ram", "H5RamGovernorAgent", "Health: Memory Limiter"),
    ("u1_scrape", "WebScrapingBrainAgent", "Utility: Content Extraction"),
    ("u2_annotate", "AutoAnnotationAgent", "Utility: Entity Extraction"),
    ("u3_git", "GitSyncAgent", "Utility: Version Control"),
    ("u4_docs", "DocumentationAgent", "Utility: Docs Generation")
]

class AgentAuditor:
    def __init__(self, db_path: str = "C:/Users/Admin/Documents/Beta Swarnv2/brain_sqlite.db"):
        self.db_path = db_path
        self.checkpoints_dir = "C:/Users/Admin/Documents/Beta Swarnv2/checkpoints"
        self.vault_dir = "C:/Users/Admin/Documents/Beta Swarnv2/obsidian-vault"

    def get_all_registered_agents(self) -> List[str]:
        try:
            return sorted([a[0] for a in REGISTERED_AGENTS])
        except Exception as e:
            logger.error(f"Error getting registered agents: {e}")
            return []

    def _table_exists(self, table_name: str) -> bool:
        try:
            if not os.path.exists(self.db_path):
                return False
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
                return cur.fetchone() is not None
        except Exception:
            return False

    def get_active_agents(self, since_days: int = 30) -> List[str]:
        try:
            active = set()
            cutoff = datetime.now() - timedelta(days=since_days)
            cutoff_iso = cutoff.isoformat()
            
            # 1. Check artifact_log
            if self._table_exists("artifact_log"):
                with sqlite3.connect(self.db_path) as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT DISTINCT source_agent FROM artifact_log WHERE timestamp >= ?", (cutoff_iso,))
                    for row in cur.fetchall():
                        if row[0]:
                            active.add(row[0])

            # 2. Check prompt_logs (if table exists)
            if self._table_exists("prompt_logs"):
                with sqlite3.connect(self.db_path) as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT DISTINCT agent_id FROM prompt_logs WHERE timestamp >= ?", (cutoff_iso,))
                    for row in cur.fetchall():
                        if row[0]:
                            active.add(row[0])

            # 3. Check checkpoints on disk
            if os.path.exists(self.checkpoints_dir):
                for f in os.listdir(self.checkpoints_dir):
                    if f.endswith("_checkpoint.json"):
                        path = os.path.join(self.checkpoints_dir, f)
                        mtime = datetime.fromtimestamp(os.path.getmtime(path))
                        if mtime >= cutoff:
                            # filename format is typically: {project_id}_{agent_id}_checkpoint.json
                            # Let's extract the agent_id cleanly
                            parts = f.replace("_checkpoint.json", "").split("_")
                            if len(parts) >= 2:
                                agent_id = "_".join(parts[1:])
                                if any(agent_id == a[0] for a in REGISTERED_AGENTS):
                                    active.add(agent_id)
            return sorted(list(active))
        except Exception as e:
            logger.error(f"Error getting active agents: {e}")
            return []

    def get_dormant_agents(self, since_days: int = 30) -> List[Tuple[str, str, str]]:
        try:
            active = self.get_active_agents(since_days)
            dormant = []
            for agent_id, name, role in REGISTERED_AGENTS:
                if agent_id not in active:
                    dormant.append((agent_id, name, role))
            return dormant
        except Exception as e:
            logger.error(f"Error getting dormant agents: {e}")
            return []

    def get_agent_stats(self, agent_id: str) -> Dict[str, Any]:
        stats = {"total_runs": 0, "success_count": 0, "failure_count": 0, "success_rate": 100.0, "last_run": "never", "artifacts_count": 0}
        try:
            # 1. Query artifact_log
            if self._table_exists("artifact_log"):
                with sqlite3.connect(self.db_path) as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT count(*) FROM artifact_log WHERE source_agent = ?", (agent_id,))
                    stats["artifacts_count"] = cur.fetchone()[0]

            # 2. Query prompt_logs
            if self._table_exists("prompt_logs"):
                with sqlite3.connect(self.db_path) as conn:
                    cur = conn.cursor()
                    cur.execute("""
                        SELECT count(*), 
                               sum(case when status='success' then 1 else 0 end),
                               sum(case when status='failed' then 1 else 0 end),
                               max(timestamp)
                        FROM prompt_logs WHERE agent_id = ?
                    """, (agent_id,))
                    row = cur.fetchone()
                    if row and row[0]:
                        stats["total_runs"] = row[0]
                        stats["success_count"] = row[1] or 0
                        stats["failure_count"] = row[2] or 0
                        stats["last_run"] = row[3] or "never"

            # 3. Check checkpoints fallback
            if stats["total_runs"] == 0 and os.path.exists(self.checkpoints_dir):
                for f in os.listdir(self.checkpoints_dir):
                    if f.endswith(f"_{agent_id}_checkpoint.json"):
                        stats["total_runs"] = 1
                        stats["success_count"] = 1
                        mtime = os.path.getmtime(os.path.join(self.checkpoints_dir, f))
                        stats["last_run"] = datetime.fromtimestamp(mtime).isoformat()
                        
            if stats["total_runs"] > 0:
                stats["success_rate"] = round((stats["success_count"] / stats["total_runs"]) * 100, 2)
            return stats
        except Exception as e:
            logger.error(f"Error getting stats for {agent_id}: {e}")
            return stats

    def confirm_tool_usage(self) -> Dict[str, bool]:
        usage = {"bitnet": False, "levelcode": False, "opencode": False, "aider": False, "goose": False}
        try:
            if not self._table_exists("artifact_log"):
                return usage
                
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                for tool, keywords in [
                    ("bitnet", ["%bitnet%"]),
                    ("levelcode", ["%levelcode%", "%s5_levelcode%"]),
                    ("opencode", ["%opencode%"]),
                    ("aider", ["%aider%"]),
                    ("goose", ["%goose%"])
                ]:
                    for kw in keywords:
                        cur.execute("SELECT count(*) FROM artifact_log WHERE content_preview LIKE ?", (kw,))
                        if cur.fetchone()[0] > 0:
                            usage[tool] = True
                            break
            return usage
        except Exception as e:
            logger.error(f"Error checking tool usage: {e}")
            return usage

    def generate_report(self) -> str:
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            active = self.get_active_agents()
            dormant = self.get_dormant_agents()
            tools = self.confirm_tool_usage()

            report = f"# Agent Activity Audit Report - {today}\n\n"
            report += f"**Total Registered Agents**: {len(REGISTERED_AGENTS)}\n"
            report += f"**Active Agents (Last 30 days)**: {len(active)}\n"
            report += f"**Dormant Agents**: {len(dormant)}\n\n"

            report += "## Tool Usage Status\n"
            for t, used in tools.items():
                status = "✅ Active" if used else "❌ Dormant"
                report += f"- **{t.title()}**: {status}\n"
            report += "\n"

            report += "## Dormant Agents List\n"
            if dormant:
                report += "| Agent ID | Name | Role Description |\n"
                report += "| --- | --- | --- |\n"
                for aid, name, role in dormant:
                    report += f"| `{aid}` | {name} | {role} |\n"
            else:
                report += "*No dormant agents found. All agents have been active!*\n"
            report += "\n"

            report += "## Active Agents Stats\n"
            if active:
                report += "| Agent ID | Runs | Success Rate | Artifacts |\n"
                report += "| --- | --- | --- | --- |\n"
                for aid in active:
                    stats = self.get_agent_stats(aid)
                    report += f"| `{aid}` | {stats['total_runs']} | {stats['success_rate']}% | {stats['artifacts_count']} |\n"
            else:
                report += "*No active agents detected in logs.*\n"

            # Write report to Obsidian
            report_dir = os.path.join(self.vault_dir, "Agent-Audit-Reports")
            os.makedirs(report_dir, exist_ok=True)
            report_path = os.path.join(report_dir, f"{today}.md")
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report)
                
            logger.info(f"Agent audit report written to: {report_path}")
            return report
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            return f"Error generating report: {e}"
