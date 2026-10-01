"""
Feature extraction for skill mastery models.

Prepares sequential interaction data (like the EdNet prototyping dataset 
or actual Interview-ai-er session history) for use in sequence models or 
gradient-boosted trees.
"""
from typing import List, Dict, Any
import numpy as np

def extract_interaction_features(interactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract temporal and cumulative features from a sequence of interactions
    for a specific skill.
    
    Expected input format for interactions:
    [
        {"correct": True, "difficulty": 0.4, "timestamp": 1600000000},
        {"correct": False, "difficulty": 0.8, "timestamp": 1600000500},
        ...
    ]
    
    Returns a dictionary of aggregated features for the candidate's skill state.
    """
    if not interactions:
        return {
            "attempt_count": 0,
            "success_rate": 0.0,
            "avg_difficulty": 0.0,
            "recent_success_rate": 0.0,
            "time_since_first_attempt": 0.0,
        }
        
    sorted_interactions = sorted(interactions, key=lambda x: x.get("timestamp", 0))
    
    attempt_count = len(sorted_interactions)
    correct_count = sum(1 for i in sorted_interactions if i.get("correct"))
    success_rate = correct_count / attempt_count
    
    difficulties = [i.get("difficulty", 0.5) for i in sorted_interactions]
    avg_difficulty = sum(difficulties) / attempt_count
    
    # Recent window features (e.g., last 3 attempts)
    recent_window = sorted_interactions[-3:]
    recent_correct = sum(1 for i in recent_window if i.get("correct"))
    recent_success_rate = recent_correct / len(recent_window)
    
    time_since_first = sorted_interactions[-1].get("timestamp", 0) - sorted_interactions[0].get("timestamp", 0)
    
    return {
        "attempt_count": attempt_count,
        "success_rate": success_rate,
        "avg_difficulty": avg_difficulty,
        "recent_success_rate": recent_success_rate,
        "time_since_first_attempt": time_since_first,
        "weighted_success": success_rate * avg_difficulty, # simple heuristic interaction feature
    }
