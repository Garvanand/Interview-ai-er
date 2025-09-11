# Project Brief: Mock Interview Platform Backend

## Project Overview
A Flask-based backend API for a mock interview platform that integrates with Supabase for data storage and Google Gemini AI for interview question generation and answer evaluation.

## Core Requirements
1. **Environment & Setup**: Flask app with proper project structure
2. **Supabase Integration**: Database connection and table models
3. **Gemini AI Integration**: Question generation and answer evaluation
4. **API Endpoints**: Session management, question handling, and logging
5. **Production Ready**: Clean, minimal, and well-structured code

## Technical Stack
- **Backend**: Flask (Python)
- **Database**: Supabase (PostgreSQL)
- **AI Service**: Google Gemini API
- **Environment**: python-dotenv
- **CORS**: flask-cors for frontend integration

## Project Structure
```
Backend(intervieweee)/
├── app/
│   ├── __init__.py
│   ├── routes/
│   ├── models/
│   └── services/
├── app.py
├── gemini_service.py
├── requirements.txt
├── .env.example
└── memory-bank/
```

## Success Criteria
- Clean, production-ready Flask application
- Proper Supabase integration with defined table schemas
- Functional Gemini AI service for interview questions
- RESTful API endpoints for session management
- Comprehensive environment configuration
- CORS enabled for frontend integration
