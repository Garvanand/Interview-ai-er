"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  BarChart3, 
  TrendingUp, 
  Clock, 
  Trophy, 
  Target, 
  Calendar,
  Brain,
  Shield,
  Code2,
  MessageCircle,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Minus
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'

interface InterviewSession {
  id: string
  interview_type: string
  start_time: string
  end_time?: string
  score?: number
  status: string
  security_events_count: number
  questions_answered: number
}

interface PerformanceMetrics {
  totalSessions: number
  averageScore: number
  bestScore: number
  totalQuestions: number
  securityFlags: number
  completionRate: number
}

interface SkillBreakdown {
  algorithm: number
  dataStructures: number
  systemDesign: number
  coding: number
  problemSolving: number
}

export default function DashboardPage() {
  const [sessions, setSessions] = useState<InterviewSession[]>([])
  const [metrics, setMetrics] = useState<PerformanceMetrics>({
    totalSessions: 0,
    averageScore: 0,
    bestScore: 0,
    totalQuestions: 0,
    securityFlags: 0,
    completionRate: 0
  })
  const [skillBreakdown, setSkillBreakdown] = useState<SkillBreakdown>({
    algorithm: 75,
    dataStructures: 82,
    systemDesign: 68,
    coding: 88,
    problemSolving: 79
  })
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadDashboardData()
  }, [])

  const loadDashboardData = async () => {
    setIsLoading(true)
    setError(null)

    try {
      // For demo purposes, we'll use mock data
      // In production, this would come from the backend
      const mockSessions: InterviewSession[] = [
        {
          id: 'session_1',
          interview_type: 'Technical',
          start_time: '2024-01-15T10:00:00Z',
          end_time: '2024-01-15T11:00:00Z',
          score: 85,
          status: 'completed',
          security_events_count: 2,
          questions_answered: 8
        },
        {
          id: 'session_2',
          interview_type: 'Technical',
          start_time: '2024-01-10T14:00:00Z',
          end_time: '2024-01-10T15:00:00Z',
          score: 92,
          status: 'completed',
          security_events_count: 0,
          questions_answered: 10
        },
        {
          id: 'session_3',
          interview_type: 'Behavioral',
          start_time: '2024-01-05T09:00:00Z',
          end_time: '2024-01-05T09:45:00Z',
          score: 78,
          status: 'completed',
          security_events_count: 1,
          questions_answered: 6
        },
        {
          id: 'session_4',
          interview_type: 'Technical',
          start_time: '2024-01-01T16:00:00Z',
          status: 'in_progress',
          security_events_count: 0,
          questions_answered: 3
        }
      ]

      setSessions(mockSessions)

      // Calculate metrics
      const completedSessions = mockSessions.filter(s => s.status === 'completed')
      const totalScore = completedSessions.reduce((sum, s) => sum + (s.score || 0), 0)
      const totalSecurityFlags = mockSessions.reduce((sum, s) => sum + s.security_events_count, 0)
      const totalQuestions = mockSessions.reduce((sum, s) => sum + s.questions_answered, 0)

      setMetrics({
        totalSessions: mockSessions.length,
        averageScore: completedSessions.length > 0 ? Math.round(totalScore / completedSessions.length) : 0,
        bestScore: Math.max(...completedSessions.map(s => s.score || 0)),
        totalQuestions,
        securityFlags: totalSecurityFlags,
        completionRate: Math.round((completedSessions.length / mockSessions.length) * 100)
      })

    } catch (err: any) {
      setError(err.message || 'Failed to load dashboard data')
    } finally {
      setIsLoading(false)
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge variant="default" className="flex items-center gap-1"><CheckCircle className="h-3 w-3" />Completed</Badge>
      case 'in_progress':
        return <Badge variant="secondary" className="flex items-center gap-1"><Clock className="h-3 w-3" />In Progress</Badge>
      case 'paused':
        return <Badge variant="outline" className="flex items-center gap-1"><Minus className="h-3 w-3" />Paused</Badge>
      default:
        return <Badge variant="outline">{status}</Badge>
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-600'
    if (score >= 80) return 'text-blue-600'
    if (score >= 70) return 'text-yellow-600'
    if (score >= 60) return 'text-orange-600'
    return 'text-red-600'
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card className="p-8 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-lg">Loading dashboard...</p>
        </Card>
      </div>
    )
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card className="p-8 text-center">
          <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <p className="text-lg text-red-600">Failed to load dashboard</p>
          <p className="text-sm text-gray-600 mt-2">{error}</p>
          <Button onClick={loadDashboardData} className="mt-4">Retry</Button>
        </Card>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Interview Dashboard</h1>
            <p className="text-muted-foreground mt-1">
              Track your performance and progress across all interview sessions
            </p>
          </div>
          <Button className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4" />
            Export Report
          </Button>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Sessions</CardTitle>
              <Calendar className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metrics.totalSessions}</div>
              <p className="text-xs text-muted-foreground">
                +2 from last month
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Average Score</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${getScoreColor(metrics.averageScore)}`}>
                {metrics.averageScore}%
              </div>
              <p className="text-xs text-muted-foreground">
                +5% from last month
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Best Score</CardTitle>
              <Trophy className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${getScoreColor(metrics.bestScore)}`}>
                {metrics.bestScore}%
              </div>
              <p className="text-xs text-muted-foreground">
                Personal best
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Completion Rate</CardTitle>
              <Target className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metrics.completionRate}%</div>
              <p className="text-xs text-muted-foreground">
                {metrics.totalSessions - Math.round(metrics.totalSessions * metrics.completionRate / 100)} incomplete
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Recent Sessions */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Clock className="h-5 w-5" />
                  Recent Interview Sessions
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {sessions.map((session) => (
                    <div key={session.id} className="flex items-center justify-between p-4 border rounded-lg">
                      <div className="flex items-center gap-4">
                        <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                          <Brain className="h-6 w-6 text-blue-600" />
                        </div>
                        <div>
                          <p className="font-medium">{session.interview_type} Interview</p>
                          <p className="text-sm text-muted-foreground">
                            {formatDate(session.start_time)}
                          </p>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="text-xs text-muted-foreground">
                              {session.questions_answered} questions
                            </span>
                            {session.security_events_count > 0 && (
                              <Badge variant="destructive" className="text-xs">
                                {session.security_events_count} flags
                              </Badge>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        {getStatusBadge(session.status)}
                        {session.score && (
                          <p className={`text-lg font-bold mt-1 ${getScoreColor(session.score)}`}>
                            {session.score}%
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Skill Breakdown */}
          <div>
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5" />
                  Skill Breakdown
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {Object.entries(skillBreakdown).map(([skill, score]) => (
                  <div key={skill} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium capitalize">
                        {skill.replace(/([A-Z])/g, ' $1').trim()}
                      </span>
                      <span className={`text-sm font-bold ${getScoreColor(score)}`}>
                        {score}%
                      </span>
                    </div>
                    <Progress value={score} className="h-2" />
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Detailed Analytics */}
        <Tabs defaultValue="performance" className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="performance">Performance</TabsTrigger>
            <TabsTrigger value="security">Security</TabsTrigger>
            <TabsTrigger value="questions">Questions</TabsTrigger>
            <TabsTrigger value="improvements">Improvements</TabsTrigger>
          </TabsList>

          <TabsContent value="performance" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Score Trend</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-64 flex items-center justify-center text-muted-foreground">
                    Score trend chart will be displayed here
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Session Duration</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-64 flex items-center justify-center text-muted-foreground">
                    Duration distribution chart will be displayed here
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="security" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Shield className="h-5 w-5" />
                    Security Events
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Total Flags</span>
                      <Badge variant="destructive">{metrics.securityFlags}</Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Clean Sessions</span>
                      <Badge variant="default">
                        {sessions.filter(s => s.security_events_count === 0).length}
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Risk Level</span>
                      <Badge variant={metrics.securityFlags > 5 ? "destructive" : metrics.securityFlags > 2 ? "secondary" : "default"}>
                        {metrics.securityFlags > 5 ? "High" : metrics.securityFlags > 2 ? "Medium" : "Low"}
                      </Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Security Recommendations</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3 text-sm">
                    {metrics.securityFlags > 0 ? (
                      <>
                        <div className="flex items-start gap-2">
                          <AlertTriangle className="h-4 w-4 text-orange-500 mt-0.5 flex-shrink-0" />
                          <p>Review flagged sessions for potential improvements</p>
                        </div>
                        <div className="flex items-start gap-2">
                          <Shield className="h-4 w-4 text-blue-500 mt-0.5 flex-shrink-0" />
                          <p>Ensure proper environment setup before interviews</p>
                        </div>
                      </>
                    ) : (
                      <div className="flex items-start gap-2">
                        <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                        <p>Excellent! No security flags detected</p>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="questions" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Question Performance</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Total Questions</span>
                      <span className="font-medium">{metrics.totalQuestions}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Questions per Session</span>
                      <span className="font-medium">
                        {Math.round(metrics.totalQuestions / metrics.totalSessions)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Completion Rate</span>
                      <span className="font-medium">{metrics.completionRate}%</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Question Types</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Algorithm</span>
                      <Badge variant="outline">40%</Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Data Structures</span>
                      <Badge variant="outline">30%</Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm">System Design</span>
                      <Badge variant="outline">20%</Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Other</span>
                      <Badge variant="outline">10%</Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="improvements" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Improvement Suggestions</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="p-4 bg-blue-50 rounded-lg">
                    <h4 className="font-medium text-blue-900 mb-2">Focus Areas</h4>
                    <ul className="text-sm text-blue-800 space-y-1">
                      <li>• Practice more system design questions (current: 68%)</li>
                      <li>• Improve algorithm problem-solving speed</li>
                      <li>• Review data structure implementations</li>
                    </ul>
                  </div>
                  
                  <div className="p-4 bg-green-50 rounded-lg">
                    <h4 className="font-medium text-green-900 mb-2">Strengths</h4>
                    <ul className="text-sm text-green-800 space-y-1">
                      <li>• Excellent coding skills (88%)</li>
                      <li>• Strong data structure knowledge (82%)</li>
                      <li>• Good problem-solving approach (79%)</li>
                    </ul>
                  </div>

                  <div className="p-4 bg-yellow-50 rounded-lg">
                    <h4 className="font-medium text-yellow-900 mb-2">Next Steps</h4>
                    <ul className="text-sm text-yellow-800 space-y-1">
                      <li>• Complete 2 more practice sessions this week</li>
                      <li>• Focus on system design fundamentals</li>
                      <li>• Review time management strategies</li>
                    </ul>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
