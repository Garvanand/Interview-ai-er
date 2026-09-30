"""
Compatibility shim re-exporting from app.security.

Preferred import: `from app.security import SecurityService, Severity, ...`
"""
from app.security.integrity import (
    SecurityService,
    Severity,
    IntegritySignal,
    SessionIntegrityReport,
)

__all__ = [
    "SecurityService",
    "Severity",
    "IntegritySignal",
    "SessionIntegrityReport",
]
