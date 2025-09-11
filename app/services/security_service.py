import logging
from typing import Dict, List, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class SecurityService:
    def __init__(self):
        self.risk_factors = {'multiple_faces': 0.8, 'copy_paste': 0.7, 'tab_switching': 0.6}
    
    def detect_cheating(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            risk_score = 0.0
            anomalies = []
            
            # Analyze face detection
            if session_data.get('face_count', 1) > 1:
                risk_score += 0.8
                anomalies.append('multiple_faces')
            
            # Analyze typing patterns
            if session_data.get('instant_chars', 0) > 100:
                risk_score += 0.7
                anomalies.append('copy_paste')
            
            # Analyze browser behavior
            if session_data.get('tab_switches', 0) > 10:
                risk_score += 0.6
                anomalies.append('tab_switching')
            
            return {
                'is_cheating': risk_score > 0.6,
                'risk_score': risk_score,
                'anomalies': anomalies,
                'recommendations': self._get_recommendations(anomalies)
            }
        except Exception as e:
            logger.error(f'Failed to detect cheating: {e}')
            return {'is_cheating': False, 'risk_score': 0.0, 'anomalies': [], 'recommendations': []}
    
    def _get_recommendations(self, anomalies: List[str]) -> List[str]:
        recommendations = []
        if 'multiple_faces' in anomalies:
            recommendations.append('Ensure only one person is visible')
        if 'copy_paste' in anomalies:
            recommendations.append('Type answers naturally')
        if 'tab_switching' in anomalies:
            recommendations.append('Stay focused on interview tab')
        return recommendations or ['Continue with normal behavior']
