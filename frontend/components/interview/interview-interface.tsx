"use client"

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Separator } from '@/components/ui/separator'
import { InterviewTimer } from './interview-timer'
import { AntiCheatGuard } from '../anti-cheat/anti-cheat-guard'
import { EnhancedCodeEditor } from '../ide/enhanced-code-editor'
import { InterviewChat } from './interview-chat'
import { apiClient, type Question, type CodeEvaluation } from '@/lib/api-client'
import { 
  Code2, 
  MessageCircle, 
  AlertTriangle, 
  CheckCircle, 
  Clock, 
  Brain, 
  Shield, 
  BarChart3,
  Play,
  Pause,
  Square,
  RotateCcw
} from 'lucide-react'

interface InterviewInterfaceProps {
  sessionId?: string
  onSessionEnd?: (finalScore: number) => void
}

interface InterviewState {
  currentQuestion: Question | null
  currentAnswer: string
  questionIndex: number
  totalQuestions: number
  sessionScore: number
  isSessionActive: boolean
  isPaused: boolean
  securityFlags: string[]
  timeRemaining: number
  showCodeEditor: boolean
  showChat: boolean
}

export function InterviewInterface({ sessionId, onSessionEnd }: InterviewInterfaceProps) {
  const [state, setState] = useState<InterviewState>({
    currentQuestion: null,
    currentAnswer: '',
    questionIndex: 0,
    totalQuestions: 10,
    sessionScore: 0,
    isSessionActive: false,
    isPaused: false,
    securityFlags: [],
    timeRemaining: 3600, // 1 hour
    showCodeEditor: false,
    showChat: false
  })

  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  // Initialize interview session
  useEffect(() => {
    if (sessionId && !state.isSessionActive) {
      initializeSession()
    }
  }, [sessionId])

  // Auto-save answer every 30 seconds
  useEffect(() => {
    if (state.isSessionActive && state.currentAnswer) {
      const interval = setInterval(() => {
        autoSaveAnswer()
      }, 30000)
      return () => clearInterval(interval)
    }
  }, [state.currentAnswer, state.isSessionActive])

  const initializeSession = async () => {
    if (!sessionId) return

    setIsLoading(true)
    setError(null)

    try {
      // Get first question
      const question = await apiClient.getQuestion(sessionId, 'technical')
      
      setState(prev => ({
        ...prev,
        currentQuestion: question,
        isSessionActive: true,
        questionIndex: 0
      }))

      // Log session start
      await apiClient.logEvent(sessionId, 'interview_started', {
        question_id: question.id,
        question_type: question.type
      })

    } catch (err: any) {
      setError(err.message || 'Failed to initialize interview session')
    } finally {
      setIsLoading(false)
    }
  }

  const getNextQuestion = async () => {
    if (!sessionId || !state.currentQuestion) return

    setIsLoading(true)
    setError(null)

    try {
      // Submit current answer if exists
      if (state.currentAnswer.trim()) {
        await submitAnswer()
      }

      // Get next question
      const nextQuestion = await apiClient.getQuestion(sessionId, 'technical')
      
      setState(prev => ({
        ...prev,
        currentQuestion: nextQuestion,
        currentAnswer: '',
        questionIndex: prev.questionIndex + 1,
        showCodeEditor: false,
        showChat: false
      }))

      // Log question transition
      await apiClient.logEvent(sessionId, 'question_transition', {
        from_question_id: state.currentQuestion.id,
        to_question_id: nextQuestion.id,
        question_index: state.questionIndex + 1
      })

    } catch (err: any) {
      setError(err.message || 'Failed to get next question')
    } finally {
      setIsLoading(false)
    }
  }

  const submitAnswer = async () => {
    if (!sessionId || !state.currentQuestion || !state.currentAnswer.trim()) return

    setIsLoading(true)
    setError(null)

    try {
      const result = await apiClient.submitAnswer(
        sessionId,
        state.currentQuestion.id,
        state.currentAnswer
      )

      // Update session score
      setState(prev => ({
        ...prev,
        sessionScore: prev.sessionScore + result.evaluation.score
      }))

      // Log answer submission
      await apiClient.logEvent(sessionId, 'answer_submitted', {
        question_id: state.currentQuestion.id,
        answer_length: state.currentAnswer.length,
        evaluation_score: result.evaluation.score
      })

      return result

    } catch (err: any) {
      setError(err.message || 'Failed to submit answer')
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  const autoSaveAnswer = async () => {
    if (!sessionId || !state.currentQuestion || !state.currentAnswer.trim()) return

    try {
      await apiClient.logEvent(sessionId, 'answer_autosaved', {
        question_id: state.currentQuestion.id,
        answer_length: state.currentAnswer.length,
        timestamp: new Date().toISOString()
      })
    } catch (error) {
      console.warn('Auto-save failed:', error)
    }
  }

  const handleCodeSubmit = async (evaluation: CodeEvaluation) => {
    if (!sessionId || !state.currentQuestion) return

    try {
      // Log code submission
      await apiClient.logEvent(sessionId, 'code_evaluation_completed', {
        question_id: state.currentQuestion.id,
        evaluation_score: evaluation.score,
        code_quality: evaluation.code_quality,
        correctness: evaluation.correctness
      })

      // Update session score
      setState(prev => ({
        ...prev,
        sessionScore: prev.sessionScore + evaluation.score
      }))

    } catch (error) {
      console.error('Failed to log code evaluation:', error)
    }
  }

  const handleSecurityFlag = (flag: string) => {
    setState(prev => ({
      ...prev,
      securityFlags: [...prev.securityFlags, flag]
    }))

    // Log security flag
    if (sessionId) {
      apiClient.logEvent(sessionId, 'security_flag_raised', {
        flag_type: flag,
        timestamp: new Date().toISOString()
      }).catch(console.error)
    }
  }

  const handleSessionEnd = async () => {
    if (!sessionId) return

    try {
      // Submit final answer if exists
      if (state.currentAnswer.trim()) {
        await submitAnswer()
      }

      // End session
      await apiClient.endSession(sessionId, state.sessionScore)

      // Log session end
      await apiClient.logEvent(sessionId, 'interview_completed', {
        final_score: state.sessionScore,
        total_questions: state.questionIndex + 1,
        security_flags: state.securityFlags
      })

      // Call callback
      if (onSessionEnd) {
        onSessionEnd(state.sessionScore)
      }

    } catch (error) {
      console.error('Failed to end session:', error)
    }
  }

  const togglePause = () => {
    setState(prev => ({
      ...prev,
      isPaused: !prev.isPaused
    }))

    // Log pause/resume
    if (sessionId) {
      apiClient.logEvent(sessionId, 'interview_paused', {
        is_paused: !state.isPaused,
        timestamp: new Date().toISOString()
      }).catch(console.error)
    }
  }

  const resetQuestion = () => {
    setState(prev => ({
      ...prev,
      currentAnswer: '',
      showCodeEditor: false,
      showChat: false
    }))
  }

  const getProgressPercentage = () => {
    return ((state.questionIndex + 1) / state.totalQuestions) * 100
  }

  const getScoreGrade = (score: number) => {
    if (score >= 90) return { grade: 'A+', color: 'text-green-600' }
    if (score >= 80) return { grade: 'A', color: 'text-green-500' }
    if (score >= 70) return { grade: 'B', color: 'text-blue-500' }
    if (score >= 60) return { grade: 'C', color: 'text-yellow-500' }
    if (score >= 50) return { grade: 'D', color: 'text-orange-500' }
    return { grade: 'F', color: 'text-red-500' }
  }

  if (isLoading && !state.currentQuestion) {
    return (
      <Card className="p-8 text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
        <p className="text-lg">Initializing interview session...</p>
      </Card>
    )
  }

  if (!state.currentQuestion) {
    return (
      <Card className="p-8 text-center">
        <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
        <p className="text-lg text-red-600">No question available</p>
        {error && <p className="text-sm text-gray-600 mt-2">{error}</p>}
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Brain className="h-5 w-5" />
                Technical Interview Session
              </CardTitle>
              <p className="text-sm text-muted-foreground mt-1">
                Question {state.questionIndex + 1} of {state.totalQuestions}
              </p>
            </div>
            <div className="flex items-center gap-4">
              {/* Progress */}
              <div className="text-center">
                <p className="text-sm font-medium">Progress</p>
                <Progress value={getProgressPercentage()} className="w-24 mt-1" />
                <p className="text-xs text-muted-foreground">
                  {state.questionIndex + 1}/{state.totalQuestions}
                </p>
              </div>

              {/* Score */}
              <div className="text-center">
                <p className="text-sm font-medium">Score</p>
                <p className={`text-lg font-bold ${getScoreGrade(state.sessionScore).color}`}>
                  {state.sessionScore}
                </p>
                <p className="text-xs text-muted-foreground">
                  {getScoreGrade(state.sessionScore).grade}
                </p>
              </div>

              {/* Timer */}
              <div className="text-center">
                <p className="text-sm font-medium">Time</p>
                <InterviewTimer 
                  duration={state.timeRemaining}
                  onTimeUp={handleSessionEnd}
                  isPaused={state.isPaused}
                />
              </div>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Security Status */}
      {state.securityFlags.length > 0 && (
        <Alert>
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Security flags detected: {state.securityFlags.join(', ')}
          </AlertDescription>
        </Alert>
      )}

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Question and Answer Section */}
        <div className="lg:col-span-2 space-y-6">
          {/* Question */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Code2 className="h-5 w-5" />
                Question {state.questionIndex + 1}
              </CardTitle>
              <div className="flex items-center gap-2">
                <Badge variant="outline">{state.currentQuestion.type}</Badge>
                <Badge variant="outline">{state.currentQuestion.difficulty}</Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="prose max-w-none">
                <p className="text-lg leading-relaxed">{state.currentQuestion.text}</p>
              </div>
            </CardContent>
          </Card>

          {/* Answer Input */}
          <Card>
            <CardHeader>
              <CardTitle>Your Answer</CardTitle>
            </CardHeader>
            <CardContent>
              <textarea
                value={state.currentAnswer}
                onChange={(e) => setState(prev => ({ ...prev, currentAnswer: e.target.value }))}
                placeholder="Type your answer here..."
                className="w-full h-32 p-3 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={!state.isSessionActive || state.isPaused}
              />
            </CardContent>
          </Card>

          {/* Action Buttons */}
          <div className="flex items-center gap-4">
            <Button
              onClick={getNextQuestion}
              disabled={!state.isSessionActive || state.isPaused || isLoading}
              className="flex items-center gap-2"
            >
              <Play className="h-4 w-4" />
              Next Question
            </Button>
            
            <Button
              onClick={submitAnswer}
              disabled={!state.currentAnswer.trim() || !state.isSessionActive || state.isPaused || isLoading}
              variant="outline"
              className="flex items-center gap-2"
            >
              <CheckCircle className="h-4 w-4" />
              Submit Answer
            </Button>

            <Button
              onClick={resetQuestion}
              variant="outline"
              className="flex items-center gap-2"
            >
              <RotateCcw className="h-4 w-4" />
              Reset
            </Button>

            <Button
              onClick={togglePause}
              variant={state.isPaused ? "default" : "outline"}
              className="flex items-center gap-2 ml-auto"
            >
              {state.isPaused ? (
                <>
                  <Play className="h-4 w-4" />
                  Resume
                </>
              ) : (
                <>
                  <Pause className="h-4 w-4" />
                  Pause
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Right Sidebar */}
        <div className="space-y-6">
          {/* Anti-Cheat Guard */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Security Monitor
              </CardTitle>
            </CardHeader>
            <CardContent>
              <AntiCheatGuard onFlag={handleSecurityFlag} />
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button
                onClick={() => setState(prev => ({ ...prev, showCodeEditor: !prev.showCodeEditor }))}
                variant="outline"
                className="w-full justify-start"
              >
                <Code2 className="h-4 w-4 mr-2" />
                {state.showCodeEditor ? 'Hide' : 'Show'} Code Editor
              </Button>
              
              <Button
                onClick={() => setState(prev => ({ ...prev, showChat: !prev.showChat }))}
                variant="outline"
                className="w-full justify-start"
              >
                <MessageCircle className="h-4 w-4 mr-2" />
                {state.showChat ? 'Hide' : 'Show'} AI Chat
              </Button>
            </CardContent>
          </Card>

          {/* Session Stats */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Session Stats
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm">Questions Answered:</span>
                <span className="font-medium">{state.questionIndex}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm">Current Score:</span>
                <span className="font-medium">{state.sessionScore}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm">Security Flags:</span>
                <span className="font-medium text-red-600">{state.securityFlags.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm">Status:</span>
                <Badge variant={state.isPaused ? "destructive" : "default"}>
                  {state.isPaused ? 'Paused' : 'Active'}
                </Badge>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Code Editor Overlay */}
      {state.showCodeEditor && (
        <Card>
          <CardHeader>
            <CardTitle>Code Editor</CardTitle>
          </CardHeader>
          <CardContent>
            <EnhancedCodeEditor
              sessionId={sessionId}
              questionId={state.currentQuestion.id}
              onCodeSubmit={handleCodeSubmit}
            />
          </CardContent>
        </Card>
      )}

      {/* Chat Overlay */}
      {state.showChat && (
        <Card>
          <CardHeader>
            <CardTitle>AI Interview Assistant</CardTitle>
          </CardHeader>
          <CardContent>
            <InterviewChat
              sessionId={sessionId}
              questionId={state.currentQuestion.id}
            />
          </CardContent>
        </Card>
      )}

      {/* End Session Button */}
      <div className="text-center">
        <Button
          onClick={handleSessionEnd}
          variant="destructive"
          size="lg"
          disabled={!state.isSessionActive}
          className="flex items-center gap-2"
        >
          <Square className="h-4 w-4" />
          End Interview Session
        </Button>
      </div>

      {/* Error Display */}
      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
    </div>
  )
}
