import pytest
from app.ai.schemas import AnswerEvaluation, CodeEvaluation, AIRun, Question
from app.ai.engine import AssessmentEngine

class MockProvider:
    def __init__(self, mode="success", mock_response=None):
        self.mode = mode
        self.mock_response = mock_response

    def generate_structured(self, prompt, schema, **kwargs):
        if self.mode == "fail":
            raise ValueError("Model validation failed")
        
        telemetry = {
            "input_tokens": 150,
            "output_tokens": 50,
            "retry_count": 0,
            "schema_validation": True
        }
        
        if self.mock_response:
            return self.mock_response, telemetry
            
        if schema == AnswerEvaluation:
            return AnswerEvaluation(
                overall_score=85,
                technical_accuracy=90,
                conceptual_depth=80,
                problem_solving=85,
                communication=85,
                completeness=85,
                evidence="Candidate demonstrated good understanding.",
                strengths=["Clear explanation"],
                weaknesses=["Missed edge cases"],
                recommended_follow_up="What about concurrency?",
                confidence=0.9
            ), telemetry
        elif schema == CodeEvaluation:
            return CodeEvaluation(
                overall_score=80,
                correctness=100,
                algorithm_quality=75,
                complexity="O(N)",
                code_quality=80,
                readability=80,
                edge_case_coverage=70,
                testability=80,
                strengths=["Works correctly"],
                issues=["Not optimal space"],
                recommendations=["Use in-place swap"],
                confidence=0.95
            ), telemetry
        elif schema == Question:
            return Question(
                question_text="Explain React hooks?",
                question_type="technical",
                domain="frontend",
                skill_tags=["react"],
                difficulty="intermediate",
                expected_reasoning="Understanding of state lifecycle.",
                evaluation_rubric="Score on clarity.",
                follow_up_axes=["useEffect details"]
            ), telemetry
        
        raise NotImplementedError(f"Schema {schema} not mocked")

    def get_metadata(self):
        return {"provider": "mock-ai", "model_name": "mock-1.0"}

FIXTURES = {
    "technical": {
        "strong": "React hooks allow you to use state and other React features without writing a class. useState is for local state, and useEffect handles side effects...",
        "weak": "Hooks are things in React that make it work better. I use them sometimes.",
        "ambiguous": "React uses hooks for state management like Redux."
    },
    "behavioral": {
        "strong": "When a team member disagreed, I scheduled a 1-on-1 to understand their perspective. We found a compromise by blending our approaches, which improved the final design.",
        "weak": "I just did what the manager said.",
        "ambiguous": "We argued a lot but eventually the project finished on time."
    },
    "coding": {
        "strong": "def two_sum(nums, target):\n    seen = {}\n    for i, num in enumerate(nums):\n        diff = target - num\n        if diff in seen:\n            return [seen[diff], i]\n        seen[num] = i\n    return []",
        "weak": "def two_sum(n, t):\n    for i in range(len(n)):\n        for j in range(len(n)):\n            if n[i]+n[j]==t: return [i,j]",
        "ambiguous": "function solve(arr, k) { return arr.filter(x => x < k); }"
    }
}

def test_engine_evaluate_answer_schema_validity_and_completeness():
    engine = AssessmentEngine(provider=MockProvider())
    
    # Test Strong Technical Answer
    result = engine.evaluate_answer(
        question="Explain React Hooks", 
        answer=FIXTURES["technical"]["strong"]
    )
    
    assert "overall_score" in result
    assert result["overall_score"] == 85
    assert result["_metadata"]["model"] == "mock-ai"
    assert result["_metadata"]["schema_validation"] is True
    assert result["_metadata"]["input_tokens"] == 150

def test_engine_evaluate_code_schema():
    engine = AssessmentEngine(provider=MockProvider())
    result = engine.evaluate_code(
        code=FIXTURES["coding"]["strong"], 
        language="python", 
        question="Two Sum"
    )
    
    assert result["correctness"] == 100
    assert result["_metadata"]["task_type"] == "evaluate_code"

def test_engine_graceful_model_failure():
    engine = AssessmentEngine(provider=MockProvider(mode="fail"))
    
    with pytest.raises(RuntimeError) as exc_info:
        engine.evaluate_answer(
            question="Explain React Hooks", 
            answer=FIXTURES["technical"]["weak"]
        )
        
    assert "AI Generation Failed" in str(exc_info.value)
    assert "Model validation failed" in str(exc_info.value)

def test_engine_follow_up_generation():
    engine = AssessmentEngine(provider=MockProvider())
    
    eval_mock = {
        "weaknesses": ["Missed edge cases"]
    }
    
    result = engine.generate_follow_up_question(
        original_question="Explain React Hooks",
        candidate_answer=FIXTURES["technical"]["weak"],
        evaluation=eval_mock,
        weakness="Missed edge cases"
    )
    
    assert result["question_text"] == "Explain React hooks?"
    assert result["_metadata"]["task_type"] == "generate_follow_up_question"
