\"\"\"
Beta Swarm Desktop System Tray Entrypoint.
Usage: python -m beta_swarm.desktop
\"\"\"
import sys
import os

# Ensure project root is in sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from beta_swarm.desktop.tray_entity import SwarmEntity

def main():
    entity = SwarmEntity()
    entity.run()

if __name__ == "__main__":
    main()
