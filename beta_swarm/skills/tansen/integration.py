# skills/tansen/integration.py
try:
    import sys
    import os
    print(f"Tansen TTS repository verified at {os.path.dirname(__file__)}")
except ImportError as e:
    print(f"Tansen not importable: {e}")
