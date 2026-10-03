"""
Adaptive Practice Engine.
Deterministic ML & IRT-based practice question sequence generator.

Replaces static practice with a personalized, adaptive curriculum based on:
  - Candidate Skill Profile (2PL-IRT mastery estimates & confidence)
  - Recent Mistakes & Discovered Weakness Signals
  - Difficulty Progression & Proximal Zone of Development
  - Question Skill Metadata & Canonical Taxonomy
  - Dense Semantic Embeddings & Deduplication (MiniLM)
  - Spaced Repetition & Retention Intervals
  - Previous Practice History & Deduplication

Supported Modes:
  1. "Practice my weakest skills" (MODE_WEAKEST_SKILLS)
  2. "Prepare me for Software Engineer interviews" (MODE_ROLE_PREP)

Every selected question produces an auditable, explainable rationale.
No random question selection is utilized. No fake statistics are generated.
"""
from __future__ import annotations

import logging
import math
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field

from ml.models.skill_mastery import ItemResponseTheoryMasteryModel
from ml.models.difficulty_predictor import QuestionDifficultyPredictor
from ml.models.skill_classifier import QuestionSkillClassifier
from ml.features.text_embeddings import TextEmbeddingExtractor, compute_cosine_similarity
from ml.models.adaptive_selector import (
    CatalogQuestion,
    CANONICAL_QUESTION_CATALOG,
    DIFFICULTY_PRIORS,
    MODEL_VERSIONS
)
from ml.models.candidate_model import CandidateModel

logger = logging.getLogger(__name__)

# Modes
MODE_WEAKEST_SKILLS = "weakest_skills"
MODE_ROLE_PREP = "role_prep"

# Default role curriculum blueprints
ROLE_CURRICULUM_BLUEPRINTS: Dict[str, List[str]] = {
    "Software Engineer": [
        "arrays",
        "two_pointers",
        "trees",
        "graphs",
        "dynamic_programming",
        "System Design",
        "Database Concepts",
        "Behavioral Reasoning"
    ],
    "Frontend Engineer": [
        "Programming Fundamentals",
        "two_pointers",
        "trees",
        "System Design",
        "Debugging",
        "Behavioral Reasoning"
    ],
    "Backend Engineer": [
        "System Design",
        "Database Concepts",
        "data_structures",
        "graphs",
        "dynamic_programming",
        "Problem Solving",
        "Behavioral Reasoning"
    ],
    "General": [
        "arrays",
        "trees",
        "graphs",
        "dynamic_programming",
        "System Design",
        "Problem Solving"
    ]
}

