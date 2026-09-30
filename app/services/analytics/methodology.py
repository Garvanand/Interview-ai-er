import math
import re
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any, Tuple
from collections import defaultdict

from .models import (
    ScoreTrendPoint,
    ScoreTrendSummary,
    SkillTrendSummary,
    QuestionTypePerformance,
    DifficultyLevelStats,
    DifficultyProgression,
    ConsistencyAnalysis,
    RepeatedWeakness,
    RecommendationImpact,
    RecentVsHistorical,
    CompletionBehavior,
    NextPracticeRecommendation
)

# Canonical Weakness Cluster definitions with matching regex patterns
WEAKNESS_CLUSTERS = [
    (
        "edge_case_handling",
        "Edge Case & Boundary Condition Coverage",
        re.compile(r"\b(edge\s*case|boundary|null|empty|overflow|zero|off\s*by\s*one)\b", re.IGNORECASE)
    ),
    (
        "time_complexity",
        "Time Complexity & Algorithmic Efficiency",
        re.compile(r"\b(time\s*complexity|o\(n\^2|o\(2\^n|suboptimal|inefficient|timeout|runtime|slow)\b", re.IGNORECASE)
    ),
    (
        "space_complexity",
        "Memory Allocation & Auxiliary Space Usage",
        re.compile(r"\b(space\s*complexity|memory|allocation|auxiliary|space\s*leak)\b", re.IGNORECASE)
    ),
    (
        "recursion_and_backtracking",
        "Recursion Termination & Base Cases",
        re.compile(r"\b(recursion|base\s*case|recursive|stack\s*overflow|backtrack)\b", re.IGNORECASE)
    ),
    (
        "code_modularity",
        "Code Decomposition & Clean Modularity",
        re.compile(r"\b(modularity|clean\s*code|readability|naming|refactor|spaghetti|single\s*responsibility)\b", re.IGNORECASE)
    ),
    (
        "scalability_architecture",
        "System Scalability & Distributed Bottlenecks",
        re.compile(r"\b(scalability|scale|bottleneck|sharding|caching|throughput|single\s*point\s*of\s*failure|latency)\b", re.IGNORECASE)
    ),
    (
        "error_handling",
        "Input Validation & Defensive Error Handling",
        re.compile(r"\b(validation|error\s*handling|exception|try\s*catch|invalid\s*input|unhandled)\b", re.IGNORECASE)
    ),
    (
        "communication_clarity",
        "Structured Communication & Clarification",
        re.compile(r"\b(communication|clarity|articulate|explanation|assumption|verbalize|unclear)\b", re.IGNORECASE)
    ),
    (
        "data_structure_selection",
        "Optimal Data Structure Selection",
        re.compile(r"\b(data\s*structure|hash\s*map|heap|priority\s*queue|trie|graph\s*traversal)\b", re.IGNORECASE)
    )
]

DIFFICULTY_WEIGHTS = {
    "beginner": 0.85,
    "intermediate": 1.00,
    "advanced": 1.25
}

def parse_iso_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str:
        return None
    try:
        # Normalize trailing Z
        clean_str = dt_str.replace('Z', '+00:00')
        return datetime.fromisoformat(clean_str)
    except Exception:
        return None

# ============================================================================
# 1. Interview Score Trends & Rolling Difficulty-Adjusted Performance
# ============================================================================

