"""
Assessment engine — orchestrates structured AI prompts with telemetry and retry safety.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.ai.providers.base import AIProvider
from app.ai.schemas import (
    AnswerEvaluation,
    CodeEvaluation,
    Question,
    SessionSynthesis,
    SkillExtraction,
)

logger = logging.getLogger(__name__)


class AssessmentEngine:
    def __init__(self, provider: AIProvider):
        self.provider = provider
        self.interview_types = {
            "technical": "Technical programming and computer science questions",
            "behavioral": "Soft skills and behavioral questions",
            "system_design": "System architecture and design questions",
            "coding": "Practical coding problems and algorithms",
            "Software Engineer": "Software engineering fundamentals and architecture",
            "Data Scientist": "Machine learning, statistical analysis, and data modeling",
            "Product Manager": "Product strategy, user empathy, and technical tradeoffs",
            "DevOps Engineer": "CI/CD, container orchestration, and reliability engineering",
        }

    def _execute_with_telemetry(self, prompt: str, schema: type) -> Dict[str, Any]:
        """Executes a generation task and wraps it with latency and metadata."""
        start_time = time.time()

        try:
            result = self.provider.generate_structured(prompt, schema)
            status = "success"
            error = None
            data = result.model_dump()
        except Exception as e:
            status = "failed"
            error = str(e)
            data = None

        latency = time.time() - start_time

        metadata = self.provider.get_metadata()
        metadata.update({
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "latency_seconds": round(latency, 3),
            "status": status,
        })

        if error:
            metadata["error"] = error
            raise RuntimeError(f"AI Generation Failed: {error}")

        return {
            "data": data,
            "metadata": metadata,
        }

    def generate_question(
        self,
        interview_type: str,
        difficulty: str = "intermediate",
        topic: Optional[str] = None,
        skill_focus: Optional[str] = None,
        target_role: Optional[str] = None,
        excluded_questions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Generate an interview question using the constrained schema with duplicate prevention."""
        context_parts = []
        if target_role:
            context_parts.append(f"Target Role: {target_role}")
        if skill_focus:
            context_parts.append(f"Core Skill Focus: {skill_focus}")
        if topic:
            context_parts.append(f"Topic: {topic}")
        context_parts.append(f"Interview Type: {self.interview_types.get(interview_type, interview_type)}")

        context = "\n".join(context_parts)

        exclusions_text = ""
        if excluded_questions:
            exclusions_list = "\n".join([f"- {q}" for q in excluded_questions[-10:]])
            exclusions_text = f"\nCRITICAL: Avoid asking any of the following questions or variations:\n{exclusions_list}\n"

        prompt = f"""
        Generate a {difficulty} difficulty interview question.

        Requirements:
        - Question should be clear, specific, and realistic for a real tech interview
        - Tailor the question specifically to the Skill Focus and Target Role
        - Include context and constraints if applicable
        - Difficulty should strictly match {difficulty} level
        - Describe expected reasoning and rubric clearly
        {exclusions_text}
        Context:
        {context}
        """

        response = self._execute_with_telemetry(prompt, Question)
        return {**response["data"], "_metadata": response["metadata"]}

    def evaluate_answer(self, question: str, answer: str, question_type: str = "technical") -> Dict[str, Any]:
        """Evaluate a text answer and provide detailed feedback."""
        prompt = f"""
        Evaluate this interview answer for a {question_type} question.

        Question: {question}
        Answer: {answer}

        You are an expert technical interviewer. Score the answer out of 100 on multiple axes.
        Provide constructive feedback, strengths, and weaknesses. Be honest and critical.
        """

        response = self._execute_with_telemetry(prompt, AnswerEvaluation)
        return {**response["data"], "_metadata": response["metadata"]}

    def evaluate_code(self, code: str, language: str, question: str) -> Dict[str, Any]:
        """Evaluate a code submission."""
        prompt = f"""
        Evaluate this {language} code submission for the following question:

        Question: {question}
        Code:
        ```{language}
        {code}
        ```

        Analyze correctness, time/space complexity, and code quality.
        Identify strengths and issues. Provide actionable recommendations.
        """

        response = self._execute_with_telemetry(prompt, CodeEvaluation)
        return {**response["data"], "_metadata": response["metadata"]}

    def generate_follow_up_question(
        self,
        original_question: str,
        candidate_answer: str,
        evaluation: Dict[str, Any],
        weakness: Optional[str] = None,
        skill_focus: Optional[str] = None,
        difficulty: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a targeted follow-up question based on previous answer and specific weakness."""
        targeted_clause = ""
        if weakness:
            targeted_clause += f"\nSpecific weakness to probe: {weakness}"
        if skill_focus:
            targeted_clause += f"\nSkill focus: {skill_focus}"
        if difficulty:
            targeted_clause += f"\nTarget difficulty: {difficulty}"

        prompt = f"""
        Based on this interview exchange, generate a targeted follow-up question.

        Original Question: {original_question}
        Candidate Answer: {candidate_answer}
        Identified Weaknesses: {evaluation.get('weaknesses', [])}
        {targeted_clause}

        Instructions:
        - Directly challenge the candidate on their gap or incomplete reasoning.
        - Do NOT ask a generic question like "Can you explain more?".
        - Ask a concrete scenario, tradeoff, or edge case testing the exact weakness.
        """
        response = self._execute_with_telemetry(prompt, Question)
        return {**response["data"], "_metadata": response["metadata"]}

    def extract_skills(self, session_transcript: str) -> Dict[str, Any]:
        """Extract candidate skills from a session transcript."""
        prompt = f"""
        Analyze this interview session transcript and extract demonstrated skills:

        Transcript:
        {session_transcript}

        Identify both technical and soft skills, assign a score out of 100 for each, and provide evidence.
        """

        response = self._execute_with_telemetry(prompt, SkillExtraction)
        return {**response["data"], "_metadata": response["metadata"]}

    def synthesize_session(self, session_data: str) -> Dict[str, Any]:
        """Synthesize overall session results."""
        prompt = f"""
        Based on the following interview session data, synthesize an overall assessment:

        Data:
        {session_data}

        Provide an overall rating, a comprehensive summary, strengths, and red flags.
        """

        response = self._execute_with_telemetry(prompt, SessionSynthesis)
        return {**response["data"], "_metadata": response["metadata"]}
