import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import json

from .providers.base import AIProvider
from .schemas import AnswerEvaluation, CodeEvaluation, Question, SkillExtraction, SessionSynthesis

logger = logging.getLogger(__name__)

class AssessmentEngine:
    def __init__(self, provider: AIProvider):
        self.provider = provider
        self.interview_types = {
            'technical': 'Technical programming and computer science questions',
            'behavioral': 'Soft skills and behavioral questions',
            'system_design': 'System architecture and design questions',
            'coding': 'Practical coding problems and algorithms'
        }

    def _execute_with_telemetry(self, prompt: str, schema: type) -> Dict[str, Any]:
        """Executes a generation task and wraps it with latency and metadata."""
        start_time = time.time()
        
        try:
            result = self.provider.generate_structured(prompt, schema)
            status = "success"
            error = None
            # Convert pydantic model to dict
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
            "status": status
        })
        
        if error:
            metadata["error"] = error
            # Never invent a score when model fails. Bubble up failure safely.
            raise RuntimeError(f"AI Generation Failed: {error}")
            
        return {
            "data": data,
            "metadata": metadata
        }

    def generate_question(self, interview_type: str, difficulty: str = 'medium', topic: Optional[str] = None) -> Dict[str, Any]:
        """Generate an interview question using the constrained schema."""
        context = f"Topic: {topic}" if topic else f"Interview Type: {self.interview_types.get(interview_type, interview_type)}"
        
        prompt = f"""
        Generate a {difficulty} difficulty interview question.
        
        Requirements:
        - Question should be clear and specific
        - Include context and constraints if applicable
        - Difficulty should strictly match {difficulty} level
        - Describe expected reasoning and rubric clearly
        
        Context:
        {context}
        """
        
        response = self._execute_with_telemetry(prompt, Question)
        return {**response["data"], "_metadata": response["metadata"]}

    def evaluate_answer(self, question: str, answer: str, question_type: str = 'technical') -> Dict[str, Any]:
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

    def generate_follow_up_question(self, original_question: str, candidate_answer: str, evaluation: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a follow up question based on previous answer."""
        prompt = f"""
        Based on this question and the candidate's answer, generate a single follow-up question that probes deeper into their weaknesses or tests their limits on the topic.
        
        Original Question: {original_question}
        Candidate Answer: {candidate_answer}
        Evaluation Notes: {evaluation.get('weaknesses', [])}
        
        Generate a single follow up question in the same format.
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
