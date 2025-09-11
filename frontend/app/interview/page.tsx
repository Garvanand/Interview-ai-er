"use client"

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { InterviewInterface } from '@/components/interview/interview-interface'
import { Brain, Shield, Clock, Trophy, AlertTriangle } from 'lucide-react'

export default function InterviewPage() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [isSessionStarted, setIsSessionStarted] = useState(false)
  const [finalScore, setFinalScore] = useState<number | null>(null)

  const handleStartInterview = async () => {
    try {
      // For demo purposes, we'll use a mock session ID
      // In production, this would come from the backend
      const mockSessionId = `session_${Date.now()}`
      setSessionId(mockSessionId)
      setIsSessionStarted(true)
      setFinalScore(null)
    } catch (error) {
      console.error('Failed to start interview:', error)
    }
  }

  const handleSessionEnd = (score: number) => {
    setFinalScore(score)
    setIsSessionStarted(false)
    setSessionId(null)
  }

  const handleNewInterview = () => {
    setFinalScore(null)
    setIsSessionStarted(false)
    setSessionId(null)
  }

  if (finalScore !== null) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card className="max-w-2xl mx-auto text-center">
          <CardHeader>
            <div className="mx-auto w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
              <Trophy className="h-8 w-8 text-green-600" />
            </div>
            <CardTitle className="text-2xl">Interview Completed!</CardTitle>
            <p className="text-muted-foreground">
              Congratulations on completing your technical interview
            </p>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="text-center">
              <p className="text-sm font-medium text-muted-foreground">Final Score</p>
              <p className="text-4xl font-bold text-green-600">{finalScore}/100</p>
              <p className="text-lg text-muted-foreground">
                {finalScore >= 90 ? 'Excellent!' : 
                 finalScore >= 80 ? 'Great job!' : 
                 finalScore >= 70 ? 'Good work!' : 
                 finalScore >= 60 ? 'Keep practicing!' : 'Review and try again!'}
              </p>
            </div>
            
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <p className="font-medium">Questions Answered</p>
                <p className="text-2xl font-bold text-blue-600">10</p>
              </div>
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <p className="font-medium">Time Taken</p>
                <p className="text-2xl font-bold text-purple-600">45m</p>
              </div>
            </div>

            <Button onClick={handleNewInterview} className="w-full">
              Start New Interview
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (isSessionStarted && sessionId) {
    return (
      <div className="container mx-auto px-4 py-8">
        <InterviewInterface 
          sessionId={sessionId}
          onSessionEnd={handleSessionEnd}
        />
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Header */}
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold">Technical Interview Hub</h1>
          <p className="text-xl text-muted-foreground">
            Test your skills with AI-powered technical interviews
          </p>
        </div>

        {/* Interview Configuration */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5" />
              Interview Configuration
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Interview Type</label>
                <div className="flex items-center gap-2">
                  <Badge variant="default">Technical</Badge>
                  <Badge variant="outline">Behavioral</Badge>
                </div>
              </div>
              
              <div className="space-y-2">
                <label className="text-sm font-medium">Difficulty</label>
                <div className="flex items-center gap-2">
                  <Badge variant="outline">Easy</Badge>
                  <Badge variant="default">Medium</Badge>
                  <Badge variant="outline">Hard</Badge>
                </div>
              </div>
              
              <div className="space-y-2">
                <label className="text-sm font-medium">Duration</label>
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4" />
                  <span>60 minutes</span>
                </div>
              </div>
            </div>

            <div className="pt-4">
              <Button 
                onClick={handleStartInterview}
                size="lg"
                className="w-full md:w-auto"
              >
                Start Interview
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Features */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5 text-green-600" />
                Anti-Cheating Protection
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>• Webcam monitoring for face detection</li>
                <li>• Audio analysis for suspicious sounds</li>
                <li>• Browser behavior tracking</li>
                <li>• Typing pattern analysis</li>
                <li>• Real-time security alerts</li>
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Brain className="h-5 w-5 text-blue-600" />
                AI-Powered Features
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>• Dynamic question generation</li>
                <li>• Real-time answer evaluation</li>
                <li>• Code analysis and scoring</li>
                <li>• Personalized feedback</li>
                <li>• Adaptive difficulty</li>
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-5 w-5 text-purple-600" />
                Interview Tools
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>• Built-in code editor</li>
                <li>• AI chat assistant</li>
                <li>• Question navigation</li>
                <li>• Progress tracking</li>
                <li>• Session management</li>
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Trophy className="h-5 w-5 text-yellow-600" />
                Performance Analytics
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>• Detailed scoring breakdown</li>
                <li>• Skill area analysis</li>
                <li>• Improvement suggestions</li>
                <li>• Historical performance</li>
                <li>• Benchmark comparisons</li>
              </ul>
            </CardContent>
          </Card>
        </div>

        {/* Instructions */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-orange-600" />
              Important Instructions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3 text-sm">
              <div className="flex items-start gap-2">
                <div className="w-2 h-2 bg-orange-500 rounded-full mt-2 flex-shrink-0"></div>
                <p>Ensure your webcam and microphone are working properly before starting</p>
              </div>
              <div className="flex items-start gap-2">
                <div className="w-2 h-2 bg-orange-500 rounded-full mt-2 flex-shrink-0"></div>
                <p>Close all unnecessary browser tabs and applications</p>
              </div>
              <div className="flex items-start gap-2">
                <div className="w-2 h-2 bg-orange-500 rounded-full mt-2 flex-shrink-0"></div>
                <p>Find a quiet environment with good lighting</p>
              </div>
              <div className="flex items-start gap-2">
                <div className="w-2 h-2 bg-orange-500 rounded-full mt-2 flex-shrink-0"></div>
                <p>Have a stable internet connection throughout the interview</p>
              </div>
              <div className="flex items-start gap-2">
                <div className="w-2 h-2 bg-orange-500 rounded-full mt-2 flex-shrink-0"></div>
                <p>Don't switch tabs or use keyboard shortcuts during the interview</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
