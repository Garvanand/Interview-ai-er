"""
Pydantic schemas for structured AI generation and evaluation.
"""
from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class AnswerEvaluation(BaseModel):
    overall_score: int = Field(description="Score out of 100")
    technical_accuracy: int = Field(description="Score out of 100 for technical accuracy")
    conceptual_depth: int = Field(description="Score out of 100 for conceptual depth")
    problem_solving: int = Field(description="Score out of 100 for problem solving")
    communication: int = Field(description="Score out of 100 for communication clarity")
    completeness: int = Field(description="Score out of 100 for answer completeness")
    evidence: str = Field(description="Summary of evidence for the scoring")
    strengths: List[str] = Field(description="List of strengths in the answer")
    weaknesses: List[str] = Field(description="List of areas for improvement")
    recommended_follow_up: str = Field(description="Suggested follow-up question based on the answer")
    confidence: float = Field(description="Confidence in evaluation from 0.0 to 1.0")
    uncertainty_notes: Optional[str] = Field(default=None, description="Any notes on why evaluation might be uncertain")


class CodeEvaluation(BaseModel):
    overall_score: int = Field(description="Score out of 100")
    correctness: int = Field(description="Score out of 100 for logic correctness")
    algorithm_quality: int = Field(description="Score out of 100 for algorithmic choices")
    complexity: str = Field(description="Time and space complexity analysis")
    code_quality: int = Field(description="Score out of 100 for clean code structure")
    readability: int = Field(description="Score out of 100 for readability")
    edge_case_coverage: int = Field(description="Score out of 100 for handling edge cases")
    testability: int = Field(description="Score out of 100 for testability")
    strengths: List[str] = Field(description="List of strengths in the code")
    issues: List[str] = Field(description="List of bugs or issues found")
    recommendations: List[str] = Field(description="Actionable recommendations to improve")
    confidence: float = Field(description="Confidence in evaluation from 0.0 to 1.0")


class Question(BaseModel):
    question_text: str = Field(description="The full text of the interview question")
    question_type: str = Field(description="E.g., technical, behavioral, system_design, coding")
    domain: str = Field(description="Domain of the question, e.g., frontend, backend, database")
    skill_tags: List[str] = Field(description="List of specific skills assessed")
    difficulty: str = Field(description="Difficulty level: beginner, intermediate, advanced")
    expected_reasoning: str = Field(description="What the candidate is expected to demonstrate")
    evaluation_rubric: str = Field(description="Rubric for scoring the answer")
    follow_up_axes: List[str] = Field(description="Potential areas for follow-up questions")


class SkillExtraction(BaseModel):
    demonstrated_skills: List[str] = Field(description="Specific technical or soft skills demonstrated")
    skill_levels: Dict[str, int] = Field(description="Mapping of skill to a score out of 100")
    evidence: str = Field(description="Textual evidence supporting these extracted skills")


class SessionSynthesis(BaseModel):
    overall_rating: str = Field(description="Overall rating e.g., Strong Hire, Hire, Leaning Hire, No Hire")
    summary: str = Field(description="Comprehensive summary of candidate performance")
    key_strengths: List[str] = Field(description="Top strengths across the session")
    red_flags: List[str] = Field(description="Any critical concerns")
