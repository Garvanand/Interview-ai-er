#!/usr/bin/env python3
"""
Full Integration Test Script
Tests both backend functionality and frontend-backend connectivity
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BACKEND_URL = "http://localhost:5000"
FRONTEND_URL = "http://localhost:3000"
TEST_USER_ID = "36897b70-7b7f-4b26-998a-3f7ffebdb39b"

def test_backend_health():
    """Test backend health and basic functionality"""
    print("🔍 Testing Backend Health...")
    try:
        response = requests.get(f"{BACKEND_URL}/api/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Backend Health: {data['status']}")
            print(f"   Database: {data['components']['database']}")
            print(f"   API: {data['components']['api']}")
            return True
        else:
            print(f"❌ Backend health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend health check error: {e}")
        return False

def test_frontend_connectivity():
    """Test if frontend is accessible"""
    print("\n🌐 Testing Frontend Connectivity...")
    try:
        response = requests.get(FRONTEND_URL, timeout=5)
        if response.status_code == 200:
            print(f"✅ Frontend is accessible at {FRONTEND_URL}")
            return True
        else:
            print(f"⚠️ Frontend responded with status: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Frontend is not accessible at {FRONTEND_URL}")
        print("   Make sure to run 'npm run dev' in the frontend directory")
        return False
    except Exception as e:
        print(f"❌ Frontend connectivity error: {e}")
        return False

def test_backend_api_endpoints():
    """Test all major backend API endpoints"""
    print("\n🚀 Testing Backend API Endpoints...")
    
    # Test metrics endpoint
    try:
        response = requests.get(f"{BACKEND_URL}/api/metrics")
        if response.status_code == 200:
            print("✅ Metrics endpoint: Working")
        else:
            print(f"❌ Metrics endpoint: Failed ({response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Metrics endpoint error: {e}")
        return False
    
    # Test session creation
    try:
        payload = {
            "user_id": TEST_USER_ID,
            "interview_type": "technical"
        }
        response = requests.post(f"{BACKEND_URL}/api/start_session", json=payload)
        if response.status_code == 200:
            data = response.json()
            session_id = data['data']['session_id']
            print("✅ Start session endpoint: Working")
            
            # Test question generation
            payload = {
                "session_id": session_id,
                "interview_type": "technical"
            }
            response = requests.post(f"{BACKEND_URL}/api/get_question", json=payload)
            if response.status_code == 200:
                data = response.json()
                question = data['data']['question']
                print("✅ Get question endpoint: Working")
                
                # Test answer submission
                payload = {
                    "session_id": session_id,
                    "question_id": question['id'],
                    "answer": "This is a test answer for integration testing."
                }
                response = requests.post(f"{BACKEND_URL}/api/submit_answer", json=payload)
                if response.status_code == 200:
                    print("✅ Submit answer endpoint: Working")
                else:
                    print(f"❌ Submit answer endpoint: Failed ({response.status_code})")
                    return False
                
                # Test code submission
                payload = {
                    "session_id": session_id,
                    "question_id": question['id'],
                    "code": "def test(): return 'Hello World'",
                    "language": "python"
                }
                response = requests.post(f"{BACKEND_URL}/api/submit_code", json=payload)
                if response.status_code == 200:
                    print("✅ Submit code endpoint: Working")
                else:
                    print(f"❌ Submit code endpoint: Failed ({response.status_code})")
                    return False
                
                # Test security check
                payload = {
                    "session_id": session_id,
                    "security_data": {
                        "face_count": 1,
                        "tab_switches": 0,
                        "copy_paste_events": 0
                    }
                }
                response = requests.post(f"{BACKEND_URL}/api/security/check", json=payload)
                if response.status_code == 200:
                    print("✅ Security check endpoint: Working")
                else:
                    print(f"❌ Security check endpoint: Failed ({response.status_code})")
                    return False
                
                # End session
                payload = {"final_score": 85.0}
                response = requests.post(f"{BACKEND_URL}/api/end_session/{session_id}", json=payload)
                if response.status_code == 200:
                    print("✅ End session endpoint: Working")
                else:
                    print(f"❌ End session endpoint: Failed ({response.status_code})")
                    return False
                
            else:
                print(f"❌ Get question endpoint: Failed ({response.status_code})")
                return False
        else:
            print(f"❌ Start session endpoint: Failed ({response.status_code})")
            return False
    except Exception as e:
        print(f"❌ API endpoints test error: {e}")
        return False
    
    return True

def test_cors_configuration():
    """Test CORS configuration between frontend and backend"""
    print("\n🌍 Testing CORS Configuration...")
    try:
        # Test preflight request
        headers = {
            'Origin': FRONTEND_URL,
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'Content-Type'
        }
        response = requests.options(f"{BACKEND_URL}/api/health", headers=headers)
        
        if response.status_code == 200:
            cors_headers = response.headers
            if 'Access-Control-Allow-Origin' in cors_headers:
                print(f"✅ CORS is properly configured")
                print(f"   Allowed Origin: {cors_headers['Access-Control-Allow-Origin']}")
                return True
            else:
                print("❌ CORS headers missing")
                return False
        else:
            print(f"❌ CORS preflight failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ CORS test error: {e}")
        return False

def test_frontend_components():
    """Test if frontend components are properly structured"""
    print("\n🧩 Testing Frontend Component Structure...")
    
    # Check if key components exist
    components_to_check = [
        "frontend/components/interview/interview-interface.tsx",
        "frontend/components/ide/enhanced-code-editor.tsx",
        "frontend/components/anti-cheat/anti-cheat-guard.tsx",
        "frontend/lib/api-client.ts",
        "frontend/app/interview/page.tsx",
        "frontend/app/ide/page.tsx",
        "frontend/app/dashboard/page.tsx"
    ]
    
    missing_components = []
    for component in components_to_check:
        try:
            with open(component, 'r') as f:
                content = f.read()
                if len(content.strip()) > 0:
                    print(f"✅ {component.split('/')[-1]}: Present")
                else:
                    missing_components.append(component)
        except FileNotFoundError:
            missing_components.append(component)
    
    if missing_components:
        print(f"❌ Missing components: {len(missing_components)}")
        for component in missing_components:
            print(f"   - {component}")
        return False
    else:
        print("✅ All frontend components are present")
        return True

def test_api_client_integration():
    """Test the API client integration"""
    print("\n🔌 Testing API Client Integration...")
    
    try:
        with open("frontend/lib/api-client.ts", 'r') as f:
            content = f.read()
            
        # Check for key imports and configurations
        checks = [
            ("API_BASE_URL", "API base URL configuration"),
            ("InterviewSession", "Interview session interface"),
            ("Question", "Question interface"),
            ("CodeEvaluation", "Code evaluation interface"),
            ("startSession", "Start session method"),
            ("getQuestion", "Get question method"),
            ("submitAnswer", "Submit answer method"),
            ("submitCode", "Submit code method")
        ]
        
        all_present = True
        for check, description in checks:
            if check in content:
                print(f"✅ {description}: Present")
            else:
                print(f"❌ {description}: Missing")
                all_present = False
        
        return all_present
    except Exception as e:
        print(f"❌ API client test error: {e}")
        return False

def run_integration_test():
    """Run the complete integration test"""
    print("🧪 Starting Full Integration Test")
    print("=" * 60)
    
    results = []
    
    # Test backend health
    results.append(("Backend Health", test_backend_health()))
    
    # Test frontend connectivity
    results.append(("Frontend Connectivity", test_frontend_connectivity()))
    
    # Test backend API endpoints
    results.append(("Backend API Endpoints", test_backend_api_endpoints()))
    
    # Test CORS configuration
    results.append(("CORS Configuration", test_cors_configuration()))
    
    # Test frontend components
    results.append(("Frontend Components", test_frontend_components()))
    
    # Test API client integration
    results.append(("API Client Integration", test_api_client_integration()))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Integration Test Results")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All integration tests passed!")
        print("🚀 Your full-stack application is ready!")
        print("\nNext steps:")
        print("1. Start the frontend: cd frontend && npm run dev")
        print("2. Open http://localhost:3000 in your browser")
        print("3. Test the complete user experience")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed")
        print("Please check the errors above and fix them")
    
    return passed == total

if __name__ == "__main__":
    try:
        success = run_integration_test()
        if not success:
            print("\n💡 Troubleshooting tips:")
            print("- Ensure backend is running: python app.py")
            print("- Ensure frontend is running: cd frontend && npm run dev")
            print("- Check environment variables in .env file")
            print("- Verify database connection and schema")
    except KeyboardInterrupt:
        print("\n⏹️ Integration test interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error during integration testing: {e}")

