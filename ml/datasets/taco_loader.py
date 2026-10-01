"""
TACO (Topics in Algorithmic Code and Optimization) Dataset Loader.
Source: BAAI/TACO (Hugging Face)
https://huggingface.co/datasets/BAAI/TACO

Used for:
- Question Difficulty Prediction
- Question Skill/Topic Classification
"""
from __future__ import annotations

import os
import ast
import re
import logging
from typing import Any, Dict, Generator, List, Optional
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Canonical 21-skill taxonomy compatible with Interview-ai-er
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

DIFFICULTY_MAP = {
    "EASY": "beginner",
    "MEDIUM": "intermediate",
    "MEDIUM_HARD": "advanced",
    "HARD": "advanced",
    "VERY_HARD": "advanced",
}

# Mapping layer: Raw TACO tags / skill_types -> Canonical Skills
TAG_MAPPING_LAYER = {
    # Dynamic programming
    "dynamic programming": ["dynamic_programming", "algorithms"],
    "dp": ["dynamic_programming", "algorithms"],
    "memoization": ["dynamic_programming", "algorithms"],
    "longest common subsequence": ["dynamic_programming", "algorithms"],
    
    # Sorting
    "sorting": ["sorting", "algorithms"],
    "sortings": ["sorting", "algorithms"],
    "sort": ["sorting", "algorithms"],
    
    # Search
    "complete search": ["search", "algorithms"],
    "search": ["search", "algorithms"],
    "binary search": ["binary_search", "search", "algorithms"],
    "ternary search": ["search", "algorithms"],
    
    # Graphs and Trees
    "graph algorithms": ["graphs", "algorithms"],
    "graph traversal": ["graphs", "algorithms"],
    "directed graphs": ["graphs", "data_structures"],
    "shortest paths": ["graphs", "algorithms"],
    "strong connectivity": ["graphs", "algorithms"],
    "flows and cuts": ["graphs", "algorithms"],
    "graphs": ["graphs", "data_structures"],
    "graph": ["graphs", "data_structures"],
    "tree algorithms": ["trees", "algorithms"],
    "tree queries": ["trees", "data_structures"],
    "trees": ["trees", "data_structures"],
    "tree": ["trees", "data_structures"],
    "spanning trees": ["trees", "graphs", "data_structures"],
    "segment trees revisited": ["trees", "data_structures"],
    "range queries": ["trees", "data_structures"],
    
    # Greedy
    "greedy algorithms": ["greedy", "algorithms"],
    "greedy": ["greedy", "algorithms"],
    
    # Divide & Conquer / Recursion / Backtracking
    "divide and conquer": ["recursion", "algorithms"],
    "recursion": ["recursion", "algorithms"],
    "backtracking": ["backtracking", "recursion", "algorithms"],
    
    # Strings
    "string algorithms": ["strings", "algorithms"],
    "strings": ["strings"],
    "string": ["strings"],
    
    # Complexity
    "amortized analysis": ["complexity"],
    "complexity": ["complexity"],
    
    # Matrices & Arrays
    "matrices": ["arrays", "data_structures"],
    "arrays": ["arrays", "data_structures"],
    "array": ["arrays", "data_structures"],
    
    # Data structures
    "data structures": ["data_structures"],
    "hashing": ["hashing", "data_structures"],
    "hash table": ["hashing", "data_structures"],
    "heaps": ["heaps", "data_structures"],
    "heap": ["heaps", "data_structures"],
    "priority queue": ["heaps", "queues", "data_structures"],
    "stacks": ["stacks", "data_structures"],
    "stack": ["stacks", "data_structures"],
    "queues": ["queues", "data_structures"],
    "queue": ["queues", "data_structures"],
    "linked lists": ["linked_lists", "data_structures"],
    "linked list": ["linked_lists", "data_structures"],
    "two pointers": ["two_pointers", "arrays", "algorithms"],
    "sliding window": ["sliding_window", "arrays", "algorithms"],
    
    # Algorithmic methods
    "constructive algorithms": ["algorithms"],
    "bit manipulation": ["algorithms"],
    "implementation": ["algorithms"],
    "mathematics": ["algorithms"],
    "number theory": ["algorithms"],
    "combinatorics": ["algorithms"],
    "geometry": ["algorithms"],
    "game theory": ["algorithms"],
    "probability": ["algorithms"],
    "ad-hoc": ["algorithms"],
    "fundamentals": ["algorithms"],
    "square root algorithms": ["algorithms"],
    "sweep line algorithms": ["algorithms"],
    "polynomials and generating functions": ["algorithms"],
}

