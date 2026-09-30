from typing import List, Dict

ROLE_SKILL_MAP: Dict[str, List[str]] = {
    "Software Engineer": [
        "Data Structures & Algorithms",
        "System Design",
        "Problem Solving",
        "Programming Fundamentals",
        "Debugging",
        "Database Concepts",
        "Communication",
        "Behavioral Reasoning"
    ],
    "Data Scientist": [
        "Statistics",
        "Machine Learning",
        "Problem Solving",
        "Database Concepts",
        "Programming Fundamentals",
        "Communication",
        "Behavioral Reasoning"
    ],
    "Product Manager": [
        "Problem Solving",
        "System Design",
        "Communication",
        "Behavioral Reasoning",
        "Data Structures & Algorithms"
    ],
    "DevOps Engineer": [
        "System Design",
        "Database Concepts",
        "Programming Fundamentals",
        "Debugging",
        "Problem Solving",
        "Communication"
    ]
}

DEFAULT_SKILLS = [
    "Problem Solving",
    "Programming Fundamentals",
    "System Design",
    "Debugging",
    "Communication"
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
