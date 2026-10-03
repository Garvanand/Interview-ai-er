"""
Manually Curated Benchmark Source.

Gold-standard expert-verified problems, canonical rubrics, and certified ground truths:
- Verified difficulty levels cross-checked against industry interview standards
- Strict canonical skill taxonomy assignments
- Hand-crafted rubric concepts with explicit validation tests
- Clean executable Python functions paired with deterministic unit test suites
"""
from __future__ import annotations

from typing import Any, Dict, List


def load_curated_difficulty_questions() -> List[Dict[str, Any]]:
    """Curated gold-standard questions for difficulty evaluation."""
    return [
        {
            "id": "curated_diff_001",
            "source": "manually_curated",
            "question": "Write a function that accepts two integers and returns their sum.",
            "expected_difficulty": "beginner",
            "verified_by": "Curriculum Board",
            "notes": "Uncontroversial elementary programming"
        },
        {
            "id": "curated_diff_002",
            "source": "manually_curated",
            "question": "Implement a function to check if a word is a palindrome, ignoring casing and non-alphanumeric characters.",
            "expected_difficulty": "beginner",
            "verified_by": "Curriculum Board",
            "notes": "Classic two-pointer or string filtering problem"
        },
        {
            "id": "curated_diff_003",
            "source": "manually_curated",
            "question": "Given the root of a binary search tree and two values min and max, trim the tree so that all its elements lie in [min, max].",
            "expected_difficulty": "intermediate",
            "verified_by": "Curriculum Board",
            "notes": "Standard tree recursion with subtree pruning"
        },
        {
            "id": "curated_diff_004",
            "source": "manually_curated",
            "question": "Given an integer array nums and an integer k, return the k most frequent elements in O(n log k) runtime.",
            "expected_difficulty": "intermediate",
            "verified_by": "Curriculum Board",
            "notes": "Hash map frequency count + min-heap top-k"
        },
        {
            "id": "curated_diff_005",
            "source": "manually_curated",
            "question": "Design an in-memory transactional database that supports BEGIN, COMMIT, ROLLBACK, GET, and SET with nested transactions.",
            "expected_difficulty": "advanced",
            "verified_by": "Curriculum Board",
            "notes": "Complex state management with undo logs"
        },
        {
            "id": "curated_diff_006",
            "source": "manually_curated",
            "question": "Implement the Aho-Corasick automaton for multi-pattern exact string matching in linear O(N + M + Z) time.",
            "expected_difficulty": "advanced",
            "verified_by": "Curriculum Board",
            "notes": "Advanced trie with failure and dictionary links"
        },
    ]


def load_curated_skill_questions() -> List[Dict[str, Any]]:
    """Curated gold-standard questions for skill tagger evaluation."""
    return [
        {
            "id": "curated_skill_001",
            "source": "manually_curated",
            "question": "Given an array of integers, find the contiguous subarray which has the largest sum and return its sum.",
            "expected_skills": ["arrays", "dynamic_programming", "algorithms"],
            "notes": "Kadane's algorithm"
        },
        {
            "id": "curated_skill_002",
            "source": "manually_curated",
            "question": "Implement a Trie (Prefix Tree) with insert, search, and startsWith methods.",
            "expected_skills": ["trees", "strings", "data_structures"],
            "notes": "Standard prefix tree"
        },
        {
            "id": "curated_skill_003",
            "source": "manually_curated",
            "question": "Given an undirected graph, find the minimum spanning tree using Kruskal's algorithm and Union-Find.",
            "expected_skills": ["graphs", "heaps", "greedy", "algorithms"],
            "notes": "Disjoint set union + edge sorting"
        },
    ]


def load_curated_code_samples() -> List[Dict[str, Any]]:
    """Curated executable code snippets with deterministic unit test suites."""
    return [
        {
            "id": "curated_code_fibonacci",
            "source": "manually_curated",
            "function_name": "fib",
            "code": "def fib(n: int) -> int:\n    if n <= 0:\n        return 0\n    elif n == 1:\n        return 1\n    a, b = 0, 1\n    for _ in range(2, n + 1):\n        a, b = b, a + b\n    return b",
            "test_cases": [
                {"input": (0,), "expected": 0},
                {"input": (1,), "expected": 1},
                {"input": (5,), "expected": 5},
                {"input": (10,), "expected": 55},
            ],
            "expected_all_pass": True,
            "expected_defect": False,
            "notes": "Efficient iterative Fibonacci O(N) time O(1) space"
        },
        {
            "id": "curated_code_is_palindrome",
            "source": "manually_curated",
            "function_name": "is_palindrome",
            "code": "def is_palindrome(s: str) -> bool:\n    clean = [c.lower() for c in s if c.isalnum()]\n    return clean == clean[::-1]",
            "test_cases": [
                {"input": ("A man, a plan, a canal: Panama",), "expected": True},
                {"input": ("race a car",), "expected": False},
                {"input": ("",), "expected": True},
            ],
            "expected_all_pass": True,
            "expected_defect": False,
            "notes": "Standard clean palindrome check"
        },
    ]
