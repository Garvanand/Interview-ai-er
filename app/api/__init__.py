"""
app/api — HTTP transport layer.

Exports the four blueprints that are registered on the Flask app.
All routes are prefixed with /api by the app factory in app/__init__.py.
"""
from app.api.interview import interview_bp
from app.api.logging import logging_bp
from app.api.intelligence import intelligence_bp
from app.api.analytics import analytics_bp

__all__ = ["interview_bp", "logging_bp", "intelligence_bp", "analytics_bp"]
