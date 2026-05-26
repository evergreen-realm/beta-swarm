# skills/clawgraph/integration.py
try:
    import sys
    import os
    # Add the current directory to sys.path so we can import clawgraph
    sys.path.append(os.path.dirname(__file__))
    import clawgraph
    print(f"ClawGraph package verified at {os.path.dirname(__file__)}")
except ImportError as e:
    print(f"ClawGraph not importable: {e}")
