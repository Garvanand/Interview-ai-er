#!/usr/bin/env python3
"""
Mock Interview Platform Backend
A comprehensive Flask-based backend for conducting AI-powered mock interviews
"""

import logging
import os
from app import create_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)

logger = logging.getLogger(__name__)

# Create Flask app
app = create_app()

if __name__ == '__main__':
    print("🚀 Starting Mock Interview Platform Backend...")
    print("=" * 60)
    
    # Display API documentation
    print("📚 API Documentation:")
    print("   POST /api/start_session     - Start new interview session")
    print("   GET  /api/get_question      - Get interview question")
    print("   POST /api/submit_answer     - Submit answer and get evaluation")
    print("   POST /api/submit_code       - Submit code for evaluation")
    print("   POST /api/log_event         - Log system events")
    print("   POST /api/log_anomaly      - Log suspicious behavior")
    print("   GET  /api/session/<id>      - Get session details")
    print("   POST /api/end_session/<id>  - End interview session")
    print("   GET  /api/user/<id>/sessions - Get user's interview history")
    print("   POST /api/follow_up_question - Get follow-up question")
    print("   POST /api/security/check    - Perform security check")
    print("   GET  /api/security/report/<id> - Get security report")
    print("   POST /api/practice/coding   - Generate coding practice questions")
    print("   GET  /api/health            - Health check")
    print("   GET  /api/metrics           - System metrics")
    
    print("\n🔧 Environment Variables Required:")
    print("   SUPABASE_URL     - Your Supabase project URL")
    print("   SUPABASE_KEY     - Your Supabase anon key")
    print("   GEMINI_API_KEY   - Your Google Gemini API key")
    print("   FLASK_SECRET_KEY - Secret key for Flask sessions")
    print("   FRONTEND_URL     - Frontend URL for CORS (optional)")
    
    print("\n🌐 Server Configuration:")
    print("   Host: 0.0.0.0 (accessible from any IP)")
    print("   Port: 5000")
    print("   Debug: Enabled")
    print("   CORS: Enabled for frontend integration")
    
    print("\n📊 Features:")
    print("   ✅ AI-powered question generation")
    print("   ✅ Intelligent answer evaluation")
    print("   ✅ Multiple interview types support")
    print("   ✅ Session management and tracking")
    print("   ✅ Comprehensive logging and monitoring")
    print("   ✅ Anomaly detection")
    print("   ✅ Follow-up question generation")
    print("   ✅ Performance metrics")
    
    print("\n🔒 Security Features:")
    print("   ✅ Input validation and sanitization")
    print("   ✅ Error handling and logging")
    print("   ✅ CORS protection")
    print("   ✅ Database connection security")
    
    print("=" * 60)
    
    try:
        # Start the server
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        print(f"\n❌ Failed to start server: {e}")
        exit(1)