def calculate_score_trends(
    sessions: List[Dict[str, Any]],
    questions_by_session: Dict[str, List[Dict[str, Any]]]
) -> ScoreTrendSummary:
    """
    Computes difficulty-normalized session trajectories, moving averages (SMA-3, EMA),
    and Ordinary Least Squares (OLS) linear regression slope.
    """
    if not sessions:
        return ScoreTrendSummary()

    # Sort sessions chronologically
    sorted_sessions = sorted(
        sessions,
        key=lambda s: parse_iso_datetime(s.get('start_time')) or datetime.min.replace(tzinfo=timezone.utc)
    )

    data_points: List[ScoreTrendPoint] = []
    raw_scores: List[float] = []

    ema_prev: Optional[float] = None
    alpha = 0.5  # EMA smoothing factor

    for idx, session in enumerate(sorted_sessions):
        s_id = session.get('id', f"s-{idx}")
        raw_score = float(session.get('score') or 0.0)
        s_questions = questions_by_session.get(s_id, [])

        # Calculate session difficulty weight
        if s_questions:
            diff_weights = []
            diff_levels = []
            for q in s_questions:
                diff = (q.get('difficulty') or 'intermediate').lower()
                diff_weights.append(DIFFICULTY_WEIGHTS.get(diff, 1.0))
                diff_levels.append(diff)
            avg_diff_weight = sum(diff_weights) / len(diff_weights)
            # Dominant difficulty level
            dominant_diff = max(set(diff_levels), key=diff_levels.count)
        else:
            avg_diff_weight = 1.0
            dominant_diff = "intermediate"

        # Difficulty normalized score: S_norm = raw * (0.7 + 0.3 * avg_diff_weight)
        normalized_score = min(100.0, raw_score * (0.7 + 0.3 * avg_diff_weight))
        normalized_score = round(normalized_score, 2)

        raw_scores.append(raw_score)

        # 3-session Simple Moving Average
        window = raw_scores[max(0, idx - 2):idx + 1]
        sma_3 = round(sum(window) / len(window), 2)

        # Exponential Moving Average
        if ema_prev is None:
            ema = raw_score
        else:
            ema = round(alpha * raw_score + (1.0 - alpha) * ema_prev, 2)
        ema_prev = ema

        start_dt = parse_iso_datetime(session.get('start_time'))
        date_str = start_dt.strftime("%Y-%m-%d %H:%M") if start_dt else f"Session {idx + 1}"

        data_points.append(ScoreTrendPoint(
            session_id=s_id,
            session_index=idx + 1,
            date=date_str,
            interview_type=session.get('interview_type') or 'General',
            raw_score=round(raw_score, 2),
            difficulty_adjusted_score=normalized_score,
            sma_3=sma_3,
            ema=ema,
            difficulty_level=dominant_diff,
            questions_count=len(s_questions),
            is_completed=(session.get('status') == 'completed')
        ))

    # OLS Linear Regression on raw_scores
    n = len(raw_scores)
    slope = 0.0
    r_squared = 0.0
    classification = "insufficient_data"

    if n >= 2:
        x_vals = list(range(1, n + 1))
        x_mean = sum(x_vals) / n
        y_mean = sum(raw_scores) / n

        numerator = sum((x_vals[i] - x_mean) * (raw_scores[i] - y_mean) for i in range(n))
        denominator = sum((x_vals[i] - x_mean) ** 2 for i in range(n))

        if denominator > 0:
            slope = round(numerator / denominator, 3)
            intercept = y_mean - slope * x_mean

            ss_tot = sum((y - y_mean) ** 2 for y in raw_scores)
            ss_res = sum((raw_scores[i] - (slope * x_vals[i] + intercept)) ** 2 for i in range(n))

            if ss_tot > 0:
                r_squared = round(max(0.0, 1.0 - (ss_res / ss_tot)), 3)

        # Trajectory classification based on slope and r_squared
        if slope >= 2.5 and r_squared >= 0.2:
            classification = "significant_improvement"
        elif slope >= 1.0:
            classification = "moderate_improvement"
        elif slope <= -2.5 and r_squared >= 0.2:
            classification = "concerning_decline"
        elif slope <= -1.0:
            classification = "moderate_decline"
        else:
            classification = "stable"

    baseline = raw_scores[0] if raw_scores else 0.0
    current_ma = data_points[-1].sma_3 if data_points and data_points[-1].sma_3 is not None else 0.0
    diff_adj_current = data_points[-1].difficulty_adjusted_score if data_points else 0.0

    return ScoreTrendSummary(
        data_points=data_points,
        linear_regression_slope=slope,
        r_squared=r_squared,
        trajectory_classification=classification,
        baseline_score=round(baseline, 2),
        current_moving_average=current_ma,
        difficulty_adjusted_current=diff_adj_current,
        total_sessions_analyzed=len(data_points)
    )

# ============================================================================
# 2. Skill Trends & Longitudinal Proficiency Aggregation
# ============================================================================