REGEX_SKILL_PATTERNS = {
    "arrays": r"\b(array|arrays|subarray|subarrays|matrix|matrices|vector|elements of array|contiguous subarray)\b",
    "strings": r"\b(string|strings|substring|substrings|palindrome|anagram|prefix|suffix|character|characters|alphabet)\b",
    "hashing": r"\b(hash|hashes|hashing|hashmap|hash map|hashset|hash table|hash tables|dictionary|frequencies|occurrences)\b",
    "two_pointers": r"\b(two pointer|two pointers|two-pointer|two-pointers|left and right pointer|two index|two indices|pointer from both ends)\b",
    "sliding_window": r"\b(sliding window|sliding-window|window of size|window of length|window of at most|contiguous subsegment of length)\b",
    "binary_search": r"\b(binary search|binary-search|logarithmic time|bisection|lower bound|upper bound|search range|bisect)\b",
    "search": r"\b(search|searching|find the index|locate|lookup|query|queries|complete search)\b",
    "sorting": r"\b(sort|sorted|sorting|quicksort|mergesort|ascending|descending|lexicographical)\b",
    "trees": r"\b(tree|trees|binary tree|bst|subtree|root|leaf|ancestor|lca)\b",
    "graphs": r"\b(graph|graphs|vertex|vertices|edge|edges|adjacency|directed|undirected|dag|cycle|shortest path|dijkstra|bfs|dfs)\b",
    "dynamic_programming": r"\b(dp|memoization|optimal substructure|subproblem|knapsack|fibonacci|longest common|dynamic programming)\b",
    "greedy": r"\b(greedy|locally optimal|interval scheduling|fractional knapsack|greedily)\b",
    "backtracking": r"\b(backtrack|backtracking|n-queens|permutations|combinations|subset sum|exhaustive search)\b",
    "heaps": r"\b(heap|heaps|priority queue|priority-queue|min-heap|max-heap|heapify|top k|kth largest|kth smallest)\b",
    "stacks": r"\b(stack|stacks|push|pop|lifo|valid parentheses|balanced brackets|monotonic stack|monotone stack|next greater)\b",
    "queues": r"\b(queue|queues|deque|fifo|enqueue|dequeue|circular queue)\b",
    "linked_lists": r"\b(linked list|linked-list|linked lists|singly linked|doubly linked|node->next|next pointer|dummy node|head node)\b",
    "recursion": r"\b(recursion|recursive|recursively|base case|recurrence|divide and conquer)\b",
    "complexity": r"\b(time complexity|space complexity|o\(n\)|o\(log|big-o|amortized|runtime constraint)\b",
    "data_structures": r"\b(data structure|data structures|container|collection)\b",
    "algorithms": r"\b(algorithm|algorithms|algorithmic|optimal strategy|efficient)\b",
}


