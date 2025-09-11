# System Patterns

## Architecture Overview

### High-Level Structure
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Flask API     │    │   External      │
│   (Next.js)     │◄──►│   Backend       │◄──►│   Services      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Supabase      │
                       │   Database      │
                       └─────────────────┘
```

## Design Patterns

### 1. Application Factory Pattern
- **Purpose**: Clean application initialization and configuration
- **Implementation**: Factory function in `app/__init__.py`
- **Benefits**: Easy testing, multiple instances, configuration flexibility

### 2. Blueprint Pattern
- **Purpose**: Modular route organization
- **Implementation**: Separate route files for different API domains
- **Benefits**: Code organization, maintainability, scalability

### 3. Service Layer Pattern
- **Purpose**: Business logic separation from routes
- **Implementation**: `gemini_service.py` for AI operations
- **Benefits**: Reusability, testability, single responsibility

### 4. Repository Pattern
- **Purpose**: Data access abstraction
- **Implementation**: Supabase client wrapper functions
- **Benefits**: Database independence, easier testing, centralized data logic

## Data Flow Patterns

### Session Management Flow
```
1. POST /api/start_session
   ↓
2. Create session record in Supabase
   ↓
3. Return session_id to frontend
```

### Question Generation Flow
```
1. GET /api/get_question
   ↓
2. Call Gemini API for question
   ↓
3. Store question in Supabase
   ↓
4. Return question to frontend
```

### Answer Evaluation Flow
```
1. POST /api/submit_answer
   ↓
2. Store answer in Supabase
   ↓
3. Call Gemini API for evaluation
   ↓
4. Update score and return feedback
```

## Error Handling Patterns

### Standard Error Response
```json
{
  "error": true,
  "message": "Descriptive error message",
  "code": "ERROR_CODE",
  "details": {}
}
```

### HTTP Status Codes
- **200**: Success
- **201**: Created (session started)
- **400**: Bad Request (validation errors)
- **404**: Not Found (session/question not found)
- **500**: Internal Server Error (server issues)

## Security Patterns

### Environment Variable Protection
- All sensitive data (API keys, URLs) stored in `.env`
- `.env.example` provided for reference
- No hardcoded secrets in source code

### CORS Configuration
- Specific origin allowance for Next.js frontend
- Secure cross-origin communication
- Production-ready CORS settings
