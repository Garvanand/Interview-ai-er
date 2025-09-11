#!/usr/bin/env python3
"""
Enhanced Backend Test Script
Tests all the new features including code evaluation, security monitoring, and practice mode
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5000"
TEST_USER_ID = "36897b70-7b7f-4b26-998a-3f7ffebdb39b"  # Your test user ID

def test_health_check():
    """Test the health check endpoint"""
    print("🔍 Testing Health Check...")
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health Check: {data['status']}")
            print(f"   Database: {data['components']['database']}")
            print(f"   API: {data['components']['api']}")
            return True
        else:
            print(f"❌ Health Check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health Check error: {e}")
        return False

def test_metrics():
    """Test the metrics endpoint"""
    print("\n📊 Testing Metrics...")
    try:
        response = requests.get(f"{BASE_URL}/api/metrics")
        if response.status_code == 200:
            data = response.json()
            metrics = data['data']['metrics']
            print(f"✅ Metrics retrieved successfully")
            print(f"   Active Sessions: {metrics['active_sessions']}")
            print(f"   Total Sessions: {metrics['total_sessions']}")
            print(f"   Total Questions: {metrics['total_questions']}")
            print(f"   Total Answers: {metrics['total_answers']}")
            return True
        else:
            print(f"❌ Metrics failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Metrics error: {e}")
        return False

def test_start_session():
    """Test starting a new interview session"""
    print("\n🚀 Testing Start Session...")
    try:
        payload = {
            "user_id": TEST_USER_ID,
            "interview_type": "technical"
        }
        response = requests.post(f"{BASE_URL}/api/start_session", json=payload)
        if response.status_code == 200:
            data = response.json()
            session_id = data['data']['session_id']
            print(f"✅ Session started successfully")
            print(f"   Session ID: {session_id}")
            print(f"   Interview Type: {data['data']['interview_type']}")
            return session_id
        else:
            print(f"❌ Start session failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Start session error: {e}")
        return None

def test_get_question(session_id):
    """Test getting a question for the session"""
    print(f"\n❓ Testing Get Question for session {session_id}...")
    try:
        payload = {
            "session_id": session_id,
            "interview_type": "technical"
        }
        response = requests.post(f"{BASE_URL}/api/get_question", json=payload)
        if response.status_code == 200:
            data = response.json()
            question = data['data']['question']
            print(f"✅ Question retrieved successfully")
            print(f"   Question ID: {question['id']}")
            print(f"   Type: {question.get('type', 'N/A')}")
            print(f"   Difficulty: {question.get('difficulty', 'N/A')}")
            print(f"   Text: {question['question'][:100]}...")
            return question
        else:
            print(f"❌ Get question failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Get question error: {e}")
        return None

def test_submit_answer(session_id, question_id):
    """Test submitting an answer"""
    print(f"\n✍️ Testing Submit Answer...")
    try:
        payload = {
            "session_id": session_id,
            "question_id": question_id,
            "answer": "This is a test answer for the interview question. I believe the solution involves understanding the core concepts and applying them systematically."
        }
        response = requests.post(f"{BASE_URL}/api/submit_answer", json=payload)
        if response.status_code == 200:
            data = response.json()
            evaluation = data['data']['evaluation']
            print(f"✅ Answer submitted successfully")
            print(f"   Score: {evaluation.get('score', 'N/A')}")
            print(f"   Feedback: {evaluation.get('feedback', 'N/A')[:100]}...")
            return evaluation
        else:
            print(f"❌ Submit answer failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Submit answer error: {e}")
        return None

def test_submit_code(session_id, question_id):
    """Test submitting code for evaluation"""
    print(f"\n💻 Testing Submit Code...")
    try:
        payload = {
            "session_id": session_id,
            "question_id": question_id,
            "code": """
def find_maximum(numbers):
    if not numbers:
        return None
    return max(numbers)

