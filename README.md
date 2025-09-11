# Mock Interview Platform Backend

A Flask-based backend API for a mock interview platform that integrates with Supabase for data storage and Google Gemini AI for interview question generation and answer evaluation.

## 🚀 Features

- **AI-Powered Questions**: Generate interview questions using Google Gemini AI
- **Smart Evaluation**: AI-powered answer evaluation with detailed feedback
- **Session Management**: Complete interview session lifecycle management
- **Real-time Logging**: Track user behavior and detect anomalies
- **Production Ready**: Clean, secure, and scalable architecture
- **CORS Enabled**: Ready for Next.js frontend integration

## 🏗️ Architecture

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

## 📁 Project Structure

```
Backend(intervieweee)/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── routes/              # API route modules
│   │   ├── __init__.py
│   │   ├── interview.py     # Interview endpoints
│   │   └── logging.py       # Logging endpoints
│   ├── models/              # Data model definitions
│   │   └── __init__.py
│   └── services/            # Business logic services
│       ├── __init__.py
│       └── supabase_service.py
├── app.py                   # Main application entry point
├── gemini_service.py        # Gemini AI service
├── requirements.txt         # Python dependencies
├── env.example             # Environment variables template
├── database_schema.sql     # Supabase database schema
├── README.md               # This file
└── memory-bank/            # Project documentation
```

## 🛠️ Setup Instructions

### 1. Prerequisites

- Python 3.8+
- pip package manager
- Supabase account and project
- Google Gemini API key

### 2. Environment Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd Backend(intervieweee)
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   # Copy the example file
   cp env.example .env
   
   # Edit .env with your actual values
   SUPABASE_URL=your_supabase_project_url
   SUPABASE_KEY=your_supabase_anon_key
   GEMINI_API_KEY=your_gemini_api_key
   FLASK_SECRET_KEY=your_secret_key_here
   FRONTEND_URL=http://localhost:3000
   ```

### 3. Database Setup

1. **Create Supabase project** at [supabase.com](https://supabase.com)
2. **Run the database schema** in your Supabase SQL editor:
   ```sql
   -- Copy and paste the contents of database_schema.sql
   ```

### 4. Run the Application

```bash
python app.py
```

The server will start on `http://localhost:5000`

## 📚 API Endpoints

### Interview Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/start_session` | Start new interview session |
| `GET` | `/api/get_question` | Get interview question |
| `POST` | `/api/submit_answer` | Submit answer and get evaluation |
| `GET` | `/api/session/<id>` | Get session details |
| `POST` | `/api/end_session/<id>` | End interview session |

### Logging & Monitoring

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/log_event` | Log system events |
| `POST` | `/api/log_anomaly` | Log suspicious behavior |
| `GET` | `/api/events/<session_id>` | Get session events |
| `GET` | `/api/anomalies/<session_id>` | Get session anomalies |
| `GET` | `/api/health` | Health check |

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SUPABASE_URL` | Your Supabase project URL | Yes |
| `SUPABASE_KEY` | Your Supabase anon key | Yes |
| `GEMINI_API_KEY` | Your Google Gemini API key | Yes |
| `FLASK_SECRET_KEY` | Flask secret key | No (defaults to dev key) |
| `FRONTEND_URL` | Frontend URL for CORS | No (defaults to localhost:3000) |

### Database Tables

- **sessions**: Interview session management
- **questions**: Question and answer storage
- **logs**: Event logging and monitoring
- **anomalies**: Suspicious behavior detection

## 🚀 Usage Examples

### Start Interview Session

```bash
curl -X POST http://localhost:5000/api/start_session \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-uuid",
    "interview_type": "Software Engineer"
  }'
```

### Get Interview Question

```bash
curl "http://localhost:5000/api/get_question?session_id=session-uuid&interview_type=Software%20Engineer"
```

### Submit Answer

```bash
curl -X POST http://localhost:5000/api/submit_answer \
  -H "Content-Type: application/json" \
  -d '{
    "question_id": "question-uuid",
    "answer_text": "I have 5 years of experience in Python development...",
    "session_id": "session-uuid"
  }'
```

### Log Event

```bash
curl -X POST http://localhost:5000/api/log_event \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session-uuid",
    "event_type": "answer_started",
    "details": {"timestamp": "2024-01-01T00:00:00Z"}
  }'
```

## 🔒 Security Features

- **Row Level Security (RLS)**: Users can only access their own data
- **Environment Variable Protection**: No hardcoded secrets
- **Input Validation**: Comprehensive request validation
- **CORS Configuration**: Secure cross-origin communication
- **Error Handling**: No sensitive information in error messages

## 🧪 Testing

The application includes comprehensive error handling and logging. Test the endpoints using:

1. **Health Check**: `GET /api/health`
2. **Invalid Requests**: Test with missing required fields
3. **Database Connectivity**: Verify Supabase connection
4. **AI Service**: Test question generation and evaluation

## 🚀 Deployment

### Production Considerations

1. **Environment Variables**: Use production-grade secret management
2. **Database**: Ensure Supabase production instance
3. **CORS**: Update `FRONTEND_URL` to production domain
4. **Logging**: Configure production logging levels
5. **HTTPS**: Use reverse proxy (nginx) with SSL

### Docker (Optional)

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions:
1. Check the logs for error details
2. Verify environment variables are set correctly
3. Ensure Supabase database schema is properly configured
4. Check Google Gemini API key validity

## 🔮 Future Enhancements

- [ ] Real-time WebSocket support
- [ ] Advanced analytics dashboard
- [ ] Multi-language support
- [ ] Interview templates
- [ ] Performance metrics
- [ ] Automated testing suite
