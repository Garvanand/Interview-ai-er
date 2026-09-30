import uuid
import logging
from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone

from app.services.orchestrator.intelligence import CandidateSkillProfile

logger = logging.getLogger(__name__)

class RecommendationStrategy(str, Enum):
    NEXT_INTERVIEW = "next_interview"
    PRACTICE_SESSION = "practice_session"
    SKILL_REINFORCEMENT = "skill_reinforcement"
    WEAK_SIGNAL_VALIDATION = "weak_signal_validation"
    REVIEW_PRIOR_MISTAKES = "review_prior_mistakes"

class RecommendationPriority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class RecommendationStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    COMPLETED = "COMPLETED"
    DISMISSED = "DISMISSED"

class Recommendation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    session_id: Optional[str] = None
    target_skill: str
    strategy: RecommendationStrategy
    reason: str
    evidence: Dict[str, Any] = Field(default_factory=dict)
    recommended_activity: Dict[str, Any] = Field(default_factory=dict)
    priority: RecommendationPriority
    expected_learning_objective: str
    status: RecommendationStatus = RecommendationStatus.PENDING
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    baseline_proficiency: float = 0.0
    post_outcome_proficiency: Optional[float] = None
    outcome_delta: Optional[float] = None
    outcome_assessment: Optional[str] = None  # "improved", "declined", "unchanged", "pending"


