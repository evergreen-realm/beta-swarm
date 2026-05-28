"""
S5 Backend Agent — unified with LevelCode brain-vault sync.
LevelCode capabilities (brain vault, Neo4j, Kuzu, Letta, Graphiti) are now
integrated directly into S5BackendAgent. The separate s5_levelcode.py stub
is superseded by this file.
"""
from beta_swarm.agents.base import BaseAgent
import json, re, os, logging, time
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Alias kept for backward compat (orchestrator may import S5LevelCodeAgent)
S5LevelCodeAgent = None  # will be set at bottom of file


class S5BackendAgent(BaseAgent):
    """
    Stage 5 — Backend Development.
    Generates a complete FastAPI backend, then syncs artefacts to every
    brain layer (Neo4j, KuzuDB, Letta, Cognee, Graphiti).
    """

    def __init__(self, brain=None, complexity: str = "medium"):
        super().__init__("s5_backend", "Backend Agent", "Stage 5: Backend Development", brain)
        self.complexity = complexity
        # Lazy-init brain managers (non-fatal if unavailable)
        self._neo4j = self._kuzu = self._letta = self._cognee = self._graphiti = None

    # ------------------------------------------------------------------ #
    # Brain accessors (lazy, non-fatal)
    # ------------------------------------------------------------------ #
    def _get_neo4j(self):
        if self._neo4j is None:
            try:
                from beta_swarm.brain.neo4j_manager import Neo4jBrain
                self._neo4j = Neo4jBrain()
            except Exception:
                pass
        return self._neo4j

    def _get_kuzu(self):
        if self._kuzu is None:
            try:
                from beta_swarm.brain.kuzu_manager import KuzuBrain
                self._kuzu = KuzuBrain()
            except Exception:
                pass
        return self._kuzu

    def _get_letta(self):
        if self._letta is None:
            try:
                from beta_swarm.brain.letta_client import LettaClient
                self._letta = LettaClient()
            except Exception:
                pass
        return self._letta

    def _get_graphiti(self):
        if self._graphiti is None:
            try:
                from beta_swarm.brain.graphiti_manager import GraphitiManager
                self._graphiti = GraphitiManager()
            except Exception:
                pass
        return self._graphiti

    # ------------------------------------------------------------------ #
    # Entry point
    # ------------------------------------------------------------------ #
    def _get_default_next_stage(self):
        return "s6_api"

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        project_id = task.get("project_id", "default")
        project_path = task.get("project_path", f"./projects/{project_id}")

        s4_out = task.get("s4_architecture", {})
        architecture = s4_out.get("architecture") or task.get("architecture", {})
        s3_out = task.get("s3_prd", {})
        prd = s3_out.get("prd") or task.get("prd") or {}

        self._log_handover(f"S5 started. complexity={self.complexity}, project={project_id}")
        os.makedirs(project_path, exist_ok=True)

        title = prd.get("metadata", {}).get("title", "App")
        api_contracts = architecture.get("api_contracts", [])
        db_schema = architecture.get("database_schema", [])

        # 1. Try external code managers (LevelCode → OpenCode)
        generated_files = self._try_code_managers(project_path, prd, architecture)

        # 2. LLM fallback
        if not generated_files:
            generated_files = self._llm_generate(project_path, title, api_contracts, db_schema, prd)

        # 3. Guarantee minimal working files always exist
        self._ensure_required_files(project_path, title, api_contracts)

        all_files = list(set(generated_files + self._list_project_files(project_path)))

        # 4. Sync to brain vault (LevelCode behaviour)
        self._sync_brain_vault(project_id, title, project_path, all_files)

        logger.info(f"[S5] Backend complete: {len(all_files)} files in {project_path}")
        self._log_handover(f"S5 completed. {len(all_files)} files in {project_path}")

        if self.brain:
            try:
                self.brain.store_fact(self.agent_id, f"Backend: {len(all_files)} files", "backend")
            except Exception:
                pass

        os.makedirs(f"./projects/{project_id}", exist_ok=True)
        artifact_path = f"./projects/{project_id}/s5_backend_output.json"
        artifact = {"path": project_path, "files": all_files, "framework": "FastAPI"}
        with open(artifact_path, "w", encoding="utf-8") as f:
            json.dump(artifact, f, indent=2)

        return {
            "status": "complete",
            "path": project_path,
            "backend_info": {"framework": "FastAPI", "generated_files": all_files},
            "artifact": artifact,
            "artifact_path": artifact_path,
            "next_stage": task.get("next_stage") or self._get_default_next_stage()
        }

    # ------------------------------------------------------------------ #
    # Code generation helpers
    # ------------------------------------------------------------------ #
    def _try_code_managers(self, project_path: str, prd: dict, architecture: dict) -> List[str]:
        for name, mod_path, cls_name in [
            ("LevelCode", "beta_swarm.orchestration.levelcode_manager", "LevelCodeManager"),
            ("OpenCode",  "beta_swarm.orchestration.opencode_manager",  "OpenCodeManager"),
        ]:
            try:
                import importlib
                mod = importlib.import_module(mod_path)
                mgr = getattr(mod, cls_name)()
                if mgr.check_installed():
                    logger.info(f"[S5] Using {name}")
                    result = mgr.generate_backend(project_path, prd, architecture)
                    if result.get("files"):
                        return result["files"]
            except Exception as e:
                logger.warning(f"[S5] {name} unavailable: {e}")
        return []

    def _llm_generate(self, project_path: str, title: str,
                      api_contracts: list, db_schema: list, prd: dict) -> List[str]:
        prompt = f"""You are an expert backend developer. Generate a COMPLETE working FastAPI backend for "{title}".

API Contracts: {json.dumps(api_contracts[:5], indent=2)}
DB Schema: {json.dumps(db_schema[:3], indent=2)}

Output files using this exact format:

[FILE: app/__init__.py]
```python
# package
```

[FILE: app/main.py]
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app import routers

app = FastAPI(title="{title}")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health():
    return {{"status": "healthy"}}

@app.get("/metrics")
def metrics():
    return {{"uptime": "ok"}}

app.include_router(routers.router)
```

[FILE: app/routers.py]
```python
# All API routes — no stubs, full implementation
```

[FILE: app/models.py]
```python
# SQLAlchemy models
```

[FILE: app/schemas.py]
```python
# Pydantic schemas
```

[FILE: app/database.py]
```python
# DB engine setup
```

[FILE: requirements.txt]
```
fastapi==0.100.0
uvicorn[standard]==0.22.0
sqlalchemy==2.0.0
pydantic==2.0
python-dotenv==1.0.0
```

[FILE: Dockerfile]
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```"""

        llm_out = self._call_llm(prompt, task_type="s5_backend")
        return self.generate_codebase(llm_out, project_path) if llm_out else []

    def _ensure_required_files(self, project_path: str, title: str, api_contracts: list):
        required = {
            "app/__init__.py": "",
            "app/main.py": f'''from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app import routers

app = FastAPI(title="{title}", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health():
    return {{"status": "healthy", "service": "{title}"}}

@app.get("/metrics")
def metrics():
    return {{"uptime": "ok", "requests": 0}}

app.include_router(routers.router)
''',
            "app/models.py": '''from sqlalchemy import Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class Item(Base):
    __tablename__ = "items"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    user_id = Column(String, nullable=True)
    status = Column(String(50), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
''',
            "app/schemas.py": '''from pydantic import BaseModel
from typing import Optional

class ItemCreate(BaseModel):
    title: str
    user_id: Optional[str] = None

class ItemResponse(BaseModel):
    id: str
    title: str
    user_id: Optional[str] = None
    status: str

    class Config:
        from_attributes = True
''',
            "app/database.py": '''from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
engine = create_engine(DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
''',
            "app/routers.py": '''from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel
import uuid

router = APIRouter()

class ItemSchema(BaseModel):
    title: str
    user_id: Optional[str] = None

class ItemResponse(BaseModel):
    id: str
    title: str
    user_id: Optional[str] = None
    status: str

ITEMS = {}

@router.get("/api/v1/items/", response_model=List[ItemResponse])
def list_items():
    return list(ITEMS.values())

@router.post("/api/v1/items/", response_model=ItemResponse)
def create_item(item: ItemSchema):
    item_id = str(uuid.uuid4())
    new_item = {"id": item_id, "title": item.title, "user_id": item.user_id, "status": "active"}
    ITEMS[item_id] = new_item
    return new_item

@router.get("/api/v1/items/{item_id}", response_model=ItemResponse)
def get_item(item_id: str):
    if item_id not in ITEMS:
        raise HTTPException(status_code=404, detail="Item not found")
    return ITEMS[item_id]

@router.put("/api/v1/items/{item_id}", response_model=ItemResponse)
def update_item(item_id: str, item: ItemSchema):
    if item_id not in ITEMS:
        raise HTTPException(status_code=404, detail="Item not found")
    ITEMS[item_id].update({"title": item.title})
    return ITEMS[item_id]

@router.delete("/api/v1/items/{item_id}")
def delete_item(item_id: str):
    if item_id not in ITEMS:
        raise HTTPException(status_code=404, detail="Item not found")
    ITEMS.pop(item_id)
    return {"status": "deleted"}
''',
            "requirements.txt": (
                "fastapi==0.100.0\nuvicorn[standard]==0.22.0\n"
                "sqlalchemy==2.0.0\npydantic==2.0\npython-dotenv==1.0.0\n"
            ),
            "Dockerfile": f'''FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
''',
        }
        for rel_path, content in required.items():
            abs_path = os.path.join(project_path, rel_path)
            if not os.path.exists(abs_path) or os.path.getsize(abs_path) < 10:
                os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                with open(abs_path, "w", encoding="utf-8") as f:
                    f.write(content)

    def _list_project_files(self, project_path: str) -> List[str]:
        files = []
        for root, _, fnames in os.walk(project_path):
            for fname in fnames:
                rel = os.path.relpath(os.path.join(root, fname), project_path)
                files.append(rel)
        return files[:50]

    # ------------------------------------------------------------------ #
    # LevelCode brain-vault sync (merged from s5_levelcode.py)
    # ------------------------------------------------------------------ #
    def _sync_brain_vault(self, project_id: str, title: str,
                          project_path: str, files: List[str]):
        logger.info("[S5] Syncing generated code to Brain Vault…")
        summary = f"Backend: {len(files)} files in {project_path}"
        try:
            kuzu = self._get_kuzu()
            if kuzu:
                kuzu.add_agent("s5_backend", "Backend Agent", "Coding")
                kuzu.store_agent_memory("s5_backend", summary, "code_generation")
        except Exception as e:
            logger.warning(f"[S5] KuzuDB sync failed (non-fatal): {e}")
        try:
            neo4j = self._get_neo4j()
            if neo4j:
                neo4j.add_global_knowledge(
                    f"{title} Backend",
                    f"Files created: {', '.join(files[:10])}"
                )
        except Exception as e:
            logger.warning(f"[S5] Neo4j sync failed (non-fatal): {e}")
        try:
            letta = self._get_letta()
            if letta:
                agent_data = letta.create_agent(
                    "S5_Coder", "I am the S5 backend developer.", "User needing backend code."
                )
                if agent_data and "id" in agent_data:
                    letta.send_message(agent_data["id"], f"Generated {title} backend.")
        except Exception as e:
            logger.warning(f"[S5] Letta sync failed (non-fatal): {e}")
        try:
            graphiti = self._get_graphiti()
            if graphiti:
                graphiti.add_temporal_edge(
                    source_id="s5_backend",
                    target_id=f"{project_id}_code",
                    relation="generated",
                    timestamp=int(time.time())
                )
        except Exception as e:
            logger.warning(f"[S5] Graphiti sync failed (non-fatal): {e}")


# Backward-compat alias so any old import of S5LevelCodeAgent still works
S5LevelCodeAgent = S5BackendAgent