def calculate_skill_trends(
    questions: List[Dict[str, Any]],
    raw_skill_profiles: Optional[List[Dict[str, Any]]] = None
) -> List[SkillTrendSummary]:
    """
    Computes time-decayed proficiency, recent vs historical separation,
    score volatility (SD), and evidence confidence for each skill.
    """
    questions_by_skill: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for q in questions:
        score = q.get('evaluation_score') or q.get('code_evaluation_score')
        if score is None:
            continue
        skill = q.get('skill_focus') or q.get('interview_type') or "Core Problem Solving"
        questions_by_skill[skill].append(q)

    # Incorporate any skills present in raw_skill_profiles that might not have matching questions in filter
    all_skills = set(questions_by_skill.keys())
    if raw_skill_profiles:
        for p in raw_skill_profiles:
            s_name = p.get('skill_name')
            if s_name:
                all_skills.add(s_name)

    summaries: List[SkillTrendSummary] = []
    now = datetime.now(timezone.utc)

    for skill in sorted(all_skills):
        skill_qs = questions_by_skill.get(skill, [])
        # Sort chronologically
        skill_qs.sort(key=lambda x: parse_iso_datetime(x.get('created_at')) or datetime.min.replace(tzinfo=timezone.utc))

        scores = [float(q.get('evaluation_score') or q.get('code_evaluation_score') or 0.0) for q in skill_qs]
        count = len(scores)

        # Confidence categorization
        if count < 2:
            confidence = "insufficient evidence"
        elif count < 4:
            confidence = "low confidence"
        elif count < 8:
            confidence = "medium confidence"
        else:
            confidence = "high confidence"

        if count == 0:
            # Check if profile data exists
            prof_data = next((p for p in (raw_skill_profiles or []) if p.get('skill_name') == skill), None)
            if prof_data:
                summaries.append(SkillTrendSummary(
                    skill_name=skill,
                    evidence_count=int(prof_data.get('evidence_count', 0)),
                    estimated_proficiency=float(prof_data.get('estimated_proficiency', 0.0)),
                    decayed_proficiency=float(prof_data.get('estimated_proficiency', 0.0)),
                    recent_average=float(prof_data.get('recent_performance', 0.0)),
                    historical_average=float(prof_data.get('historical_performance', 0.0)),
                    net_delta=round(float(prof_data.get('recent_performance', 0.0)) - float(prof_data.get('historical_performance', 0.0)), 2),
                    volatility_sd=0.0,
                    confidence=prof_data.get('confidence', 'insufficient evidence'),
                    trend_status="uncalibrated",
                    last_evaluated=prof_data.get('last_evaluated_timestamp'),
                    score_history=[]
                ))
            continue

        mean_score = sum(scores) / count

        # Volatility: Standard Deviation
        variance = sum((s - mean_score) ** 2 for s in scores) / count
        volatility = round(math.sqrt(variance), 2)

        # Time-decayed proficiency: w_j = exp(-0.05 * days_ago)
        weights = []
        weighted_scores = []
        history_records = []

        for q in skill_qs:
            s = float(q.get('evaluation_score') or q.get('code_evaluation_score') or 0.0)
            dt = parse_iso_datetime(q.get('created_at'))
            if dt:
                days_ago = max(0.0, (now - dt).total_seconds() / 86400.0)
            else:
                days_ago = 0.0

            w = math.exp(-0.05 * days_ago)
            weights.append(w)
            weighted_scores.append(w * s)

            history_records.append({
                'score': round(s, 1),
                'difficulty': q.get('difficulty', 'intermediate'),
                'created_at': q.get('created_at')
            })

        total_weight = sum(weights)
        decayed_prof = round(sum(weighted_scores) / total_weight, 2) if total_weight > 0 else round(mean_score, 2)

        # Recent vs Historical window (window size = 3)
        if count <= 3:
            recent_avg = round(mean_score, 2)
            hist_avg = round(mean_score, 2)
            net_delta = 0.0
            trend_status = "uncalibrated"
        else:
            recent_scores = scores[-3:]
            historical_scores = scores[:-3]
            recent_avg = round(sum(recent_scores) / len(recent_scores), 2)
            hist_avg = round(sum(historical_scores) / len(historical_scores), 2)
            net_delta = round(recent_avg - hist_avg, 2)

            if net_delta >= 8.0:
                trend_status = "demonstrated_growth"
            elif net_delta <= -8.0:
                trend_status = "skill_regression"
            else:
                trend_status = "plateaued"

        last_eval = skill_qs[-1].get('created_at')

        summaries.append(SkillTrendSummary(
            skill_name=skill,
            evidence_count=count,
            estimated_proficiency=round(mean_score, 2),
            decayed_proficiency=decayed_prof,
            recent_average=recent_avg,
            historical_average=hist_avg,
            net_delta=net_delta,
            volatility_sd=volatility,
            confidence=confidence,
            trend_status=trend_status,
            last_evaluated=last_eval,
            score_history=history_records
        ))

    # Sort descending by evidence_count
    summaries.sort(key=lambda s: s.evidence_count, reverse=True)
    return summaries

# ============================================================================
# 3. Question-Type & Modality Performance
# ============================================================================

def calculate_question_type_performance(questions: List[Dict[str, Any]]) -> List[QuestionTypePerformance]:
    """
    Breaks down performance by modality: Coding, System Design, Algorithmic, Conceptual/Behavioral.
    """
    groups: Dict[str, List[Dict[str, Any]]] = {
        "coding": [],
        "system_design": [],
        "algorithmic": [],
        "conceptual_behavioral": []
    }

    for q in questions:
        score = q.get('evaluation_score') or q.get('code_evaluation_score')
        if score is None:
            continue

        skill_text = f"{q.get('skill_focus', '')} {q.get('interview_type', '')}".lower()
        has_code = bool(q.get('code_text') or q.get('code_evaluation_score') or q.get('programming_language'))

        if has_code:
            groups["coding"].append(q)
        elif any(k in skill_text for k in ["system", "design", "architecture", "distributed"]):
            groups["system_design"].append(q)
        elif any(k in skill_text for k in ["algorithm", "data struct", "leetcode", "array", "tree", "graph"]):
            groups["algorithmic"].append(q)
        else:
            groups["conceptual_behavioral"].append(q)

    results: List[QuestionTypePerformance] = []

    for q_type, q_list in groups.items():
        if not q_list:
            continue
        scores = [float(q.get('evaluation_score') or q.get('code_evaluation_score') or 0.0) for q in q_list]
        scores_sorted = sorted(scores)
        count = len(scores)

        avg_score = round(sum(scores) / count, 2)
        mid = count // 2
        median_score = round((scores_sorted[mid] if count % 2 != 0 else (scores_sorted[mid - 1] + scores_sorted[mid]) / 2.0), 2)
        pass_rate = round((len([s for s in scores if s >= 70.0]) / count) * 100.0, 1)

        # Extract strengths & weaknesses
        all_strengths = []
        all_weaknesses = []
        for q in q_list:
            eval_det = q.get('evaluation_details') or q.get('code_evaluation_details') or {}
            if isinstance(eval_det, dict):
                for s in (eval_det.get('strengths') or []):
                    if isinstance(s, str) and len(s) > 3:
                        all_strengths.append(s[:60])
                for w in (eval_det.get('weaknesses') or eval_det.get('issues') or []):
                    if isinstance(w, str) and len(w) > 3:
                        all_weaknesses.append(w[:60])

        top_strengths = [item for item, _ in defaultdict(int, {x: all_strengths.count(x) for x in set(all_strengths)}).items()][:3]
        top_weaknesses = [item for item, _ in defaultdict(int, {x: all_weaknesses.count(x) for x in set(all_weaknesses)}).items()][:3]

        results.append(QuestionTypePerformance(
            question_type=q_type,
            total_attempted=count,
            average_score=avg_score,
            median_score=median_score,
            pass_rate=pass_rate,
            top_strengths=top_strengths,
            top_weaknesses=top_weaknesses
        ))

    return results

# ============================================================================
# 4. Difficulty Progression & Adaptive Frontier
# ============================================================================

def calculate_difficulty_progression(
    questions: List[Dict[str, Any]],
    logs: Optional[List[Dict[str, Any]]] = None
) -> DifficultyProgression:
    """
    Measures how candidate performs across Beginner, Intermediate, and Advanced tiers,
    evaluates score retention when difficulty is increased, and determines current performance frontier.
    """
    levels_data: Dict[str, List[float]] = {
        "beginner": [],
        "intermediate": [],
        "advanced": []
    }

    questions_by_session: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for q in questions:
        s_id = q.get('session_id')
        if s_id:
            questions_by_session[s_id].append(q)

        score = q.get('evaluation_score') or q.get('code_evaluation_score')
        if score is not None:
            diff = (q.get('difficulty') or "intermediate").lower()
            if diff in levels_data:
                levels_data[diff].append(float(score))
            else:
                levels_data["intermediate"].append(float(score))

    levels_stats: Dict[str, DifficultyLevelStats] = {}
    for level, scores in levels_data.items():
        if scores:
            count = len(scores)
            avg = round(sum(scores) / count, 2)
            pass_rate = round((len([s for s in scores if s >= 70.0]) / count) * 100.0, 1)
            var = sum((s - avg) ** 2 for s in scores) / count
            sd = round(math.sqrt(var), 2)
            levels_stats[level] = DifficultyLevelStats(
                level=level,
                total_attempted=count,
                average_score=avg,
                pass_rate=pass_rate,
                standard_deviation=sd
            )
        else:
            levels_stats[level] = DifficultyLevelStats(level=level)

    # Evaluate promotion transitions within sessions
    diff_rank = {"beginner": 1, "intermediate": 2, "advanced": 3}
    promotions_attempted = 0
    promotions_sustained = 0

    for s_id, s_qs in questions_by_session.items():
        # Sort chronologically
        s_qs.sort(key=lambda x: parse_iso_datetime(x.get('created_at')) or datetime.min.replace(tzinfo=timezone.utc))
        for i in range(1, len(s_qs)):
            prev_q = s_qs[i - 1]
            curr_q = s_qs[i]

            prev_diff = (prev_q.get('difficulty') or "intermediate").lower()
            curr_diff = (curr_q.get('difficulty') or "intermediate").lower()

            curr_score = curr_q.get('evaluation_score') or curr_q.get('code_evaluation_score')

            if diff_rank.get(curr_diff, 2) > diff_rank.get(prev_diff, 2) and curr_score is not None:
                promotions_attempted += 1
                if float(curr_score) >= 70.0:
                    promotions_sustained += 1

    sustained_rate = round((promotions_sustained / promotions_attempted) * 100.0, 1) if promotions_attempted > 0 else 0.0

    # Calculate Current Performance Frontier:
    # Highest difficulty where candidate maintains avg >= 70 with >= 2 attempts
    adv_stat = levels_stats.get("advanced")
    int_stat = levels_stats.get("intermediate")

    if adv_stat and adv_stat.total_attempted >= 2 and adv_stat.average_score >= 70.0:
        frontier = "advanced"
    elif int_stat and int_stat.total_attempted >= 2 and int_stat.average_score >= 70.0:
        frontier = "intermediate"
    else:
        frontier = "beginner"

    return DifficultyProgression(
        levels=levels_stats,
        promotion_transitions_attempted=promotions_attempted,
        promotion_sustained_rate=sustained_rate,
        current_performance_frontier=frontier
    )

# ============================================================================
# 5. Consistency & Dispersion Analysis
# ============================================================================

def calculate_consistency(scores: List[float]) -> ConsistencyAnalysis:
    """
    Computes statistical dispersion via Coefficient of Variation (CV = SD / Mean)
    and Interquartile Range (IQR). Translates CV into a normalized 0-100 Consistency Index.
    """
    if not scores:
        return ConsistencyAnalysis()

    n = len(scores)
    sorted_scores = sorted(scores)
    mean_val = round(sum(scores) / n, 2)

    # Median
    mid = n // 2
    median_val = round(sorted_scores[mid] if n % 2 != 0 else (sorted_scores[mid - 1] + sorted_scores[mid]) / 2.0, 2)

    # Standard Deviation
    var = sum((s - mean_val) ** 2 for s in scores) / n
    sd = round(math.sqrt(var), 2)

    # Min, Max, Range
    min_val = round(sorted_scores[0], 2)
    max_val = round(sorted_scores[-1], 2)
    score_range = round(max_val - min_val, 2)

    # Interquartile Range (IQR)
    def percentile(p: float) -> float:
        k = (len(sorted_scores) - 1) * p
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_scores[int(k)]
        d0 = sorted_scores[int(f)] * (c - k)
        d1 = sorted_scores[int(c)] * (k - f)
        return d0 + d1

    q1 = percentile(0.25)
    q3 = percentile(0.75)
    iqr_val = round(q3 - q1, 2)

    # Coefficient of Variation
    cv = round((sd / mean_val) * 100.0, 2) if mean_val > 0 else 0.0

    # Consistency Index = max(0, min(100, 100 - (CV * 1.5)))
    consistency_idx = round(max(0.0, min(100.0, 100.0 - (cv * 1.5))), 1)

    if n < 2:
        category = "Insufficient Data"
    elif cv < 12.0:
        category = "Highly Consistent"
    elif cv < 22.0:
        category = "Moderately Consistent"
    else:
        category = "Volatile / High Variance"

    return ConsistencyAnalysis(
        score_count=n,
        mean_score=mean_val,
        median_score=median_val,
        standard_deviation=sd,
        coefficient_of_variation=cv,
        iqr=iqr_val,
        min_score=min_val,
        max_score=max_val,
        score_range=score_range,
        consistency_index=consistency_idx,
        consistency_category=category
    )

# ============================================================================
# 6. Repeated Weaknesses & Critical Error Patterns
# ============================================================================

def calculate_repeated_weaknesses(
    questions: List[Dict[str, Any]],
    total_sessions_count: int
) -> List[RepeatedWeakness]:
    """
    Extracts raw evaluative weaknesses and code issues, maps them to canonical clusters,
    determines distinct session recurrence, recency, and persistence status.
    """
    cluster_occurrences: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        'canonical_label': '',
        'total_count': 0,
        'sessions': set(),
        'snippets': [],
        'latest_dt': datetime.min.replace(tzinfo=timezone.utc),
        'skills': defaultdict(int)
    })

    # Sort questions chronologically
    sorted_qs = sorted(
        questions,
        key=lambda q: parse_iso_datetime(q.get('created_at')) or datetime.min.replace(tzinfo=timezone.utc)
    )

    latest_session_id = sorted_qs[-1].get('session_id') if sorted_qs else None

    for q in sorted_qs:
        s_id = q.get('session_id', 'unknown')
        q_skill = q.get('skill_focus') or q.get('interview_type') or "Problem Solving"
        q_dt = parse_iso_datetime(q.get('created_at')) or datetime.min.replace(tzinfo=timezone.utc)

        eval_det = q.get('evaluation_details') or q.get('code_evaluation_details') or {}
        raw_weaknesses = []

        if isinstance(eval_det, dict):
            for w in (eval_det.get('weaknesses') or eval_det.get('issues') or []):
                if isinstance(w, str) and len(w.strip()) > 3:
                    raw_weaknesses.append(w.strip())

        # Also check evaluation_feedback text for keywords if list was empty
        feedback_text = q.get('evaluation_feedback', '')
        if not raw_weaknesses and feedback_text and len(feedback_text) > 10:
            raw_weaknesses.append(feedback_text[:120])

        for raw_w in raw_weaknesses:
            matched = False
            for cluster_key, canonical_label, pattern in WEAKNESS_CLUSTERS:
                if pattern.search(raw_w):
                    entry = cluster_occurrences[cluster_key]
                    entry['canonical_label'] = canonical_label
                    entry['total_count'] += 1
                    entry['sessions'].add(s_id)
                    entry['skills'][q_skill] += 1
                    if len(entry['snippets']) < 3 and raw_w not in entry['snippets']:
                        entry['snippets'].append(raw_w[:120])
                    if q_dt > entry['latest_dt']:
                        entry['latest_dt'] = q_dt
                    matched = True
                    break

            if not matched and len(raw_w) > 8:
                # Group under general conceptual cluster
                entry = cluster_occurrences["general_conceptual_gap"]
                entry['canonical_label'] = "General Solution & Conceptual Gaps"
                entry['total_count'] += 1
                entry['sessions'].add(s_id)
                entry['skills'][q_skill] += 1
                if len(entry['snippets']) < 3 and raw_w not in entry['snippets']:
                    entry['snippets'].append(raw_w[:120])
                if q_dt > entry['latest_dt']:
                    entry['latest_dt'] = q_dt

    results: List[RepeatedWeakness] = []
    tot_sessions = max(1, total_sessions_count)

    for cluster_key, entry in cluster_occurrences.items():
        distinct_sessions = len(entry['sessions'])
        session_pct = round((distinct_sessions / tot_sessions) * 100.0, 1)
        recency_flag = bool(latest_session_id and latest_session_id in entry['sessions'])

        # Persistence Classification
        if distinct_sessions >= 3 or session_pct >= 40.0:
            persistence = "persistent_blocker"
        elif recency_flag and entry['total_count'] >= 2:
            persistence = "emerging_issue"
        elif not recency_flag and distinct_sessions >= 2:
            persistence = "resolving"
        else:
            persistence = "sporadic"

        # Determine dominant skill
        dominant_skill = None
        if entry['skills']:
            dominant_skill = max(entry['skills'].items(), key=lambda x: x[1])[0]

        results.append(RepeatedWeakness(
            weakness_cluster=cluster_key,
            canonical_label=entry['canonical_label'],
            total_occurrences=entry['total_count'],
            distinct_sessions_count=distinct_sessions,
            session_percentage=session_pct,
            recency_flag=recency_flag,
            persistence_status=persistence,
            evidence_snippets=entry['snippets'],
            target_skill=dominant_skill
        ))

    # Sort so persistent blockers come first, then total occurrences
    priority_order = {"persistent_blocker": 0, "emerging_issue": 1, "resolving": 2, "sporadic": 3}
    results.sort(key=lambda r: (priority_order.get(r.persistence_status, 99), -r.total_occurrences))
    return results

# ============================================================================
# 7. Improvement After Recommendations (Intervention Effectiveness)
# ============================================================================

def calculate_recommendation_impact(
    recommendations: List[Dict[str, Any]],
    questions: List[Dict[str, Any]]
) -> List[RecommendationImpact]:
    """
    Evaluates whether completed/accepted recommendations produced measurable performance lift
    by tracking subsequent question scores in the target skill.
    """
    results: List[RecommendationImpact] = []

    for rec in recommendations:
        rec_id = rec.get('id', '')
        target_skill = rec.get('target_skill', '')
        strategy = rec.get('strategy', '')
        reason = rec.get('reason', '')
        status = (rec.get('status') or '').upper()

        if status not in ("COMPLETED", "ACCEPTED"):
            continue

        baseline_prof = float(rec.get('baseline_proficiency') or 0.0)
        completed_at_str = rec.get('completed_at') or rec.get('created_at')
        completed_dt = parse_iso_datetime(completed_at_str)

        # Questions evaluated in that skill strictly after recommendation was actioned
        post_scores = []
        for q in questions:
            q_skill = q.get('skill_focus') or q.get('interview_type') or ''
            if q_skill.lower() == target_skill.lower():
                q_dt = parse_iso_datetime(q.get('created_at'))
                if completed_dt and q_dt and q_dt > completed_dt:
                    score = q.get('evaluation_score') or q.get('code_evaluation_score')
                    if score is not None:
                        post_scores.append(float(score))

        if post_scores:
            post_avg = round(sum(post_scores) / len(post_scores), 2)
            delta = round(post_avg - baseline_prof, 2)
            if delta >= 5.0:
                outcome = "verified_improvement"
            elif delta <= -5.0:
                outcome = "regression"
            else:
                outcome = "no_measurable_change"

            results.append(RecommendationImpact(
                recommendation_id=rec_id,
                target_skill=target_skill,
                strategy=strategy,
                reason=reason,
                completed_at=completed_at_str,
                baseline_proficiency=baseline_prof,
                post_proficiency=post_avg,
                delta=delta,
                outcome_status=outcome,
                post_questions_evaluated=len(post_scores)
            ))
        else:
            # Check if outcome was already evaluated and persisted on the model
            persisted_delta = rec.get('outcome_delta')
            persisted_status = rec.get('outcome_assessment')
            if persisted_delta is not None:
                results.append(RecommendationImpact(
                    recommendation_id=rec_id,
                    target_skill=target_skill,
                    strategy=strategy,
                    reason=reason,
                    completed_at=completed_at_str,
                    baseline_proficiency=baseline_prof,
                    post_proficiency=rec.get('post_outcome_proficiency'),
                    delta=float(persisted_delta),
                    outcome_status="verified_improvement" if persisted_delta >= 5 else "no_measurable_change",
                    post_questions_evaluated=1
                ))
            else:
                results.append(RecommendationImpact(
                    recommendation_id=rec_id,
                    target_skill=target_skill,
                    strategy=strategy,
                    reason=reason,
                    completed_at=completed_at_str,
                    baseline_proficiency=baseline_prof,
                    post_proficiency=None,
                    delta=None,
                    outcome_status="awaiting_evidence",
                    post_questions_evaluated=0
                ))

    return results

# ============================================================================
# 8. Recent vs Historical Performance Comparison
# ============================================================================

