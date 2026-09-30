import pytest
from app.services.security_service import SecurityService

@pytest.fixture
def service():
    return SecurityService()

def test_single_minor_event_no_review(service):
    events = [{"type": "Window blur/tab switch detected"}]
    report = service.process_raw_events("session_123", events)
    
    # 1 tab switch should be LOW severity, small weight (0.1), no review recommended
    assert report.total_signals == 1
    assert report.aggregation_score == 0.1
    assert report.review_recommended is False
    assert report.summary == "Minor anomalies recorded. No immediate review necessary."

def test_multiple_minor_events_triggers_frequency_aggregation(service):
    # 6 tab switches should trigger frequent_focus_loss
    events = [{"type": "Window blur/tab switch detected"}] * 6
    report = service.process_raw_events("session_123", events)
    
    # 6 * 0.1 + 0.9 * 0.6 (frequent_focus_loss HIGH severity)
    assert report.total_signals == 7
    assert report.aggregation_score >= 0.7
    assert report.review_recommended is True
    assert "Manual review" in report.summary
    assert any(sig.signal_type == "frequent_focus_loss" for sig in report.signals)

def test_hardware_unavailable_no_review(service):
    # Camera denied should be LOW risk, doesn't immediately mark as review recommended
    events = [{"type": "Webcam denied or unavailable"}]
    report = service.process_raw_events("session_123", events)
    
    assert report.total_signals == 1
    assert report.review_recommended is False
    assert report.signals[0].severity == "LOW"

def test_combination_of_moderate_events_triggers_review(service):
    # Combination of paste + devtools
    events = [
        {"type": "Large paste detected"},
        {"type": "Devtools hotkey detected"},
        {"type": "Devtools suspected open"}
    ]
    report = service.process_raw_events("session_123", events)
    
    assert report.total_signals == 3
    # 0.3 * 1.0 (paste) + 0.3 * 0.8 (hotkey) + 0.3 * 0.6 (devtools dimensions)
    # 0.3 + 0.24 + 0.18 = 0.72
    assert report.aggregation_score >= 0.7
    assert report.review_recommended is True

def test_empty_events_is_normal(service):
    report = service.process_raw_events("session_123", [])
    
    assert report.total_signals == 0
    assert report.aggregation_score == 0.0
    assert report.review_recommended is False
    assert report.summary == "Session integrity appears normal."
