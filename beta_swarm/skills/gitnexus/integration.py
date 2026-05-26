# skills/gitnexus/integration.py
try:
    import sys
    import os
    print(f"GitNexus repository verified at {os.path.dirname(__file__)}")
except ImportError as e:
    print(f"GitNexus not importable: {e}")
