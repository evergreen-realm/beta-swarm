# kuzu_manager.py - Backward-compatible shim redirecting to the dual-mode sqlite_brain.py.
from beta_swarm.brain.sqlite_brain import KuzuBrain, get_brain

__all__ = ["KuzuBrain", "get_brain"]
