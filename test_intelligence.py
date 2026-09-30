import pytest
from app.services.orchestrator.intelligence import CandidateSkillProfile, SkillEvidenceAggregator, SkillEvidence
from datetime import datetime, timezone

def test_initial_skill_profile():
    profile = CandidateSkillProfile(user_id="u1", skill_name="System Design")
    assert profile.estimated_proficiency == 0.0
    assert profile.confidence == "insufficient evidence"
    assert profile.evidence_count == 0
    assert profile.improvement_trend == "neutral"

def test_aggregator_single_evidence():
    aggregator = SkillEvidenceAggregator()
    profile = CandidateSkillProfile(user_id="u1", skill_name="System Design")
    
    evidence = SkillEvidence(session_id="s1", question_id="q1", score=80.0)
    profile = aggregator.process_evidence(profile, evidence)
    
    assert profile.evidence_count == 1
    assert profile.confidence == "insufficient evidence"
    assert profile.estimated_proficiency == 80.0
    assert profile.recent_performance == 80.0
    assert profile.historical_performance == 0.0
    assert profile.improvement_trend == "neutral"

def test_aggregator_recent_window():
    aggregator = SkillEvidenceAggregator(recent_window_size=3)
    profile = CandidateSkillProfile(user_id="u1", skill_name="System Design")
    
    # Add 3 pieces of evidence (all fit in recent window)
    for i, score in enumerate([70.0, 80.0, 90.0]):
        evidence = SkillEvidence(session_id=f"s{i}", question_id=f"q{i}", score=score)
        profile = aggregator.process_evidence(profile, evidence)
        
    assert profile.evidence_count == 3
    assert profile.confidence == "low confidence" # < 4
    # recent performance should be average of 70, 80, 90 = 80.0
    assert profile.recent_performance == 80.0
    assert profile.historical_performance == 0.0
    assert profile.estimated_proficiency == 80.0
    assert profile.improvement_trend == "neutral"

def test_aggregator_historical_weighting():
    aggregator = SkillEvidenceAggregator(recent_window_size=3, historical_weight=0.4, recent_weight=0.6)
    profile = CandidateSkillProfile(user_id="u1", skill_name="System Design")
    
    # Add 5 pieces of evidence
    # First 2 are historical, last 3 are recent
    scores = [50.0, 60.0, 80.0, 90.0, 100.0]
    for i, score in enumerate(scores):
        evidence = SkillEvidence(session_id=f"s{i}", question_id=f"q{i}", score=score)
        profile = aggregator.process_evidence(profile, evidence)
        
    assert profile.evidence_count == 5
    assert profile.confidence == "medium confidence" # >= 4 and < 8
    
    # historical = avg(50, 60) = 55.0
    assert profile.historical_performance == 55.0
    # recent = avg(80, 90, 100) = 90.0
    assert profile.recent_performance == 90.0
    
    # proficiency = (0.4 * 55.0) + (0.6 * 90.0) = 22.0 + 54.0 = 76.0
    assert profile.estimated_proficiency == 76.0
    
    # trend = recent - historical = 90 - 55 = 35 >= 10 -> "improving"
    assert profile.improvement_trend == "improving"

def test_aggregator_declining_trend():
    aggregator = SkillEvidenceAggregator(recent_window_size=2)
    profile = CandidateSkillProfile(user_id="u1", skill_name="System Design")
    
    # Historical: 90, 90 (avg = 90)
    # Recent: 50, 60 (avg = 55)
    scores = [90.0, 90.0, 50.0, 60.0]
    for i, score in enumerate(scores):
        evidence = SkillEvidence(session_id=f"s{i}", question_id=f"q{i}", score=score)
        profile = aggregator.process_evidence(profile, evidence)
        
    assert profile.historical_performance == 90.0
    assert profile.recent_performance == 55.0
    assert profile.improvement_trend == "declining"

def test_aggregator_stable_trend():
    aggregator = SkillEvidenceAggregator(recent_window_size=2)
    profile = CandidateSkillProfile(user_id="u1", skill_name="System Design")
    
    # Historical: 80, 80 (avg = 80)
    # Recent: 78, 82 (avg = 80)
    scores = [80.0, 80.0, 78.0, 82.0]
    for i, score in enumerate(scores):
        evidence = SkillEvidence(session_id=f"s{i}", question_id=f"q{i}", score=score)
        profile = aggregator.process_evidence(profile, evidence)
        
    assert profile.historical_performance == 80.0
    assert profile.recent_performance == 80.0
    assert profile.improvement_trend == "stable"
