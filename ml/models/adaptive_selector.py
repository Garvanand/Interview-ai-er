"""
Deterministic ML-Assisted Adaptive Question Selector.
Category: HYBRID ML + IRT DECISION LAYER.
Models:
    - 2PL-IRT Skill Mastery Model (ednet_2pl_irt_v1.0)
    - TACO Question Difficulty Predictor (taco_difficulty_v1.0)
    - Sentence-Transformers MiniLM Semantic Embeddings (all-minilm-l6-v2)
    - TACO Canonical Question Skill Classifier (taco_skill_classifier_v1.0)

Decision Pipeline:
    candidate skill state
    ↓
    candidate weaknesses
    ↓
    eligible questions
    ↓
    difficulty prediction
    ↓
    skill coverage
    ↓
    semantic deduplication
    ↓
    adaptive ranking
    ↓
    next question

Deterministic Decision Layer:
    Every decision is ranked using a mathematically sound multi-factor formula.
    LLMs are NOT permitted to freely choose question sequences.
    Full explainability is generated for "Why was this question selected?".
"""
from __future__ import annotations

import logging
import math
import time
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from ml.models.skill_mastery import ItemResponseTheoryMasteryModel
from ml.models.difficulty_predictor import QuestionDifficultyPredictor
from ml.models.skill_classifier import QuestionSkillClassifier
from ml.features.text_embeddings import TextEmbeddingExtractor, compute_cosine_similarity

logger = logging.getLogger(__name__)

# Model version constants
MODEL_VERSIONS = [
    "ednet_2pl_irt_v1.0",
    "taco_difficulty_v1.0",
    "all-minilm-l6-v2-semantic-embeddings",
    "taco_skill_classifier_v1.0"
]

# Canonical difficulty priors for 2PL-IRT
DIFFICULTY_PRIORS: Dict[str, float] = {
    "beginner": -1.2,
    "intermediate": 0.0,
    "advanced": 1.4,
}


