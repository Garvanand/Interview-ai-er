"""
Configuration settings for the Mock Interview Platform
"""

import os
from datetime import timedelta

class Config:
    """Base configuration class"""
    
    # Flask Configuration
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Supabase Configuration
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
    
    # Gemini AI Configuration
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    
    # CORS Configuration
    FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = 'app.log'
    
    # Rate Limiting (if implemented)
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = "memory://"
    
    # Security Configuration
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Database Configuration
    DATABASE_POOL_SIZE = 10
    DATABASE_MAX_OVERFLOW = 20
    
    # AI Configuration
    MAX_QUESTION_LENGTH = 500
    MAX_ANSWER_LENGTH = 2000
    EVALUATION_TIMEOUT = 30  # seconds
    
    # Interview Configuration
    SUPPORTED_INTERVIEW_TYPES = [
        'Software Engineer',
        'Data Scientist', 
        'Product Manager',
        'DevOps Engineer'
    ]
    
    SUPPORTED_DIFFICULTIES = ['beginner', 'intermediate', 'advanced']
    
    # Validation Configuration
    MIN_ANSWER_LENGTH = 10
    MAX_QUESTIONS_PER_SESSION = 20
    
    # Monitoring Configuration
    HEALTH_CHECK_INTERVAL = 60  # seconds
    METRICS_COLLECTION_INTERVAL = 300  # seconds

class DevelopmentConfig(Config):
    """Development configuration"""
    
    DEBUG = True
    TESTING = False
    
    # Development-specific settings
    LOG_LEVEL = 'DEBUG'
    SESSION_COOKIE_SECURE = False
    
    # Allow more verbose logging
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

class TestingConfig(Config):
    """Testing configuration"""
    
    DEBUG = False
    TESTING = True
    
    # Use test database
    SUPABASE_URL = os.environ.get('TEST_SUPABASE_URL') or Config.SUPABASE_URL
    SUPABASE_KEY = os.environ.get('TEST_SUPABASE_KEY') or Config.SUPABASE_KEY
    
    # Disable rate limiting for tests
    RATELIMIT_ENABLED = False
    
    # Faster timeouts for testing
    EVALUATION_TIMEOUT = 5

class ProductionConfig(Config):
    """Production configuration"""
    
    DEBUG = False
    TESTING = False
    
    # Production security settings
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'
    
    # Production logging
    LOG_LEVEL = 'WARNING'
    
    # Production rate limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = "redis://localhost:6379/0"
    
    # Production database settings
    DATABASE_POOL_SIZE = 20
    DATABASE_MAX_OVERFLOW = 30

class StagingConfig(Config):
    """Staging configuration"""
    
    DEBUG = False
    TESTING = False
    
    # Staging-specific settings
    LOG_LEVEL = 'INFO'
    SESSION_COOKIE_SECURE = False  # May not have HTTPS in staging
    
    # Moderate rate limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = "memory://"

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'staging': StagingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get configuration based on environment"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])
