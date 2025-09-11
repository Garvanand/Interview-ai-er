# Active Context

## Current Task
Scaffolding a complete Flask backend for a mock interview platform with Supabase integration and Gemini AI services.

## Immediate Goals
1. **Project Structure**: Create organized directory structure with Flask app factory
2. **Core Dependencies**: Set up requirements.txt and environment configuration
3. **Supabase Integration**: Implement database connection and table schemas
4. **Gemini Service**: Create AI service for question generation and evaluation
5. **API Endpoints**: Implement all required REST endpoints
6. **Production Readiness**: Ensure clean, minimal, and maintainable code

## Current Status
- **Phase**: Planning and Documentation
- **Progress**: 0% - Memory Bank created, ready for implementation
- **Next Step**: User approval of plan before moving to implementation

## Key Decisions Made
- **Architecture**: Flask app factory pattern with blueprint organization
- **Database**: Supabase with defined table schemas for users, sessions, questions, logs, anomalies
- **AI Integration**: Google Gemini API for interview question generation and evaluation
- **API Design**: RESTful JSON endpoints with proper error handling
- **Security**: Environment variable protection for all sensitive data

## Technical Considerations
- **CORS**: Enabled for Next.js frontend integration
- **Error Handling**: Standardized error response format
- **Logging**: Structured logging for debugging and monitoring
- **Validation**: Input validation for all API endpoints
- **Testing**: Code structure should support easy testing

## Dependencies to Install
- Flask and Flask-CORS for web framework
- supabase-py for database operations
- google-genai for AI services
- python-dotenv for environment management

## Files to Create
1. `app.py` - Main Flask application entry point
2. `gemini_service.py` - Gemini AI service helper
3. `requirements.txt` - Python dependencies
4. `.env.example` - Environment variables template
5. `app/__init__.py` - Flask app factory
6. `app/routes/` - API route modules
7. `app/models/` - Data model definitions
8. `app/services/` - Business logic services

## Success Metrics
- Clean, production-ready Flask application
- All required API endpoints functional
- Proper Supabase integration with defined schemas
- Working Gemini AI service
- Comprehensive environment configuration
- CORS enabled for frontend integration
