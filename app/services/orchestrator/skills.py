from typing import List, Dict

ROLE_SKILL_MAP: Dict[str, List[str]] = {
    "Software Engineer": [
        "Data Structures & Algorithms",
        "System Architecture",
        "API Design & Integration",
        "Concurrency & Parallelism",
        "Testing & Reliability"
    ],
    "Data Scientist": [
        "Statistical Modeling & Probability",
        "Machine Learning Algorithms",
        "Data Pipelines & SQL",
        "Feature Engineering",
        "Model Evaluation & Ethics"
    ],
    "Product Manager": [
        "Product Strategy & Vision",
        "Metrics & Experimentation",
        "User Empathy & Problem Definition",
        "Prioritization & Tradeoffs",
        "Technical Communication"
    ],
    "DevOps Engineer": [
        "CI/CD Pipeline Design",
        "Containerization & Orchestration",
        "Infrastructure as Code",
        "Observability & Incident Management",
        "Cloud Security & Compliance"
    ]
}

DEFAULT_SKILLS = [
    "Core Problem Solving",
    "System Architecture",
    "Code Quality & Design",
    "Debugging & Edge Cases",
    "Performance Optimization"
]

def get_skills_for_role(role_or_type: str) -> List[str]:
    """Retrieve the standard skill matrix for a target role or interview type."""
    normalized = (role_or_type or "").strip()
    for role, skills in ROLE_SKILL_MAP.items():
        if role.lower() == normalized.lower():
            return list(skills)
    
    # Check partial match
    for role, skills in ROLE_SKILL_MAP.items():
        if role.lower() in normalized.lower() or normalized.lower() in role.lower():
            return list(skills)
            
    return list(DEFAULT_SKILLS)
