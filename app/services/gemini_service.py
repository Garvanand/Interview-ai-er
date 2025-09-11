import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import google.generativeai as genai

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        genai.configure(api_key=self.api_key)
        self.model = None
        self.interview_types = {
            'technical': 'Technical programming and computer science questions',
            'behavioral': 'Soft skills and behavioral questions',
            'system_design': 'System architecture and design questions',
            'coding': 'Practical coding problems and algorithms'
        }

    def _get_model(self):
        """Lazy initialization of Gemini model"""
        if self.model is None:
            try:
                self.model = genai.GenerativeModel('gemini-1.5-pro')
                logger.info("Gemini model initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini model: {e}")
                raise
        return self.model

    def generate_question(self, interview_type: str, difficulty: str = 'medium') -> Dict[str, Any]:
        """Generate an interview question based on type and difficulty"""
        try:
            model = self._get_model()
            
            prompt = f"""
            Generate a {difficulty} difficulty {interview_type} interview question.
            
            Requirements:
            - Question should be clear and specific
            - Include context and constraints if applicable
            - Provide expected answer format
            - Difficulty should match {difficulty} level
            
            Interview Type: {self.interview_types.get(interview_type, interview_type)}
            
            Return the response in this exact JSON format:
            {{
                "question": "The actual question text",
                "type": "{interview_type}",
                "difficulty": "{difficulty}",
                "category": "specific category within the type",
                "expected_format": "text, code, diagram, etc.",
                "hints": ["hint1", "hint2"],
                "learning_objectives": ["objective1", "objective2"]
            }}
            """
            
            response = model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Extract JSON from response
            if '```json' in response_text:
                json_start = response_text.find('```json') + 7
                json_end = response_text.find('```', json_start)
                response_text = response_text[json_start:json_end].strip()
            elif '```' in response_text:
                json_start = response_text.find('```') + 3
                json_end = response_text.find('```', json_start)
                response_text = response_text[json_start:json_end].strip()
            
            import json
            question_data = json.loads(response_text)
            
            # Add metadata
            question_data['created_at'] = datetime.now(timezone.utc).isoformat()
            question_data['model_used'] = 'gemini-1.5-pro'
            
            logger.info(f"Generated {interview_type} question successfully")
            return question_data
            
        except Exception as e:
            logger.error(f"Failed to generate question: {e}")
            # Return fallback question
            return {
                "question": f"Explain the key concepts of {interview_type} and provide examples.",
                "type": interview_type,
                "difficulty": difficulty,
                "category": "general",
                "expected_format": "text",
                "hints": ["Think about fundamental principles", "Consider practical applications"],
                "learning_objectives": ["Understand core concepts", "Apply knowledge practically"],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "model_used": "fallback"
            }

    def evaluate_answer(self, question: str, answer: str, question_type: str = 'technical') -> Dict[str, Any]:
        """Evaluate an answer and provide detailed feedback"""
        try:
            model = self._get_model()
            
            prompt = f"""
            Evaluate this interview answer for a {question_type} question.
            
            Question: {question}
            Answer: {answer}
            
            Provide a comprehensive evaluation in this exact JSON format:
            {{
                "score": 85,
                "feedback": "Overall good answer with room for improvement",
                "strengths": ["Clear explanation", "Good examples"],
                "improvements": ["Add more technical details", "Include edge cases"],
                "technical_accuracy": 80,
                "clarity": 90,
                "completeness": 75,
                "specificity": 85,
                "recommendations": ["Study related concepts", "Practice similar problems"]
            }}
            
            Scoring criteria:
            - Score: 0-100 overall
            - Technical accuracy: 0-100
            - Clarity: 0-100
            - Completeness: 0-100
            - Specificity: 0-100
            """
            
            response = model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Extract JSON from response
            if '```json' in response_text:
                json_start = response_text.find('```json') + 7
                json_end = response_text.find('```', json_start)
                response_text = response_text[json_start:json_end].strip()
            elif '```' in response_text:
                json_start = response_text.find('```') + 3
                json_end = response_text.find('```', json_start)
                response_text = response_text[json_start:json_end].strip()
            
            import json
            evaluation = json.loads(response_text)
            
            # Add metadata
            evaluation['evaluated_at'] = datetime.now(timezone.utc).isoformat()
            evaluation['model_used'] = 'gemini-1.5-pro'
            evaluation['question_type'] = question_type
            
            logger.info(f"Answer evaluation completed successfully")
            return evaluation
            
        except Exception as e:
            logger.error(f"Failed to evaluate answer: {e}")
            # Return fallback evaluation
            return {
                "score": 70,
                "feedback": "Answer evaluation failed, using fallback scoring",
                "strengths": ["Answer provided"],
                "improvements": ["Unable to provide specific feedback"],
                "technical_accuracy": 70,
                "clarity": 70,
                "completeness": 70,
                "specificity": 70,
                "recommendations": ["Review the question and answer"],
                "evaluated_at": datetime.now(timezone.utc).isoformat(),
                "model_used": "fallback",
                "question_type": question_type
            }

    def evaluate_code(self, code: str, language: str, question: str) -> Dict[str, Any]:
        """Evaluate code submission and provide detailed analysis"""
        try:
            model = self._get_model()
            
            prompt = f"""
            Evaluate this {language} code submission for the following question:
            
            Question: {question}
            Code:
            ```{language}
            {code}
            ```
            
            Provide a comprehensive code evaluation in this exact JSON format:
            {{
                "score": 85,
                "code_quality": 80,
                "correctness": 90,
                "efficiency": 85,
                "readability": 88,
                "time_complexity": "O(n log n)",
                "space_complexity": "O(n)",
                "feedback": "Good solution with minor improvements possible",
                "strengths": ["Clean code structure", "Efficient algorithm"],
                "improvements": ["Add input validation", "Consider edge cases"],
                "best_practices": 85,
                "test_cases": ["Basic functionality works", "Handles common inputs"],
                "suggestions": ["Add error handling", "Optimize memory usage"]
            }}
            
            Evaluation criteria:
            - Code quality: Code structure, naming, organization
            - Correctness: Does it solve the problem correctly
            - Efficiency: Time and space complexity
            - Readability: Code clarity and maintainability
            - Best practices: Following language conventions
            """
            
            response = model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Extract JSON from response
            if '```json' in response_text:
                json_start = response_text.find('```json') + 7
                json_end = response_text.find('```', json_start)
                response_text = response_text[json_start:json_end].strip()
            elif '```' in response_text:
                json_start = response_text.find('```') + 3
                json_end = response_text.find('```', json_start)
                response_text = response_text[json_start:json_end].strip()
            
            import json
            evaluation = json.loads(response_text)
            
            # Add metadata
            evaluation['evaluated_at'] = datetime.now(timezone.utc).isoformat()
            evaluation['model_used'] = 'gemini-1.5-pro'
            evaluation['language'] = language
            evaluation['code_length'] = len(code)
            
            logger.info(f"Code evaluation completed successfully for {language}")
            return evaluation
            
        except Exception as e:
            logger.error(f"Failed to evaluate code: {e}")
            # Return fallback evaluation
            return {
                "score": 70,
                "code_quality": 70,
                "correctness": 70,
                "efficiency": 70,
                "readability": 70,
                "time_complexity": "Unknown",
                "space_complexity": "Unknown",
                "feedback": "Code evaluation failed, using fallback scoring",
                "strengths": ["Code submitted"],
                "improvements": ["Unable to provide specific feedback"],
                "best_practices": 70,
                "test_cases": ["Basic submission"],
                "suggestions": ["Review the code and question"],
                "evaluated_at": datetime.now(timezone.utc).isoformat(),
                "model_used": "fallback",
                "language": language,
                "code_length": len(code)
            }

    def generate_coding_question(self, topic: str, difficulty: str = 'medium') -> Dict[str, Any]:
        """Generate a coding-specific question"""
        try:
            model = self._get_model()
            
            prompt = f"""
            Generate a {difficulty} difficulty coding question about {topic}.
            
            Requirements:
            - Should be a practical programming problem
            - Include clear problem description
            - Specify input/output format
            - Provide example test cases
            - Include constraints and edge cases
            
            Return the response in this exact JSON format:
            {{
                "question": "Problem description",
                "type": "coding",
                "topic": "{topic}",
                "difficulty": "{difficulty}",
                "input_format": "Description of input format",
                "output_format": "Description of expected output",
                "constraints": ["constraint1", "constraint2"],
                "examples": [
                    {{
                        "input": "example input",
                        "output": "expected output",
                        "explanation": "brief explanation"
                    }}
                ],
                "hints": ["hint1", "hint2"],
                "learning_objectives": ["objective1", "objective2"]
            }}
            """
            
            response = model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Extract JSON from response
            if '```json' in response_text:
                json_start = response_text.find('```json') + 7
                json_end = response_text.find('```', json_start)
                response_text = response_text[json_start:json_end].strip()
            elif '```' in response_text:
                json_start = response_text.find('```') + 3
                json_end = response_text.find('```', json_start)
                response_text = response_text[json_start:json_end].strip()
            
            import json
            question_data = json.loads(response_text)
            
            # Add metadata
            question_data['created_at'] = datetime.now(timezone.utc).isoformat()
            question_data['model_used'] = 'gemini-1.5-pro'
            
            logger.info(f"Generated coding question about {topic} successfully")
            return question_data
            
        except Exception as e:
            logger.error(f"Failed to generate coding question: {e}")
            # Return fallback question
            return {
                "question": f"Implement a solution for a {topic} problem with {difficulty} difficulty.",
                "type": "coding",
                "topic": topic,
                "difficulty": difficulty,
                "input_format": "Standard input format",
                "output_format": "Standard output format",
                "constraints": ["Basic constraints apply"],
                "examples": [
                    {
                        "input": "Sample input",
                        "output": "Sample output",
                        "explanation": "Basic example"
                    }
                ],
                "hints": ["Think about the problem step by step"],
                "learning_objectives": ["Understand the concept", "Apply programming skills"],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "model_used": "fallback"
            }

    def generate_follow_up_question(self, original_question: str, user_answer: str, 
                                  evaluation: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a follow-up question based on user's answer and evaluation"""
        try:
            model = self._get_model()
            
            prompt = f"""
            Based on the user's answer and evaluation, generate a follow-up question.
            
            Original Question: {original_question}
            User Answer: {user_answer}
            Evaluation Score: {evaluation.get('score', 0)}/100
            
            Generate a follow-up question that:
            - Builds on the user's understanding
            - Addresses areas for improvement
            - Maintains appropriate difficulty level
            - Provides learning opportunity
            
            Return the response in this exact JSON format:
            {{
                "question": "Follow-up question text",
                "type": "follow_up",
                "difficulty": "appropriate level",
                "context": "Why this question is relevant",
                "learning_objective": "What this question aims to teach",
                "hints": ["hint1", "hint2"]
            }}
            """
            
            response = model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Extract JSON from response
            if '```json' in response_text:
                json_start = response_text.find('```json') + 7
                json_end = response_text.find('```', json_start)
                response_text = response_text[json_start:json_end].strip()
            elif '```' in response_text:
                json_start = response_text.find('```') + 3
                json_end = response_text.find('```', json_start)
                response_text = response_text[json_start:json_end].strip()
            
            import json
            follow_up = json.loads(response_text)
            
            # Add metadata
            follow_up['created_at'] = datetime.now(timezone.utc).isoformat()
            follow_up['model_used'] = 'gemini-1.5-pro'
            follow_up['original_question_id'] = evaluation.get('question_id', 'unknown')
            
            logger.info("Follow-up question generated successfully")
            return follow_up
            
        except Exception as e:
            logger.error(f"Failed to generate follow-up question: {e}")
            # Return fallback question
            return {
                "question": "Can you elaborate on your previous answer and provide additional examples?",
                "type": "follow_up",
                "difficulty": "medium",
                "context": "Building on your previous response",
                "learning_objective": "Deepen understanding and provide examples",
                "hints": ["Think about related concepts", "Consider edge cases"],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "model_used": "fallback",
                "original_question_id": evaluation.get('question_id', 'unknown')
            }

    def analyze_answer_quality(self, answer: str, question_type: str) -> Dict[str, Any]:
        """Analyze the quality of an answer without full evaluation"""
        try:
            model = self._get_model()
            
            prompt = f"""
            Analyze the quality of this {question_type} answer without providing a full evaluation.
            
            Answer: {answer}
            
            Provide a quick quality analysis in this exact JSON format:
            {{
                "word_count": 150,
                "technical_depth": "high/medium/low",
                "clarity_level": "high/medium/low",
                "completeness": "high/medium/low",
                "structure_quality": "high/medium/low",
                "key_points_count": 5,
                "improvement_areas": ["area1", "area2"]
            }}
            """
            
            response = model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Extract JSON from response
            if '```json' in response_text:
                json_start = response_text.find('```json') + 7
                json_end = response_text.find('```', json_start)
                response_text = response_text[json_start:json_end].strip()
            elif '```' in response_text:
                json_start = response_text.find('```') + 3
                json_end = response_text.find('```', json_start)
                response_text = response_text[json_start:json_end].strip()
            
            import json
            analysis = json.loads(response_text)
            
            # Add metadata
            analysis['analyzed_at'] = datetime.now(timezone.utc).isoformat()
            analysis['model_used'] = 'gemini-1.5-pro'
            
            logger.info("Answer quality analysis completed successfully")
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze answer quality: {e}")
            # Return fallback analysis
            return {
                "word_count": len(answer.split()),
                "technical_depth": "medium",
                "clarity_level": "medium",
                "completeness": "medium",
                "structure_quality": "medium",
                "key_points_count": 3,
                "improvement_areas": ["Unable to analyze"],
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
                "model_used": "fallback"
            }

    def health_check(self) -> Dict[str, Any]:
        """Check the health and status of the Gemini service"""
        try:
            model = self._get_model()
            
            # Test with a simple prompt
            response = model.generate_content("Hello, this is a health check.")
            
            return {
                "status": "healthy",
                "model": "gemini-1.5-pro",
                "api_key_configured": bool(self.api_key),
                "model_accessible": True,
                "last_check": datetime.now(timezone.utc).isoformat(),
                "response_time": "normal"
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "model": "gemini-1.5-pro",
                "api_key_configured": bool(self.api_key),
                "model_accessible": False,
                "last_check": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }
