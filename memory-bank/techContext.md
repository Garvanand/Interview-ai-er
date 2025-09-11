# Technical Context

## Technology Stack

### Core Framework
- **Flask**: Lightweight Python web framework for API development
- **Python**: Primary programming language (3.8+ recommended)

### Database & Storage
- **Supabase**: PostgreSQL-based backend-as-a-service
- **supabase-py**: Official Python client for Supabase
- **PostgreSQL**: Underlying database system

### AI & Machine Learning
- **Google Gemini API**: Advanced AI model for question generation and evaluation
- **google-genai**: Official Python client for Gemini API

### Development Tools
- **python-dotenv**: Environment variable management
- **flask-cors**: Cross-Origin Resource Sharing support
- **requirements.txt**: Python dependency management

## Development Environment
- **OS**: Windows 10 (PowerShell)
- **Python**: 3.8+ with pip
- **Virtual Environment**: Recommended for dependency isolation
- **IDE**: Cursor with AI assistance

## Technical Constraints
- **API Design**: RESTful JSON endpoints
- **CORS**: Enabled for Next.js frontend integration
- **Error Handling**: Comprehensive error responses
- **Logging**: Structured logging for debugging and monitoring
- **Security**: Environment variable protection for API keys

## Dependencies
```
flask>=2.3.0
flask-cors>=4.0.0
supabase-py>=2.0.0
google-genai>=0.3.0
python-dotenv>=1.0.0
```

## Architecture Patterns
- **MVC-like**: Routes, Models, Services separation
- **Service Layer**: Business logic isolation
- **Repository Pattern**: Data access abstraction
- **Environment Configuration**: Centralized config management