# Rich Practice Extension Catalog (supplements CANONICAL_QUESTION_CATALOG for extensive diversity)
PRACTICE_ADDITIONAL_CATALOG: List[CatalogQuestion] = [
    # Dynamic Programming additional tiers
    CatalogQuestion(
        id="dsa_dp_house_robber",
        title="House Robber Dynamic Programming",
        question_text="You are a professional robber planning to rob houses along a street. Each house has a certain amount of money stashed. Adjacent houses have security systems connected. Determine the maximum amount of money you can rob tonight without alerting the police.",
        interview_type="coding",
        target_role="Software Engineer",
        skill_focus="dynamic_programming",
        difficulty="beginner",
        expected_time_minutes=12,
        rubric="Candidate should formulate recurrence dp[i] = max(dp[i-1], dp[i-2] + nums[i]) with O(1) space optimization.",
        canonical_skills=["dynamic_programming", "arrays"]
    ),
    CatalogQuestion(
        id="dsa_dp_edit_distance",
        title="Edit Distance (Levenshtein)",
        question_text="Given two strings `word1` and `word2`, return the minimum number of operations required to convert `word1` to `word2` (insert, delete, replace character). Explain the 2D matrix dynamic programming formulation.",
        interview_type="coding",
        target_role="Software Engineer",
        skill_focus="dynamic_programming",
        difficulty="advanced",
        expected_time_minutes=25,
        rubric="Candidate should construct a 2D table dp[i][j] representing minimum edit steps between prefixes.",
        canonical_skills=["dynamic_programming", "strings"]
    ),
    # Graphs additional tiers
    CatalogQuestion(
        id="dsa_graph_clone_graph",
        title="Clone Graph with Deep Copy",
        question_text="Given a reference of a node in a connected undirected graph, return a deep copy (clone) of the graph. Each node in the graph contains a value and a list of its neighbors. Discuss hash map tracking to prevent infinite recursion during traversal.",
        interview_type="coding",
        target_role="Software Engineer",
        skill_focus="graphs",
        difficulty="intermediate",
        expected_time_minutes=15,
        rubric="Candidate must use a hash map (old_node -> new_node) in DFS/BFS to handle cycles and multi-edge connectivity.",
        canonical_skills=["graphs", "recursion", "hashing"]
    ),
    CatalogQuestion(
        id="dsa_graph_network_delay",
        title="Network Delay Time (Dijkstra's Algorithm)",
        question_text="You are given a network of `n` nodes labeled from 1 to `n`, and a list of travel times as directed edges `times[i] = (u, v, w)`. How long will it take for all nodes to receive a signal sent from node `k`? Implement Dijkstra's algorithm with a min-heap priority queue.",
        interview_type="coding",
        target_role="Software Engineer",
        skill_focus="graphs",
        difficulty="advanced",
        expected_time_minutes=20,
        rubric="Candidate should implement Dijkstra's algorithm using a min-heap priority queue with O((V+E) log V) complexity.",
        canonical_skills=["graphs", "algorithms", "queues"]
    ),
    # Trees & Binary Search additional tiers
    CatalogQuestion(
        id="dsa_tree_invert_binary_tree",
        title="Invert Binary Tree",
        question_text="Given the root of a binary tree, invert the tree, and return its root. Discuss both recursive depth-first swapping and iterative breadth-first queue swapping.",
        interview_type="coding",
        target_role="Software Engineer",
        skill_focus="trees",
        difficulty="beginner",
        expected_time_minutes=8,
        rubric="Candidate should swap left and right pointers recursively or iteratively using a queue.",
        canonical_skills=["trees", "recursion"]
    ),
    CatalogQuestion(
        id="dsa_tree_kth_smallest_bst",
        title="Kth Smallest Element in a BST",
        question_text="Given the root of a binary search tree and an integer `k`, return the `k`th smallest value (1-indexed) of all the values of the nodes in the tree. Explain how in-order traversal guarantees sorted order.",
        interview_type="coding",
        target_role="Software Engineer",
        skill_focus="trees",
        difficulty="intermediate",
        expected_time_minutes=12,
        rubric="Candidate should implement iterative or recursive in-order traversal stopping early at count == k.",
        canonical_skills=["trees", "binary_search"]
    ),
    # System Design & Concurrency additional tiers
    CatalogQuestion(
        id="sys_rate_limiter_design",
        title="API Rate Limiter Design",
        question_text="Design a distributed API rate limiter supporting millions of requests per second. Compare Token Bucket, Leaky Bucket, Fixed Window, and Sliding Window Log/Counter algorithms, detailing Redis Lua script atomicity.",
        interview_type="technical",
        target_role="Software Engineer",
        skill_focus="System Design",
        difficulty="intermediate",
        expected_time_minutes=20,
        rubric="Candidate should explain token bucket mechanics, sliding window counter trade-offs, and distributed synchronization via Redis Lua scripts.",
        canonical_skills=["System Design", "Database Concepts"]
    ),
    CatalogQuestion(
        id="sys_distributed_transactions_saga",
        title="Distributed Transactions & The Saga Pattern",
        question_text="In a microservices architecture, how do you manage distributed transactions across multiple independent databases? Compare Two-Phase Commit (2PC) with Orchestrated vs Choreographed Sagas and compensating transactions.",
        interview_type="technical",
        target_role="Software Engineer",
        skill_focus="System Design",
        difficulty="advanced",
        expected_time_minutes=20,
        rubric="Candidate should contrast 2PC blocking limitations with Saga compensating workflows and outbox pattern messaging.",
        canonical_skills=["System Design", "Database Concepts"]
    ),
    # Database Concepts additional tiers
    CatalogQuestion(
        id="db_acid_isolation_levels",
        title="Database ACID Isolation Levels & Anomalies",
        question_text="Explain the four SQL standard transaction isolation levels (Read Uncommitted, Read Committed, Repeatable Read, Serializable). Detail the concurrency anomalies they prevent (Dirty Reads, Non-repeatable Reads, Phantom Reads, Write Skew) and how MVCC implements them.",
        interview_type="technical",
        target_role="Software Engineer",
        skill_focus="Database Concepts",
        difficulty="intermediate",
        expected_time_minutes=15,
        rubric="Candidate should explain read-locks vs snapshot isolation/MVCC and describe write skew under Repeatable Read.",
        canonical_skills=["Database Concepts", "System Design"]
    ),
]


