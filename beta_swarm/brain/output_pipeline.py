import os
import json
from datetime import datetime
import glob

class OutputPipeline:
    def __init__(self, brain=None):
        self.brain = brain
        if self.brain is None:
            try:
                from beta_swarm.brain.kuzu_manager import KuzuBrain
                self.brain = KuzuBrain()
            except Exception as e:
                print(f"Failed to init KuzuBrain for OutputPipeline: {e}")
        self.vault_path = r"C:\Users\Admin\Documents\Beta Swarnv2\obsidian-vault"

    def store(self, agent_id: str, output_type: str, content: str, project: str = "default"):
        timestamp = datetime.now().isoformat()
        artifact_id = f"{agent_id}_{project}_{int(datetime.now().timestamp())}"

        # 1. Store in KuzuDB
        db_status = "FAIL: No DB"
        if self.brain:
            try:
                res = self.brain.store_artifact(project, agent_id, content[:1000])
                if res.get("status") == "success":
                    self.brain.query(f"""
                        MATCH (ag:Agent {{id: '{agent_id}'}}), (ar:Artifact {{id: '{res['artifact_id']}'}})
                        CREATE (ag)-[:PRODUCED]->(ar)
                    """)
                    db_status = "OK"
                else:
                    db_status = f"FAIL: {res.get('message')}"
            except Exception as e:
                db_status = f"FAIL: {e}"

        # 2. Append to agent's Obsidian file
        agent_file_pattern = os.path.join(self.vault_path, "03-Agents", f"{agent_id}-*.md")
        agent_files = glob.glob(agent_file_pattern)
        if agent_files:
            with open(agent_files[0], "a", encoding="utf-8") as f:
                f.write(f"\n### {timestamp} — {output_type}\n\n")
                f.write(f"```\n{content[:2000]}\n```\n\n")
                f.write(f"**Project:** {project} | **DB:** {db_status}\n\n")

        # 3. Append to daily note
        daily_file = os.path.join(self.vault_path, "00-Daily", f"{datetime.now().strftime('%Y-%m-%d')}.md")
        os.makedirs(os.path.dirname(daily_file), exist_ok=True)
        with open(daily_file, "a", encoding="utf-8") as f:
            f.write(f"- [{datetime.now().strftime('%H:%M')}] **{agent_id}** | {output_type} | Project: {project} | DB: {db_status}\n")

        # 4. Update cache
        cache_file = "beta_swarm/brain/output_cache.json"
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        cache = []
        if os.path.exists(cache_file):
            with open(cache_file) as f:
                cache = json.load(f)
        cache.append({
            "artifact_id": artifact_id,
            "agent_id": agent_id,
            "type": output_type,
            "project": project,
            "timestamp": timestamp,
            "preview": content[:200]
        })
        with open(cache_file, "w") as f:
            json.dump(cache[-1000:], f, indent=2)  # Keep last 1000

        return {"artifact_id": artifact_id, "db_status": db_status}
