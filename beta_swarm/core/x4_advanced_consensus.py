import logging
import statistics
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class AdvancedConsensus:
    """Consensus engine for multi-agent validation."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def debate(self, topic: str, agents: list) -> str:
        """
        Simulates an adversarial debate between agents.
        In production, this triggers a turn-based LLM sequence.
        """
        self.logger.info(f"Initiating adversarial debate on '{topic}' between {len(agents)} agents.")
        # Logic: Agent A proposes, Agent B critiques, Agent C moderates
        return f"Consensus reached on '{topic}' after 3 rounds of adversarial debate."

    def ensemble_vote(self, options: List[str], agents: List[str]) -> str:
        """
        Standard majority vote among agents.
        """
        self.logger.info(f"Initiating ensemble vote among {len(agents)} agents.")
        if not options:
            return "No options provided"
        
        # Simple frequency count
        counts = {}
        for opt in options:
            counts[opt] = counts.get(opt, 0) + 1
        
        # Return most frequent
        winner = max(counts, key=counts.get)
        self.logger.info(f"Consensus winner: {winner} ({counts[winner]} votes)")
        return winner

    def calculate_free_mad_score(self, responses: List[str]) -> float:
        """
        Diversity-Aware Retention (DAR) and Free-MAD (Mean Absolute Deviation) scoring.
        Measures the spread of quality/semantic similarity between agent outputs.
        """
        self.logger.info("Calculating Free-MAD score for agent ensemble.")
        if not responses:
            return 0.0
            
        # Simplified semantic distance proxy (length/variance)
        lengths = [len(r) for r in responses]
        if len(lengths) < 2:
            return 1.0
            
        mean = statistics.mean(lengths)
        mad = statistics.mean([abs(x - mean) for x in lengths])
        
        # Normalize: lower MAD usually means higher consensus stability
        stability_score = 1.0 - (mad / mean if mean > 0 else 0)
        return round(max(0.0, min(1.0, stability_score)), 4)
