import multiprocessing
import time
import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.getcwd())

from beta_swarm.dashboard.launcher import run_web, run_tui

if __name__ == "__main__":
    # Fix for Windows multiprocessing
    multiprocessing.freeze_support()
    
    print("Initializing JARVIS Swarm Dashboard...")
    
    # Start web server in a separate process
    web_proc = multiprocessing.Process(target=run_web, daemon=True)
    web_proc.start()
    
    time.sleep(2) # Give web server a head start
    
    # Start TUI in main process
    try:
        run_tui()
    except KeyboardInterrupt:
        print("\nShutting down dashboard...")
    except Exception as e:
        print(f"Error starting TUI: {e}")
    finally:
        if web_proc.is_alive():
            web_proc.terminate()