class RecommendationEngine:
    """
    Personalized recommendation engine running on top of the Candidate Skill Intelligence layer.
    Transforms evidence and evaluation signals into explainable, non-generic next actions.
    """

    PRIORITY_WEIGHTS = {
        RecommendationPriority.CRITICAL: 4,
        RecommendationPriority.HIGH: 3,
        RecommendationPriority.MEDIUM: 2,
        RecommendationPriority.LOW: 1
    }

    def generate_recommendations(
        self,
        user_id: str,
        skill_profiles: List[CandidateSkillProfile],
        session_questions: Optional[List[Dict[str, Any]]] = None,
        session_id: Optional[str] = None
    ) -> List[Recommendation]:
        """
        Synthesize longitudinal skill intelligence and granular interaction evaluations
        to generate prioritized, explainable recommendations across all five core strategies:
          1. Next Interview
          2. Practice Session
          3. Skill Reinforcement
          4. Weak-Signal Validation
          5. Review of Prior Mistakes
        """
        recommendations: List[Recommendation] = []
        profiles_by_skill = {p.skill_name: p for p in skill_profiles}
        session_questions = session_questions or []

        # -------------------------------------------------------------------------
        # Strategy A: Question-Level Interaction & Evaluation Disconnects
        # -------------------------------------------------------------------------
        for q in session_questions:
            q_id = q.get('id', 'unknown')
            q_text = q.get('question_text', '')
            eval_score = q.get('evaluation_score') or q.get('code_evaluation_score') or 0.0
            eval_details = q.get('evaluation_details') or q.get('code_evaluation_details') or {}
            is_code = bool(q.get('code_text') or q.get('code_evaluation_score'))

            # Case 1: Review Prior Mistakes (Severe mistakes or failed questions)
            if eval_score < 55.0 and eval_score > 0.0:
                issues = eval_details.get('issues') or eval_details.get('weaknesses') or ["General solution deficiencies"]
                skill_tag = q.get('interview_type') or "Problem Solving"
                baseline_prof = profiles_by_skill[skill_tag].estimated_proficiency if skill_tag in profiles_by_skill else eval_score

                recommendations.append(Recommendation(
                    user_id=user_id,
                    session_id=session_id,
                    target_skill=skill_tag,
                    strategy=RecommendationStrategy.REVIEW_PRIOR_MISTAKES,
                    reason=f"Candidate scored {eval_score}/100 on question '{q_text[:60]}...' with identified issues: {', '.join(issues[:2])}.",
                    evidence={
                        'question_id': q_id,
                        'question_text': q_text,
                        'score': eval_score,
                        'issues_identified': issues[:3]
                    },
                    recommended_activity={
                        'type': 'mistake_remediation',
                        'title': f"Guided Bug & Remediation Review: {skill_tag}",
                        'problem_context': q_text,
                        'remediation_steps': [
                            "Perform step-by-step invariant trace to locate failure point",
                            "Identify unhandled boundary conditions or edge cases",
                            "Re-implement corrected solution without looking at previous attempt"
                        ]
                    },
                    priority=RecommendationPriority.HIGH,
                    expected_learning_objective=f"Identify root cause of failure on '{q_text[:40]}' and implement verified edge-case validation.",
                    baseline_proficiency=baseline_prof
                ))

            # Case 2: Strong coding correctness but weak explanation
            if is_code:
                correctness = eval_details.get('correctness', 0)
                readability = eval_details.get('readability', 100)
                code_quality = eval_details.get('code_quality', 100)
                # Check if implementation succeeded but communication/conceptual depth was lacking
                explanation_score = (readability + code_quality) / 2.0
                if correctness >= 75 and explanation_score < 60:
                    comm_prof = profiles_by_skill.get("Communication", CandidateSkillProfile(user_id=user_id, skill_name="Communication")).estimated_proficiency
                    recommendations.append(Recommendation(
                        user_id=user_id,
                        session_id=session_id,
                        target_skill="Communication",
                        strategy=RecommendationStrategy.NEXT_INTERVIEW,
                        reason=f"Candidate demonstrated high coding correctness ({correctness}/100) but low code clarity and explanation score ({round(explanation_score, 1)}/100).",
                        evidence={
                            'question_id': q_id,
                            'correctness': correctness,
                            'explanation_score': explanation_score,
                            'readability': readability,
                            'code_quality': code_quality
                        },
                        recommended_activity={
                            'type': 'interview_session',
                            'title': "Architectural Walkthrough & Invariant Explanation Interview",
                            'domain': 'Communication & Code Articulation',
                            'focus_areas': [
                                "Explain code structure before typing",
                                "Verbalize state transitions and invariants",
                                "Structured defense of architectural trade-offs"
                            ]
                        },
                        priority=RecommendationPriority.HIGH,
                        expected_learning_objective="Articulate data structures, state invariants, and execution flows clearly to an engineering peer during live coding.",
                        baseline_proficiency=comm_prof
                    ))

            # Case 3: Strong implementation but poor complexity analysis
            if is_code:
                correctness = eval_details.get('correctness', 0)
                complexity_analysis = str(eval_details.get('complexity', '')).lower()
                issues = [str(i).lower() for i in (eval_details.get('issues') or [])]
                has_complexity_issue = any("complexity" in issue or "o(n" in issue or "space" in issue or "time" in issue for issue in issues)

                if correctness >= 75 and (has_complexity_issue or "suboptimal" in complexity_analysis or "poor" in complexity_analysis):
                    dsa_prof = profiles_by_skill.get("Data Structures & Algorithms", CandidateSkillProfile(user_id=user_id, skill_name="Data Structures & Algorithms")).estimated_proficiency
                    recommendations.append(Recommendation(
                        user_id=user_id,
                        session_id=session_id,
                        target_skill="Data Structures & Algorithms",
                        strategy=RecommendationStrategy.PRACTICE_SESSION,
                        reason=f"Candidate solved code logic ({correctness}/100) but exhibited deficiencies in asymptotic complexity analysis or selected suboptimal Big-O bounds.",
                        evidence={
                            'question_id': q_id,
                            'correctness': correctness,
                            'complexity_analysis': eval_details.get('complexity'),
                            'complexity_related_issues': [i for i in issues if 'complexity' in i or 'o(n' in i or 'space' in i]
                        },
                        recommended_activity={
                            'type': 'complexity_drill',
                            'title': "Targeted Asymptotic Complexity & Space-Time Trade-off Drill",
                            'topics': ["Master Theorem", "Recurrence Relations", "Auxiliary Space vs Stack Frame Allocation"],
                            'sample_exercises': [
                                "Differentiate between worst-case and amortized time bounds",
                                "Optimize O(N^2) quadratic nested loops to O(N log N) or O(N)"
                            ]
                        },
                        priority=RecommendationPriority.MEDIUM,
                        expected_learning_objective="Accurately compute rigorous Big-O time and auxiliary space bounds across iterative and recursive paradigms.",
                        baseline_proficiency=dsa_prof
                    ))

        # -------------------------------------------------------------------------
        # Strategy B: Longitudinal Skill Intelligence Analysis
        # -------------------------------------------------------------------------
        for skill_name, profile in profiles_by_skill.items():
            prof = profile.estimated_proficiency
            count = profile.evidence_count
            trend = profile.improvement_trend
            conf = profile.confidence

            # Case 4: Weak algorithmic reasoning
            if ("algorithm" in skill_name.lower() or skill_name == "Data Structures & Algorithms") and prof < 60.0 and count >= 1:
                recommendations.append(Recommendation(
                    user_id=user_id,
                    session_id=session_id,
                    target_skill=skill_name,
                    strategy=RecommendationStrategy.PRACTICE_SESSION,
                    reason=f"Longitudinal algorithmic proficiency is weak ({prof}/100) across {count} evaluated signals with {trend} trend.",
                    evidence={
                        'estimated_proficiency': prof,
                        'evidence_count': count,
                        'recent_performance': profile.recent_performance,
                        'historical_performance': profile.historical_performance,
                        'trend': trend
                    },
                    recommended_activity={
                        'type': 'targeted_practice',
                        'title': "Algorithmic Pattern Drills: Data Structures & Core Recursion",
                        'difficulty': 'intermediate' if prof >= 40 else 'beginner',
                        'recommended_modules': [
                            "Two-pointer & sliding window invariants",
                            "Binary tree traversal & recursive reduction",
                            "Dynamic programming state-transition modeling"
                        ]
                    },
                    priority=RecommendationPriority.HIGH,
                    expected_learning_objective="Formulate correct state transitions and recursive invariants on intermediate algorithmic problems.",
                    baseline_proficiency=prof
                ))

            # Case 5: Repeated weakness in system design
            if "system design" in skill_name.lower() and prof < 60.0:
                is_repeated = count >= 2
                recommendations.append(Recommendation(
                    user_id=user_id,
                    session_id=session_id,
                    target_skill=skill_name,
                    strategy=RecommendationStrategy.PRACTICE_SESSION,
                    reason=(
                        f"Repeated deficiency in System Design ({prof}/100 across {count} sessions) indicating difficulty with architectural tradeoffs."
                        if is_repeated else
                        f"Initial System Design evaluation indicates low proficiency ({prof}/100)."
                    ),
                    evidence={
                        'estimated_proficiency': prof,
                        'evidence_count': count,
                        'is_repeated': is_repeated,
                        'recent_performance': profile.recent_performance,
                        'trend': trend
                    },
                    recommended_activity={
                        'type': 'progressive_system_design',
                        'title': "System Design Progressive Mastery Drill",
                        'progression_stages': [
                            "Stage 1: Capacity estimation & Single-node bottlenecks",
                            "Stage 2: Caching hierarchies (Redis/Memcached) and CDN offloading",
                            "Stage 3: Data partitioning (sharding) & consensus protocols"
                        ]
                    },
                    priority=RecommendationPriority.CRITICAL if is_repeated else RecommendationPriority.HIGH,
                    expected_learning_objective="Design scalable, fault-tolerant distributed topologies with explicit partition tolerance, cache invalidation, and replication strategies.",
                    baseline_proficiency=prof
                ))

            # Case 6: Skill Reinforcement (High proficiency skills with steady or improving trend)
            if prof >= 75.0 and count >= 2 and trend in ("improving", "stable"):
                recommendations.append(Recommendation(
                    user_id=user_id,
                    session_id=session_id,
                    target_skill=skill_name,
                    strategy=RecommendationStrategy.SKILL_REINFORCEMENT,
                    reason=f"Strong performance demonstrated in {skill_name} ({prof}/100 across {count} evaluations, trend: {trend}). Reinforce to achieve Staff-level mastery.",
                    evidence={
                        'estimated_proficiency': prof,
                        'evidence_count': count,
                        'trend': trend,
                        'recent_performance': profile.recent_performance
                    },
                    recommended_activity={
                        'type': 'advanced_challenge',
                        'title': f"Staff-Level Deep Dive: {skill_name}",
                        'difficulty': 'advanced',
                        'focus': "Extreme boundary edge cases, high concurrency contention, and fault-injection scenarios"
                    },
                    priority=RecommendationPriority.LOW,
                    expected_learning_objective=f"Cement advanced domain competence in {skill_name} by solving ambiguous, production-grade failure scenarios.",
                    baseline_proficiency=prof
                ))

            # Case 7: Weak-Signal Validation (Insufficient evidence)
            if count <= 2 or conf in ("insufficient evidence", "low confidence"):
                recommendations.append(Recommendation(
                    user_id=user_id,
                    session_id=session_id,
                    target_skill=skill_name,
                    strategy=RecommendationStrategy.WEAK_SIGNAL_VALIDATION,
                    reason=f"Signal for {skill_name} has low confidence ({count} evidence points recorded, model confidence: '{conf}'). Additional targeted validation is required.",
                    evidence={
                        'evidence_count': count,
                        'model_confidence': conf,
                        'estimated_proficiency': prof
                    },
                    recommended_activity={
                        'type': 'diagnostic_assessment',
                        'title': f"Targeted Diagnostic Assessment: {skill_name}",
                        'num_questions': 3,
                        'coverage': f"Multi-angle evaluation of core fundamentals in {skill_name}"
                    },
                    priority=RecommendationPriority.MEDIUM,
                    expected_learning_objective=f"Gather sufficient empirical signal to elevate model confidence in {skill_name} from '{conf}' to 'medium confidence' or 'high confidence'.",
                    baseline_proficiency=prof
                ))

        # -------------------------------------------------------------------------
        # Strategy C: Next Interview Strategy (If no specific interview recommendation was generated)
        # -------------------------------------------------------------------------
        has_next_interview_rec = any(r.strategy == RecommendationStrategy.NEXT_INTERVIEW for r in recommendations)
        if not has_next_interview_rec:
            # Find the lowest performing skill with sufficient evidence to focus the next interview
            candidate_weak_skills = [
                p for p in skill_profiles
                if p.estimated_proficiency < 70.0 and p.evidence_count >= 1
            ]
            if candidate_weak_skills:
                weakest = min(candidate_weak_skills, key=lambda x: x.estimated_proficiency)
                recommendations.append(Recommendation(
                    user_id=user_id,
                    session_id=session_id,
                    target_skill=weakest.skill_name,
                    strategy=RecommendationStrategy.NEXT_INTERVIEW,
                    reason=f"Candidate's lowest assessed skill is {weakest.skill_name} ({weakest.estimated_proficiency}/100). The upcoming interview should directly test growth in this focus area.",
                    evidence={
                        'target_skill': weakest.skill_name,
                        'estimated_proficiency': weakest.estimated_proficiency,
                        'evidence_count': weakest.evidence_count,
                        'trend': weakest.improvement_trend
                    },
                    recommended_activity={
                        'type': 'orchestrated_interview',
                        'title': f"Focused Technical Interview: {weakest.skill_name}",
                        'target_skill': weakest.skill_name,
                        'suggested_difficulty': 'intermediate' if weakest.estimated_proficiency >= 45 else 'beginner'
                    },
                    priority=RecommendationPriority.HIGH,
                    expected_learning_objective=f"Demonstrate measurable improvement in {weakest.skill_name} under timed interview conditions.",
                    baseline_proficiency=weakest.estimated_proficiency
                ))
            elif skill_profiles:
                # Balanced candidate: recommend full simulation
                top_skill = max(skill_profiles, key=lambda x: x.estimated_proficiency)
                recommendations.append(Recommendation(
                    user_id=user_id,
                    session_id=session_id,
                    target_skill="Full Loop Simulation",
                    strategy=RecommendationStrategy.NEXT_INTERVIEW,
                    reason="Candidate has solid baseline proficiency across assessed skills. Next step is a full-loop comprehensive simulation.",
                    evidence={'overall_profiles_count': len(skill_profiles)},
                    recommended_activity={
                        'type': 'full_loop_simulation',
                        'title': "Comprehensive Full-Loop Mock Interview",
                        'difficulty': 'advanced'
                    },
                    priority=RecommendationPriority.MEDIUM,
                    expected_learning_objective="Sustain high technical execution and clear communication across a full 5-question multi-domain panel.",
                    baseline_proficiency=top_skill.estimated_proficiency
                ))
            else:
                # Brand new candidate with zero profiles: recommend initial diagnostic interview
                recommendations.append(Recommendation(
                    user_id=user_id,
                    session_id=session_id,
                    target_skill="Core Problem Solving",
                    strategy=RecommendationStrategy.NEXT_INTERVIEW,
                    reason="No previous assessment data or skill profiles found for candidate. An initial diagnostic interview is recommended to establish an authoritative baseline.",
                    evidence={'status': 'initial_candidate_onboarding', 'evidence_count': 0},
                    recommended_activity={
                        'type': 'diagnostic_interview',
                        'title': "Initial Baseline Diagnostic Technical Interview",
                        'difficulty': 'intermediate',
                        'target_role': 'Software Engineer'
                    },
                    priority=RecommendationPriority.HIGH,
                    expected_learning_objective="Establish verified empirical signals across algorithms, system design, and communication to seed personalized recommendation models.",
                    baseline_proficiency=0.0
                ))

        # -------------------------------------------------------------------------
        # Deduplication and Priority Sorting
        # -------------------------------------------------------------------------
        deduped: List[Recommendation] = []
        seen_keys = set()
        for rec in recommendations:
            key = (rec.strategy, rec.target_skill, rec.recommended_activity.get('title'))
            if key not in seen_keys:
                seen_keys.add(key)
                deduped.append(rec)

        # Sort descending by priority weight
        deduped.sort(
            key=lambda r: self.PRIORITY_WEIGHTS.get(r.priority, 0),
            reverse=True
        )

        return deduped

    def evaluate_outcome(
        self,
        recommendation: Recommendation,
        current_proficiency: float
    ) -> Recommendation:
        """
        Evaluate and record the outcome of a recommendation after subsequent candidate activity.
        Computes the delta between post-activity proficiency and baseline proficiency.
        """
        delta = round(current_proficiency - recommendation.baseline_proficiency, 2)
        recommendation.post_outcome_proficiency = current_proficiency
        recommendation.outcome_delta = delta
        recommendation.completed_at = datetime.now(timezone.utc).isoformat()
        recommendation.status = RecommendationStatus.COMPLETED

        if delta >= 5.0:
            recommendation.outcome_assessment = "improved"
        elif delta <= -5.0:
            recommendation.outcome_assessment = "declined"
        else:
            recommendation.outcome_assessment = "unchanged"

        return recommendation
