# kuzu_manager.py - Backward-compatible shim redirecting to the dual-mode kuzudb_manager.py.
from beta_swarm.brain.kuzudb_manager import KuzuBrain, get_brain

__all__ = ["KuzuBrain", "get_brain"]
