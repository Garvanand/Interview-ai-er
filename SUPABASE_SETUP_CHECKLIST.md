# Supabase Setup Checklist for Mock Interview Platform

## ✅ **Phase 1: Project Creation**
- [ ] **Create Supabase Account**
  - [ ] Go to [supabase.com](https://supabase.com)
  - [ ] Sign up with GitHub or create account
  - [ ] Verify email address

- [ ] **Create New Project**
  - [ ] Click "New project"
  - [ ] Choose organization
  - [ ] Enter project name: `mock-interview-platform`
  - [ ] Set strong database password (save this!)
  - [ ] Choose region (closest to users)
  - [ ] Wait for project setup (5-10 minutes)

## ✅ **Phase 2: Get Credentials**
- [ ] **Extract Project Details**
  - [ ] Go to **Settings** → **API**
  - [ ] Copy **Project URL** (format: `https://[project-id].supabase.co`)
  - [ ] Copy **anon public** key (starts with `eyJ...`)
  - [ ] Note **service_role** key (keep private, admin only)

## ✅ **Phase 3: Database Schema**
- [ ] **Run Database Schema**
  - [ ] Go to **SQL Editor** in Supabase dashboard
  - [ ] Click "New query"
  - [ ] Copy entire `database_schema.sql` content
  - [ ] Paste into SQL editor
  - [ ] Click "Run" to execute
  - [ ] Verify no errors in execution

- [ ] **Verify Tables Created**
  - [ ] Go to **Table Editor**
  - [ ] Confirm these tables exist:
    - [ ] `sessions`
    - [ ] `questions`
    - [ ] `logs`
    - [ ] `anomalies`
  - [ ] Check table structure matches schema

## ✅ **Phase 4: Environment Configuration**
- [ ] **Create .env File**
  - [ ] Copy `env.example` to `.env`
  - [ ] Update with your actual values:
    - [ ] `SUPABASE_URL` = your project URL
    - [ ] `SUPABASE_KEY` = your anon key
    - [ ] `GEMINI_API_KEY` = your Gemini API key
    - [ ] `FLASK_SECRET_KEY` = generate secure key
    - [ ] `FRONTEND_URL` = your frontend URL

## ✅ **Phase 5: Test Connection**
- [ ] **Install Dependencies**
  - [ ] Create virtual environment: `python -m venv venv`
  - [ ] Activate virtual environment
  - [ ] Install requirements: `pip install -r requirements.txt`

- [ ] **Run Connection Test**
  - [ ] Execute: `python test_supabase.py`
  - [ ] Verify all tests pass
  - [ ] Check for any error messages

## ✅ **Phase 6: Start Backend**
- [ ] **Launch Flask Application**
  - [ ] Run: `python app.py`
  - [ ] Verify server starts without errors
  - [ ] Check console output for success messages
  - [ ] Test health endpoint: `GET /api/health`

## ✅ **Phase 7: Test API Endpoints**
- [ ] **Basic Functionality**
  - [ ] Health check: `GET /api/health`
  - [ ] Start session: `POST /api/start_session`
  - [ ] Get question: `GET /api/get_question`
  - [ ] Submit answer: `POST /api/submit_answer`
  - [ ] Log event: `POST /api/log_event`

## 🔧 **Troubleshooting Common Issues**

### **Connection Issues**
- [ ] Verify `.env` file exists and has correct values
- [ ] Check Supabase project is active (not paused)
- [ ] Ensure database schema was run successfully
- [ ] Verify anon key is correct (not service role key)

### **Table Access Issues**
- [ ] Confirm RLS policies are active
- [ ] Check table names match exactly
- [ ] Verify user permissions in Supabase

### **Environment Variable Issues**
- [ ] Ensure `.env` file is in project root
- [ ] Check for typos in variable names
- [ ] Restart Flask app after changing `.env`

## 📊 **Verification Commands**

```bash
# Test Supabase connection
python test_supabase.py

# Start Flask backend
python app.py

# Test health endpoint (in another terminal)
curl http://localhost:5000/api/health
```

## 🎯 **Success Indicators**

- ✅ Flask app starts without errors
- ✅ Health endpoint returns `{"status": "healthy"}`
- ✅ All API endpoints respond correctly
- ✅ Database operations work (create, read, update)
- ✅ No connection errors in logs

## 🚨 **Security Notes**

- [ ] Never commit `.env` file to version control
- [ ] Use anon key for client operations
- [ ] Keep service role key private
- [ ] Regularly rotate API keys
- [ ] Monitor database access logs

## 📞 **Support Resources**

- **Supabase Docs**: [supabase.com/docs](https://supabase.com/docs)
- **Supabase Community**: [github.com/supabase/supabase/discussions](https://github.com/supabase/supabase/discussions)
- **Flask Documentation**: [flask.palletsprojects.com](https://flask.palletsprojects.com)

---

**Status**: ⏳ In Progress  
**Last Updated**: [Date]  
**Next Step**: [Current Phase]
