#!/usr/bin/env python3
"""
Simple API test script for debugging
"""

import requests
import json

BASE_URL = "http://localhost:5000/api"

def test_health():
    """Test health endpoint"""
    print("🔍 Testing Health Endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"✅ Status: {response.status_code}")
        print(f"✅ Response: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_start_session():
    """Test session creation"""
    print("\n🔍 Testing Session Creation...")
    try:
        data = {
            "user_id": "test-user-123",
            "interview_type": "Software Engineer"
        }
        response = requests.post(
            f"{BASE_URL}/start_session",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        print(f"✅ Status: {response.status_code}")
        print(f"✅ Response: {response.json()}")
        return response.json()
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

def test_log_event(session_id):
    """Test logging an event"""
    print(f"\n🔍 Testing Log Event for session {session_id}...")
    try:
        data = {
            "session_id": session_id,
            "event_type": "session_started",
            "details": {"test": True}
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
    """Run all tests"""
    print("🚀 Starting API Tests...\n")
    
    # Test health
    if not test_health():
        print("❌ Health check failed. Stopping tests.")
        return
    
    # Test session creation
    session_result = test_start_session()
    if not session_result or session_result.get('error'):
        print("❌ Session creation failed. Check server logs.")
        return
    
    session_id = session_result.get('data', {}).get('session_id')
    if not session_id:
        print("❌ No session ID returned.")
        return
    
    print(f"✅ Session created with ID: {session_id}")
    
    # Test getting a question
    question_result = test_get_question(session_id)
    
    # Test logging an event
    log_result = test_log_event(session_id)
    
    print("\n🎉 API Testing Complete!")

if __name__ == "__main__":
    main()