# Test the function
test_data = [1, 5, 3, 9, 2, 7]
result = find_maximum(test_data)
print(f"Maximum value: {result}")
            """,
            "language": "python"
        }
        response = requests.post(f"{BASE_URL}/api/submit_code", json=payload)
        if response.status_code == 200:
            data = response.json()
            evaluation = data['data']['evaluation']
            print(f"✅ Code submitted successfully")
            print(f"   Score: {evaluation.get('score', 'N/A')}")
            print(f"   Code Quality: {evaluation.get('code_quality', 'N/A')}")
            print(f"   Correctness: {evaluation.get('correctness', 'N/A')}")
            print(f"   Time Complexity: {evaluation.get('time_complexity', 'N/A')}")
            return evaluation
        else:
            print(f"❌ Submit code failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Submit code error: {e}")
        return False

def test_security_check(session_id):
    """Test security monitoring"""
    print(f"\n🛡️ Testing Security Check...")
    try:
        payload = {
            "session_id": session_id,
            "security_data": {
                "face_count": 1,
                "tab_switches": 0,
                "copy_paste_events": 0,
                "typing_pattern": "normal",
                "browser_focus": True
            }
        }
        response = requests.post(f"{BASE_URL}/api/security/check", json=payload)
        if response.status_code == 200:
            data = response.json()
            security_result = data['data']['security_result']
            print(f"✅ Security check completed")
            print(f"   Risk Score: {security_result.get('risk_score', 'N/A')}")
            print(f"   Is Cheating: {security_result.get('is_cheating', 'N/A')}")
            print(f"   Anomalies: {security_result.get('anomalies', [])}")
            return security_result
        else:
            print(f"❌ Security check failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Security check error: {e}")
        return None

def test_log_event(session_id):
    """Test logging an event"""
    print(f"\n📝 Testing Log Event...")
    try:
        payload = {
            "session_id": session_id,
            "event_type": "test_event",
            "details": {
                "test": True,
                "timestamp": datetime.now().isoformat(),
                "description": "This is a test event for the enhanced backend"
            }
        }
        response = requests.post(f"{BASE_URL}/api/log_event", json=payload)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Event logged successfully")
            print(f"   Event ID: {data['data']['event_id']}")
            return True
        else:
            print(f"❌ Log event failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Log event error: {e}")
        return False

def test_practice_coding():
    """Test practice mode coding question generation"""
    print(f"\n🎯 Testing Practice Coding...")
    try:
        payload = {
            "topic": "algorithms",
            "difficulty": "medium"
        }
        response = requests.post(f"{BASE_URL}/api/practice/coding", json=payload)
        if response.status_code == 200:
            data = response.json()
            question = data['data']['question']
            print(f"✅ Practice question generated successfully")
            print(f"   Topic: {question.get('topic', 'N/A')}")
            print(f"   Difficulty: {question.get('difficulty', 'N/A')}")
            print(f"   Question: {question.get('question', 'N/A')[:100]}...")
            return question
        else:
            print(f"❌ Practice coding failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Practice coding error: {e}")
        return None

def test_end_session(session_id):
    """Test ending the session"""
    print(f"\n🏁 Testing End Session...")
    try:
        payload = {
            "final_score": 85.5
        }
        response = requests.post(f"{BASE_URL}/api/end_session/{session_id}", json=payload)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Session ended successfully")
            print(f"   Final Score: {data['data']['final_score']}")
            print(f"   Status: {data['data']['status']}")
            return True
        else:
            print(f"❌ End session failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ End session error: {e}")
        return False

def test_session_details(session_id):
    """Test getting session details"""
    print(f"\n📋 Testing Get Session Details...")
    try:
        response = requests.get(f"{BASE_URL}/api/session/{session_id}")
        if response.status_code == 200:
            data = response.json()
            session = data['data']['session']
            print(f"✅ Session details retrieved successfully")
            print(f"   Status: {session.get('status', 'N/A')}")
            print(f"   Score: {session.get('score', 'N/A')}")
            print(f"   Questions: {len(session.get('questions', []))}")
            return True
        else:
            print(f"❌ Get session details failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Get session details error: {e}")
        return False

def run_comprehensive_test():
    """Run all tests in sequence"""
    print("🧪 Starting Enhanced Backend Comprehensive Test")
    print("=" * 60)
    
    # Test basic functionality
    if not test_health_check():
        print("❌ Health check failed, stopping tests")
        return False
    
    if not test_metrics():
        print("❌ Metrics test failed, stopping tests")
        return False
    
    # Test session management
    session_id = test_start_session()
    if not session_id:
        print("❌ Session creation failed, stopping tests")
        return False
    
    # Test question functionality
    question = test_get_question(session_id)
    if not question:
        print("❌ Question retrieval failed, stopping tests")
        return False
    
    # Test answer submission
    evaluation = test_submit_answer(session_id, question['id'])
    if not evaluation:
        print("❌ Answer submission failed, stopping tests")
        return False
    
    # Test code submission
    code_result = test_submit_code(session_id, question['id'])
    if code_result is False:
        print("❌ Code submission failed, stopping tests")
        return False
    
    # Test security monitoring
    security_result = test_security_check(session_id)
    if not security_result:
        print("❌ Security check failed, stopping tests")
        return False
    
    # Test event logging
    if not test_log_event(session_id):
        print("❌ Event logging failed, stopping tests")
        return False
    
    # Test practice mode
    practice_question = test_practice_coding()
    if not practice_question:
        print("❌ Practice mode failed, stopping tests")
        return False
    
    # Test session details
    if not test_session_details(session_id):
        print("❌ Session details failed, stopping tests")
        return False
    
    # End the session
    if not test_end_session(session_id):
        print("❌ Session ending failed, stopping tests")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All Enhanced Backend Tests Completed Successfully!")
    print("✅ Health Check: Working")
    print("✅ Metrics: Working")
    print("✅ Session Management: Working")
    print("✅ Question Generation: Working")
    print("✅ Answer Evaluation: Working")
    print("✅ Code Evaluation: Working")
    print("✅ Security Monitoring: Working")
    print("✅ Event Logging: Working")
    print("✅ Practice Mode: Working")
    print("✅ Session Details: Working")
    print("✅ Session Ending: Working")
    
    return True

if __name__ == "__main__":
    try:
        success = run_comprehensive_test()
        if success:
            print("\n🚀 Enhanced Backend is fully functional and ready for frontend integration!")
        else:
            print("\n❌ Some tests failed. Please check the backend configuration.")
    except KeyboardInterrupt:
        print("\n⏹️ Tests interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error during testing: {e}")
