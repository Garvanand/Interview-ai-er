"""
Skill Tagger Evaluation.
"""
import time
import json
from ml.models.skill_classifier import QuestionSkillClassifier

def evaluate():
    classifier = QuestionSkillClassifier()
    
    # Test dataset
    test_cases = [
        {"question": "How do you traverse a binary tree?", "expected_skill": "trees"},
        {"question": "Write a SQL query to join two tables.", "expected_skill": "databases"},
        {"question": "Explain React hooks.", "expected_skill": "frontend"},
        {"question": "How does Docker containerization work?", "expected_skill": "devops"},
        {"question": "What is the time complexity of quicksort?", "expected_skill": "algorithms"}
    ]
    
    start_time = time.time()
    correct = 0
    total = len(test_cases)
    
    for case in test_cases:
        # returns dict with "top_skills" list
        res = classifier.predict(case["question"])
        skills = res.get("top_skills", [])
        if not skills:
            continue
            
        top_skill = skills[0]
        
        # Exact match or heuristic match
        if top_skill.lower() == case["expected_skill"].lower():
            correct += 1
            
    latency_ms = (time.time() - start_time) / total * 1000
    accuracy = correct / total
    
    metrics = {
        "model": "QuestionSkillClassifier",
        "accuracy": accuracy,
        "inference_latency_ms": latency_ms,
        "test_size": total
    }
    
    return metrics

if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
