#!/usr/bin/env python3
"""
Test script with real user ID from Supabase Auth
"""

import requests
import json

BASE_URL = "http://localhost:5000/api"

# Real user ID from Supabase Auth
REAL_USER_ID = "36897b70-7b7f-4b26-998a-3f7ffebdb39b"

def test_start_session_with_real_user():
    """Test session creation with real user ID"""
    print("🔍 Testing Session Creation with Real User ID...")
    try:
        data = {
            "user_id": REAL_USER_ID,
            "interview_type": "Software Engineer"
        }
        
        print(f"   Using User ID: {REAL_USER_ID}")
        print(f"   Sending data: {data}")
        
        response = requests.post(
            f"{BASE_URL}/start_session",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"✅ Status: {response.status_code}")
        print(f"✅ Response: {response.json()}")
        
        if response.status_code == 201:
            session_data = response.json().get('data', {})
            session_id = session_data.get('session_id')
            print(f"🎉 Success! Session ID: {session_id}")
            return session_id
        else:
            print(f"❌ Failed to create session")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_get_question(session_id):
    """Test getting a question"""
    print(f"\n🔍 Testing Get Question for session {session_id}...")
    try:
        params = {
            "session_id": session_id,
            "interview_type": "Software Engineer"
        }
        response = requests.get(f"{BASE_URL}/get_question", params=params)
        print(f"✅ Status: {response.status_code}")
        print(f"✅ Response: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_submit_answer(session_id, question_id):
    """Test submitting an answer"""
    print(f"\n🔍 Testing Submit Answer for question {question_id}...")
    try:
        data = {
            "session_id": session_id,
            "question_id": question_id,
            "answer_text": "This is a test answer for evaluation purposes."
        }
        response = requests.post(
            f"{BASE_URL}/submit_answer",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        print(f"✅ Status: {response.status_code}")
        print(f"✅ Response: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_log_event(session_id):
    """Test logging an event"""
    print(f"\n🔍 Testing Log Event for session {session_id}...")
    try:
        data = {
            "session_id": session_id,
            "event_type": "session_started",
            "details": {"test": True, "user_id": REAL_USER_ID}
        }
        response = requests.post(
            f"{BASE_URL}/log_event",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        print(f"✅ Status: {response.status_code}")
        print(f"✅ Response: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def main():
    """Run comprehensive test with real user"""
    print("🚀 Testing with Real User ID from Supabase Auth...\n")
    print(f"👤 User ID: {REAL_USER_ID}")
    
    # Test session creation
    session_id = test_start_session_with_real_user()
    
    if not session_id:
        print("\n❌ Test failed at session creation!")
        return
    
    print(f"\n✅ Session created successfully: {session_id}")
    
    # Test getting a question
    question_result = test_get_question(session_id)
    if question_result and not question_result.get('error'):
        question_data = question_result.get('data', {})
        question_id = question_data.get('question_id')
        
        if question_id:
            # Test submitting an answer
            answer_result = test_submit_answer(session_id, question_id)
        else:
            print("❌ No question ID returned")
    else:
        print("❌ Failed to get question")
    
    # Test logging an event
    log_result = test_log_event(session_id)
    
    print("\n🎉 Real User Test Complete!")
    print(f"📊 Session ID: {session_id}")
    print(f"👤 User ID: {REAL_USER_ID}")

if __name__ == "__main__":
    main()
