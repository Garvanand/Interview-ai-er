#!/usr/bin/env python3
"""
Comprehensive API Test Suite for Mock Interview Platform
"""

import requests
import json
import uuid
import time
from datetime import datetime

BASE_URL = "http://localhost:5000/api"

# Test configuration
REAL_USER_ID = "36897b70-7b7f-4b26-998a-3f7ffebdb39b"
TEST_INTERVIEW_TYPE = "Software Engineer"

class APITester:
    """Comprehensive API testing class"""
    
    def __init__(self):
        self.session_id = None
        self.question_id = None
        self.test_results = []
        
    def log_test(self, test_name, success, details=None):
        """Log test results"""
        result = {
            'test': test_name,
            'success': success,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   Details: {details}")
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        try:
            response = requests.get(f"{BASE_URL}/health")
            success = response.status_code == 200
            
            if success:
                data = response.json()
                self.log_test("Health Check", True, {
                    'status': data.get('status'),
                    'database': data.get('components', {}).get('database')
                })
            else:
                self.log_test("Health Check", False, {
                    'status_code': response.status_code,
                    'response': response.text
                })
                
        except Exception as e:
            self.log_test("Health Check", False, {'error': str(e)})
    
    def test_start_session(self):
        """Test session creation"""
        try:
            data = {
                "user_id": REAL_USER_ID,
                "interview_type": TEST_INTERVIEW_TYPE
            }
            
            response = requests.post(
                f"{BASE_URL}/start_session",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            
            success = response.status_code == 201
            
            if success:
                response_data = response.json()
                self.session_id = response_data['data']['session_id']
                self.log_test("Start Session", True, {
                    'session_id': self.session_id,
                    'interview_type': TEST_INTERVIEW_TYPE
                })
            else:
                self.log_test("Start Session", False, {
                    'status_code': response.status_code,
                    'response': response.text
                })
                
        except Exception as e:
            self.log_test("Start Session", False, {'error': str(e)})
    
    def test_get_question(self):
        """Test question generation"""
        if not self.session_id:
            self.log_test("Get Question", False, {'error': 'No session ID available'})
            return
            
        try:
            params = {
                "session_id": self.session_id,
                "interview_type": TEST_INTERVIEW_TYPE,
                "difficulty": "intermediate"
            }
            
            response = requests.get(f"{BASE_URL}/get_question", params=params)
            
            success = response.status_code == 200
            
            if success:
                response_data = response.json()
                self.question_id = response_data['data']['question_id']
                self.log_test("Get Question", True, {
                    'question_id': self.question_id,
                    'difficulty': 'intermediate'
                })
            else:
                self.log_test("Get Question", False, {
                    'status_code': response.status_code,
                    'response': response.text
                })
                
        except Exception as e:
            self.log_test("Get Question", False, {'error': str(e)})
    
    def test_submit_answer(self):
        """Test answer submission and evaluation"""
        if not self.session_id or not self.question_id:
            self.log_test("Submit Answer", False, {'error': 'Missing session or question ID'})
            return
            
        try:
            data = {
                "session_id": self.session_id,
                "question_id": self.question_id,
                "answer_text": "I have experience with algorithms and data structures. I've implemented various sorting algorithms and worked with linked lists, arrays, and trees. In my previous role, I optimized a search function using binary search which improved performance by 40%."
            }
            
            response = requests.post(
                f"{BASE_URL}/submit_answer",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            
            success = response.status_code == 200
            
            if success:
                response_data = response.json()
                evaluation = response_data['data']['evaluation']
                self.log_test("Submit Answer", True, {
                    'evaluation_score': evaluation.get('score'),
                    'feedback_length': len(evaluation.get('feedback', '')),
                    'improvements_count': len(evaluation.get('improvements', []))
                })
            else:
                self.log_test("Submit Answer", False, {
                    'status_code': response.status_code,
                    'response': response.text
                })
                
        except Exception as e:
            self.log_test("Submit Answer", False, {'error': str(e)})
    
    def test_log_event(self):
        """Test event logging"""
        if not self.session_id:
            self.log_test("Log Event", False, {'error': 'No session ID available'})
            return
            
        try:
            data = {
                "session_id": self.session_id,
                "event_type": "user_action",
                "details": {
                    "action": "test_event",
                    "timestamp": datetime.now().isoformat(),
                    "test": True
                }
            }
            
            response = requests.post(
                f"{BASE_URL}/log_event",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            
            success = response.status_code == 200
            
            if success:
                response_data = response.json()
                self.log_test("Log Event", True, {
                    'event_type': 'user_action',
                    'timestamp': response_data['data']['timestamp']
                })
            else:
                self.log_test("Log Event", False, {
                    'status_code': response.status_code,
                    'response': response.text
                })
                
        except Exception as e:
            self.log_test("Log Event", False, {'error': str(e)})
    
    def test_log_anomaly(self):
        """Test anomaly logging"""
        if not self.session_id:
            self.log_test("Log Anomaly", False, {'error': 'No session ID available'})
            return
            
        try:
            data = {
                "session_id": self.session_id,
                "anomaly_type": "low_score",
                "severity": "medium",
                "details": {
                    "reason": "test_anomaly",
                    "score": 25,
                    "test": True
                }
            }
            
            response = requests.post(
                f"{BASE_URL}/log_anomaly",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            
            success = response.status_code == 200
            
            if success:
                response_data = response.json()
                self.log_test("Log Anomaly", True, {
                    'anomaly_type': 'low_score',
                    'severity': 'medium'
                })
            else:
                self.log_test("Log Anomaly", False, {
                    'status_code': response.status_code,
                    'response': response.text
                })
                
        except Exception as e:
            self.log_test("Log Anomaly", False, {'error': str(e)})
    
    def test_get_session_details(self):
        """Test session details retrieval"""
        if not self.session_id:
            self.log_test("Get Session Details", False, {'error': 'No session ID available'})
            return
            
        try:
            response = requests.get(f"{BASE_URL}/session/{self.session_id}")
            
            success = response.status_code == 200
            
            if success:
                response_data = response.json()
                stats = response_data['data'].get('statistics', {})
                self.log_test("Get Session Details", True, {
                    'total_questions': stats.get('total_questions', 0),
                    'answered_questions': stats.get('answered_questions', 0),
                    'completion_rate': stats.get('completion_rate', 0)
                })
            else:
                self.log_test("Get Session Details", False, {
                    'status_code': response.status_code,
                    'response': response.text
                })
                
        except Exception as e:
            self.log_test("Get Session Details", False, {'error': str(e)})
    
    def test_get_user_sessions(self):
        """Test user sessions retrieval"""
        try:
            response = requests.get(f"{BASE_URL}/user/{REAL_USER_ID}/sessions?limit=5")
            
            success = response.status_code == 200
            
            if success:
                response_data = response.json()
                sessions = response_data['data']['sessions']
                self.log_test("Get User Sessions", True, {
                    'sessions_count': len(sessions),
                    'total_count': response_data['data']['total_count']
                })
            else:
                self.log_test("Get User Sessions", False, {
                    'status_code': response.status_code,
                    'response': response.text
                })
                
        except Exception as e:
            self.log_test("Get User Sessions", False, {'error': str(e)})
    
    def test_follow_up_question(self):
        """Test follow-up question generation"""
        try:
            data = {
                "question": "Explain the time complexity of binary search.",
                "answer": "Binary search has O(log n) time complexity because it divides the search space in half with each iteration.",
                "interview_type": TEST_INTERVIEW_TYPE
            }
            
            response = requests.post(
                f"{BASE_URL}/follow_up_question",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            
            success = response.status_code == 200
            
            if success:
                response_data = response.json()
                follow_up = response_data['data']['follow_up_question']
                self.log_test("Follow-up Question", True, {
                    'follow_up_length': len(follow_up),
                    'has_content': len(follow_up.strip()) > 0
                })
            else:
                self.log_test("Follow-up Question", False, {
                    'status_code': response.status_code,
                    'response': response.text
                })
                
        except Exception as e:
            self.log_test("Follow-up Question", False, {'error': str(e)})
    
    def test_end_session(self):
        """Test session ending"""
        if not self.session_id:
            self.log_test("End Session", False, {'error': 'No session ID available'})
            return
            
        try:
            data = {
                "final_score": 75.5
            }
            
            response = requests.post(
                f"{BASE_URL}/end_session/{self.session_id}",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            
            success = response.status_code == 200
            
            if success:
                response_data = response.json()
                self.log_test("End Session", True, {
                    'status': response_data['data']['status'],
                    'final_score': response_data['data']['final_score']
                })
            else:
                self.log_test("End Session", False, {
                    'status_code': response.status_code,
                    'response': response.text
                })
                
        except Exception as e:
            self.log_test("End Session", False, {'error': str(e)})
    
    def test_metrics_endpoint(self):
        """Test metrics endpoint"""
        try:
            response = requests.get(f"{BASE_URL}/metrics")
            
            success = response.status_code == 200
            
            if success:
                response_data = response.json()
                metrics = response_data['data']['metrics']
                self.log_test("Get Metrics", True, {
                    'total_sessions': metrics.get('total_sessions'),
                    'active_sessions': metrics.get('active_sessions')
                })
            else:
                self.log_test("Get Metrics", False, {
                    'status_code': response.status_code,
                    'response': response.text
                })
                
        except Exception as e:
            self.log_test("Get Metrics", False, {'error': str(e)})
    
    def test_error_handling(self):
        """Test error handling with invalid data"""
        test_cases = [
            {
                'name': 'Invalid Session Creation - Missing User ID',
                'endpoint': '/start_session',
                'method': 'POST',
                'data': {'interview_type': 'Software Engineer'},
                'expected_status': 400
            },
            {
                'name': 'Invalid Session Creation - Invalid Interview Type',
                'endpoint': '/start_session',
                'method': 'POST',
                'data': {'user_id': REAL_USER_ID, 'interview_type': 'Invalid Type'},
                'expected_status': 400
            },
            {
                'name': 'Invalid Answer Submission - Missing Fields',
                'endpoint': '/submit_answer',
                'method': 'POST',
                'data': {'session_id': 'test'},
                'expected_status': 400
            },
            {
                'name': 'Invalid Event Logging - Missing Event Type',
                'endpoint': '/log_event',
                'method': 'POST',
                'data': {'session_id': 'test'},
                'expected_status': 400
            }
        ]
        
        for test_case in test_cases:
            try:
                if test_case['method'] == 'POST':
                    response = requests.post(
                        f"{BASE_URL}{test_case['endpoint']}",
                        json=test_case['data'],
                        headers={"Content-Type": "application/json"}
                    )
                else:
                    response = requests.get(f"{BASE_URL}{test_case['endpoint']}")
                
                success = response.status_code == test_case['expected_status']
                
                if success:
                    self.log_test(f"Error Handling - {test_case['name']}", True, {
                        'expected_status': test_case['expected_status'],
                        'actual_status': response.status_code
                    })
                else:
                    self.log_test(f"Error Handling - {test_case['name']}", False, {
                        'expected_status': test_case['expected_status'],
                        'actual_status': response.status_code,
                        'response': response.text
                    })
                    
            except Exception as e:
                self.log_test(f"Error Handling - {test_case['name']}", False, {'error': str(e)})
    
    def test_code_submission(self):
        """Test code submission and evaluation"""
        if not self.session_id or not self.question_id:
            self.log_test("Code Submission", False, {'error': 'Missing session or question ID'})
            return
            
        try:
            data = {
                "session_id": self.session_id,
                "question_id": self.question_id,
                "code": "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
                "language": "python"
            }
            
            response = requests.post(
                f"{BASE_URL}/submit_code",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            
            success = response.status_code == 200
            
            if success:
                response_data = response.json()
                evaluation = response_data['data']['evaluation']
                self.log_test("Code Submission", True, {
                    'evaluation_score': evaluation.get('score'),
                    'code_quality': evaluation.get('code_quality'),
                    'correctness': evaluation.get('correctness'),
                    'efficiency': evaluation.get('efficiency')
                })
            else:
                self.log_test("Code Submission", False, {
                    'status_code': response.status_code,
                    'response': response.text
                })
                
        except Exception as e:
            self.log_test("Code Submission", False, {'error': str(e)})

    def test_security_check(self):
        """Test security check endpoint"""
        if not self.session_id:
            self.log_test("Security Check", False, {'error': 'No session ID available'})
            return
            
        try:
            data = {
                "session_id": self.session_id,
                "security_data": {
                    "face_count": 1,
                    "instant_chars": 50,
                    "tab_switches": 2,
                    "typing_speed": 120
                }
            }
            
            response = requests.post(
                f"{BASE_URL}/security/check",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            
            success = response.status_code == 200
            
            if success:
                response_data = response.json()
                security_result = response_data['data']
                self.log_test("Security Check", True, {
                    'is_cheating': security_result.get('is_cheating'),
                    'risk_score': security_result.get('risk_score'),
                    'anomalies_count': len(security_result.get('anomalies', []))
                })
            else:
                self.log_test("Security Check", False, {
                    'status_code': response.status_code,
                    'response': response.text
                })
                
        except Exception as e:
            self.log_test("Security Check", False, {'error': str(e)})

    def test_security_report(self):
        """Test security report endpoint"""
        if not self.session_id:
            self.log_test("Security Report", False, {'error': 'No session ID available'})
            return
            
        try:
            response = requests.get(f"{BASE_URL}/security/report/{self.session_id}")
            
            success = response.status_code == 200
            
            if success:
                response_data = response.json()
                self.log_test("Security Report", True, {
                    'security_score': response_data['data'].get('security_score'),
                    'total_events': response_data['data'].get('total_events')
                })
            else:
                self.log_test("Security Report", False, {
                    'status_code': response.status_code,
                    'response': response.text
                })
                
        except Exception as e:
            self.log_test("Security Report", False, {'error': str(e)})

    def test_practice_coding(self):
        """Test coding practice question generation"""
        try:
            data = {
                "interview_type": "Software Engineer",
                "difficulty": "intermediate",
                "topic": "algorithms"
            }
            
            response = requests.post(
                f"{BASE_URL}/practice/coding",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            
            success = response.status_code == 200
            
            if success:
                response_data = response.json()
                question = response_data['data']['question']
                self.log_test("Practice Coding", True, {
                    'question_length': len(question),
                    'difficulty': 'intermediate',
                    'topic': 'algorithms'
                })
            else:
                self.log_test("Practice Coding", False, {
                    'status_code': response.status_code,
                    'response': response.text
                })
                
        except Exception as e:
            self.log_test("Practice Coding", False, {'error': str(e)})
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting Comprehensive API Test Suite...\n")
        print(f"👤 Using User ID: {REAL_USER_ID}")
        print(f"🎯 Interview Type: {TEST_INTERVIEW_TYPE}")
        print("=" * 60)
        
        # Core functionality tests
        self.test_health_endpoint()
        self.test_start_session()
        self.test_get_question()
        self.test_submit_answer()
        self.test_code_submission()
        self.test_log_event()
        self.test_log_anomaly()
        
        # Security and monitoring tests
        self.test_security_check()
        self.test_security_report()
        
        # Session management tests
        self.test_get_session_details()
        self.test_get_user_sessions()
        self.test_follow_up_question()
        self.test_end_session()
        
        # Practice and additional features
        self.test_practice_coding()
        
        # System tests
        self.test_metrics_endpoint()
        
        # Error handling tests
        self.test_error_handling()
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result['success']:
                    print(f"   - {result['test']}: {result['details']}")
        
        print(f"\n🎉 Test Suite Complete!")
        print(f"📅 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def main():
    """Main test runner"""
    tester = APITester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()