def map_to_canonical_skills(
    tags: Optional[List[str]] = None,
    skill_types: Optional[List[str]] = None,
    question_text: str = ""
) -> List[str]:
    """
    Applies the mapping layer to transform raw TACO dataset tags, skill_types,
    and problem statement signals into the canonical 21-skill taxonomy.
    """
    mapped_skills = set()

    # 1. Process dataset tags
    if tags:
        for tag in tags:
            tag_clean = str(tag).strip().lower()
            if tag_clean in TAG_MAPPING_LAYER:
                mapped_skills.update(TAG_MAPPING_LAYER[tag_clean])

    # 2. Process dataset skill_types
    if skill_types:
        for sk in skill_types:
            sk_clean = str(sk).strip().lower()
            if sk_clean in TAG_MAPPING_LAYER:
                mapped_skills.update(TAG_MAPPING_LAYER[sk_clean])

    # 3. Process problem text signals for precision
    text_lower = question_text.lower()
    for skill, pattern in REGEX_SKILL_PATTERNS.items():
        if re.search(pattern, text_lower):
            # Target specific structural signals
            if skill in [
                "two_pointers", "sliding_window", "binary_search",
                "heaps", "stacks", "queues", "linked_lists",
                "backtracking", "recursion", "complexity", "hashing"
            ]:
                mapped_skills.add(skill)
                if skill in ["heaps", "stacks", "queues", "linked_lists", "hashing"]:
                    mapped_skills.add("data_structures")
                if skill in ["binary_search", "backtracking", "two_pointers", "sliding_window", "recursion"]:
                    mapped_skills.add("algorithms")

    # If empty, default to general algorithmic problem solving
    if not mapped_skills:
        mapped_skills.add("algorithms")

    # Ensure all returned skills are valid canonical taxonomy members
    return sorted([s for s in mapped_skills if s in CANONICAL_SKILLS])


@dataclass
class TACOSample:
    question_id: str
    question_text: str
    difficulty_raw: str
    difficulty_normalized: str
    tags: List[str]
    skill_types: List[str] = field(default_factory=list)
    canonical_skills: List[str] = field(default_factory=list)
    input_output: Optional[Dict[str, Any]] = None
    starter_code: Optional[str] = None


