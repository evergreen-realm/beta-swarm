"""GitNexus Indexer — parses git repos into searchable code intel."""

import os
import subprocess
import json
import logging
from pathlib import Path
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class GitNexusIndexer:
    def __init__(self, repo_path: str = "."):
        try:
            self.repo_path = Path(repo_path).resolve()
            self.index: Dict[str, Any] = {
                "files": [],
                "functions": [],
                "classes": [],
                "imports": [],
                "commits": [],
                "parsed_files": [],
                "metadata": {
                    "indexed_at": 0,
                    "repo_name": self.repo_path.name
                }
            }
            self.ignored_dirs = {".git", "node_modules", "__pycache__", "venv", ".venv", "dist", "build"}
            self.code_extensions = {".py", ".js", ".ts", ".tsx", ".rs", ".go", ".java", ".c", ".cpp", ".hpp", ".cc", ".h"}
            self.other_extensions = {".md", ".yml", ".yaml", ".json", ".toml", ".sh"}
            logger.info(f"GitNexusIndexer initialized for {self.repo_path}")
        except Exception as e:
            logger.error(f"Error in init: {e}")

    def build_index(self) -> Dict[str, Any]:
        try:
            if not (self.repo_path / ".git").exists():
                logger.warning(f"{self.repo_path} is not a git repository.")
                
            logger.info(f"Indexing repository: {self.repo_path}")
            self._index_files()
            self._index_commits()
            self._index_code_structure()
            
            import time
            self.index["metadata"]["indexed_at"] = time.time()
            
            # Write results to databases
            self.write_to_sqlite()
            self.write_to_neo4j()
            
            return {"status": "complete", "file_count": len(self.index["files"]), "repo": str(self.repo_path)}
        except Exception as e:
            logger.error(f"Failed to build index: {e}")
            return {"status": "error", "error": str(e)}

    def _index_files(self):
        try:
            for root, dirs, files in os.walk(self.repo_path):
                dirs[:] = [d for d in dirs if d not in self.ignored_dirs and not d.startswith(".")]
                
                rel_root = Path(root).relative_to(self.repo_path)
                for f in files:
                    ext = Path(f).suffix.lower()
                    if ext in self.code_extensions or ext in self.other_extensions:
                        self.index["files"].append({
                            "path": str(rel_root / f) if str(rel_root) != "." else f,
                            "type": ext.lstrip("."),
                            "size": os.path.getsize(os.path.join(root, f))
                        })
        except Exception as e:
            logger.error(f"Error indexing files: {e}")

    def _index_commits(self):
        try:
            result = subprocess.run(
                ["git", "-C", str(self.repo_path), "log", "--pretty=format:%H|%an|%ad|%s", "--date=short", "-n", "50"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if not line: continue
                    parts = line.split("|", 3)
                    if len(parts) == 4:
                        self.index["commits"].append({
                            "hash": parts[0],
                            "author": parts[1],
                            "date": parts[2],
                            "message": parts[3]
                        })
        except Exception as e:
            logger.error(f"Commit indexing failed: {e}")

    def _index_code_structure(self):
        try:
            from beta_swarm.tools.gitnexus.ast_parser import TreeSitterParser
            parser = TreeSitterParser()
            self.index["parsed_files"] = []
            
            for file_info in self.index["files"]:
                rel_path = file_info["path"]
                full_path = self.repo_path / rel_path
                ext = Path(rel_path).suffix.lower()
                
                try:
                    if ext in self.code_extensions:
                        res = parser.parse_file(str(full_path))
                        if res and not res.get("error") or res.get("language") == "regex-fallback":
                            for fn in res.get("functions", []):
                                self.index["functions"].append({
                                    "name": fn["name"], "file": rel_path,
                                    "line": fn.get("start_line", 0), "end_line": fn.get("end_line", 0)
                                })
                            for cl in res.get("classes", []):
                                self.index["classes"].append({
                                    "name": cl["name"], "file": rel_path,
                                    "line": cl.get("start_line", 0), "end_line": cl.get("end_line", 0)
                                })
                            for imp in res.get("imports", []):
                                self.index["imports"].append({
                                    "file": rel_path, "module": imp.get("module", "")
                                })
                            self.index["parsed_files"].append({
                                "path": rel_path, "language": res.get("language", "unknown"),
                                "functions": res.get("functions", []), "classes": res.get("classes", []),
                                "imports": res.get("imports", []), "calls": res.get("calls", [])
                            })
                        else:
                            self.index["parsed_files"].append({
                                "path": rel_path, "language": "text",
                                "functions": [], "classes": [], "imports": [], "calls": [], "size": file_info.get("size", 0)
                            })
                    else:
                        self.index["parsed_files"].append({
                            "path": rel_path, "language": ext.lstrip("."),
                            "functions": [], "classes": [], "imports": [], "calls": [], "size": file_info.get("size", 0)
                        })
                except Exception as file_err:
                    logger.error(f"Error parsing file {rel_path}: {file_err}")
                    self.index["parsed_files"].append({
                        "path": rel_path, "language": "error",
                        "functions": [], "classes": [], "imports": [], "calls": [], "size": file_info.get("size", 0)
                    })
        except Exception as e:
            logger.error(f"Error indexing code structure: {e}")

    def write_to_sqlite(self):
        try:
            import sqlite3
            import hashlib
            from datetime import datetime, timezone
            
            db_path = os.environ.get(
                "BRAIN_SQLITE_DB",
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "brain_sqlite.db")
            )
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS code_index (
                    file_path TEXT PRIMARY KEY,
                    project_id TEXT,
                    language TEXT,
                    entities TEXT,
                    functions_count INTEGER,
                    classes_count INTEGER,
                    indexed_at TEXT,
                    content_hash TEXT
                )
            """)
            
            project_id = self.index["metadata"].get("repo_name", "unknown_project")
            indexed_at_str = datetime.now(timezone.utc).isoformat()
            
            for file_info in self.index.get("parsed_files", []):
                rel_path = file_info["path"]
                full_path = self.repo_path / rel_path
                content_hash = ""
                try:
                    with open(full_path, "rb") as f:
                        content_hash = hashlib.md5(f.read()).hexdigest()
                except Exception:
                    pass
                
                entities = {
                    "functions": file_info.get("functions", []),
                    "classes": file_info.get("classes", []),
                    "imports": file_info.get("imports", []),
                    "calls": file_info.get("calls", [])
                }
                
                cursor.execute("""
                    INSERT OR REPLACE INTO code_index (
                        file_path, project_id, language, entities, functions_count, classes_count, indexed_at, content_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rel_path,
                    project_id,
                    file_info.get("language", "unknown"),
                    json.dumps(entities),
                    len(file_info.get("functions", [])),
                    len(file_info.get("classes", [])),
                    indexed_at_str,
                    content_hash
                ))
            conn.commit()
            conn.close()
            logger.info("Code index written to SQLite.")
        except Exception as e:
            logger.error(f"Failed to write code index to SQLite: {e}")

    def write_to_neo4j(self):
        try:
            from beta_swarm.brain.neo4j_manager import Neo4jBrain
            neo4j = Neo4jBrain()
            
            for file_info in self.index.get("parsed_files", []):
                rel_path = file_info["path"]
                query_file = """
                MERGE (cf:CodeFile {path: $path})
                SET cf.language = $language
                """
                with neo4j.driver.session() as session:
                    session.run(query_file, path=rel_path, language=file_info.get("language", "unknown"))
                    
                    for func in file_info.get("functions", []):
                        query_func = """
                        MATCH (cf:CodeFile {path: $path})
                        MERGE (fn:Function {name: $name, file: $path})
                        SET fn.start_line = $start_line, fn.end_line = $end_line
                        MERGE (cf)-[:DEFINES]->(fn)
                        """
                        session.run(query_func, path=rel_path, name=func["name"], start_line=func.get("start_line", 0), end_line=func.get("end_line", 0))
                        
                    for cls in file_info.get("classes", []):
                        query_cls = """
                        MATCH (cf:CodeFile {path: $path})
                        MERGE (cl:Class {name: $name, file: $path})
                        SET cl.start_line = $start_line, cl.end_line = $end_line
                        MERGE (cf)-[:DEFINES]->(cl)
                        """
                        session.run(query_cls, path=rel_path, name=cls["name"], start_line=cls.get("start_line", 0), end_line=cls.get("end_line", 0))
                        
                    for imp in file_info.get("imports", []):
                        mod_name = imp.get("module", "").strip()
                        if mod_name:
                            query_imp = """
                            MATCH (cf:CodeFile {path: $path})
                            MERGE (m:Module {name: $mod_name})
                            MERGE (cf)-[:DEPENDS_ON]->(m)
                            """
                            session.run(query_imp, path=rel_path, mod_name=mod_name)
            neo4j.close()
            logger.info("Code index written to Neo4j.")
        except Exception as e:
            logger.error(f"Failed to write code index to Neo4j: {e}")

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        try:
            query_lower = query.lower()
            results = []
            for func in self.index["functions"]:
                if query_lower in func["name"].lower():
                    results.append({"type": "function", **func})
            for cls in self.index["classes"]:
                if query_lower in cls["name"].lower():
                    results.append({"type": "class", **cls})
            for commit in self.index["commits"]:
                if query_lower in commit["message"].lower():
                    results.append({"type": "commit", **commit})
            return sorted(results, key=lambda x: x.get("line", 0))[:limit]
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def export_to_json(self, output_path: str = "gitnexus_index.json"):
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(self.index, f, indent=2)
            logger.info(f"Index exported to {output_path}")
        except Exception as e:
            logger.error(f"Failed to export to JSON: {e}")

    def export_index(self, output_path: str = "gitnexus_index.json"):
        try:
            self.export_to_json(output_path)
        except Exception as e:
            logger.error(f"Export index failed: {e}")
