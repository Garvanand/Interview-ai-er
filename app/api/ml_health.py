from flask import Blueprint, jsonify
from ml.serving.inference_service import InferenceService

ml_health_bp = Blueprint("ml_health", __name__)

@ml_health_bp.route("/health", methods=["GET"])
def get_health():
    """Returns ML Serving layer health and loaded models."""
    health_info = InferenceService.get_health()
    return jsonify({
        "status": "ok",
        "models": health_info
    })