class TACODatasetLoader:
    """Loads and normalizes BAAI/TACO dataset samples with canonical skill mapping."""

    def __init__(self, split: str = "train", streaming: bool = True, local_path: Optional[str] = None):
        self.split = split
        self.streaming = streaming
        self.local_path = local_path or self._find_local_parquet()

    def _find_local_parquet(self) -> Optional[str]:
        candidates = [
            Path("ml/data/taco_train_shard0.parquet"),
            Path("ml/data/taco_train.parquet"),
            Path(__file__).parent.parent / "data" / "taco_train_shard0.parquet",
            Path(__file__).parent.parent / "data" / "taco_train.parquet",
        ]
        for p in candidates:
            if p.exists() and p.stat().st_size > 0:
                return str(p.resolve())
        return None

    def _parse_list_field(self, raw_val: Any) -> List[str]:
        if not raw_val:
            return []
        if isinstance(raw_val, list):
            return [str(x).strip() for x in raw_val if str(x).strip()]
        if isinstance(raw_val, str):
            s = raw_val.strip()
            if s.startswith("[") and s.endswith("]"):
                try:
                    parsed = ast.literal_eval(s)
                    if isinstance(parsed, list):
                        return [str(x).strip() for x in parsed if str(x).strip()]
                except Exception:
                    pass
            return [t.strip() for t in s.split(",") if t.strip()]
        return []

    def load_samples(self, limit: Optional[int] = None) -> Generator[TACOSample, None, None]:
        """Yield normalized TACO samples mapped to canonical skills."""
        # Method 1: Local Parquet file (fastest, offline-safe)
        if self.local_path and os.path.exists(self.local_path):
            try:
                import pandas as pd
                logger.info("Loading TACO samples from local parquet: %s", self.local_path)
                df = pd.read_parquet(self.local_path)
                count = 0
                for idx, row in df.iterrows():
                    if limit and count >= limit:
                        break
                    
                    q_text = str(row.get("question", "")).strip()
                    if not q_text:
                        continue
                    
                    raw_diff = str(row.get("difficulty", "MEDIUM")).upper()
                    norm_diff = DIFFICULTY_MAP.get(raw_diff, "intermediate")
                    tags = self._parse_list_field(row.get("tags"))
                    skill_types = self._parse_list_field(row.get("skill_types"))
                    canonical = map_to_canonical_skills(tags, skill_types, q_text)

                    yield TACOSample(
                        question_id=str(row.get("id", count)),
                        question_text=q_text,
                        difficulty_raw=raw_diff,
                        difficulty_normalized=norm_diff,
                        tags=tags,
                        skill_types=skill_types,
                        canonical_skills=canonical,
                        starter_code=row.get("starter_code"),
                    )
                    count += 1
                return
            except Exception as e:
                logger.warning("Failed loading from local parquet %s: %s", self.local_path, e)

        # Method 2: Remote Parquet URL
        try:
            import pandas as pd
            remote_url = "https://huggingface.co/datasets/BAAI/TACO/resolve/main/ALL/train-00000-of-00009.parquet"
            logger.info("Loading TACO samples from remote parquet: %s", remote_url)
            df = pd.read_parquet(remote_url)
            count = 0
            for idx, row in df.iterrows():
                if limit and count >= limit:
                    break
                q_text = str(row.get("question", "")).strip()
                if not q_text:
                    continue
                raw_diff = str(row.get("difficulty", "MEDIUM")).upper()
                norm_diff = DIFFICULTY_MAP.get(raw_diff, "intermediate")
                tags = self._parse_list_field(row.get("tags"))
                skill_types = self._parse_list_field(row.get("skill_types"))
                canonical = map_to_canonical_skills(tags, skill_types, q_text)

                yield TACOSample(
                    question_id=str(row.get("id", count)),
                    question_text=q_text,
                    difficulty_raw=raw_diff,
                    difficulty_normalized=norm_diff,
                    tags=tags,
                    skill_types=skill_types,
                    canonical_skills=canonical,
                    starter_code=row.get("starter_code"),
                )
                count += 1
            return
        except Exception as e:
            logger.warning("Failed loading from remote parquet: %s. Using bootstrap data.", e)

        # Method 3: Bootstrap Fallback
        bootstrap_data = [
            ("Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.", ["arrays", "hashing", "two_pointers", "data_structures", "algorithms"]),
            ("Given a string s, find the length of the longest substring without repeating characters.", ["strings", "sliding_window", "hashing", "two_pointers", "algorithms"]),
            ("Given an array of intervals intervals where intervals[i] = [starti, endi], merge all overlapping intervals.", ["arrays", "sorting", "algorithms"]),
            ("Given the root of a binary tree, return its maximum depth.", ["trees", "recursion", "data_structures", "algorithms"]),
            ("There are a total of numCourses courses you have to take, labeled from 0 to numCourses - 1. You are given prerequisites. Find if possible to finish.", ["graphs", "search", "data_structures", "algorithms"]),
            ("You are given an integer array coins representing coins of different denominations and an integer amount. Return fewest coins needed.", ["dynamic_programming", "algorithms"]),
            ("You are given an array of k linked-lists lists, each linked-list is sorted in ascending order. Merge all into one sorted linked-list.", ["linked_lists", "heaps", "sorting", "data_structures", "algorithms"]),
            ("Given an array of integers nums sorted in non-decreasing order, find the starting and ending position of a given target value in O(log n).", ["binary_search", "search", "arrays", "complexity", "algorithms"]),
            ("Implement a MyQueue class using two stacks. The queue should support push, pop, peek, and empty.", ["stacks", "queues", "data_structures"]),
            ("Given an integer array nums of unique elements, return all possible subsets (the power set).", ["backtracking", "recursion", "algorithms"]),
        ]
        for idx, (text, skills) in enumerate(bootstrap_data):
            if limit and idx >= limit:
                break
            yield TACOSample(
                question_id=f"bootstrap_{idx}",
                question_text=text,
                difficulty_raw="MEDIUM",
                difficulty_normalized="intermediate",
                tags=skills,
                skill_types=skills,
                canonical_skills=skills,
            )
