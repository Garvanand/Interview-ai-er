"""
Interview-Specific Benchmark Source.

Realistic technical interview prompts, candidate responses, and session trajectories:
- System design, concurrency, frontend, and backend architecture problems
- Real candidate answer transcripts with varying proficiency levels
- Multi-step interview session simulation trajectories
"""
from __future__ import annotations

from typing import Any, Dict, List


def load_interview_specific_questions() -> List[Dict[str, Any]]:
    """Realistic coding, system design, and backend interview questions."""
    return [
        {
            "id": "interview_sys_001",
            "source": "interview_specific",
            "track": "system_design",
            "question": "Design a globally distributed rate limiter for a public REST API supporting 100,000 requests per second with multi-region consistency.",
            "expected_difficulty": "advanced",
            "expected_skills": ["complexity", "algorithms", "hashing"],
            "notes": "Classic Senior/Staff system design question"
        },
        {
            "id": "interview_algo_001",
            "source": "interview_specific",
            "track": "coding",
            "question": "Given a stream of integers, design a data structure that dynamically computes the median in O(1) time after each insertion using two heaps.",
            "expected_difficulty": "intermediate",
            "expected_skills": ["heaps", "data_structures", "algorithms"],
            "notes": "LeetCode Medium/Hard classic two-heap median stream"
        },
        {
            "id": "interview_be_001",
            "source": "interview_specific",
            "track": "backend",
            "question": "Explain how database connection pooling works under high concurrency. Discuss connection starvation, wait queues, and max lifecycle timeouts.",
            "expected_difficulty": "intermediate",
            "expected_skills": ["complexity", "data_structures"],
            "notes": "Practical backend engineering interview question"
        },
        {
            "id": "interview_fe_001",
            "source": "interview_specific",
            "track": "frontend",
            "question": "Explain the reconciliation algorithm in React. How does the virtual DOM compare elements and what role do keys play in list diffing?",
            "expected_difficulty": "intermediate",
            "expected_skills": ["trees", "algorithms"],
            "notes": "Standard frontend React framework architecture"
        },
        {
            "id": "interview_dsa_001",
            "source": "interview_specific",
            "track": "coding",
            "question": "Implement an in-memory Key-Value store with key expiration (TTL) and passive/active cleanup threads.",
            "expected_difficulty": "advanced",
            "expected_skills": ["hashing", "heaps", "data_structures"],
            "notes": "Practical system coding question with concurrency"
        },
    ]


def load_interview_specific_answers() -> List[Dict[str, Any]]:
    """Realistic candidate interview answer transcripts for rubric coverage evaluation."""
    return [
        {
            "id": "interview_ans_001",
            "source": "interview_specific",
            "topic": "Distributed Consensus (Raft)",
            "question": "How does the Raft consensus algorithm guarantee leader election safety and log replication?",
            "concepts": [
                "Leader election with randomized election timeouts",
                "Heartbeat messages from leader to followers",
                "Log entry replication quorum (majority commit)",
                "Term numbers preventing stale leader split-brain"
            ],
            "candidate_answer": (
                "Raft elects a leader using randomized timeouts so followers don't split votes at the exact same moment. "
                "Once a candidate receives votes from a majority of nodes, it becomes leader and sends periodic heartbeats. "
                "When a client writes data, the leader appends to its log and replicates to followers; once a quorum (majority) "
                "acknowledges the log entry, the leader commits it and replies to the client. Higher term numbers ensure any old leader is deposed."
            ),
            "expected_coverage": 100.0,
            "quality_tier": "strong_senior",
            "notes": "Comprehensive, articulated senior engineer response"
        },
        {
            "id": "interview_ans_002",
            "source": "interview_specific",
            "topic": "Kafka Architecture",
            "question": "What is the role of consumer groups and partition assignment in Apache Kafka?",
            "concepts": [
                "Horizontal scalability via partitions",
                "One consumer per partition within a group",
                "Offset management and commit semantics",
                "Consumer rebalance protocol upon node departure"
            ],
            "candidate_answer": (
                "Kafka uses partitions to distribute load. Within a consumer group, each partition is read by only one consumer "
                "so messages are processed in order per partition. If a consumer dies, Kafka triggers a rebalance."
            ),
            "expected_coverage": 75.0,  # Covers partitions, single consumer, and rebalance; omits offset commit semantics
            "quality_tier": "solid_mid",
            "notes": "Good mid-level response with one omitted sub-concept"
        },
    ]


def load_interview_adaptive_session_profiles() -> List[Dict[str, Any]]:
    """Simulation profiles for evaluating adaptive selection behavior across an interview."""
    return [
        {
            "profile_id": "sim_struggling_novice",
            "source": "interview_specific",
            "candidate_role": "Junior Backend Developer",
            "initial_theta": -1.2,
            "skill_state": {
                "dynamic_programming": {"mastery": 0.15, "scores": [20.0, 10.0], "weaknesses": ["memoization"]},
                "arrays": {"mastery": 0.60, "scores": [70.0], "weaknesses": []},
                "graphs": {"mastery": 0.30, "scores": [35.0], "weaknesses": ["traversal"]},
            },
            "expected_first_target_skill": "dynamic_programming",
            "expected_difficulty_direction": "beginner",
            "notes": "Severe weakness in DP should trigger remediation at beginner level"
        },
        {
            "profile_id": "sim_high_performing_senior",
            "source": "interview_specific",
            "candidate_role": "Senior Distributed Systems Engineer",
            "initial_theta": 1.5,
            "skill_state": {
                "graphs": {"mastery": 0.90, "scores": [95.0, 90.0], "strengths": ["shortest path"]},
                "dynamic_programming": {"mastery": 0.85, "scores": [85.0], "strengths": ["substructure"]},
                "trees": {"mastery": 0.88, "scores": [90.0], "strengths": ["BST"]},
            },
            "expected_first_target_skill": None,  # Can pick any under-tested skill
            "expected_difficulty_direction": "advanced",
            "notes": "Consistently high scores should target advanced level questions"
        },
    ]
