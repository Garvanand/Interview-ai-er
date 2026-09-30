from flask import Flask
from flask_cors import CORS
import os
from dotenv import load_dotenv

def create_app():
    """Application factory for Flask app"""
    # Load environment variables
    load_dotenv()
    
    # Create Flask app
    app = Flask(__name__)
    
    # Configure app
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')
    app.config['SUPABASE_URL'] = os.getenv('SUPABASE_URL')
    app.config['SUPABASE_KEY'] = os.getenv('SUPABASE_KEY')
    app.config['GEMINI_API_KEY'] = os.getenv('GEMINI_API_KEY')
    app.config['FRONTEND_URL'] = os.getenv('FRONTEND_URL', 'http://localhost:3000')
    
    # Validate required environment variables
    required_vars = ['SUPABASE_URL', 'SUPABASE_KEY', 'GEMINI_API_KEY']
    missing_vars = [var for var in required_vars if not app.config.get(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    # Configure CORS
    CORS(app, origins=[app.config['FRONTEND_URL']], supports_credentials=True)
    
    # Register blueprints
    from app.routes.interview import interview_bp
    from app.routes.logging import logging_bp
    from app.routes.intelligence import intelligence_bp
    from app.routes.analytics import analytics_bp
    
    app.register_blueprint(interview_bp, url_prefix='/api')
    app.register_blueprint(logging_bp, url_prefix='/api')
    app.register_blueprint(intelligence_bp, url_prefix='/api/intelligence')
    app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
    
    # Error handlers
    @app.errorhandler(400)
    def bad_request(error):
        return {'error': True, 'message': 'Bad request', 'code': 'BAD_REQUEST'}, 400
    
    @app.errorhandler(404)
    def not_found(error):
        return {'error': True, 'message': 'Not found', 'code': 'NOT_FOUND'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return {'error': True, 'message': 'Internal server error', 'code': 'INTERNAL_ERROR'}, 500
    
    return app
