"""
Run all ML evaluations and generate a report.
"""
import sys
import json
from . import evaluate_difficulty
from . import evaluate_skill_tagger
from . import evaluate_answer_analyzer
from . import evaluate_code_model
from . import evaluate_mastery_model

def run_all():
    print("Running ML Evaluation Framework...\n")
    
    reports = []
    
    evaluators = [
        ("QuestionDifficultyPredictor", evaluate_difficulty.evaluate),
        ("SkillClassifier", evaluate_skill_tagger.evaluate),
        ("ConceptCoverageAnalyzer", evaluate_answer_analyzer.evaluate),
        ("CodeDefectDetector", evaluate_code_model.evaluate),
        ("BayesianKnowledgeTracing", evaluate_mastery_model.evaluate)
    ]
    
    for name, func in evaluators:
        print(f"Evaluating {name}...")
        try:
            metrics = func()
            reports.append(metrics)
        except Exception as e:
            print(f"Error evaluating {name}: {e}")
            
    # Print human readable
    print("\n" + "="*50)
    print("HUMAN READABLE EVALUATION REPORT")
    print("="*50)
    for rep in reports:
        print(f"Model: {rep['model']}")
        print(f"  Test Size: {rep['test_size']}")
        print(f"  Latency:   {rep['inference_latency_ms']:.2f} ms")
        if "accuracy" in rep:
            print(f"  Accuracy:  {rep['accuracy']:.2f}")
        if "mean_absolute_error" in rep:
            print(f"  MAE:       {rep['mean_absolute_error']:.2f}")
        print("-" * 30)
        
    # Print machine readable
    print("\n" + "="*50)
    print("MACHINE READABLE (JSON) REPORT")
    print("="*50)
    print(json.dumps(reports, indent=2))

if __name__ == "__main__":
    run_all()