def calculate_recent_vs_historical(
    sessions: List[Dict[str, Any]],
    questions: List[Dict[str, Any]]
) -> RecentVsHistorical:
    """
    Compares metrics across the recent window (last 3 sessions) vs historical sessions.
    """
    sorted_sessions = sorted(
        sessions,
        key=lambda s: parse_iso_datetime(s.get('start_time')) or datetime.min.replace(tzinfo=timezone.utc)
    )

    n_sessions = len(sorted_sessions)
    if n_sessions == 0:
        return RecentVsHistorical()

    # Window cutoff
    recent_count = min(3, n_sessions)
    if n_sessions <= 3:
        # Not enough historical baseline
        recent_sessions = sorted_sessions
        hist_sessions = []
    else:
        recent_sessions = sorted_sessions[-recent_count:]
        hist_sessions = sorted_sessions[:-recent_count]

    recent_ids = {s.get('id') for s in recent_sessions}
    hist_ids = {s.get('id') for s in hist_sessions}

    recent_scores = [float(s.get('score') or 0.0) for s in recent_sessions if s.get('score') is not None]
    hist_scores = [float(s.get('score') or 0.0) for s in hist_sessions if s.get('score') is not None]

    recent_avg = round(sum(recent_scores) / len(recent_scores), 2) if recent_scores else 0.0
    hist_avg = round(sum(hist_scores) / len(hist_scores), 2) if hist_scores else recent_avg

    score_delta = round(recent_avg - hist_avg, 2)
    pct_change = round(((recent_avg - hist_avg) / hist_avg) * 100.0, 1) if hist_avg > 0 else 0.0

    # Advanced question ratios
    recent_qs = [q for q in questions if q.get('session_id') in recent_ids]
    hist_qs = [q for q in questions if q.get('session_id') in hist_ids]

    def advanced_ratio(qs: List[Dict[str, Any]]) -> float:
        if not qs:
            return 0.0
        adv = len([q for q in qs if (q.get('difficulty') or '').lower() == 'advanced'])
        return round((adv / len(qs)) * 100.0, 1)

    recent_adv = advanced_ratio(recent_qs)
    hist_adv = advanced_ratio(hist_qs)

    # Consistency CV
    def calc_cv(vals: List[float]) -> float:
        if len(vals) < 2:
            return 0.0
        m = sum(vals) / len(vals)
        if m <= 0:
            return 0.0
        sd = math.sqrt(sum((v - m) ** 2 for v in vals) / len(vals))
        return round((sd / m) * 100.0, 1)

    recent_cv = calc_cv(recent_scores)
    hist_cv = calc_cv(hist_scores)

    meaningful = bool(len(recent_scores) >= 2 and len(hist_scores) >= 2 and abs(score_delta) >= 6.0)

    if not hist_sessions:
        verdict = "Initial calibration phase (baseline established)"
    elif score_delta >= 7.0 and meaningful:
        verdict = "Statistically meaningful growth observed across recent interviews"
    elif score_delta <= -7.0 and meaningful:
        verdict = "Measurable performance dip detected; targeted practice advised"
    else:
        verdict = "Steady, consistent baseline maintained with low variance"

    return RecentVsHistorical(
        recent_period_label=f"Last {recent_count} Sessions",
        historical_period_label="Prior Baseline",
        recent_average_score=recent_avg,
        historical_average_score=hist_avg,
        score_delta=score_delta,
        score_pct_change=pct_change,
        recent_advanced_ratio=recent_adv,
        historical_advanced_ratio=hist_adv,
        recent_consistency_cv=recent_cv,
        historical_consistency_cv=hist_cv,
        recent_sample_size=len(recent_sessions),
        historical_sample_size=len(hist_sessions),
        statistically_meaningful=meaningful,
        verdict=verdict
    )

# ============================================================================
# 9. Interview Completion Behavior
# ============================================================================

def calculate_completion_behavior(
    sessions: List[Dict[str, Any]],
    questions: List[Dict[str, Any]]
) -> CompletionBehavior:
    """
    Computes session completion rate, duration metrics, and score differences
    between completed vs abandoned sessions.
    """
    if not sessions:
        return CompletionBehavior()

    total_sessions = len(sessions)
    completed = []
    abandoned = []

    durations_minutes = []

    for s in sessions:
        is_completed = (s.get('status') == 'completed')
        if is_completed:
            completed.append(s)
            start_dt = parse_iso_datetime(s.get('start_time'))
            end_dt = parse_iso_datetime(s.get('end_time'))
            if start_dt and end_dt:
                duration_m = max(1.0, (end_dt - start_dt).total_seconds() / 60.0)
                # Filter out absurd test artifacts > 180 min
                if duration_m <= 180.0:
                    durations_minutes.append(duration_m)
        else:
            abandoned.append(s)

    completed_count = len(completed)
    abandoned_count = len(abandoned)
    completion_rate = round((completed_count / total_sessions) * 100.0, 1)

    avg_duration = round(sum(durations_minutes) / len(durations_minutes), 1) if durations_minutes else 30.0

    questions_by_session: Dict[str, int] = defaultdict(int)
    for q in questions:
        s_id = q.get('session_id')
        if s_id:
            questions_by_session[s_id] += 1

    total_qs = sum(questions_by_session.values())
    avg_qs = round(total_qs / total_sessions, 1) if total_sessions > 0 else 0.0

    completed_scores = [float(s.get('score') or 0.0) for s in completed if s.get('score') is not None]
    abandoned_scores = [float(s.get('score') or 0.0) for s in abandoned if s.get('score') is not None]

    comp_avg = round(sum(completed_scores) / len(completed_scores), 2) if completed_scores else 0.0
    ab_avg = round(sum(abandoned_scores) / len(abandoned_scores), 2) if abandoned_scores else 0.0

    return CompletionBehavior(
        total_sessions=total_sessions,
        completed_sessions=completed_count,
        abandoned_sessions=abandoned_count,
        completion_rate=completion_rate,
        avg_duration_minutes=avg_duration,
        avg_questions_per_session=avg_qs,
        completed_avg_score=comp_avg,
        abandoned_avg_score=ab_avg
    )

# ============================================================================
# 10. Next-Practice Actionability Engine
# ============================================================================

