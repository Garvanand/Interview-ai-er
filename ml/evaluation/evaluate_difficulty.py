"""
Difficulty Predictor Evaluation.
"""
import time
import json
from ml.models.difficulty_predictor import QuestionDifficultyPredictor

def evaluate():
    predictor = QuestionDifficultyPredictor()
    
    # Test dataset
    test_cases = [
        {"question": "What is 2 + 2?", "expected_band": "beginner"},
        {"question": "Implement a distributed key-value store using Paxos.", "expected_band": "advanced"},
        {"question": "Explain how garbage collection works in Python.", "expected_band": "intermediate"},
        {"question": "Reverse a linked list.", "expected_band": "intermediate"},
        {"question": "Design the architecture for a global video streaming service.", "expected_band": "advanced"}
    ]
    
    start_time = time.time()
    correct = 0
    total = len(test_cases)
    
    for case in test_cases:
        res = predictor.predict(case["question"])
        band = res.get("difficulty")
        
        if band == case["expected_band"]:
            correct += 1
            
    latency_ms = (time.time() - start_time) / total * 1000
    accuracy = correct / total
    
    metrics = {
        "model": "QuestionDifficultyPredictor",
        "accuracy": accuracy,
        "inference_latency_ms": latency_ms,
        "test_size": total
    }
    
    return metrics

if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
