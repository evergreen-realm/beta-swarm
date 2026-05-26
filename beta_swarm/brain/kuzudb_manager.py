# kuzudb_manager.py — backward-compat shim.
# This module was renamed to sqlite_brain.py.  All imports should migrate
# to: from beta_swarm.brain.sqlite_brain import SQLiteBrain, KuzuBrain, get_brain
from beta_swarm.brain.sqlite_brain import SQLiteBrain, KuzuBrain, get_brain  # noqa: F401

__all__ = ["KuzuBrain", "SQLiteBrain", "get_brain"]
