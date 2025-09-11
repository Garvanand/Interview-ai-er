#!/usr/bin/env python3
"""
Test script with proper UUID format
"""

import requests
import json
import uuid

BASE_URL = "http://localhost:5000/api"

def test_start_session_with_uuid():
    """Test session creation with proper UUID"""
    print("🔍 Testing Session Creation with UUID...")
    try:
        # Generate a proper UUID
        test_user_id = str(uuid.uuid4())
        print(f"   Generated UUID: {test_user_id}")
        
        data = {
            "user_id": test_user_id,
            "interview_type": "Software Engineer"
        }
        
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

def main():
    """Run UUID test"""
    print("🚀 Testing with Proper UUID Format...\n")
    
    # Test session creation with UUID
    session_id = test_start_session_with_uuid()
    
    if session_id:
        # Test getting a question
        question_result = test_get_question(session_id)
        print("\n🎉 UUID Test Complete!")
    else:
        print("\n❌ UUID Test Failed!")

if __name__ == "__main__":
    main()
