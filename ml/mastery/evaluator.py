"""
Evaluator for candidate skill/mastery modeling.
Validates the mastery estimation layer against simulated or standard interaction datasets.
"""
from typing import List, Tuple
from .bkt import BKTModel, Interaction, MasteryEstimate
import logging

logger = logging.getLogger(__name__)

def evaluate_mastery_model(dataset: List[Tuple[str, List[Interaction]]]) -> dict:
    """
    Evaluates the mastery model on a dataset of (skill, interaction_sequence).
    
    Args:
        dataset: A list of tuples, each containing a skill name and a chronological 
                 sequence of Interaction objects.
                 
    Returns:
        A dictionary containing evaluation metrics.
    """
    model = BKTModel()
    
    # Track metrics
    predictions: List[MasteryEstimate] = []
    
    # Simple evaluation: run the model over the dataset and collect output
    # In a real environment, we would compute AUC or RMSE against actual test outcomes.
    for skill, sequence in dataset:
        estimate = model.predict_sequence(skill, sequence)
        predictions.append(estimate)
        
    avg_mastery = sum(p.mastery for p in predictions) / len(predictions) if predictions else 0
    avg_confidence = sum(p.confidence for p in predictions) / len(predictions) if predictions else 0
    
    logger.info(f"Evaluated mastery model on {len(dataset)} sequences.")
    logger.info(f"Average Estimated Mastery: {avg_mastery:.3f}")
    
    return {
        "sequence_count": len(dataset),
        "average_mastery": avg_mastery,
        "average_confidence": avg_confidence,
        "predictions": predictions
    }

def run_sample_evaluation():
    """
    Run a sample evaluation on a synthetic sequence reflecting typical interview
    learning curves.
    """
    # Simulate a candidate improving over time
    interactions_improving = [
        Interaction(correct=False, difficulty=0.4, timestamp=1.0),
        Interaction(correct=False, difficulty=0.5, timestamp=2.0),
        Interaction(correct=True, difficulty=0.3, timestamp=3.0),
        Interaction(correct=True, difficulty=0.6, timestamp=4.0),
        Interaction(correct=True, difficulty=0.7, timestamp=5.0),
    ]
    
    # Simulate a candidate struggling consistently
    interactions_struggling = [
        Interaction(correct=False, difficulty=0.3, timestamp=1.0),
        Interaction(correct=True, difficulty=0.2, timestamp=2.0),
        Interaction(correct=False, difficulty=0.4, timestamp=3.0),
        Interaction(correct=False, difficulty=0.5, timestamp=4.0),
    ]
    
    dataset = [
        ("graphs", interactions_improving),
        ("dynamic_programming", interactions_struggling)
    ]
    
    results = evaluate_mastery_model(dataset)
    for p in results["predictions"]:
        print(f"Skill: {p.skill:20s} | Mastery: {p.mastery:.3f} | Trend: {p.trend:10s} | Conf: {p.confidence:.3f}")

if __name__ == "__main__":
    run_sample_evaluation()
