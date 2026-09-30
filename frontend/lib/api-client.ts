const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:5000/api'

export interface InterviewSession {
  id: string
  user_id: string
  interview_type: string
  start_time: string
  end_time?: string
  score: number
  status: 'active' | 'completed'
}

export interface Question {
  id: string
  session_id: string
  question_text: string
  interview_type: string
  answer_text?: string
  evaluation_score?: number
  evaluation_feedback?: string
  evaluation_details?: any
  code_text?: string
  programming_language?: string
  created_at: string
  updated_at?: string
}

export interface CodeEvaluation {
  score: number
  feedback: string
  code_quality: number
  correctness: number
  efficiency: number
  readability: number
  improvements: string[]
  strengths: string[]
  time_complexity: string
  space_complexity: string
  edge_cases_handled: boolean
  best_practices: number
}

export interface SecurityCheck {
  is_cheating: boolean
  risk_score: number
  anomalies: string[]
  recommendations: string[]
  confidence: number
}

export interface AnswerEvaluation {
  score: number
  feedback: string
  improvements: string[]
  strengths: string[]
  technical_accuracy: number
  communication: number
  problem_solving: number
}

export interface CandidateSkillProfile {
  id?: string
  user_id: string
  skill_name: string
  estimated_proficiency: number
  confidence: 'insufficient evidence' | 'low confidence' | 'medium confidence' | 'high confidence'
  evidence_count: number
  recent_performance: number
  historical_performance: number
  improvement_trend: 'improving' | 'declining' | 'stable' | 'neutral'
  last_evaluated_timestamp?: string
  evidence_history?: Array<{
    session_id: string
    question_id: string
    score: number
    timestamp: string
  }>
}

export interface Recommendation {
  id: string
  user_id: string
  session_id?: string
  target_skill: string
  strategy: 'next_interview' | 'practice_session' | 'skill_reinforcement' | 'weak_signal_validation' | 'review_prior_mistakes'
  reason: string
  evidence: Record<string, any>
  recommended_activity: {
    type?: string
    title?: string
    description?: string
    difficulty?: string
    progression_stages?: string[]
    remediation_steps?: string[]
    focus_areas?: string[]
    topics?: string[]
    [key: string]: any
  }
  priority: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
  expected_learning_objective: string
  status: 'PENDING' | 'ACCEPTED' | 'COMPLETED' | 'DISMISSED'
  created_at: string
  completed_at?: string
  baseline_proficiency: number
  post_outcome_proficiency?: number
  outcome_delta?: number
  outcome_assessment?: 'improved' | 'declined' | 'unchanged' | 'pending'
}

