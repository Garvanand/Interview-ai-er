"""
Question Skill/Topic Classification Model.
Category: TRAINED BY US (TF-IDF + OneVsRest Classifier on BAAI/TACO).
Taxonomy: 21 Canonical Skills compatible with Interview-ai-er.
"""
from __future__ import annotations

import os
import re
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path
from ml.versioning import stamp_inference
from ml.calibration import get_confidence_metadata

logger = logging.getLogger(__name__)

CANONICAL_SKILLS = [
    "arrays",
    "hashing",
    "strings",
    "sorting",
    "search",
    "two_pointers",
    "sliding_window",
    "trees",
    "graphs",
    "dynamic_programming",
    "greedy",
    "backtracking",
    "heaps",
    "stacks",
    "queues",
    "linked_lists",
    "binary_search",
    "recursion",
    "complexity",
    "data_structures",
    "algorithms",
]

DEFAULT_WEIGHTS_PATH = "ml/models/weights/skill_classifier.joblib"


class QuestionSkillClassifier:
    """Classifies interview questions into canonical technical skills."""

    def __init__(self, weights_path: Optional[str] = None):
        self.weights_path = weights_path or self._find_default_weights()
        self._model = None
        self._vectorizer = None
        self._threshold = 0.35
        self.model_version = "1.0.0"
        self.skills_list = CANONICAL_SKILLS
        self._load_weights()

    def _find_default_weights(self) -> Optional[str]:
        candidates = [
            Path(DEFAULT_WEIGHTS_PATH),
            Path(__file__).parent / "weights" / "skill_classifier.joblib",
        ]
        for p in candidates:
            if p.exists():
                return str(p.resolve())
        return None

    def _load_weights(self):
        if not self.weights_path or not os.path.exists(self.weights_path):
            logger.warning("Weights path %s not found. Using heuristic taxonomy fallback.", self.weights_path)
            return
        try:
            import joblib
            data = joblib.load(self.weights_path)
            if isinstance(data, dict) and "classifier" in data and "vectorizer" in data:
                self._model = data["classifier"]
                self._vectorizer = data["vectorizer"]
                self.skills_list = data.get("canonical_skills", CANONICAL_SKILLS)
                self._threshold = data.get("threshold", 0.35)
                self.model_version = data.get("model_version", "1.0.0")
            else:
                self._model = data
            logger.info("Loaded skill classifier from %s (version: %s)", self.weights_path, self.model_version)
        except Exception as e:
            logger.warning("Could not load skill classifier weights: %s. Using heuristic fallback.", e)
            self._model = None

    def predict(self, question_text: str, threshold: Optional[float] = None, top_k: int = 5) -> Dict[str, Any]:
        """
        Predict skills associated with question text.
        Returns:
        {
            "skills": [
                {
                    "skill": "dynamic_programming",
                    "confidence": 0.91
                }
            ],
            "top_skills": ["dynamic_programming"],
            "model_version": "1.0.0",
            "method": "trained_multilabel_classifier"
        }
        """
        if not isinstance(question_text, str) or not question_text.strip():
            return {
                "skills": [],
                "top_skills": ["algorithms"],
                "confidence_scores": {},
                "confidence": 0.0,
                "model_version": "unavailable",
                "method": "malformed_input_handler",
                "source": "unavailable",
                "error": "Malformed input: question_text must be a non-empty string",
            }

        th = threshold if threshold is not None else self._threshold

        if self._model is not None and self._vectorizer is not None:
            try:
                X = self._vectorizer.transform([question_text])
                probs = self._model.predict_proba(X)[0]
                
                scored_skills = []
                for idx, skill in enumerate(self.skills_list):
                    prob = float(probs[idx])
                    scored_skills.append((skill, prob))
                
                scored_skills.sort(key=lambda x: x[1], reverse=True)
                
                # Filter by threshold or at least top 1
                filtered = [(s, p) for s, p in scored_skills if p >= th]
                if not filtered:
                    filtered = [scored_skills[0]]
                
                filtered = filtered[:top_k]
                skills_out = [
                    {"skill": s, "confidence": round(p, 2)}
                    for s, p in filtered
                ]
                
                _raw_conf = skills_out[0]["confidence"] if skills_out else 0.0
                _conf_meta = get_confidence_metadata("question-skill-v1", _raw_conf, source_tier="ml")
                ml_res = {
                    "skills": skills_out,
                    "top_skills": [s["skill"] for s in skills_out],
                    "confidence_scores": {s["skill"]: s["confidence"] for s in skills_out},
                    "confidence": _raw_conf,
                    "model_version": self.model_version,
                    "method": "trained_multilabel_classifier",
                    "source": "ml",
                    "confidence_metadata": _conf_meta.to_dict(),
                    "confidence_band": _conf_meta.confidence_band.value,
                }
                return stamp_inference("question-skill-v1", ml_res)
            except Exception as e:
                logger.warning("Error running classifier inference: %s. Falling back to heuristics.", e)

        # DETERMINISTIC TAXONOMY HEURISTIC FALLBACK
        text = question_text.lower()
        matches: Dict[str, float] = {}

        rules = {
            "arrays": (r"\b(array|arrays|subarray|subarrays|matrix|matrices|elements of array|vector)\b", 0.75),
            "strings": (r"\b(string|strings|substring|substrings|palindrome|anagram|prefix|suffix|character|characters)\b", 0.80),
            "hashing": (r"\b(hash|hashes|hashing|hashmap|hash map|hashset|hash table|hash tables|dictionary|frequency)\b", 0.85),
            "sorting": (r"\b(sort|sorted|sorting|quicksort|mergesort|ascending|descending|order)\b", 0.75),
            "search": (r"\b(search|searching|find|locate|lookup|query|queries|complete search)\b", 0.70),
            "two_pointers": (r"\b(two pointer|two pointers|two-pointer|two-pointers|left and right pointer|two index|two indices)\b", 0.85),
            "sliding_window": (r"\b(sliding window|sliding-window|window of size|window of length|window of at most)\b", 0.90),
            "trees": (r"\b(tree|trees|binary tree|bst|subtree|root|leaf|ancestor|lca)\b", 0.85),
            "graphs": (r"\b(graph|graphs|vertex|vertices|edge|edges|adjacency|directed|undirected|dag|cycle|shortest path|dijkstra|bfs|dfs)\b", 0.85),
            "dynamic_programming": (r"\b(dp|memoization|optimal substructure|subproblem|knapsack|fibonacci|longest common|dynamic programming)\b", 0.90),
            "greedy": (r"\b(greedy|locally optimal|interval scheduling|fractional knapsack|greedily)\b", 0.85),
            "backtracking": (r"\b(backtrack|backtracking|n-queens|permutations|combinations|subset sum|exhaustive search)\b", 0.85),
            "heaps": (r"\b(heap|heaps|priority queue|priority-queue|min-heap|max-heap|heapify|top k|kth largest)\b", 0.85),
            "stacks": (r"\b(stack|stacks|push|pop|lifo|valid parentheses|balanced brackets|monotonic stack)\b", 0.85),
            "queues": (r"\b(queue|queues|deque|fifo|enqueue|dequeue|circular queue)\b", 0.85),
            "linked_lists": (r"\b(linked list|linked-list|linked lists|singly linked|doubly linked|node->next|next pointer|head node)\b", 0.90),
            "binary_search": (r"\b(binary search|binary-search|logarithmic time|bisection|lower bound|upper bound)\b", 0.88),
            "recursion": (r"\b(recursion|recursive|recursively|base case|recurrence|divide and conquer)\b", 0.80),
            "complexity": (r"\b(time complexity|space complexity|o\(n\)|o\(log|big-o|amortized|runtime constraint)\b", 0.75),
            "data_structures": (r"\b(data structure|data structures|container|collection|node)\b", 0.70),
            "algorithms": (r"\b(algorithm|algorithms|algorithmic|optimal strategy|efficient|solution|system|distributed|cache|caching)\b", 0.70),
        }

        for skill, (pattern, base_score) in rules.items():
            found = len(re.findall(pattern, text))
            if found > 0:
                score = min(0.98, base_score + (found - 1) * 0.05)
                matches[skill] = score

        if not matches:
            matches["algorithms"] = 0.50

        sorted_matches = sorted(matches.items(), key=lambda x: x[1], reverse=True)[:top_k]
        skills_out = [
            {"skill": s, "confidence": round(p, 2)}
            for s, p in sorted_matches
        ]

        _raw_conf = skills_out[0]["confidence"] if skills_out else 0.50
        _conf_meta = get_confidence_metadata("question-skill-v1", _raw_conf, source_tier="deterministic")
        heuristic_res = {
            "skills": skills_out,
            "top_skills": [s["skill"] for s in skills_out],
            "confidence_scores": {s["skill"]: s["confidence"] for s in skills_out},
            "confidence": _raw_conf,
            "model_version": "heuristic_fallback_v1",
            "method": "deterministic_keyword_taxonomy",
            "source": "deterministic",
            "confidence_metadata": _conf_meta.to_dict(),
            "confidence_band": _conf_meta.confidence_band.value,
        }
        return stamp_inference("question-skill-v1", heuristic_res, version_override="heuristic_fallback_v1")
