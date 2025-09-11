"use client"

import { useState, useEffect, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { InterviewTimer } from './timer'
import { AntiCheatGuard } from '@/components/anti-cheat/anti-cheat-guard'
import { apiClient, type Question, type AnswerEvaluation, type SecurityCheck } from '@/lib/api-client'
import { AlertCircle, CheckCircle, XCircle, Code, MessageSquare, Camera, Shield } from 'lucide-react'

interface InterviewSessionProps {
  userId: string
  interviewType: string
  onSessionEnd: (finalScore: number) => void
}

export function InterviewSession({ userId, interviewType, onSessionEnd }: InterviewSessionProps) {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null)
  const [answerText, setAnswerText] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [evaluation, setEvaluation] = useState<AnswerEvaluation | null>(null)
  const [sessionScore, setSessionScore] = useState(0)
  const [questionCount, setQuestionCount] = useState(0)
  const [securityFlags, setSecurityFlags] = useState<string[]>([])
  const [securityData, setSecurityData] = useState<any>({})
  const [isSessionActive, setIsSessionActive] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const securityCheckInterval = useRef<NodeJS.Timeout | null>(null)
  const typingStartTime = useRef<number>(Date.now())
  const keystrokes = useRef<number[]>([])

  // Initialize session
  useEffect(() => {
    const startSession = async () => {
      try {
        setError(null)
        const result = await apiClient.startSession(userId, interviewType)
        setSessionId(result.session_id)
        setIsSessionActive(true)
        
        // Log session start
        await apiClient.logEvent(result.session_id, 'session_started', {
          interview_type: interviewType,
          user_id: userId
        })
        
        // Get first question
        await getNextQuestion()
      } catch (err: any) {
        setError(err.message || 'Failed to start session')
      }
    }

    if (userId && interviewType) {
      startSession()
    }
  }, [userId, interviewType])

  // Security monitoring
  useEffect(() => {
    if (!sessionId || !isSessionActive) return

    // Periodic security checks
    securityCheckInterval.current = setInterval(async () => {
      try {
        const securityCheck = await apiClient.securityCheck(sessionId, securityData)
        
        if (securityCheck.is_cheating) {
          setSecurityFlags(prev => [...prev, `Security Alert: ${securityCheck.anomalies.join(', ')}`])
          
          // Log anomaly
          await apiClient.logAnomaly(sessionId, 'cheating_detected', 'high', {
            risk_score: securityCheck.risk_score,
            anomalies: securityCheck.anomalies
          })
        }
      } catch (err) {
        console.error('Security check failed:', err)
      }
    }, 10000) // Check every 10 seconds

    return () => {
      if (securityCheckInterval.current) {
        clearInterval(securityCheckInterval.current)
      }
    }
  }, [sessionId, isSessionActive, securityData])

  // Typing analysis
  useEffect(() => {
    const handleKeydown = () => {
      const now = Date.now()
      keystrokes.current.push(now)
      
      // Keep only last 20 keystrokes
      if (keystrokes.current.length > 20) {
        keystrokes.current = keystrokes.current.slice(-20)
      }
      
      // Calculate typing speed
      if (keystrokes.current.length >= 5) {
        const timeSpan = now - keystrokes.current[0]
        const charsPerMinute = (keystrokes.current.length / timeSpan) * 60000
        
        setSecurityData(prev => ({
          ...prev,
          typing_speed: Math.round(charsPerMinute),
          keystroke_count: keystrokes.current.length
        }))
      }
    }

    if (isSessionActive) {
      document.addEventListener('keydown', handleKeydown)
      return () => document.removeEventListener('keydown', handleKeydown)
    }
  }, [isSessionActive])

  const getNextQuestion = async () => {
    if (!sessionId) return

    try {
      setError(null)
      const result = await apiClient.getQuestion(sessionId, interviewType, 'intermediate')
      
      const question: Question = {
        id: result.question_id,
        session_id: sessionId,
        question_text: result.question_text,
        interview_type: interviewType,
        created_at: new Date().toISOString()
      }
      
      setCurrentQuestion(question)
      setAnswerText('')
      setEvaluation(null)
      setQuestionCount(prev => prev + 1)
      
      // Log question generation
      await apiClient.logEvent(sessionId, 'question_generated', {
        question_id: result.question_id,
        difficulty: result.difficulty
      })
    } catch (err: any) {
      setError(err.message || 'Failed to get question')
    }
  }

  const submitAnswer = async () => {
    if (!sessionId || !currentQuestion || !answerText.trim()) return

    setIsSubmitting(true)
    try {
      setError(null)
      
      // Calculate answer metrics for security
      const answerLength = answerText.length
      const typingDuration = (Date.now() - typingStartTime.current) / 1000
      const instantChars = answerLength > 100 ? answerLength : 0
      
      setSecurityData(prev => ({
        ...prev,
        answer_length: answerLength,
        typing_duration: typingDuration,
        instant_chars: instantChars
      }))
      
      const result = await apiClient.submitAnswer(sessionId, currentQuestion.id, answerText)
      setEvaluation(result.evaluation)
      setSessionScore(result.session_score)
      
      // Log answer submission
      await apiClient.logEvent(sessionId, 'answer_submitted', {
        question_id: currentQuestion.id,
        answer_length: answerLength,
        evaluation_score: result.evaluation.score
      })
      
      // Log low score anomaly if applicable
      if (result.evaluation.score < 50) {
        await apiClient.logAnomaly(sessionId, 'low_score', 'medium', {
          score: result.evaluation.score,
          question_id: currentQuestion.id
        })
      }
      
    } catch (err: any) {
      setError(err.message || 'Failed to submit answer')
    } finally {
      setIsSubmitting(false)
    }
  }

  const endSession = async () => {
    if (!sessionId) return

    try {
      setError(null)
      const result = await apiClient.endSession(sessionId, sessionScore)
      
      // Log session end
      await apiClient.logEvent(sessionId, 'session_ended', {
        final_score: sessionScore,
        total_questions: questionCount
      })
      
      setIsSessionActive(false)
      onSessionEnd(sessionScore)
      
    } catch (err: any) {
      setError(err.message || 'Failed to end session')
    }
  }

  const handleSecurityFlag = (flag: string) => {
    setSecurityFlags(prev => [...prev, flag])
    
    // Log security flag
    if (sessionId) {
      apiClient.logEvent(sessionId, 'security_flag', { flag }).catch(console.error)
    }
  }

  if (!sessionId) {
    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-yellow-500" />
            Initializing Session
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p>Setting up your interview session...</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Session Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <MessageSquare className="h-5 w-5" />
                Interview Session
              </CardTitle>
              <p className="text-sm text-muted-foreground mt-1">
                {interviewType} • Question {questionCount}
              </p>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-center">
                <p className="text-sm font-medium">Score</p>
                <p className="text-2xl font-bold text-green-600">{sessionScore}</p>
              </div>
              <InterviewTimer seconds={1800} onTimeUp={endSession} />
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Current Question */}
      {currentQuestion && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              Question {questionCount}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-lg">{currentQuestion.question_text}</p>
            
            <div className="space-y-3">
              <label htmlFor="answer" className="text-sm font-medium">
                Your Answer
              </label>
              <Textarea
                id="answer"
                value={answerText}
                onChange={(e) => setAnswerText(e.target.value)}
                placeholder="Type your answer here..."
                className="min-h-[120px]"
                onFocus={() => typingStartTime.current = Date.now()}
              />
              
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">
                  {answerText.length} characters
                </span>
                <Button 
                  onClick={submitAnswer} 
                  disabled={isSubmitting || !answerText.trim()}
                >
                  {isSubmitting ? 'Submitting...' : 'Submit Answer'}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Evaluation Results */}
      {evaluation && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-500" />
              Evaluation Results
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm font-medium">Overall Score</p>
                <p className="text-3xl font-bold text-green-600">{evaluation.score}/100</p>
              </div>
              <div>
                <p className="text-sm font-medium">Technical Accuracy</p>
                <Progress value={evaluation.technical_accuracy} className="mt-2" />
                <p className="text-sm text-muted-foreground mt-1">{evaluation.technical_accuracy}/100</p>
              </div>
            </div>
            
            <div>
              <p className="text-sm font-medium">Feedback</p>
              <p className="text-sm mt-1">{evaluation.feedback}</p>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm font-medium">Strengths</p>
                <ul className="text-sm mt-1 space-y-1">
                  {evaluation.strengths.map((strength, index) => (
                    <li key={index} className="flex items-center gap-2">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      {strength}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="text-sm font-medium">Improvements</p>
                <ul className="text-sm mt-1 space-y-1">
                  {evaluation.improvements.map((improvement, index) => (
                    <li key={index} className="flex items-center gap-2">
                      <XCircle className="h-4 w-4 text-red-500" />
                      {improvement}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
            
            <div className="flex gap-2">
              <Button onClick={getNextQuestion} variant="outline">
                Next Question
              </Button>
              <Button onClick={endSession} variant="destructive">
                End Session
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Security Monitoring */}
      <AntiCheatGuard
        onFlag={handleSecurityFlag}
        enableWebcam
        enableTypingAnalysis
        enableDevtoolsDetection
      />

      {/* Security Flags */}
      {securityFlags.length > 0 && (
        <Card className="border-red-200 bg-red-50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-700">
              <Shield className="h-5 w-5" />
              Security Alerts
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {securityFlags.map((flag, index) => (
                <li key={index} className="flex items-center gap-2 text-sm text-red-700">
                  <AlertCircle className="h-4 w-4" />
                  {flag}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Error Display */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
    </div>
  )
}