class APIClient {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`
    
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.message || `HTTP ${response.status}`)
    }

    return response.json()
  }

  // Interview Session Management
  async startSession(userId: string, interviewType: string): Promise<{ session_id: string; interview_type: string }> {
    return this.request('/start_session', {
      method: 'POST',
      body: JSON.stringify({ user_id: userId, interview_type: interviewType }),
    })
  }

  async getQuestion(sessionId: string, interviewType: string, difficulty: string = 'intermediate'): Promise<{ question_id: string; question_text: string; difficulty: string }> {
    const params = new URLSearchParams({
      session_id: sessionId,
      interview_type: interviewType,
      difficulty,
    })
    return this.request(`/get_question?${params}`)
  }

  async submitAnswer(sessionId: string, questionId: string, answerText: string): Promise<{ evaluation: AnswerEvaluation; session_score: number }> {
    return this.request('/submit_answer', {
      method: 'POST',
      body: JSON.stringify({
        session_id: sessionId,
        question_id: questionId,
        answer_text: answerText,
      }),
    })
  }

  async submitCode(sessionId: string, questionId: string, code: string, language: string): Promise<{ evaluation: CodeEvaluation; session_score: number }> {
    return this.request('/submit_code', {
      method: 'POST',
      body: JSON.stringify({
        session_id: sessionId,
        question_id: questionId,
        code,
        language,
      }),
    })
  }

  async endSession(sessionId: string, finalScore?: number): Promise<{ status: string; final_score: number }> {
    return this.request(`/end_session/${sessionId}`, {
      method: 'POST',
      body: JSON.stringify({ final_score: finalScore }),
    })
  }

  // Security & Monitoring
  async securityCheck(sessionId: string, securityData: any): Promise<SecurityCheck> {
    return this.request('/security/check', {
      method: 'POST',
      body: JSON.stringify({
        session_id: sessionId,
        security_data: securityData,
      }),
    })
  }

  async getSecurityReport(sessionId: string): Promise<any> {
    return this.request(`/security/report/${sessionId}`)
  }

  // Logging & Events
  async logEvent(sessionId: string, eventType: string, details: any = {}): Promise<{ timestamp: string }> {
    return this.request('/log_event', {
      method: 'POST',
      body: JSON.stringify({
        session_id: sessionId,
        event_type: eventType,
        details,
      }),
    })
  }

  async logAnomaly(sessionId: string, anomalyType: string, severity: string, details: any = {}): Promise<void> {
    return this.request('/log_anomaly', {
      method: 'POST',
      body: JSON.stringify({
        session_id: sessionId,
        anomaly_type: anomalyType,
        severity,
        details,
      }),
    })
  }

  // Session Information
  async getSessionDetails(sessionId: string): Promise<any> {
    return this.request(`/session/${sessionId}`)
  }

  async getUserSessions(userId: string, limit: number = 10): Promise<{ sessions: InterviewSession[]; total_count: number }> {
    return this.request(`/user/${userId}/sessions?limit=${limit}`)
  }

  // Practice & Additional Features
  async generatePracticeQuestion(interviewType: string, difficulty: string = 'intermediate', topic: string = 'coding'): Promise<{ question: string; interview_type: string; difficulty: string; topic: string }> {
    return this.request('/practice/coding', {
      method: 'POST',
      body: JSON.stringify({
        interview_type: interviewType,
        difficulty,
        topic,
      }),
    })
  }

  async getFollowUpQuestion(question: string, answer: string, interviewType: string): Promise<{ follow_up_question: string }> {
    return this.request('/follow_up_question', {
      method: 'POST',
      body: JSON.stringify({
        question,
        answer,
        interview_type: interviewType,
      }),
    })
  }

  // Candidate Skill Intelligence & Recommendations
  async getCandidateSkills(userId: string): Promise<{ success: boolean; user_id: string; profiles: CandidateSkillProfile[] }> {
    return this.request(`/intelligence/skills/${userId}`)
  }

  async getRecommendations(userId: string, status?: string, strategy?: string): Promise<{ success: boolean; count: number; recommendations: Recommendation[] }> {
    const params = new URLSearchParams()
    if (status) params.append('status', status)
    if (strategy) params.append('strategy', strategy)
    const qs = params.toString() ? `?${params.toString()}` : ''
    return this.request(`/intelligence/recommendations/${userId}${qs}`)
  }

  async generateRecommendations(userId: string, sessionId?: string): Promise<{ success: boolean; count: number; recommendations: Recommendation[] }> {
    return this.request(`/intelligence/recommendations/${userId}/generate`, {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId })
    })
  }

  async updateRecommendationStatus(recommendationId: string, status: string): Promise<{ success: boolean; recommendation: Recommendation }> {
    return this.request(`/intelligence/recommendations/${recommendationId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status })
    })
  }

  async evaluateRecommendationOutcome(recommendationId: string, currentProficiency?: number): Promise<{ success: boolean; outcome: any; recommendation: Recommendation }> {
    return this.request(`/intelligence/recommendations/${recommendationId}/evaluate_outcome`, {
      method: 'POST',
      body: JSON.stringify({ current_proficiency: currentProficiency })
    })
  }

  // System Health
  async healthCheck(): Promise<{ status: string; database: string }> {
    return this.request('/health')
  }

  async getMetrics(): Promise<any> {
    return this.request('/metrics')
  }
}

export const apiClient = new APIClient()
