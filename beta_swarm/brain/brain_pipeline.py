import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

@dataclass
class Artifact:
    artifact_type: str  # one of: "prd", "code", "review", "error", "research", "architecture", "deployment"
    project_id: str
    content: str
    source_agent: str
    artifact_id: str = field(default_factory=lambda: "")
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: "")

    def __post_init__(self):
        if not self.artifact_id:
            self.artifact_id = hashlib.md5(self.content.encode('utf-8')).hexdigest()
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Artifact':
        return cls(
            artifact_type=data.get("artifact_type", ""),
            project_id=data.get("project_id", ""),
            content=data.get("content", ""),
            source_agent=data.get("source_agent", ""),
            artifact_id=data.get("artifact_id", ""),
            metadata=data.get("metadata") or {},
            timestamp=data.get("timestamp", "")
        )


class BrainPipeline:
    def __init__(self, project_path: str = "C:/Users/Admin/Documents/Beta Swarnv2"):
        self.project_path = project_path
        self.db_path = f"{project_path}/brain_sqlite.db"
        self._ensure_schema()

    # Lazy Initializers
    def _neo4j(self):
        if not hasattr(self, "_neo4j_instance"):
            from beta_swarm.brain.neo4j_manager import Neo4jBrain
            manager = Neo4jBrain()
            if not hasattr(manager, "store_fact"):
                def store_fact(agent_id: str, topic: str, content: str, metadata: str):
                    query = """
                    MERGE (a:Agent {id: $agent_id})
                    CREATE (f:Fact {content: $content, topic: $topic, metadata: $metadata, timestamp: timestamp()})
                    CREATE (a)-[:PRODUCED]->(f)
                    """
                    with manager.driver.session() as session:
                        session.run(query, agent_id=agent_id, content=content, topic=topic, metadata=metadata)
                    return {"status": "success"}
                manager.store_fact = store_fact
            self._neo4j_instance = manager
        return self._neo4j_instance

    def _sqlite(self):
        if not hasattr(self, "_sqlite_connection"):
            import sqlite3
            self._sqlite_connection = sqlite3.connect(self.db_path, check_same_thread=False)
        return self._sqlite_connection

    def _cognee(self):
        if not hasattr(self, "_cognee_instance"):
            from beta_swarm.brain.cognee_client import CogneeClient
            self._cognee_instance = CogneeClient()
        return self._cognee_instance

    def _letta(self):
        if not hasattr(self, "_letta_instance"):
            from beta_swarm.brain.letta_client import LettaClient
            self._letta_instance = LettaClient()
        return self._letta_instance

    def _graphiti(self):
        if not hasattr(self, "_graphiti_instance"):
            from beta_swarm.brain.graphiti_manager import GraphitiManager
            self._graphiti_instance = GraphitiManager()
        return self._graphiti_instance

    def _obsidian(self):
        if not hasattr(self, "_obsidian_instance"):
            from beta_swarm.brain.obsidian_manager import ObsidianManager
            vault_path = f"{self.project_path}/obsidian-vault"
            manager = ObsidianManager(vault_path=vault_path)
            if not hasattr(manager, "write_note"):
                def write_note(relative_path: str, content: str):
                    full_path = f"{manager.vault_path}/{relative_path}"
                    import os
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    with open(full_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    return True
                manager.write_note = write_note
            self._obsidian_instance = manager
        return self._obsidian_instance

    def _ensure_schema(self):
        conn = self._sqlite()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS artifact_log (
                artifact_id TEXT PRIMARY KEY,
                artifact_type TEXT,
                project_id TEXT,
                source_agent TEXT,
                content_hash TEXT,
                content_preview TEXT,
                timestamp TEXT,
                cognee_processed INTEGER DEFAULT 0,
                graphiti_processed INTEGER DEFAULT 0,
                letta_processed INTEGER DEFAULT 0,
                neo4j_processed INTEGER DEFAULT 0,
                obsidian_written INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending'
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS brain_state (
                layer TEXT PRIMARY KEY,
                last_sync TEXT,
                item_count INTEGER DEFAULT 0,
                healthy INTEGER DEFAULT 1
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS temporal_facts (
                entity_id TEXT,
                fact_content TEXT,
                source TEXT,
                timestamp TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS letta_queue (
                artifact_id TEXT,
                source_agent TEXT,
                content TEXT,
                timestamp TEXT
            )
        """)
        
        layers = ["cognee", "graphiti", "letta", "neo4j", "sqlite", "obsidian"]
        for layer in layers:
            cursor.execute("""
                INSERT OR IGNORE INTO brain_state (layer, last_sync, item_count, healthy)
                VALUES (?, ?, ?, ?)
            """, (layer, None, 0, 1))
        conn.commit()

    def _update_layer_state(self, layer: str, healthy: bool):
        try:
            conn = self._sqlite()
            cursor = conn.cursor()
            timestamp = datetime.now(timezone.utc).isoformat()
            if healthy:
                cursor.execute("""
                    UPDATE brain_state 
                    SET healthy = 1, last_sync = ?, item_count = item_count + 1 
                    WHERE layer = ?
                """, (timestamp, layer))
            else:
                cursor.execute("""
                    UPDATE brain_state 
                    SET healthy = 0, last_sync = ? 
                    WHERE layer = ?
                """, (timestamp, layer))
            conn.commit()
        except Exception:
            pass

    def _fallback_entity_extraction(self, content: str) -> Dict[str, Any]:
        cap_phrases = re.findall(r'\b[A-Z][a-zA-Z0-9]*(?:\s+[A-Z][a-zA-Z0-9]*)*\b', content)
        camel_cases = re.findall(r'\b[a-z]+[A-Z][a-zA-Z0-9]*\b', content)
        snake_cases = re.findall(r'\b[a-z]+_[a-z0-9_]*\b', content)
        entities = sorted(list(set(cap_phrases + camel_cases + snake_cases)))
        return {
            "status": "fallback",
            "entities": entities,
            "extracted_at": datetime.now(timezone.utc).isoformat()
        }

    # Layer Processors
    def _process_cognee(self, artifact: Artifact) -> Dict[str, Any]:
        try:
            cognee = self._cognee()
            doc_res = cognee.add_document(content=artifact.content, doc_id=artifact.artifact_id)
            cognify_res = cognee.cognify()
            if not doc_res or not cognify_res:
                raise Exception("Cognee returned empty response")
            self._update_layer_state("cognee", healthy=True)
            return {
                "status": "ok",
                "cognee_response": doc_res,
                "cognify_response": cognify_res
            }
        except Exception as e:
            self._update_layer_state("cognee", healthy=False)
            fallback_res = self._fallback_entity_extraction(artifact.content)
            fallback_res["error"] = str(e)
            return fallback_res

    def _process_graphiti(self, artifact: Artifact) -> Dict[str, Any]:
        try:
            graphiti = self._graphiti()
            res = graphiti.add_fact(
                entity_id=artifact.artifact_id,
                fact_content=artifact.content[:500],
                source=artifact.source_agent,
                timestamp=artifact.timestamp
            )
            if res.get("status") == "error":
                raise Exception(res.get("error", "Unknown Graphiti error"))
            self._update_layer_state("graphiti", healthy=True)
            return {
                "status": "ok",
                "fact_id": res.get("fact_id")
            }
        except Exception as e:
            self._update_layer_state("graphiti", healthy=False)
            try:
                conn = self._sqlite()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO temporal_facts (entity_id, fact_content, source, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (artifact.artifact_id, artifact.content[:500], artifact.source_agent, artifact.timestamp))
                conn.commit()
                return {"status": "fallback", "note": "Stored in SQLite temporal_facts", "error": str(e)}
            except Exception as sql_err:
                return {"status": "error", "note": "SQLite store failed", "error": f"{str(e)} | {str(sql_err)}"}

    def _process_letta(self, artifact: Artifact) -> Dict[str, Any]:
        try:
            letta = self._letta()
            agent_name = f"swarm_{artifact.source_agent}"
            agent_res = letta.create_agent(
                name=agent_name,
                persona="You are a specialized Swarm memory agent.",
                human="Beta Swarm System"
            )
            agent_id = agent_res.get("id")
            if not agent_id:
                raise Exception("Letta agent creation did not return a valid agent ID")
            msg_res = letta.send_message(agent_id=agent_id, message=artifact.content)
            if not msg_res:
                raise Exception("Letta send_message failed or returned empty response")
            self._update_layer_state("letta", healthy=True)
            return {"status": "ok", "agent_id": agent_id, "message_status": "sent"}
        except Exception as e:
            self._update_layer_state("letta", healthy=False)
            try:
                conn = self._sqlite()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO letta_queue (artifact_id, source_agent, content, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (artifact.artifact_id, artifact.source_agent, artifact.content, artifact.timestamp))
                conn.commit()
                return {"status": "fallback", "note": "Queued in SQLite letta_queue", "error": str(e)}
            except Exception as sql_err:
                return {"status": "error", "note": "SQLite queue failed", "error": f"{str(e)} | {str(sql_err)}"}

    def _process_neo4j(self, artifact: Artifact, layer_results: Dict[str, Any]) -> Dict[str, Any]:
        try:
            neo4j = self._neo4j()
            statuses = {k: v.get("status") for k, v in layer_results.items()}
            metadata = {
                "artifact_type": artifact.artifact_type,
                "artifact_id": artifact.artifact_id,
                "layer_statuses": statuses,
                "timestamp": artifact.timestamp
            }
            res = neo4j.store_fact(
                agent_id=artifact.source_agent,
                topic=f"{artifact.project_id}_{artifact.artifact_type}",
                content=artifact.content[:1000],
                metadata=json.dumps(metadata)
            )
            self._update_layer_state("neo4j", healthy=True)
            return {"status": "ok", "neo4j_response": res}
        except Exception as e:
            self._update_layer_state("neo4j", healthy=False)
            return {"status": "error", "error": str(e)}

    def _process_obsidian(self, artifact: Artifact, layer_results: Dict[str, Any]) -> Dict[str, Any]:
        try:
            obsidian = self._obsidian()
            folder_map = {
                "prd": "01-PRDs",
                "code": "02-Code-Reviews",
                "review": "02-Code-Reviews",
                "research": "03-Research",
                "architecture": "03-Research",
                "error": "04-Errors"
            }
            folder = folder_map.get(artifact.artifact_type, "99-Misc")
            relative_path = f"{folder}/{artifact.artifact_id}.md"

            c_res = layer_results.get("cognee", {})
            g_res = layer_results.get("graphiti", {})
            l_res = layer_results.get("letta", {})
            n_res = layer_results.get("neo4j", {})

            def details(r):
                d = str(r.get("entities") or r.get("fact_id") or r.get("agent_id") or r.get("neo4j_response") or r.get("error", ""))
                return d[:100] + "..." if len(d) > 100 else d

            note_content = f"""# Artifact: {artifact.artifact_id}

## Artifact Metadata
| Field | Value |
| :--- | :--- |
| **Artifact ID** | {artifact.artifact_id} |
| **Type** | {artifact.artifact_type} |
| **Project ID** | {artifact.project_id} |
| **Source Agent** | {artifact.source_agent} |
| **Timestamp** | {artifact.timestamp} |

## Processing Results
| Layer | Status | Details / Error |
| :--- | :--- | :--- |
| **Cognee** | {c_res.get("status", "skipped")} | {details(c_res)} |
| **Graphiti** | {g_res.get("status", "skipped")} | {details(g_res)} |
| **Letta** | {l_res.get("status", "skipped")} | {details(l_res)} |
| **Neo4j** | {n_res.get("status", "skipped")} | {details(n_res)} |

## Content Preview
```
{artifact.content[:2000]}
```
"""
            obsidian.write_note(relative_path, note_content)
            self._update_layer_state("obsidian", healthy=True)
            return {"status": "ok", "relative_path": relative_path}
        except Exception as e:
            self._update_layer_state("obsidian", healthy=False)
            return {"status": "error", "error": str(e)}

    # Main Methods
    def ingest(self, artifact: Artifact) -> Dict[str, Any]:
        # Step 0: Log in SQLite
        try:
            conn = self._sqlite()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO artifact_log (
                    artifact_id, artifact_type, project_id, source_agent, content_hash, content_preview, timestamp, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                artifact.artifact_id,
                artifact.artifact_type,
                artifact.project_id,
                artifact.source_agent,
                hashlib.md5(artifact.content.encode('utf-8')).hexdigest(),
                artifact.content[:200],
                artifact.timestamp,
                "pending"
            ))
            conn.commit()
        except Exception as e:
            logger.error(f"SQLite log failed: {e}")

        layer_results = {}
        layer_results["cognee"] = self._process_cognee(artifact)
        layer_results["graphiti"] = self._process_graphiti(artifact)
        layer_results["letta"] = self._process_letta(artifact)
        layer_results["neo4j"] = self._process_neo4j(artifact, layer_results)
        layer_results["obsidian"] = self._process_obsidian(artifact, layer_results)

        # Step 5: Update log
        overall_status = "partial"
        try:
            statuses = [layer_results[l].get("status") for l in ["cognee", "graphiti", "letta", "neo4j", "obsidian"]]
            overall_status = "complete" if all(s == "ok" for s in statuses) else "partial"
            conn = self._sqlite()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE artifact_log
                SET cognee_processed = ?,
                    graphiti_processed = ?,
                    letta_processed = ?,
                    neo4j_processed = ?,
                    obsidian_written = ?,
                    status = ?
                WHERE artifact_id = ?
            """, (
                1 if layer_results["cognee"].get("status") == "ok" else 0,
                1 if layer_results["graphiti"].get("status") == "ok" else 0,
                1 if layer_results["letta"].get("status") == "ok" else 0,
                1 if layer_results["neo4j"].get("status") == "ok" else 0,
                1 if layer_results["obsidian"].get("status") == "ok" else 0,
                overall_status,
                artifact.artifact_id
            ))
            conn.commit()
            self._update_layer_state("sqlite", healthy=True)
        except Exception as e:
            logger.error(f"SQLite status update failed: {e}")
            self._update_layer_state("sqlite", healthy=False)

        return {
            "artifact_id": artifact.artifact_id,
            "overall_status": overall_status,
            "layers": layer_results
        }

    def ingest_project(self, project_id: str, artifacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for art_dict in artifacts:
            if "project_id" not in art_dict:
                art_dict["project_id"] = project_id
            results.append(self.ingest(Artifact.from_dict(art_dict)))
        return results

    def get_pipeline_status(self, artifact_id: str) -> Dict[str, Any]:
        try:
            conn = self._sqlite()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM artifact_log WHERE artifact_id = ?", (artifact_id,))
            row = cursor.fetchone()
            if not row:
                return {"status": "not_found", "artifact_id": artifact_id}
            columns = [c[0] for c in cursor.description]
            return dict(zip(columns, row))
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_brain_health(self) -> Dict[str, Any]:
        try:
            conn = self._sqlite()
            cursor = conn.cursor()
            cursor.execute("SELECT layer, last_sync, item_count, healthy FROM brain_state")
            rows = cursor.fetchall()
            return {r[0]: {"last_sync": r[1], "item_count": r[2], "healthy": bool(r[3])} for r in rows}
        except Exception as e:
            return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    from beta_swarm.brain.brain_pipeline import BrainPipeline, Artifact
    bp = BrainPipeline()
    art = Artifact.from_dict({
        "artifact_type": "prd",
        "project_id": "test-001",
        "content": "# PRD: Test Project\nThis project uses React and FastAPI.",
        "source_agent": "s3_prd"
    })
    result = bp.ingest(art)
    print(f"Pipeline status: {result['overall_status']}")
    print(f"Layers: {list(result['layers'].keys())}")
