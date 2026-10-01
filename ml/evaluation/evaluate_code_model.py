"""
Code Model (Defect Detector) Evaluation.
"""
import time
import json
from ml.models.defect_detector import CodeDefectDetector

def evaluate():
    detector = CodeDefectDetector()
    
    # Test dataset
    test_cases = [
        {
            "code": "def divide(a, b):\n    return a / b",
            "expected_defect": True # Missing zero-division check
        },
        {
            "code": "def add(a, b):\n    return a + b",
            "expected_defect": False
        },
        {
            "code": "def get_item(lst, idx):\n    return lst[idx]",
            "expected_defect": True # Missing bounds check
        }
    ]
    
    start_time = time.time()
    correct = 0
    total = len(test_cases)
    
    for case in test_cases:
        result = detector.analyze_code(case["code"])
        
        # Heuristic check
        has_defect = result.get("defect_probability", 0.0) > 0.5
        if has_defect == case["expected_defect"]:
            correct += 1
            
    latency_ms = (time.time() - start_time) / total * 1000
    accuracy = correct / total
    
    metrics = {
        "model": "CodeDefectDetector",
        "accuracy": accuracy,
        "inference_latency_ms": latency_ms,
        "test_size": total
    }
    
    return metrics

if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
