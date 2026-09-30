"""
Session Integrity and Anomaly Aggregation Service.

Risk Aggregation Strategy:
- Signals are collected from Level 1 (Browser/OS) and Level 2 (Hardware availability).
- Each signal has a base weight based on its severity (LOW=0.1, MEDIUM=0.3, HIGH=0.6).
- The weight is multiplied by the signal's confidence (0.0 - 1.0).
- Temporal decay or frequency scaling is applied (e.g. frequent tab switches scales risk).
- A final aggregation score >= 0.7 triggers a 'review_recommended' flag.
- Communicates anomalies responsibly without definitive unfair labeling.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class IntegritySignal(BaseModel):
    signal_type: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str
    confidence: float
    evidence: str
    severity: Severity


class SessionIntegrityReport(BaseModel):
    session_id: str
    total_signals: int
    aggregation_score: float  # 0.0 to 1.0 risk score
    review_recommended: bool
    signals: List[IntegritySignal]
    confidence_in_assessment: float
    summary: str


class SecurityService:
    def __init__(self):
        self.severity_weights = {
            Severity.LOW: 0.1,
            Severity.MEDIUM: 0.3,
            Severity.HIGH: 0.6,
        }

    def process_raw_events(self, session_id: str, events: List[Dict[str, Any]]) -> SessionIntegrityReport:
        """Processes raw events from the frontend and returns a structured integrity report."""
        signals: List[IntegritySignal] = []

        tab_switches = 0
        paste_events = 0

        for event in events:
            event_type = event.get("type")
            evidence_msg = event.get("evidence", "")

            if event_type in ["Window blur/tab switch detected", "Page hidden detected"]:
                tab_switches += 1
                signals.append(
                    IntegritySignal(
                        signal_type="focus_loss",
                        source="browser_api",
                        confidence=1.0,
                        evidence=evidence_msg or "Window blur or visibility hidden event detected",
                        severity=Severity.LOW,
                    )
                )
            elif event_type == "Large paste detected":
                paste_events += 1
                signals.append(
                    IntegritySignal(
                        signal_type="large_paste",
                        source="browser_clipboard",
                        confidence=1.0,
                        evidence=evidence_msg or "Large chunk of text pasted",
                        severity=Severity.MEDIUM,
                    )
                )
            elif event_type == "Devtools hotkey detected":
                signals.append(
                    IntegritySignal(
                        signal_type="devtools_access",
                        source="browser_keyboard",
                        confidence=0.8,
                        evidence=evidence_msg or "Keyboard shortcut associated with developer tools detected",
                        severity=Severity.MEDIUM,
                    )
                )
            elif event_type == "Devtools suspected open":
                signals.append(
                    IntegritySignal(
                        signal_type="devtools_access",
                        source="browser_window_dimensions",
                        confidence=0.6,
                        evidence=evidence_msg or "Window dimensions suggest DevTools is open",
                        severity=Severity.MEDIUM,
                    )
                )
            elif event_type == "Suspicious rapid typing cadence":
                signals.append(
                    IntegritySignal(
                        signal_type="bot_behavior",
                        source="browser_keyboard",
                        confidence=0.7,
                        evidence=evidence_msg or "Typing cadence is suspiciously rapid or uniform",
                        severity=Severity.MEDIUM,
                    )
                )
            elif event_type == "Webcam denied or unavailable":
                signals.append(
                    IntegritySignal(
                        signal_type="hardware_unavailable",
                        source="browser_media",
                        confidence=1.0,
                        evidence=evidence_msg or "Camera access was denied or device not found",
                        severity=Severity.LOW,
                    )
                )
            else:
                signals.append(
                    IntegritySignal(
                        signal_type="unknown_anomaly",
                        source="client_event",
                        confidence=0.5,
                        evidence=event_type or "Unknown anomalous event",
                        severity=Severity.LOW,
                    )
                )

        if tab_switches > 5:
            signals.append(
                IntegritySignal(
                    signal_type="frequent_focus_loss",
                    source="aggregation",
                    confidence=0.9,
                    evidence=f"Candidate lost window focus {tab_switches} times",
                    severity=Severity.HIGH,
                )
            )

        return self._generate_report(session_id, signals)

    def _generate_report(self, session_id: str, signals: List[IntegritySignal]) -> SessionIntegrityReport:
        total_risk = 0.0

        for sig in signals:
            base_weight = self.severity_weights[sig.severity]
            total_risk += base_weight * sig.confidence

        aggregation_score = min(1.0, total_risk)
        review_recommended = aggregation_score >= 0.7
        assessment_confidence = 0.8 if len(signals) > 0 else 0.9

        summary = "Session integrity appears normal."
        if review_recommended:
            summary = "Multiple anomalies detected. Manual review of session evidence is recommended."
        elif len(signals) > 0:
            summary = "Minor anomalies recorded. No immediate review necessary."

        return SessionIntegrityReport(
            session_id=session_id,
            total_signals=len(signals),
            aggregation_score=round(aggregation_score, 2),
            review_recommended=review_recommended,
            signals=signals,
            confidence_in_assessment=assessment_confidence,
            summary=summary,
        )

    def detect_cheating(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy compatibility wrapper for older implementations."""
        events = []
        if "events" in session_data:
            events = session_data["events"]
        else:
            if session_data.get("tab_switches", 0) > 0:
                events.extend([{"type": "Window blur/tab switch detected"}] * session_data.get("tab_switches", 0))
            if session_data.get("instant_chars", 0) > 100:
                events.append({"type": "Large paste detected"})
            if session_data.get("face_count", 1) > 1:
                events.append({"type": "Multiple faces (Legacy)", "evidence": "Legacy CV signal"})

        report = self.process_raw_events(session_data.get("session_id", "unknown"), events)

        return {
            "is_cheating": report.review_recommended,
            "risk_score": report.aggregation_score,
            "anomalies": [sig.signal_type for sig in report.signals],
            "recommendations": [report.summary],
            "confidence": report.confidence_in_assessment,
            "report": report.model_dump(),
        }
