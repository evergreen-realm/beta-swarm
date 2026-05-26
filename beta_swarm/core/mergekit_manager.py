import os
import shutil
import subprocess
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class MergeKitManager:
    """Manager for dynamic model merging via MergeKit CLI."""
    
    def __init__(self):
        self.binary = shutil.which("mergekit-yaml")
        if not self.binary:
            # Fallback for common local paths
            local_bin = os.path.expanduser("~/.local/bin/mergekit-yaml")
            if os.path.exists(local_bin):
                self.binary = local_bin
        
        if self.binary:
            logger.info(f"MergeKit found at {self.binary}")
        else:
            logger.warning("MergeKit binary (mergekit-yaml) not found in PATH.")

    def apply_recipe(self, recipe_path: str, output_path: str, options: Dict[str, Any] = None) -> bool:
        """
        Executes mergekit-yaml with the specified recipe.
        """
        if not self.binary:
            logger.error("Cannot merge: MergeKit not installed.")
            return False
            
        if not os.path.exists(recipe_path):
            logger.error(f"Recipe file not found: {recipe_path}")
            return False

        logger.info(f"Applying MergeKit recipe: {recipe_path} -> {output_path}")
        
        cmd = [self.binary, recipe_path, output_path]
        if options:
            for k, v in options.items():
                cmd.extend([f"--{k}", str(v)])
                
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info("Merge completed successfully.")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Merge failed: {e.stderr}")
            return False
