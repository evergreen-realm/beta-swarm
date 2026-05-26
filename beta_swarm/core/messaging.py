"""
Backward-compat shim.  Import MessageBus from message_bus.py instead.
"""
from beta_swarm.core.message_bus import MessageBus  # noqa: F401

__all__ = ["MessageBus"]