def generate_next_practice_recommendations(
    skill_trends: List[SkillTrendSummary],
    repeated_weaknesses: List[RepeatedWeakness],
    difficulty_progression: DifficultyProgression,
    consistency: ConsistencyAnalysis
) -> List[NextPracticeRecommendation]:
    """
    Synthesizes multi-dimensional evidence into a prioritized practice roadmap
    to empower candidate decisions on what to tackle next.
    """
    recommendations: List[NextPracticeRecommendation] = []
    priority_counter = 1

    # Rule 1: Persistent Blocker Weakness (Highest Priority)
    top_blocker = next((w for w in repeated_weaknesses if w.persistence_status == "persistent_blocker"), None)
    if top_blocker:
        target_skill = top_blocker.target_skill or "Core Problem Solving"
        evidence_str = f"Recurring in {top_blocker.distinct_sessions_count} sessions ({top_blocker.session_percentage}% recurrence rate)."
        if top_blocker.evidence_snippets:
            evidence_str += f" Evidence: \"{top_blocker.evidence_snippets[0]}\""

        recommendations.append(NextPracticeRecommendation(
            priority=priority_counter,
            target_skill=target_skill,
            recommended_difficulty="intermediate",
            question_type="coding" if "edge" in top_blocker.weakness_cluster or "time" in top_blocker.weakness_cluster else "conceptual",
            learning_objective=f"Eliminate persistent blind spot in {top_blocker.canonical_label}.",
            rationale=f"This error pattern was detected in multiple sessions and represents your single largest barrier to reaching advanced tier.",
            evidence_context=evidence_str
        ))
        priority_counter += 1

    # Rule 2: Near-Frontier Mastery (Skill with estimated proficiency between 60.0 and 74.0)
    frontier_skill = next((s for s in skill_trends if 60.0 <= s.estimated_proficiency < 75.0 and s.evidence_count >= 2), None)
    if frontier_skill:
        recommendations.append(NextPracticeRecommendation(
            priority=priority_counter,
            target_skill=frontier_skill.skill_name,
            recommended_difficulty="advanced" if difficulty_progression.current_performance_frontier != "beginner" else "intermediate",
            question_type="coding",
            learning_objective=f"Push proficiency from {frontier_skill.estimated_proficiency}% past the 75% Mastery Threshold.",
            rationale=f"You have demonstrated solid fundamentals in {frontier_skill.skill_name}. Pushing to higher difficulty scenarios will solidify hire-readiness.",
            evidence_context=f"Current proficiency: {frontier_skill.estimated_proficiency}% across {frontier_skill.evidence_count} evaluations (Volatility SD: {frontier_skill.volatility_sd})."
        ))
        priority_counter += 1

    # Rule 3: Uncalibrated / Insufficient Evidence Skill
    uncalibrated_skill = next((s for s in skill_trends if s.confidence in ("insufficient evidence", "low confidence") and s.evidence_count > 0), None)
    if uncalibrated_skill:
        recommendations.append(NextPracticeRecommendation(
            priority=priority_counter,
            target_skill=uncalibrated_skill.skill_name,
            recommended_difficulty="intermediate",
            question_type="system_design" if "system" in uncalibrated_skill.skill_name.lower() else "coding",
            learning_objective=f"Calibrate skill baseline for {uncalibrated_skill.skill_name} with verified evidence.",
            rationale=f"Only {uncalibrated_skill.evidence_count} question(s) evaluated. Additional data is required to establish statistical confidence.",
            evidence_context=f"Confidence status: '{uncalibrated_skill.confidence}'. Current uncalibrated score: {uncalibrated_skill.estimated_proficiency}%."
        ))
        priority_counter += 1

    # Rule 4: High Volatility Stabilization (if consistency is low)
    if consistency.coefficient_of_variation >= 20.0 and len(recommendations) < 4:
        volatile_skill = max(skill_trends, key=lambda s: s.volatility_sd, default=None)
        if volatile_skill and volatile_skill.evidence_count >= 2:
            recommendations.append(NextPracticeRecommendation(
                priority=priority_counter,
                target_skill=volatile_skill.skill_name,
                recommended_difficulty="intermediate",
                question_type="coding",
                learning_objective="Standardize problem-solving cadence to reduce score swings.",
                rationale=f"Performance shows high variance (CV {consistency.coefficient_of_variation}%). Focus on structured solution templates.",
                evidence_context=f"Skill volatility standard deviation: {volatile_skill.volatility_sd} points across {volatile_skill.evidence_count} questions."
            ))
            priority_counter += 1

    # Fallback if no specific condition met
    if not recommendations and skill_trends:
        lowest_skill = min(skill_trends, key=lambda s: s.estimated_proficiency)
        recommendations.append(NextPracticeRecommendation(
            priority=1,
            target_skill=lowest_skill.skill_name,
            recommended_difficulty="intermediate",
            question_type="coding",
            learning_objective=f"Strengthen baseline proficiency in {lowest_skill.skill_name}.",
            rationale=f"This skill is currently your lowest evaluated area at {lowest_skill.estimated_proficiency}%.",
            evidence_context=f"Evaluated across {lowest_skill.evidence_count} questions."
        ))

    return recommendations
