"""
Answer Analyzer (Concept Coverage) Evaluation.
"""
import time
import json
from ml.models.concept_coverage import ConceptCoverageAnalyzer

def evaluate():
    model = ConceptCoverageAnalyzer()
    
    # Test dataset
    test_cases = [
        {
            "question": "What are the core components of Kubernetes?",
            "concepts": ["Pod", "Node", "Kubelet", "Control Plane"],
            "answer": "Kubernetes has a control plane that manages nodes, and the smallest unit is a pod.",
            "expected_coverage": 75.0 # Mentions Control Plane, Node, Pod
        },
        {
            "question": "Explain CI/CD.",
            "concepts": ["Continuous Integration", "Continuous Deployment", "Automation"],
            "answer": "It is about automating the deployment process.",
            "expected_coverage": 33.3 # Mentions Automation/Deployment
        },
    ]
    
    start_time = time.time()
    errors = 0
    total = len(test_cases)
    
    for case in test_cases:
        res = model.evaluate_concepts(case["answer"], case["concepts"])
        # Compare actual coverage vs expected
        coverage = res.get("overall_coverage_pct", 0.0)
        error = abs(coverage - case["expected_coverage"])
        errors += error
            
    latency_ms = (time.time() - start_time) / total * 1000
    mae = errors / total
    
    metrics = {
        "model": "ConceptCoverageModel",
        "mean_absolute_error": mae,
        "inference_latency_ms": latency_ms,
        "test_size": total
    }
    
    return metrics

if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