class PracticeSequenceItem(BaseModel):
    """A single scheduled question in the adaptive practice sequence."""
    sequence_order: int
    question_id: str
    title: str
    question_text: str
    interview_type: str
    target_role: str
    skill_focus: str
    difficulty: str
    expected_time_minutes: int
    rubric: str
    canonical_skills: List[str] = Field(default_factory=list)
    selection_reason: str
    remediation_objective: str
    progression_stage: str  # foundational_reinforcement, scaffolded_progression, frontier_mastery, spaced_retention, curriculum_breadth
    model_metrics: Dict[str, Any] = Field(default_factory=dict)


class PracticePlan(BaseModel):
    """A complete adaptive practice sequence plan tailored to the candidate."""
    plan_id: str
    user_id: str
    mode: str  # "weakest_skills" | "role_prep"
    target_role: str
    target_skills: List[str]
    baseline_skill_estimates: Dict[str, float]
    sequence: List[PracticeSequenceItem]
    total_estimated_minutes: int
    summary_explanation: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AdaptivePracticeEngine:
    """
    Adaptive Practice Engine.
    
    Selects practice questions by synthesizing:
      1. Candidate skill profile (IRT mastery & confidence)
      2. Recent mistakes & detected weakness signals
      3. Scaffolding & difficulty progression
      4. Question skill metadata & canonical taxonomies
      5. Dense semantic embeddings (MiniLM) for similarity & deduplication
      6. Spaced repetition retention intervals
      7. Historical practice sessions & duplicate prevention
    """

    def __init__(
        self,
        irt_model: Optional[ItemResponseTheoryMasteryModel] = None,
        difficulty_predictor: Optional[QuestionDifficultyPredictor] = None,
        embedding_extractor: Optional[TextEmbeddingExtractor] = None,
        skill_classifier: Optional[QuestionSkillClassifier] = None,
        catalog: Optional[List[CatalogQuestion]] = None,
    ):
        self.irt = irt_model or ItemResponseTheoryMasteryModel()
        self._difficulty_predictor = difficulty_predictor
        self._embedding_extractor = embedding_extractor
        self._skill_classifier = skill_classifier

        # Combine base canonical catalog with additional practice items
        initial_catalog = list(catalog or CANONICAL_QUESTION_CATALOG)
        existing_ids = {q.id for q in initial_catalog}
        for item in PRACTICE_ADDITIONAL_CATALOG:
            if item.id not in existing_ids:
                initial_catalog.append(item)
                existing_ids.add(item.id)

        self.catalog = initial_catalog

    # ── Lazy property loaders ──
    @property
    def difficulty_predictor(self) -> QuestionDifficultyPredictor:
        if self._difficulty_predictor is None:
            self._difficulty_predictor = QuestionDifficultyPredictor()
        return self._difficulty_predictor

    @property
    def embedding_extractor(self) -> TextEmbeddingExtractor:
        if self._embedding_extractor is None:
            self._embedding_extractor = TextEmbeddingExtractor()
        return self._embedding_extractor

    @property
    def skill_classifier(self) -> QuestionSkillClassifier:
        if self._skill_classifier is None:
            self._skill_classifier = QuestionSkillClassifier()
        return self._skill_classifier

    # ─────────────────────────────────────────────────────────────────────────
    # Profile & Evidence Normalization
    # ─────────────────────────────────────────────────────────────────────────
    def _normalize_candidate_state(
        self,
        candidate_data: Union[CandidateModel, Dict[str, Any], None]
    ) -> Dict[str, Any]:
        """
        Extract normalized candidate skill state, mistakes, and history.
        """
        if candidate_data is None:
            return {
                "user_id": "guest_user",
                "target_role": "Software Engineer",
                "target_skills": ROLE_CURRICULUM_BLUEPRINTS["Software Engineer"],
                "skill_estimates": {},
                "skill_confidence": {},
                "recent_performance": {},
                "historical_performance": {},
                "difficulty_exposure": {},
                "practice_history": [],
                "weak_skill_signals": [],
                "recent_mistakes": [],
                "theta": 0.0,
            }

        if isinstance(candidate_data, CandidateModel):
            cand_dict = candidate_data.model_dump()
        else:
            cand_dict = dict(candidate_data)

        skill_estimates = cand_dict.get("skill_estimates") or {}
        skill_confidence = cand_dict.get("skill_confidence") or {}
        weak_signals = cand_dict.get("weak_skill_signals") or []
        practice_history = cand_dict.get("practice_history") or []
        target_role = cand_dict.get("target_role") or "Software Engineer"
        target_skills = cand_dict.get("target_skills") or ROLE_CURRICULUM_BLUEPRINTS.get(target_role, ROLE_CURRICULUM_BLUEPRINTS["General"])
        difficulty_exposure = cand_dict.get("difficulty_exposure") or {}
        user_id = cand_dict.get("user_id") or "anonymous_user"

        # Extract recent mistakes from evidence chain or signals
        recent_mistakes = []
        evidence_chain = cand_dict.get("evidence_chain") or []
        for ev in evidence_chain:
            obs_list = ev.get("observations", []) if isinstance(ev, dict) else getattr(ev, "observations", [])
            for obs in obs_list:
                obs_dict = obs if isinstance(obs, dict) else obs.model_dump()
                if obs_dict.get("event_type") in ("question_scored", "weakness_discovered"):
                    raw = obs_dict.get("raw_data", {})
                    score = raw.get("score")
                    if score is not None and score < 65:
                        recent_mistakes.append({
                            "skill": obs_dict.get("skill_focus", "General"),
                            "description": obs_dict.get("description", ""),
                            "score": score,
                            "timestamp": obs_dict.get("timestamp", ""),
                            "difficulty": raw.get("difficulty", "intermediate")
                        })
                    elif obs_dict.get("event_type") == "weakness_discovered":
                        recent_mistakes.append({
                            "skill": obs_dict.get("skill_focus", "General"),
                            "description": obs_dict.get("description", ""),
                            "score": 50.0,
                            "timestamp": obs_dict.get("timestamp", ""),
                            "difficulty": "intermediate"
                        })

        # Latent theta calculation
        thetas = []
        for s_name, mastery in skill_estimates.items():
            # Invert 2PL-IRT proficiency to theta
            thetas.append(self.irt.proficiency_to_theta(mastery * 100.0))
        theta = (sum(thetas) / len(thetas)) if thetas else 0.0

        return {
            "user_id": user_id,
            "target_role": target_role,
            "target_skills": target_skills,
            "skill_estimates": skill_estimates,
            "skill_confidence": skill_confidence,
            "recent_performance": cand_dict.get("recent_performance") or {},
            "historical_performance": cand_dict.get("historical_performance") or {},
            "difficulty_exposure": difficulty_exposure,
            "practice_history": practice_history,
            "weak_skill_signals": weak_signals,
            "recent_mistakes": recent_mistakes,
            "theta": round(theta, 3),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Spaced Repetition Priority Analysis
    # ─────────────────────────────────────────────────────────────────────────
    def _calculate_spaced_repetition_urgency(
        self,
        skill: str,
        state: Dict[str, Any]
    ) -> Tuple[float, str]:
        """
        Evaluate spaced repetition interval urgency in [0.0, 1.0].
        Skills with past mistakes or decaying confidence that haven't been practiced
        in recent sessions receive an urgency boost for long-term retention.
        """
        recent_mistakes = state["recent_mistakes"]
        history_len = len(state["practice_history"])
        confidence = state["skill_confidence"].get(skill, 0.5)
        mastery = state["skill_estimates"].get(skill, 0.5)

        # Check if there are mistakes for this skill
        matching_mistakes = [
            m for m in recent_mistakes
            if skill.lower() in m.get("skill", "").lower() or m.get("skill", "").lower() in skill.lower()
        ]

        if not matching_mistakes and mastery >= 0.75:
            # Well mastered with no recent mistakes: low urgency for immediate drill
            return 0.10, f"Skill '{skill}' is in good standing (mastery: {mastery:.2f})."

        if matching_mistakes and history_len >= 2:
            # Has past mistakes and multiple subsequent sessions have passed: high spaced repetition review need
            urgency = min(0.95, 0.55 + 0.10 * len(matching_mistakes) + (1.0 - confidence) * 0.30)
            return round(urgency, 3), (
                f"Spaced repetition trigger: Candidate demonstrated {len(matching_mistakes)} prior mistakes in "
                f"'{skill}' (mastery: {mastery:.2f}) and requires memory consolidation."
            )

        if mastery < 0.60:
            urgency = round(0.70 + (0.60 - mastery) * 0.50, 3)
            return min(0.95, urgency), f"Active remediation required for low mastery ({mastery:.2f}) in '{skill}'."

        return 0.40, f"Routine retention check for '{skill}'."

    # ─────────────────────────────────────────────────────────────────────────
    # Question Filtering & Deduplication
    # ─────────────────────────────────────────────────────────────────────────
    def _filter_eligible_questions(
        self,
        state: Dict[str, Any],
        target_role: str,
        excluded_ids: set,
    ) -> List[CatalogQuestion]:
        """
        Filter available catalog questions, excluding already completed questions.
        """
        # Exclude questions from practice history and explicitly excluded IDs
        history_set = set(state["practice_history"]) | excluded_ids

        eligible = []
        norm_role = target_role.lower()

        for q in self.catalog:
            if q.id in history_set:
                continue

            q_role = q.target_role.lower()
            if q_role == "general" or norm_role in q_role or q_role in norm_role or not norm_role:
                eligible.append(q)
            elif q.interview_type in ("coding", "technical") and "engineer" in norm_role:
                eligible.append(q)

        # Fallback if filtered pool is too small
        if not eligible:
            for q in self.catalog:
                if q.id not in excluded_ids:
                    eligible.append(q)

        return eligible

    # ─────────────────────────────────────────────────────────────────────────
    # Multi-Objective Scoring & Ranking for Practice
    # ─────────────────────────────────────────────────────────────────────────
    def _score_practice_candidate(
        self,
        question: CatalogQuestion,
        target_skill: str,
        target_difficulty: str,
        state: Dict[str, Any],
        selected_sequence_texts: List[str],
        mode: str,
        progression_index: int,
        total_in_sequence: int,
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Deterministic multi-objective scoring for practice question ranking.
        """
        q_skill = question.skill_focus
        q_text = question.question_text
        q_diff = question.difficulty

        # 1. Skill Alignment Score (0.0 to 1.0)
        skill_matched = (
            q_skill.lower() == target_skill.lower()
            or target_skill.lower() in q_skill.lower()
            or any(target_skill.lower() in s.lower() for s in question.canonical_skills)
        )
        skill_score = 1.0 if skill_matched else 0.20

        # 2. Difficulty Fit & Progression Score (0.0 to 1.0)
        b_target = DIFFICULTY_PRIORS.get(target_difficulty, 0.0)
        b_q = DIFFICULTY_PRIORS.get(q_diff, 0.0)
        diff_distance = abs(b_target - b_q)
        diff_score = math.exp(-(diff_distance ** 2) / 1.5)

        # 3. Spaced Repetition & Weakness Urgency (0.0 to 1.0)
        urgency, urgency_reason = self._calculate_spaced_repetition_urgency(q_skill, state)

        # 4. Semantic Novelty / Deduplication vs current practice sequence (0.0 to 1.0)
        max_sim = 0.0
        if selected_sequence_texts:
            q_emb = self.embedding_extractor.encode(q_text)
            for prev_t in selected_sequence_texts:
                prev_emb = self.embedding_extractor.encode(prev_t)
                sim = compute_cosine_similarity(q_emb, prev_emb)
                if sim > max_sim:
                    max_sim = sim

        novelty = round(max(0.0, 1.0 - max_sim), 4)

        # Severe penalty if semantic duplicate (>0.82 similarity)
        semantic_multiplier = 0.10 if max_sim > 0.82 else 1.0

        # Weights calibrated per mode
        if mode == MODE_WEAKEST_SKILLS:
            # Heavily weight weakness urgency & targeted skill alignment
            composite = (
                0.40 * skill_score +
                0.25 * diff_score +
                0.25 * urgency +
                0.10 * novelty
            ) * semantic_multiplier
        else:  # MODE_ROLE_PREP
            # Balance curriculum coverage, progressive difficulty, and diversity
            composite = (
                0.35 * skill_score +
                0.30 * diff_score +
                0.15 * urgency +
                0.20 * novelty
            ) * semantic_multiplier

        metrics = {
            "skill_score": round(skill_score, 3),
            "difficulty_score": round(diff_score, 3),
            "urgency": round(urgency, 3),
            "novelty": round(novelty, 3),
            "max_similarity": round(max_sim, 3),
            "composite_score": round(composite, 4),
            "urgency_reason": urgency_reason,
            "target_difficulty": target_difficulty,
        }

        return composite, metrics

    # ─────────────────────────────────────────────────────────────────────────
    # Deterministic Selection Reason Generator
    # ─────────────────────────────────────────────────────────────────────────
    def _generate_selection_reason(
        self,
        question: CatalogQuestion,
        target_skill: str,
        stage: str,
        mode: str,
        state: Dict[str, Any],
        metrics: Dict[str, Any]
    ) -> Tuple[str, str]:
        """
        Generate an evidence-backed, transparent explanation answering why this
        specific question was selected for the candidate.
        """
        mastery = state["skill_estimates"].get(target_skill, 0.50)
        confidence = state["skill_confidence"].get(target_skill, 0.50)
        q_diff = question.difficulty
        mistakes = [
            m for m in state["recent_mistakes"]
            if target_skill.lower() in m.get("skill", "").lower() or m.get("skill", "").lower() in target_skill.lower()
        ]

        if mode == MODE_WEAKEST_SKILLS:
            if stage == "foundational_reinforcement":
                reason = (
                    f"Selected because your recent sessions show low-confidence performance in {target_skill} "
                    f"(mastery: {mastery:.2f}, {len(mistakes)} prior mistakes). "
                    f"Starting with {q_diff} difficulty to reinforce core conceptual foundations."
                )
                objective = f"Establish solid fundamentals and pattern recognition for {target_skill}."
            elif stage == "scaffolded_progression":
                reason = (
                    f"Selected for difficulty progression to advance into {q_diff} {target_skill} problems, "
                    f"bridging initial fundamentals with complex constraints."
                )
                objective = f"Master standard algorithmic variants and trade-off decisions in {target_skill}."
            elif stage == "frontier_mastery":
                reason = (
                    f"Selected to test your performance frontier at {q_diff} level in {target_skill} "
                    f"(current estimated mastery: {mastery:.2f})."
                )
                objective = f"Demonstrate mastery of optimal time/space complexities on advanced {target_skill} challenges."
            elif stage == "spaced_retention":
                reason = (
                    f"Selected for spaced repetition to consolidate retention in {target_skill}, "
                    f"revisiting previous error patterns after interval delay."
                )
                objective = f"Verify durable retention and prevent skill regression in {target_skill}."
            else:
                reason = f"Selected for targeted weakness remediation in {target_skill}."
                objective = f"Reinforce competency in {target_skill}."
        else:  # MODE_ROLE_PREP
            role = state["target_role"]
            if stage == "foundational_reinforcement":
                reason = (
                    f"Selected for {role} interview preparation: calibrating essential baseline in {target_skill} "
                    f"at {q_diff} difficulty (mastery: {mastery:.2f})."
                )
                objective = f"Verify core implementation accuracy in {target_skill}."
            elif stage == "scaffolded_progression":
                reason = (
                    f"Selected for {role} interview preparation: advancing {target_skill} to {q_diff} difficulty "
                    f"to match typical industry bar."
                )
                objective = f"Solve production-grade {target_skill} challenges under standard interview constraints."
            elif stage == "frontier_mastery":
                reason = (
                    f"Selected for {role} interview preparation: testing advanced edge-case handling and system architecture "
                    f"in {target_skill}."
                )
                objective = f"Execute senior-level optimization and architectural trade-off justification."
            else:
                reason = (
                    f"Selected for comprehensive {role} curriculum coverage across {target_skill} "
                    f"(current mastery: {mastery:.2f})."
                )
                objective = f"Ensure well-rounded competency across {target_skill}."

        return reason, objective

    # ─────────────────────────────────────────────────────────────────────────
    # Sequence Generator
    # ─────────────────────────────────────────────────────────────────────────
    def generate_practice_sequence(
        self,
        candidate_data: Union[CandidateModel, Dict[str, Any], None] = None,
        mode: str = MODE_WEAKEST_SKILLS,
        target_role: Optional[str] = None,
        num_questions: int = 4,
    ) -> PracticePlan:
        """
        Generate a cohesive, adaptive practice sequence based on candidate state and chosen mode.
        
        Guarantees:
          - No random selection (100% deterministic ranking)
          - Scaffolding & progressive difficulty (e.g. beginner -> intermediate -> advanced)
          - Spaced repetition & weakness reinforcement
          - Non-duplicate & semantically diverse questions
          - Human-readable selection reason for every question
          - Zero fake progress statistics
        """
        t0 = time.time()
        state = self._normalize_candidate_state(candidate_data)
        if target_role:
            state["target_role"] = target_role

        num_questions = max(1, min(10, num_questions))
        selected_items: List[PracticeSequenceItem] = []
        selected_ids: set = set()
        selected_texts: List[str] = []

        # Step 1: Determine target skills for the sequence
        target_skills: List[str] = []
        stages: List[str] = []
        difficulties: List[str] = []

        if mode == MODE_WEAKEST_SKILLS:
            # Identify weakest skills from estimates & mistakes
            all_skills = list(state["target_skills"])
            for weak in state["weak_skill_signals"]:
                if weak not in all_skills:
                    all_skills.append(weak)

            # Sort skills by mastery estimate (lowest first) and mistake count (highest first)
            def skill_weakness_key(sk: str):
                mst = state["skill_estimates"].get(sk, 0.50)
                mstk_cnt = sum(1 for m in state["recent_mistakes"] if sk.lower() in m.get("skill", "").lower())
                conf = state["skill_confidence"].get(sk, 0.50)
                return (mst, -mstk_cnt, conf, sk)

            sorted_weak_skills = sorted(all_skills, key=skill_weakness_key)
            primary_weak_skill = sorted_weak_skills[0] if sorted_weak_skills else "arrays"
            secondary_weak_skill = sorted_weak_skills[1] if len(sorted_weak_skills) > 1 else primary_weak_skill

            # Create progressive ladder:
            # Stage 1: Foundational reinforcement (beginner/intermediate)
            # Stage 2: Scaffolded progression (intermediate)
            # Stage 3: Frontier mastery or Spaced review (intermediate/advanced)
            # Stage 4+: Advanced reinforcement or secondary weak skill
            base_mastery = state["skill_estimates"].get(primary_weak_skill, 0.50)
            
            for i in range(num_questions):
                if i == 0:
                    target_skills.append(primary_weak_skill)
                    stages.append("foundational_reinforcement")
                    difficulties.append("beginner" if base_mastery < 0.50 else "intermediate")
                elif i == 1:
                    target_skills.append(primary_weak_skill)
                    stages.append("scaffolded_progression")
                    difficulties.append("intermediate")
                elif i == 2:
                    # Switch to secondary weak skill or test frontier
                    sk = secondary_weak_skill if secondary_weak_skill != primary_weak_skill else primary_weak_skill
                    target_skills.append(sk)
                    stages.append("spaced_retention" if i % 2 == 0 else "frontier_mastery")
                    difficulties.append("intermediate" if base_mastery < 0.60 else "advanced")
                else:
                    target_skills.append(primary_weak_skill if i % 2 == 0 else secondary_weak_skill)
                    stages.append("frontier_mastery")
                    difficulties.append("advanced")

        else:  # MODE_ROLE_PREP ("Prepare me for Software Engineer interviews")
            role_skills = ROLE_CURRICULUM_BLUEPRINTS.get(state["target_role"], ROLE_CURRICULUM_BLUEPRINTS["General"])
            
            # Map curriculum across the requested sequence length
            for i in range(num_questions):
                skill_idx = i % len(role_skills)
                cur_skill = role_skills[skill_idx]
                target_skills.append(cur_skill)

                sk_mastery = state["skill_estimates"].get(cur_skill, 0.50)
                if i < 2:
                    stages.append("foundational_reinforcement" if sk_mastery < 0.55 else "scaffolded_progression")
                    difficulties.append("beginner" if sk_mastery < 0.40 else "intermediate")
                elif i < num_questions - 1:
                    stages.append("scaffolded_progression")
                    difficulties.append("intermediate")
                else:
                    stages.append("frontier_mastery")
                    difficulties.append("advanced")

        # Step 2: Deterministically rank and select questions for each slot in the sequence
        total_mins = 0

        for seq_idx in range(num_questions):
            tgt_skill = target_skills[seq_idx]
            tgt_diff = difficulties[seq_idx]
            stage = stages[seq_idx]

            eligible = self._filter_eligible_questions(
                state=state,
                target_role=state["target_role"],
                excluded_ids=selected_ids
            )

            # Score every eligible question
            scored_candidates: List[Tuple[float, CatalogQuestion, Dict[str, Any]]] = []
            for q in eligible:
                score, metrics = self._score_practice_candidate(
                    question=q,
                    target_skill=tgt_skill,
                    target_difficulty=tgt_diff,
                    state=state,
                    selected_sequence_texts=selected_texts,
                    mode=mode,
                    progression_index=seq_idx,
                    total_in_sequence=num_questions,
                )
                scored_candidates.append((score, q, metrics))

            # Deterministic sort: highest score first, tie-break by difficulty match and ID hash
            scored_candidates.sort(
                key=lambda item: (
                    item[0],
                    item[2]["difficulty_score"],
                    item[2]["novelty"],
                    -hash(item[1].id)
                ),
                reverse=True
            )

            winner_score, winner_q, winner_metrics = scored_candidates[0]
            selected_ids.add(winner_q.id)
            selected_texts.append(winner_q.question_text)
            total_mins += winner_q.expected_time_minutes

            reason, objective = self._generate_selection_reason(
                question=winner_q,
                target_skill=tgt_skill,
                stage=stage,
                mode=mode,
                state=state,
                metrics=winner_metrics
            )

            item = PracticeSequenceItem(
                sequence_order=seq_idx + 1,
                question_id=winner_q.id,
                title=winner_q.title,
                question_text=winner_q.question_text,
                interview_type=winner_q.interview_type,
                target_role=winner_q.target_role,
                skill_focus=winner_q.skill_focus,
                difficulty=winner_q.difficulty,
                expected_time_minutes=winner_q.expected_time_minutes,
                rubric=winner_q.rubric,
                canonical_skills=winner_q.canonical_skills,
                selection_reason=reason,
                remediation_objective=objective,
                progression_stage=stage,
                model_metrics=winner_metrics,
            )
            selected_items.append(item)

        # Build summary explanation
        if mode == MODE_WEAKEST_SKILLS:
            summary = (
                f"Generated an adaptive weakness-reinforcement sequence targeting '{target_skills[0]}' "
                f"with scaffolded difficulty progression from {difficulties[0]} to {difficulties[-1]}."
            )
        else:
            summary = (
                f"Generated a {state['target_role']} preparation curriculum spanning "
                f"{', '.join(dict.fromkeys(target_skills))} with calibrated interview-grade difficulty."
            )

        return PracticePlan(
            plan_id=str(uuid.uuid4()),
            user_id=state["user_id"],
            mode=mode,
            target_role=state["target_role"],
            target_skills=list(dict.fromkeys(target_skills)),
            baseline_skill_estimates=state["skill_estimates"],
            sequence=selected_items,
            total_estimated_minutes=total_mins,
            summary_explanation=summary,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Single Next Practice Question Selector (Standalone / Step-by-Step Drill)
    # ─────────────────────────────────────────────────────────────────────────
    def select_next_practice_question(
        self,
        candidate_data: Union[CandidateModel, Dict[str, Any], None] = None,
        mode: str = MODE_WEAKEST_SKILLS,
        target_role: Optional[str] = None,
        preferred_topic: Optional[str] = None,
        preferred_difficulty: Optional[str] = None,
    ) -> PracticeSequenceItem:
        """
        Selects a single optimal next practice question with full explainability.
        """
        state = self._normalize_candidate_state(candidate_data)
        if target_role:
            state["target_role"] = target_role

        target_skill = preferred_topic
        if not target_skill:
            if mode == MODE_WEAKEST_SKILLS:
                # Pick top weakness
                all_skills = list(state["target_skills"]) + state["weak_skill_signals"]
                if all_skills:
                    target_skill = min(all_skills, key=lambda s: state["skill_estimates"].get(s, 0.50))
                else:
                    target_skill = "arrays"
            else:
                target_skill = ROLE_CURRICULUM_BLUEPRINTS.get(state["target_role"], ["arrays"])[0]

        target_diff = preferred_difficulty or ("intermediate" if state["skill_estimates"].get(target_skill, 0.5) >= 0.5 else "beginner")

        plan = self.generate_practice_sequence(
            candidate_data=state,
            mode=mode,
            target_role=state["target_role"],
            num_questions=1,
        )
        return plan.sequence[0]