@dataclass
class CatalogQuestion:
    """Pre-tagged canonical question in the question bank."""
    id: str
    title: str
    question_text: str
    interview_type: str        # coding, technical, frontend, backend, system_design, behavioral
    target_role: str           # Software Engineer, Frontend Engineer, Backend Engineer, General
    skill_focus: str           # arrays, graphs, dynamic_programming, trees, etc.
    difficulty: str            # beginner, intermediate, advanced
    expected_time_minutes: int # estimated duration in minutes
    rubric: str                # key concepts or evaluation criteria
    canonical_skills: List[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# CURATED CANONICAL QUESTION CATALOG
# ─────────────────────────────────────────────────────────────────────────────
CANONICAL_QUESTION_CATALOG: List[CatalogQuestion] = [
    # ── Coding / DSA: Arrays & Hashing ──
    CatalogQuestion(
        id="dsa_arr_two_sum",
        title="Two Sum with Hash Map",
        question_text="Given an array of integers `nums` and an integer `target`, return the indices of the two numbers such that they add up to `target`. Optimize for O(N) time using a hash map.",
        interview_type="coding",
        target_role="Software Engineer",
        skill_focus="arrays",
        difficulty="beginner",
        expected_time_minutes=10,
        rubric="Candidate should utilize a hash map for single-pass O(N) lookup instead of brute-force O(N^2).",
        canonical_skills=["arrays", "hashing"]
    ),
    CatalogQuestion(
        id="dsa_arr_group_anagrams",
        title="Group Anagrams",
        question_text="Given an array of strings `strs`, group the anagrams together. You can return the answer in any order. Discuss time complexity with character count vs sorting.",
        interview_type="coding",
        target_role="Software Engineer",
        skill_focus="hashing",
        difficulty="intermediate",
        expected_time_minutes=15,
        rubric="Candidate should identify character frequency tuple or sorted string as canonical hash key.",
        canonical_skills=["hashing", "strings", "arrays"]
    ),
    CatalogQuestion(
        id="dsa_arr_longest_consecutive",
        title="Longest Consecutive Sequence",
        question_text="Given an unsorted array of integers `nums`, return the length of the longest consecutive elements sequence in O(N) time without sorting.",
        interview_type="coding",
        target_role="Software Engineer",
        skill_focus="arrays",
        difficulty="advanced",
        expected_time_minutes=20,
        rubric="Candidate should use a hash set and only expand sequences starting from sequence boundaries (`num - 1 not in set`).",
        canonical_skills=["arrays", "hashing"]
    ),

    # ── Coding / DSA: Two Pointers & Sliding Window ──
    CatalogQuestion(
        id="dsa_ptr_valid_palindrome",
        title="Valid Palindrome",
        question_text="A phrase is a palindrome if, after converting all uppercase letters into lowercase letters and removing all non-alphanumeric characters, it reads the same forward and backward. Determine if it is a palindrome using two pointers in O(1) extra space.",
        interview_type="coding",
        target_role="Software Engineer",
        skill_focus="two_pointers",
        difficulty="beginner",
        expected_time_minutes=10,
        rubric="Check inward movement of left and right pointers skipping non-alphanumeric characters.",
        canonical_skills=["two_pointers", "strings"]
    ),
    CatalogQuestion(
        id="dsa_ptr_container_most_water",
        title="Container With Most Water",
        question_text="Given an integer array `height` representing vertical lines, find two lines that together with the x-axis form a container that contains the most water. Explain the greedy two-pointer narrowing strategy.",
        interview_type="coding",
        target_role="Software Engineer",
        skill_focus="two_pointers",
        difficulty="intermediate",
        expected_time_minutes=15,
        rubric="Candidate must prove why moving the shorter boundary inward preserves the optimal solution search.",
        canonical_skills=["two_pointers", "greedy", "arrays"]
    ),
    CatalogQuestion(
        id="dsa_win_min_window_substring",
        title="Minimum Window Substring",
        question_text="Given two strings `s` and `t`, return the minimum window substring of `s` such that every character in `t` (including duplicates) is included in the window. Optimize for O(N) time complexity.",
        interview_type="coding",
        target_role="Software Engineer",
        skill_focus="sliding_window",
        difficulty="advanced",
        expected_time_minutes=25,
        rubric="Candidate should implement a two-pointer sliding window with match counts and frequency dictionaries.",
        canonical_skills=["sliding_window", "hashing", "strings"]
    ),

    # ── Coding / DSA: Linked Lists & Stacks ──
    CatalogQuestion(
        id="dsa_ll_reverse_list",
        title="Reverse Linked List",
        question_text="Given the head of a singly linked list, reverse the list iteratively and return the reversed list. Discuss both iterative and recursive approaches.",
        interview_type="coding",
        target_role="Software Engineer",
        skill_focus="linked_lists",
        difficulty="beginner",
        expected_time_minutes=10,
        rubric="Proper three-pointer manipulation (prev, curr, next_node) without pointer cycle errors.",
        canonical_skills=["linked_lists", "recursion"]
    ),
    CatalogQuestion(
        id="dsa_stk_valid_parentheses",
        title="Valid Parentheses",
        question_text="Given a string `s` containing just the characters '(', ')', '{', '}', '[' and ']', determine if the input string is valid using a stack.",
        interview_type="coding",
        target_role="Software Engineer",
        skill_focus="stacks",
        difficulty="beginner",
        expected_time_minutes=10,
        rubric="Candidate should push open brackets onto stack and pop matching closing brackets, checking empty stack at end.",
        canonical_skills=["stacks", "strings"]
    ),
    CatalogQuestion(
        id="dsa_ll_lru_cache",
        title="LRU Cache Implementation",
        question_text="Design a data structure that follows the constraints of a Least Recently Used (LRU) cache with O(1) get and put operations using a doubly linked list and hash map.",
        interview_type="coding",
        target_role="Software Engineer",
        skill_focus="data_structures",
        difficulty="intermediate",
        expected_time_minutes=20,
        rubric="Candidate must use a doubly linked list with sentinel head/tail nodes and hash map for O(1) access/eviction.",
        canonical_skills=["data_structures", "linked_lists", "hashing"]
    ),

    # ── Coding / DSA: Trees & Binary Search ──
    CatalogQuestion(
        id="dsa_tree_max_depth",
        title="Maximum Depth of Binary Tree",
        question_text="Given the root of a binary tree, return its maximum depth. Compare depth-first search (DFS) with breadth-first search (BFS) level-order traversal.",
        interview_type="coding",
        target_role="Software Engineer",
        skill_focus="trees",
        difficulty="beginner",
        expected_time_minutes=10,
        rubric="Candidate should implement standard postorder recursion: `1 + max(depth(left), depth(right))`.",
        canonical_skills=["trees", "recursion"]
    ),
    CatalogQuestion(
        id="dsa_tree_lowest_common_ancestor",
        title="Lowest Common Ancestor in Binary Tree",
        question_text="Given a binary tree and two nodes `p` and `q`, find their lowest common ancestor (LCA). Handle cases where nodes are on opposite subtrees or in an ancestor-descendant relation.",
        interview_type="coding",
        target_role="Software Engineer",
        skill_focus="trees",
        difficulty="intermediate",
        expected_time_minutes=15,
        rubric="Candidate should write recursive DFS returning node if matched, combining left and right subtrees.",
        canonical_skills=["trees", "recursion", "algorithms"]
    ),
    CatalogQuestion(
        id="dsa_bs_search_rotated_array",
        title="Search in Rotated Sorted Array",
        question_text="Given an integer array `nums` sorted in ascending order (with distinct values) that is rotated at an unknown pivot index, search for a `target` in O(log N) runtime.",
        interview_type="coding",
        target_role="Software Engineer",
        skill_focus="binary_search",
        difficulty="intermediate",
        expected_time_minutes=15,
        rubric="Candidate must identify which half of the array is normally sorted and decide where to recurse.",
        canonical_skills=["binary_search", "arrays"]
    ),
    CatalogQuestion(
        id="dsa_tree_serialize_deserialize",
        title="Serialize and Deserialize Binary Tree",
        question_text="Design an algorithm to serialize and deserialize a binary tree to and from a string representation. Discuss traversal ordering and null-node markers.",
        interview_type="coding",
        target_role="Software Engineer",
        skill_focus="trees",
        difficulty="advanced",
        expected_time_minutes=25,
        rubric="Candidate should use pre-order traversal or BFS queue with delimiter tokens and sentinel null markers.",
        canonical_skills=["trees", "data_structures", "strings"]
    ),

    # ── Coding / DSA: Graphs ──
    CatalogQuestion(
        id="dsa_graph_num_islands",
        title="Number of Islands",
        question_text="Given an `m x n` 2D binary grid representing a map of '1's (land) and '0's (water), return the number of islands. Implement using DFS or BFS and analyze space complexity.",
        interview_type="coding",
        target_role="Software Engineer",
        skill_focus="graphs",
        difficulty="intermediate",
        expected_time_minutes=15,
        rubric="Candidate should execute flood fill with in-place grid marking or a visited set to avoid infinite recursion.",
        canonical_skills=["graphs", "search", "recursion"]
    ),
    CatalogQuestion(
        id="dsa_graph_course_schedule",
        title="Course Schedule & Cycle Detection",
        question_text="There are a total of `numCourses` courses you have to take, labeled from 0 to numCourses - 1. You are given an array `prerequisites`. Determine if you can finish all courses using topological sort or cycle detection.",
        interview_type="coding",
        target_role="Software Engineer",
        skill_focus="graphs",
        difficulty="intermediate",
        expected_time_minutes=20,
        rubric="Candidate should construct an adjacency list and implement Kahn's algorithm (indegrees) or 3-color DFS.",
        canonical_skills=["graphs", "algorithms"]
    ),
    CatalogQuestion(
        id="dsa_graph_word_ladder",
        title="Word Ladder Shortest Transformation",
        question_text="Given two words `beginWord` and `endWord`, and a dictionary `wordList`, return the number of words in the shortest transformation sequence. Formulate as a shortest-path graph problem.",
        interview_type="coding",
        target_role="Software Engineer",
        skill_focus="graphs",
        difficulty="advanced",
        expected_time_minutes=25,
        rubric="Candidate should formulate BFS on state graph, optimizing intermediate word bucket patterns.",
        canonical_skills=["graphs", "search", "queues"]
    ),

    # ── Coding / DSA: Dynamic Programming ──
    CatalogQuestion(
        id="dsa_dp_climbing_stairs",
        title="Climbing Stairs",
        question_text="You are climbing a staircase that takes `n` steps to reach the top. Each time you can climb 1 or 2 steps. In how many distinct ways can you climb to the top? Optimize from recursive to O(1) space.",
        interview_type="coding",
        target_role="Software Engineer",
        skill_focus="dynamic_programming",
        difficulty="beginner",
        expected_time_minutes=10,
        rubric="Candidate should identify recurrence relation `dp[i] = dp[i-1] + dp[i-2]` and reduce memory to 2 variables.",
        canonical_skills=["dynamic_programming", "recursion"]
    ),
    CatalogQuestion(
        id="dsa_dp_coin_change",
        title="Coin Change Problem",
        question_text="Given an integer array `coins` and an integer `amount`, return the fewest number of coins needed to make up that amount. If that amount cannot be made up, return -1.",
        interview_type="coding",
        target_role="Software Engineer",
        skill_focus="dynamic_programming",
        difficulty="intermediate",
        expected_time_minutes=15,
        rubric="Candidate should build a bottom-up DP table `dp[a] = min(dp[a], dp[a - c] + 1)` with amount initialization.",
        canonical_skills=["dynamic_programming", "algorithms"]
    ),
    CatalogQuestion(
        id="dsa_dp_word_break",
        title="Word Break Problem",
        question_text="Given a string `s` and a dictionary of strings `wordDict`, return true if `s` can be segmented into a space-separated sequence of one or more dictionary words.",
        interview_type="coding",
        target_role="Software Engineer",
        skill_focus="dynamic_programming",
        difficulty="intermediate",
        expected_time_minutes=15,
        rubric="Candidate should use boolean DP array `dp[i]` indicating prefix reachability with hash set lookups.",
        canonical_skills=["dynamic_programming", "strings", "hashing"]
    ),
    CatalogQuestion(
        id="dsa_dp_longest_increasing_subsequence",
        title="Longest Increasing Subsequence",
        question_text="Given an integer array `nums`, return the length of the longest strictly increasing subsequence. First explain the O(N^2) DP approach, then discuss the O(N log N) patience sorting / binary search optimization.",
        interview_type="coding",
        target_role="Software Engineer",
        skill_focus="dynamic_programming",
        difficulty="advanced",
        expected_time_minutes=20,
        rubric="Candidate should explain both classical DP and patience sorting with `bisect_left`.",
        canonical_skills=["dynamic_programming", "binary_search", "complexity"]
    ),

    # ── Frontend Engineering ──
    CatalogQuestion(
        id="fe_react_hooks_pitfalls",
        title="React useEffect Dependencies & Lifecycle",
        question_text="Explain how React's `useEffect` hook operates under the hood. What are common pitfalls with dependency arrays (stale closures, infinite loops, object reference inequality), and how do `useCallback` or `useMemo` prevent them?",
        interview_type="technical",
        target_role="Frontend Engineer",
        skill_focus="Programming Fundamentals",
        difficulty="intermediate",
        expected_time_minutes=12,
        rubric="Candidate should articulate closure capture, Object.is dependency comparison, and cleanup functions.",
        canonical_skills=["Programming Fundamentals", "Debugging"]
    ),
    CatalogQuestion(
        id="fe_js_event_loop",
        title="JavaScript Event Loop & Microtasks",
        question_text="Explain the JavaScript Event Loop. Detail the execution order between the Call Stack, Macrotask Queue (setTimeout, I/O), and Microtask Queue (Promises, queueMicrotask, MutationObserver). Provide code examples.",
        interview_type="technical",
        target_role="Frontend Engineer",
        skill_focus="Programming Fundamentals",
        difficulty="intermediate",
        expected_time_minutes=12,
        rubric="Candidate must correctly trace execution order: synchronous script -> all microtasks -> render phase -> next macrotask.",
        canonical_skills=["Programming Fundamentals", "Debugging"]
    ),
    CatalogQuestion(
        id="fe_web_performance_crp",
        title="Critical Rendering Path & Performance Optimization",
        question_text="Walk through the browser Critical Rendering Path from HTML byte stream to pixels on screen. How do script defer/async, CSS object model construction, reflow, and repaint impact Core Web Vitals (LCP, INP, CLS)?",
        interview_type="technical",
        target_role="Frontend Engineer",
        skill_focus="System Design",
        difficulty="advanced",
        expected_time_minutes=15,
        rubric="Candidate should articulate DOM + CSSOM -> Render Tree -> Layout (reflow) -> Paint, and explain layout thrashing.",
        canonical_skills=["System Design", "Problem Solving"]
    ),

    # ── Backend & System Design ──
    CatalogQuestion(
        id="be_rest_idempotency",
        title="Idempotent API Design & Safe Retries",
        question_text="How do you design idempotent REST and RPC APIs for payment processing and distributed state changes? Discuss idempotency keys, atomic database reservations, and cache deduplication strategies.",
        interview_type="technical",
        target_role="Backend Engineer",
        skill_focus="System Design",
        difficulty="intermediate",
        expected_time_minutes=15,
        rubric="Candidate should explain unique request token lookup, transactional lock or conditional insert, and duplicate response caching.",
        canonical_skills=["System Design", "Database Concepts"]
    ),
    CatalogQuestion(
        id="be_db_indexing_btree",
        title="Database Indexing, B-Trees, and Query Planning",
        question_text="How do relational database B-Tree indexes work? Compare composite index column ordering rules (leftmost prefix) with covering indexes, and explain why poorly ordered composite indexes fail to accelerate queries.",
        interview_type="technical",
        target_role="Backend Engineer",
        skill_focus="Database Concepts",
        difficulty="intermediate",
        expected_time_minutes=15,
        rubric="Candidate should explain tree branch traversal, leaf node disk block pointers, and leftmost prefix matching.",
        canonical_skills=["Database Concepts", "Data Structures & Algorithms"]
    ),
    CatalogQuestion(
        id="sys_distributed_cache_redis",
        title="Distributed Caching & Cache Invalidation",
        question_text="Design a distributed caching tier using Redis for high-throughput reads. How do you handle cache-aside, write-through, cache stampede (thundering herd), and cache penetration?",
        interview_type="technical",
        target_role="Software Engineer",
        skill_focus="System Design",
        difficulty="advanced",
        expected_time_minutes=20,
        rubric="Candidate should articulate mutex locking or probabilistic early expiration for thundering herd, and Bloom filters for penetration.",
        canonical_skills=["System Design", "Database Concepts"]
    ),

    # ── Behavioral & Communication ──
    CatalogQuestion(
        id="beh_tech_disagreement",
        title="Resolving Technical Architecture Disagreements",
        question_text="Describe a situation where you had a strong technical disagreement with a team member or architect regarding system design or tech stack choice. How did you evaluate trade-offs, communicate, and reach a resolution?",
        interview_type="technical",
        target_role="Software Engineer",
        skill_focus="Behavioral Reasoning",
        difficulty="intermediate",
        expected_time_minutes=10,
        rubric="Candidate should demonstrate data-driven trade-off analysis, respectful listen-first communication, and commitment to team alignment.",
        canonical_skills=["Behavioral Reasoning", "Communication"]
    ),
    CatalogQuestion(
        id="beh_production_outage",
        title="Production Incident Response & Postmortem",
        question_text="Tell me about a high-severity production outage or critical bug you were involved in diagnosing and fixing. Walk through your triage process, containment strategy, root cause analysis, and blameless postmortem.",
        interview_type="technical",
        target_role="Software Engineer",
        skill_focus="Problem Solving",
        difficulty="advanced",
        expected_time_minutes=12,
        rubric="Candidate should cover observability, immediate mitigation (rollback/flag), root-cause analysis (5 whys), and preventive guardrails.",
        canonical_skills=["Problem Solving", "Debugging", "Communication"]
    ),
]


class AdaptiveQuestionSelector:
    """
    Deterministic decision layer for adaptive question selection in interview sessions.

    Connects:
        - Candidate Skill State & 2PL-IRT Latent Ability
        - Candidate Weaknesses & Remediation Priorities
        - TACO Question Difficulty Predictor (ML Signal)
        - Question Skill Metadata & Role Skill Coverage
        - Sentence-Transformers MiniLM Semantic Deduplication (ML Signal)
        - Time Budget Management & Pacing Constraints

    Enforces deterministic ranking over all candidate questions.
    Generates explainability records for every decision.
    """

    def __init__(
        self,
        irt_model: Optional[ItemResponseTheoryMasteryModel] = None,
        difficulty_predictor: Optional[QuestionDifficultyPredictor] = None,
        embedding_extractor: Optional[TextEmbeddingExtractor] = None,
        skill_classifier: Optional[QuestionSkillClassifier] = None,
        catalog: Optional[List[CatalogQuestion]] = None,
        weights: Optional[Dict[str, float]] = None,
    ):
        self.irt = irt_model or ItemResponseTheoryMasteryModel()
        self._difficulty_predictor = difficulty_predictor
        self._embedding_extractor = embedding_extractor
        self._skill_classifier = skill_classifier
        self.catalog = list(catalog or CANONICAL_QUESTION_CATALOG)

        # Multi-factor ranking weights (calibrated to sum to 1.0)
        self.weights = weights or {
            "skill_need": 0.35,        # Prioritize weaknesses & curriculum coverage
            "difficulty_fit": 0.30,    # Target candidate's zone of proximal development
            "novelty": 0.25,           # Avoid semantic duplicates & promote diversity
            "time_budget": 0.10,       # Pacing & remaining interview budget
        }

    # ── Lazy model properties ──
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
    # STEP 1 & 2: Candidate Skill State & Weakness Assessment
    # ─────────────────────────────────────────────────────────────────────────
    def assess_candidate_skill_state(
        self,
        skills_distribution: Dict[str, Any],
        questions_asked: List[Any],
        candidate_theta: float,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Synthesize candidate skill state across all tracked skills.

        Returns:
            Dict mapping skill_name -> {
                "mastery": float (0.0 to 1.0),
                "questions_count": int,
                "average_score": float,
                "recent_score": Optional[float],
                "weaknesses": List[str],
                "strengths": List[str],
                "theta": float,
                "is_weakness": bool,
                "weakness_severity": float (0.0 to 1.0)
            }
        """
        skill_states: Dict[str, Dict[str, Any]] = {}

        for skill_name, signal in skills_distribution.items():
            # Support both Pydantic SkillSignal and dict
            scores = getattr(signal, "scores", None)
            if scores is None and isinstance(signal, dict):
                scores = signal.get("scores", [])
            scores = scores or []

            avg_score = round(sum(scores) / len(scores), 2) if scores else 50.0
            recent_score = scores[-1] if scores else None

            # Weaknesses & strengths from signal
            weaknesses = getattr(signal, "weaknesses", None)
            if weaknesses is None and isinstance(signal, dict):
                weaknesses = signal.get("weaknesses", [])
            weaknesses = weaknesses or []

            strengths = getattr(signal, "strengths", None)
            if strengths is None and isinstance(signal, dict):
                strengths = signal.get("strengths", [])
            strengths = strengths or []

            # 2PL-IRT mastery probability
            mastery = getattr(signal, "mastery", None)
            if mastery is None:
                if scores:
                    mastery = round(max(0.05, min(0.95, avg_score / 100.0)), 2)
                else:
                    mastery = round(self.irt.theta_to_proficiency(candidate_theta) / 100.0, 2)

            # Determine weakness severity
            is_weak = False
            severity = 0.0

            if scores and avg_score < 65.0:
                is_weak = True
                severity += (65.0 - avg_score) / 65.0 * 0.7

            if weaknesses:
                is_weak = True
                severity += min(0.3, len(weaknesses) * 0.15)

            severity = round(min(1.0, max(0.0, severity)), 2)

            skill_states[skill_name] = {
                "mastery": mastery,
                "questions_count": len(scores),
                "average_score": avg_score,
                "recent_score": recent_score,
                "weaknesses": list(weaknesses),
                "strengths": list(strengths),
                "theta": candidate_theta,
                "is_weakness": is_weak,
                "weakness_severity": severity,
            }

        return skill_states

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 3: Eligible Questions Retrieval
    # ─────────────────────────────────────────────────────────────────────────
    def get_eligible_questions(
        self,
        interview_type: str,
        target_role: str,
        asked_ids: List[str],
        asked_texts: List[str],
        candidate_pool: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Filter available questions to those matching the interview context
        and not previously asked.
        """
        asked_id_set = {str(qid) for qid in asked_ids if qid}
        norm_asked_texts = {"".join(filter(str.isalnum, t.lower())) for t in asked_texts if t}

        pool_candidates: List[Dict[str, Any]] = []

        # If an external pool was provided, convert to unified dict
        if candidate_pool:
            for q in candidate_pool:
                pool_candidates.append(dict(q))
        else:
            # Use canonical catalog
            for q in self.catalog:
                pool_candidates.append({
                    "id": q.id,
                    "title": q.title,
                    "question_text": q.question_text,
                    "interview_type": q.interview_type,
                    "target_role": q.target_role,
                    "skill_focus": q.skill_focus,
                    "difficulty": q.difficulty,
                    "expected_time_minutes": q.expected_time_minutes,
                    "rubric": q.rubric,
                    "canonical_skills": q.canonical_skills,
                })

        eligible: List[Dict[str, Any]] = []
        norm_role = (target_role or "").lower()
        norm_type = (interview_type or "").lower()

        for q in pool_candidates:
            qid = str(q.get("id", ""))
            qtext = q.get("question_text", "")
            norm_qtext = "".join(filter(str.isalnum, qtext.lower()))

            # Deduplication check
            if qid and qid in asked_id_set:
                continue
            if norm_qtext and norm_qtext in norm_asked_texts:
                continue

            # Role/type matching check (broad compatibility)
            q_role = q.get("target_role", "").lower()
            q_type = q.get("interview_type", "").lower()

            matches_type = (
                norm_type in q_type
                or q_type in norm_type
                or norm_type in ("coding", "technical", "software engineer")
                or q_type in ("coding", "technical")
            )
            matches_role = (
                norm_role in q_role
                or q_role in norm_role
                or q_role == "general"
                or not norm_role
            )

            if matches_type or matches_role:
                eligible.append(q)

        # Fallback: if strict filtering emptied the pool, allow any unasked catalog question
        if not eligible and pool_candidates:
            for q in pool_candidates:
                qid = str(q.get("id", ""))
                if qid not in asked_id_set:
                    eligible.append(q)

        return eligible

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 4: Difficulty Prediction & Proximity Fit
    # ─────────────────────────────────────────────────────────────────────────
    def compute_difficulty_fit(
        self,
        candidate_theta: float,
        question: Dict[str, Any],
        target_difficulty: str = "intermediate",
    ) -> Tuple[float, str, float]:
        """
        Calculate difficulty fit in [0.0, 1.0] using 2PL-IRT Fisher Information
        and ability-difficulty proximity.

        Returns:
            (difficulty_fit, predicted_difficulty, model_confidence)
        """
        q_text = question.get("question_text", "")
        nominal_diff = question.get("difficulty", target_difficulty).lower()

        # ML signal: run difficulty predictor if question text is available
        predicted_diff = nominal_diff
        confidence = 0.85
        try:
            pred = self.difficulty_predictor.predict(q_text)
            pred_level = pred.get("predicted_difficulty")
            if pred_level and pred_level in DIFFICULTY_PRIORS:
                # If heuristic fallback and question has explicit difficulty, prefer explicit nominal difficulty
                if pred.get("method") == "deterministic_heuristic_fallback" and question.get("difficulty"):
                    predicted_diff = nominal_diff
                else:
                    predicted_diff = pred_level.lower()
            confidence = float(pred.get("confidence", 0.85))
        except Exception as e:
            logger.debug("Difficulty prediction fallback: %s", e)

        # Map predicted difficulty to 2PL-IRT difficulty parameter b
        b = DIFFICULTY_PRIORS.get(predicted_diff, 0.0)

        # Compute Gaussian proximity fit: highest when candidate ability matches question difficulty
        sigma = 1.2
        proximity = math.exp(-((candidate_theta - b) ** 2) / (2.0 * (sigma ** 2)))

        # Also incorporate Fisher Information: I(theta) = a^2 * p * (1 - p)
        # Peak information occurs at theta == b (where p = 0.5)
        p = self.irt.probability_correct(candidate_theta, b, discrimination_a=1.2)
        fisher_info = (1.2 ** 2) * p * (1.0 - p)
        normalized_info = fisher_info / 0.36  # Max possible info with a=1.2 is 0.36

        fit = round(proximity * 0.70 + normalized_info * 0.30, 4)
        return min(1.0, max(0.05, fit)), predicted_diff, round(confidence, 3)

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 5: Skill Coverage & Need Score
    # ─────────────────────────────────────────────────────────────────────────
    def compute_skill_need(
        self,
        target_skill: str,
        skill_states: Dict[str, Dict[str, Any]],
        role_skills: List[str],
    ) -> Tuple[float, float, str]:
        """
        Evaluate need score in [0.0, 1.0] for a skill based on:
        1. Weakness targeting (remediation priority)
        2. Curriculum deficit (untested skills in role matrix)

        Returns:
            (skill_need_score, current_mastery, primary_reason)
        """
        # Match target_skill against tracked skills (case-insensitive substring match)
        matched_state = None
        matched_skill_name = target_skill

        for s_name, state in skill_states.items():
            if s_name.lower() == target_skill.lower() or target_skill.lower() in s_name.lower() or s_name.lower() in target_skill.lower():
                matched_state = state
                matched_skill_name = s_name
                break

        if matched_state is None:
            # Untested skill not yet in state
            current_mastery = 0.50
            questions_count = 0
            weakness_severity = 0.0
            is_weakness = False
        else:
            current_mastery = matched_state["mastery"]
            questions_count = matched_state["questions_count"]
            weakness_severity = matched_state["weakness_severity"]
            is_weakness = matched_state["is_weakness"]

        # 1. Weakness remediation need
        if is_weakness and weakness_severity > 0.0:
            need = 0.60 + 0.40 * weakness_severity
            reason = f"Probing active weakness in {matched_skill_name} (mastery: {current_mastery}, severity: {weakness_severity})"
        # 2. Untested curriculum skill
        elif questions_count == 0:
            # High priority to cover untested role skills
            is_core_role_skill = any(target_skill.lower() in r.lower() or r.lower() in target_skill.lower() for r in role_skills)
            need = 0.75 if is_core_role_skill else 0.55
            reason = f"Broadening assessment — {matched_skill_name} has not yet been evaluated"
        # 3. Already tested skill without active weakness
        else:
            # Diminishing returns: lower priority for repeatedly tested proficient skills
            need = max(0.10, 0.40 / (1.0 + questions_count))
            reason = f"Re-evaluating {matched_skill_name} (already tested {questions_count}x, mastery: {current_mastery})"

        return round(min(1.0, max(0.05, need)), 4), round(current_mastery, 2), reason

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 6: Semantic Deduplication & Novelty
    # ─────────────────────────────────────────────────────────────────────────
    def compute_semantic_novelty(
        self,
        candidate_question_text: str,
        previous_question_texts: List[str],
    ) -> Tuple[float, float, Optional[str]]:
        """
        Evaluate semantic novelty in [0.0, 1.0] by computing dense embedding
        cosine similarity against previously asked questions.

        Returns:
            (novelty, max_similarity, most_similar_text)
        """
        if not previous_question_texts:
            return 1.0, 0.0, None

        cand_emb = self.embedding_extractor.encode(candidate_question_text)
        max_sim = 0.0
        most_sim_text = None

        for prev_text in previous_question_texts:
            if not prev_text:
                continue
            prev_emb = self.embedding_extractor.encode(prev_text)
            sim = compute_cosine_similarity(cand_emb, prev_emb)

            # Exact text or subset match guard
            norm_cand = "".join(filter(str.isalnum, candidate_question_text.lower()))
            norm_prev = "".join(filter(str.isalnum, prev_text.lower()))
            if norm_cand == norm_prev or (len(norm_cand) > 30 and norm_cand in norm_prev):
                sim = 1.0

            if sim > max_sim:
                max_sim = sim
                most_sim_text = prev_text

        novelty = round(max(0.0, 1.0 - max_sim), 4)
        return novelty, round(max_sim, 4), most_sim_text

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 7: Time Budget Pacing Factor
    # ─────────────────────────────────────────────────────────────────────────
    def compute_time_budget_factor(
        self,
        question: Dict[str, Any],
        remaining_seconds: int,
        total_budget_seconds: int,
        questions_remaining: int,
    ) -> float:
        """
        Adjust question fit based on remaining interview time budget.
        If time is running out, favors concise questions over lengthy system design problems.
        """
        if questions_remaining <= 0:
            return 1.0

        est_minutes = float(question.get("expected_time_minutes", 15))
        est_seconds = est_minutes * 60.0

        avg_remaining_per_q = float(remaining_seconds) / float(questions_remaining)

        if avg_remaining_per_q <= 0:
            # Over budget: heavily favor shortest questions
            return round(max(0.1, 1.0 - (est_minutes / 30.0)), 3)

        # Ratio of available time to estimated time
        ratio = avg_remaining_per_q / max(60.0, est_seconds)

        if ratio >= 1.0:
            # Adequate time
            return 1.0
        else:
            # Constrained time: penalize long questions proportionally
            return round(max(0.15, ratio), 3)

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 8 & 9: Full Adaptive Ranking Pipeline & Next Question Selection
    # ─────────────────────────────────────────────────────────────────────────
    def select_next_question(
        self,
        candidate_skill_state: Optional[Dict[str, Any]] = None,
        current_difficulty: str = "intermediate",
        previous_question_history: Optional[List[Any]] = None,
        recent_evaluation_evidence: Optional[Dict[str, Any]] = None,
        candidate_questions_pool: Optional[List[Dict[str, Any]]] = None,
        time_budget_seconds: int = 2700,
        elapsed_seconds: int = 0,
        max_questions: int = 5,
        target_role: str = "Software Engineer",
        interview_type: str = "coding",
        role_skills: Optional[List[str]] = None,
        candidate_theta: Optional[float] = None,
        asked_question_ids: Optional[List[str]] = None,
        target_skills: Optional[List[str]] = None,
        skill_coverage_counts: Optional[Dict[str, int]] = None,
        exploration_prob: float = 0.0,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Execute the deterministic adaptive ranking pipeline.

        Returns:
            {
                "selected_question": Dict[str, Any],
                "decision": Dict[str, Any],         # Exact user schema
                "all_decisions": List[Dict[str, Any]],
                "why_selected": str,                # Evidence-based explainability text
                "target_skill": str,
                "current_mastery": float,
                "model_versions": List[str]
            }
        """
        t0 = time.time()
        candidate_skill_state = dict(candidate_skill_state or {})
        previous_question_history = list(previous_question_history or [])

        # Backward compatibility for legacy test signatures
        if target_skills:
            role_skills = role_skills or target_skills
        role_skills = role_skills or ["Data Structures & Algorithms", "Problem Solving", "System Design", "Programming Fundamentals"]

        if skill_coverage_counts:
            for sk, cnt in skill_coverage_counts.items():
                if sk not in candidate_skill_state:
                    candidate_skill_state[sk] = {
                        "mastery": 0.80 if cnt > 0 else 0.50,
                        "questions_count": cnt,
                        "scores": [80.0] * cnt if cnt > 0 else [],
                        "weaknesses": [],
                        "strengths": [],
                    }

        # Extract history text and IDs
        asked_ids = list(asked_question_ids or [])
        asked_texts = []
        for q in previous_question_history:
            if hasattr(q, "question_id"):
                asked_ids.append(q.question_id)
            elif isinstance(q, dict) and "question_id" in q:
                asked_ids.append(q["question_id"])
            elif isinstance(q, dict) and "id" in q:
                asked_ids.append(q["id"])

            if hasattr(q, "question_text"):
                asked_texts.append(q.question_text)
            elif isinstance(q, dict) and "question_text" in q:
                asked_texts.append(q["question_text"])

        # Estimate candidate theta from explicit param, skill state, or history
        if candidate_theta is None:
            candidate_theta = 0.0
            if isinstance(candidate_skill_state, dict):
                theta_val = candidate_skill_state.get("_candidate_theta")
                if theta_val is not None:
                    candidate_theta = float(theta_val)
                else:
                    # Average theta from skill signals
                    thetas = [
                        getattr(s, "theta", 0.0) if hasattr(s, "theta") else s.get("theta", 0.0)
                        for s in candidate_skill_state.values()
                        if isinstance(s, (dict, object))
                    ]
                    if thetas:
                        candidate_theta = sum(thetas) / len(thetas)

        # 1. Synthesize candidate skill state & weaknesses
        skill_states = self.assess_candidate_skill_state(
            candidate_skill_state,
            previous_question_history,
            candidate_theta,
        )

        # 2. Retrieve eligible questions
        eligible = self.get_eligible_questions(
            interview_type=interview_type,
            target_role=target_role,
            asked_ids=asked_ids,
            asked_texts=asked_texts,
            candidate_pool=candidate_questions_pool,
        )

        if not eligible:
            # Emergency fallback: construct a targeted diagnostic question
            logger.warning("Eligible question pool exhausted. Generating fallback diagnostic.")
            fallback_q = {
                "id": f"diagnostic_{int(time.time())}",
                "title": "Comprehensive Technical Assessment",
                "question_text": f"Explain your approach to designing a resilient, scalable solution for a high-concurrency problem in {target_role}.",
                "interview_type": interview_type,
                "target_role": target_role,
                "skill_focus": role_skills[0] if role_skills else "Problem Solving",
                "difficulty": current_difficulty,
                "expected_time_minutes": 15,
                "rubric": "Evaluates architectural trade-offs, concurrency handling, and structured communication.",
                "canonical_skills": ["System Design", "Problem Solving"],
            }
            eligible = [fallback_q]

        # 3. Calculate remaining budget
        remaining_seconds = max(0, time_budget_seconds - elapsed_seconds)
        questions_remaining = max(1, max_questions - len(previous_question_history))

        # 4. Score every eligible question across the multi-factor decision layer
        scored_candidates: List[Dict[str, Any]] = []

        w_skill = self.weights["skill_need"]
        w_diff = self.weights["difficulty_fit"]
        w_nov = self.weights["novelty"]
        w_time = self.weights["time_budget"]

        for q in eligible:
            q_skill = q.get("skill_focus") or q.get("domain", role_skills[0])
            q_text = q.get("question_text", "")

            # Factor A: Skill Need (weakness targeting + coverage deficit)
            skill_need, current_mastery, skill_reason = self.compute_skill_need(
                q_skill, skill_states, role_skills
            )

            # Factor B: Difficulty Fit (IRT proximity + Fisher info)
            difficulty_fit, predicted_diff, diff_conf = self.compute_difficulty_fit(
                candidate_theta, q, target_difficulty=current_difficulty
            )

            # Factor C: Semantic Novelty (deduplication vs previous questions)
            novelty, max_sim, most_sim_text = self.compute_semantic_novelty(
                q_text, asked_texts
            )

            # Factor D: Time Budget Factor
            time_factor = self.compute_time_budget_factor(
                q, remaining_seconds, time_budget_seconds, questions_remaining
            )

            # COMPOSITE SCORE (0.0 to 1.0)
            composite_score = (
                w_skill * skill_need
                + w_diff * difficulty_fit
                + w_nov * novelty
                + w_time * time_factor
            )

            # Severe semantic penalty: if question is essentially a duplicate (>0.85 similarity)
            if max_sim > 0.85:
                composite_score *= 0.10

            scored_candidates.append({
                "question": q,
                "candidate_skill": q_skill,
                "current_mastery": current_mastery,
                "target_skill": q_skill,
                "candidate_question_score": round(composite_score, 4),
                "difficulty_fit": round(difficulty_fit, 4),
                "novelty": round(novelty, 4),
                "time_budget_factor": round(time_factor, 4),
                "skill_need": round(skill_need, 4),
                "predicted_difficulty": predicted_diff,
                "max_similarity": round(max_sim, 4),
                "most_similar_text": most_sim_text,
                "skill_reason": skill_reason,
            })

        # 5. Deterministic sorting: highest composite score wins
        # Tie-breaker: higher difficulty_fit, then higher novelty, then deterministic ID hash
        scored_candidates.sort(
            key=lambda c: (
                c["candidate_question_score"],
                c["difficulty_fit"],
                c["novelty"],
                -hash(str(c["question"].get("id", ""))),
            ),
            reverse=True,
        )

        # Winning candidate
        winner = scored_candidates[0]
        selected_q = winner["question"]

        # Build structured decision logs for all evaluated candidates
        all_decisions: List[Dict[str, Any]] = []
        for i, c in enumerate(scored_candidates):
            is_selected = (i == 0)
            decision_entry = {
                "candidate_skill": c["candidate_skill"],
                "current_mastery": c["current_mastery"],
                "target_skill": c["target_skill"],
                "candidate_question_score": c["candidate_question_score"],
                "difficulty_fit": c["difficulty_fit"],
                "novelty": c["novelty"],
                "selected": is_selected,
                "model_versions": list(MODEL_VERSIONS),
            }
            all_decisions.append(decision_entry)

        selected_decision = all_decisions[0]

        # 6. Generate explainability text: "Why was this question selected?"
        why_selected = self.generate_selection_explanation(
            winner=winner,
            previous_history=previous_question_history,
            candidate_theta=candidate_theta,
            remaining_seconds=remaining_seconds,
            questions_remaining=questions_remaining,
        )

        return {
            "selected_question": selected_q,
            "decision": selected_decision,
            "all_decisions": all_decisions,
            "why_selected": why_selected,
            "target_skill": winner["target_skill"],
            "current_mastery": winner["current_mastery"],
            "model_versions": list(MODEL_VERSIONS),
            "selection_latency_ms": round((time.time() - t0) * 1000.0, 2),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 10: Explainability Generator
    # ─────────────────────────────────────────────────────────────────────────
    def generate_selection_explanation(
        self,
        winner: Dict[str, Any],
        previous_history: List[Any],
        candidate_theta: float,
        remaining_seconds: int,
        questions_remaining: int,
    ) -> str:
        """
        Synthesize evidence from candidate's actual session history into a clear,
        auditable explanation answering: "Why was this question selected?".
        """
        q = winner["question"]
        q_title = q.get("title") or q.get("question_text", "")[:40]
        skill = winner["target_skill"]
        mastery = winner["current_mastery"]
        score = winner["candidate_question_score"]
        fit = winner["difficulty_fit"]
        diff = winner["predicted_difficulty"]
        novelty = winner["novelty"]

        reasons: List[str] = []

        # Skill & mastery rationale
        reasons.append(
            f"Question '{q_title}' was selected (overall score: {score:.2f}) targeting skill '{skill}' "
            f"(candidate current mastery: {mastery:.2f})."
        )

        # Historical evidence from session
        history_evidence = []
        for i, prev in enumerate(previous_history):
            prev_score = getattr(prev, "score", None)
            if prev_score is None and isinstance(prev, dict):
                prev_score = prev.get("score")
            prev_skill = getattr(prev, "skill_focus", "")
            if not prev_skill and isinstance(prev, dict):
                prev_skill = prev.get("skill_focus", "")

            if prev_score is not None:
                if prev_score < 65.0:
                    history_evidence.append(
                        f"In question {i+1} on '{prev_skill}', candidate scored {prev_score:.0f}%, indicating need for reinforcement."
                    )
                elif prev_skill.lower() == skill.lower():
                    history_evidence.append(
                        f"In question {i+1}, candidate scored {prev_score:.0f}% on '{prev_skill}'."
                    )

        if history_evidence:
            reasons.append(" " + " ".join(history_evidence))
        else:
            reasons.append(
                f" This skill has not yet been thoroughly assessed in the current session."
            )

        # Difficulty fit rationale
        reasons.append(
            f" Difficulty fit is {fit:.2f} (predicted level '{diff}' matches candidate latent ability theta={candidate_theta:+.2f})."
        )

        # Semantic novelty rationale
        reasons.append(
            f" Semantic novelty is {novelty:.2f}, verifying distinct conceptual ground from previous questions."
        )

        # Time budget rationale
        rem_min = int(remaining_seconds // 60)
        reasons.append(
            f" Remaining time budget is {rem_min}m ({questions_remaining} questions left), matching question duration."
        )

        return "".join(reasons)
