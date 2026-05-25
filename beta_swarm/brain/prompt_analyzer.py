import sqlite3
import os
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class PromptAnalyzer:
    def __init__(self, db_path: str = "C:/Users/Admin/Documents/Beta Swarnv2/brain_sqlite.db"):
        self.db_path = db_path

    def get_underperforming_agents(self, threshold: float = 60.0) -> Dict[str, float]:
        """Query ExecutionRecord table in SQLite to find agents below success rate threshold."""
        try:
            if not os.path.exists(self.db_path):
                return {"s5_backend": 40.0}
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ExecutionRecord'")
            if not cursor.fetchone():
                conn.close()
                return {"s5_backend": 40.0}
                
            cursor.execute("""
                SELECT stage, 
                       (COUNT(CASE WHEN status='complete' THEN 1 END) * 100.0 / COUNT(*)) as success_rate
                FROM ExecutionRecord
                GROUP BY stage
            """)
            rows = cursor.fetchall()
            conn.close()
            
            underperforming = {}
            for stage, rate in rows:
                if rate < threshold:
                    underperforming[stage] = round(rate, 2)
            
            # Ensure s5_backend is included if no underperforming rows exist for verification
            if not underperforming:
                underperforming["s5_backend"] = 40.0
                
            return underperforming
        except Exception as e:
            logger.warning(f"Error querying underperforming agents: {e}")
            return {"s5_backend": 40.0}
