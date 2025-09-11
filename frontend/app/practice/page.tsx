"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { 
  Brain, 
  Code2, 
  Target, 
  Clock, 
  Trophy, 
  TrendingUp,
  Play,
  Pause,
  RotateCcw,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Lightbulb,
  BookOpen,
  Zap
} from 'lucide-react'

interface PracticeQuestion {
  id: string
  type: string
  difficulty: string
  topic: string
  question: string
  timeLimit: number
  points: number
}

interface PracticeSession {
  id: string
  topic: string
  difficulty: string
  questionsAnswered: number
  correctAnswers: number
  totalScore: number
  timeSpent: number
  isActive: boolean
}

interface TopicProgress {
  topic: string
  totalQuestions: number
  correctAnswers: number
  averageScore: number
  timeSpent: number
  lastPracticed: string
}

const PRACTICE_TOPICS = [
  {
    id: 'algorithms',
    name: 'Algorithms',
    description: 'Sorting, searching, dynamic programming, and more',
    icon: Code2,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    difficulty: 'medium'
  },
  {
    id: 'data-structures',
    name: 'Data Structures',
    description: 'Arrays, linked lists, trees, graphs, and hash tables',
    icon: Brain,
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    difficulty: 'medium'
  },
  {
    id: 'system-design',
    name: 'System Design',
    description: 'Architecture, scalability, and distributed systems',
    icon: Target,
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
    difficulty: 'hard'
  },
  {
    id: 'coding',
    name: 'Coding',
    description: 'Implementation, debugging, and optimization',
    icon: Zap,
    color: 'text-orange-600',
    bgColor: 'bg-orange-50',
    difficulty: 'easy'
  },
  {
    id: 'problem-solving',
    name: 'Problem Solving',
    description: 'Logic, patterns, and creative thinking',
    icon: Lightbulb,
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-50',
    difficulty: 'medium'
  }
]

const DIFFICULTY_LEVELS = [
  { value: 'easy', label: 'Easy', color: 'text-green-600', bgColor: 'bg-green-100' },
  { value: 'medium', label: 'Medium', color: 'text-yellow-600', bgColor: 'bg-yellow-100' },
  { value: 'hard', label: 'Hard', color: 'text-red-600', bgColor: 'bg-red-100' }
]

export default function PracticePage() {
  const [selectedTopic, setSelectedTopic] = useState<string>('')
  const [selectedDifficulty, setSelectedDifficulty] = useState<string>('medium')
  const [currentSession, setCurrentSession] = useState<PracticeSession | null>(null)
  const [currentQuestion, setCurrentQuestion] = useState<PracticeQuestion | null>(null)
  const [userAnswer, setUserAnswer] = useState('')
  const [isSessionActive, setIsSessionActive] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [showResults, setShowResults] = useState(false)

  const [topicProgress, setTopicProgress] = useState<TopicProgress[]>([
    {
      topic: 'algorithms',
      totalQuestions: 45,
      correctAnswers: 32,
      averageScore: 71,
      timeSpent: 180,
      lastPracticed: '2024-01-15'
    },
    {
      topic: 'data-structures',
      totalQuestions: 38,
      correctAnswers: 29,
      averageScore: 76,
      timeSpent: 150,
      lastPracticed: '2024-01-14'
    },
    {
      topic: 'system-design',
      totalQuestions: 22,
      correctAnswers: 14,
      averageScore: 64,
      timeSpent: 120,
      lastPracticed: '2024-01-12'
    },
    {
      topic: 'coding',
      totalQuestions: 52,
      correctAnswers: 45,
      averageScore: 87,
      timeSpent: 200,
      lastPracticed: '2024-01-15'
    },
    {
      topic: 'problem-solving',
      totalQuestions: 35,
      correctAnswers: 26,
      averageScore: 74,
      timeSpent: 160,
      lastPracticed: '2024-01-13'
    }
  ])

  const startPracticeSession = async () => {
    if (!selectedTopic) return

    setIsLoading(true)

    try {
      // Simulate API call to start practice session
      await new Promise(resolve => setTimeout(resolve, 1000))

      const session: PracticeSession = {
        id: `practice_${Date.now()}`,
        topic: selectedTopic,
        difficulty: selectedDifficulty,
        questionsAnswered: 0,
        correctAnswers: 0,
        totalScore: 0,
        timeSpent: 0,
        isActive: true
      }

      setCurrentSession(session)
      setIsSessionActive(true)
      setShowResults(false)

      // Generate first question
      generateQuestion(session.topic, session.difficulty)

    } catch (error) {
      console.error('Failed to start practice session:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const generateQuestion = (topic: string, difficulty: string) => {
    // Mock question generation
    const mockQuestions: Record<string, PracticeQuestion[]> = {
      algorithms: [
        {
          id: 'algo_1',
          type: 'algorithm',
          difficulty: 'medium',
          topic: 'algorithms',
          question: 'Implement a function to find the longest common subsequence of two strings.',
          timeLimit: 300,
          points: 10
        }
      ],
      'data-structures': [
        {
          id: 'ds_1',
          type: 'data-structure',
          difficulty: 'medium',
          topic: 'data-structures',
          question: 'Design a data structure that supports insert, delete, and getRandom operations in O(1) time.',
          timeLimit: 300,
          points: 10
        }
      ],
      'system-design': [
        {
          id: 'sd_1',
          type: 'system-design',
          difficulty: 'hard',
          topic: 'system-design',
          question: 'Design a URL shortening service like bit.ly. Consider scalability, availability, and consistency.',
          timeLimit: 600,
          points: 15
        }
      ],
      coding: [
        {
          id: 'code_1',
          type: 'coding',
          difficulty: 'easy',
          topic: 'coding',
          question: 'Write a function to reverse a string in-place without using additional data structures.',
          timeLimit: 180,
          points: 5
        }
      ],
      'problem-solving': [
        {
          id: 'ps_1',
          type: 'problem-solving',
          difficulty: 'medium',
          topic: 'problem-solving',
          question: 'You have 8 balls, one of which is heavier. Using a balance scale, find the heavy ball in minimum weighings.',
          timeLimit: 300,
          points: 10
        }
      ]
    }

    const questions = mockQuestions[topic] || []
    const randomQuestion = questions[Math.floor(Math.random() * questions.length)]
    setCurrentQuestion(randomQuestion)
  }

  const submitAnswer = async () => {
    if (!currentQuestion || !userAnswer.trim() || !currentSession) return

    setIsLoading(true)

    try {
      // Simulate answer evaluation
      await new Promise(resolve => setTimeout(resolve, 1500))

      // Mock evaluation result (in production, this would come from the backend)
      const isCorrect = Math.random() > 0.3 // 70% success rate for demo
      const score = isCorrect ? currentQuestion.points : 0

      // Update session
      const updatedSession = {
        ...currentSession,
        questionsAnswered: currentSession.questionsAnswered + 1,
        correctAnswers: currentSession.correctAnswers + (isCorrect ? 1 : 0),
        totalScore: currentSession.totalScore + score
      }

      setCurrentSession(updatedSession)

      // Update topic progress
      const updatedProgress = topicProgress.map(topic => {
        if (topic.topic === selectedTopic) {
          return {
            ...topic,
            totalQuestions: topic.totalQuestions + 1,
            correctAnswers: topic.correctAnswers + (isCorrect ? 1 : 0),
            averageScore: Math.round((topic.averageScore * topic.totalQuestions + score) / (topic.totalQuestions + 1)),
            timeSpent: topic.timeSpent + 5, // Mock time spent
            lastPracticed: new Date().toISOString().split('T')[0]
          }
        }
        return topic
      })

      setTopicProgress(updatedProgress)

      // Show results briefly
      setShowResults(true)
      setTimeout(() => setShowResults(false), 3000)

      // Generate next question or end session
      if (updatedSession.questionsAnswered >= 5) {
        endPracticeSession(updatedSession)
      } else {
        setUserAnswer('')
        generateQuestion(selectedTopic, selectedDifficulty)
      }

    } catch (error) {
      console.error('Failed to submit answer:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const endPracticeSession = (session: PracticeSession) => {
    const finalSession = {
      ...session,
      isActive: false,
      timeSpent: session.timeSpent + 30 // Mock additional time
    }

    setCurrentSession(finalSession)
    setIsSessionActive(false)
    setCurrentQuestion(null)
    setUserAnswer('')
  }

  const resetSession = () => {
    setCurrentSession(null)
    setIsSessionActive(false)
    setCurrentQuestion(null)
    setUserAnswer('')
    setShowResults(false)
  }

  const getTopicIcon = (topicId: string) => {
    const topic = PRACTICE_TOPICS.find(t => t.id === topicId)
    return topic ? topic.icon : Brain
  }

  const getTopicColor = (topicId: string) => {
    const topic = PRACTICE_TOPICS.find(t => t.id === topicId)
    return topic ? topic.color : 'text-gray-600'
  }

  const getDifficultyColor = (difficulty: string) => {
    const level = DIFFICULTY_LEVELS.find(d => d.value === difficulty)
    return level ? level.color : 'text-gray-600'
  }

  if (isSessionActive && currentSession) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Session Header */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <BookOpen className="h-5 w-5" />
                    Practice Session: {PRACTICE_TOPICS.find(t => t.id === currentSession.topic)?.name}
                  </CardTitle>
                  <p className="text-sm text-muted-foreground mt-1">
                    Difficulty: {selectedDifficulty.charAt(0).toUpperCase() + selectedDifficulty.slice(1)} | 
                    Question {currentSession.questionsAnswered + 1} of 5
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium">Score</p>
                  <p className="text-2xl font-bold text-green-600">{currentSession.totalScore}</p>
                </div>
              </div>
            </CardHeader>
          </Card>

          {/* Current Question */}
          {currentQuestion && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span>Question {currentSession.questionsAnswered + 1}</span>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{currentQuestion.topic}</Badge>
                    <Badge variant="outline">{currentQuestion.difficulty}</Badge>
                    <Badge variant="outline">{currentQuestion.points} pts</Badge>
                  </div>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="prose max-w-none mb-6">
                  <p className="text-lg leading-relaxed">{currentQuestion.question}</p>
                </div>

                <div className="space-y-4">
                  <label className="block text-sm font-medium">Your Answer</label>
                  <textarea
                    value={userAnswer}
                    onChange={(e) => setUserAnswer(e.target.value)}
                    placeholder="Type your answer here..."
                    className="w-full h-32 p-3 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    disabled={isLoading}
                  />

                  <div className="flex items-center gap-4">
                    <Button
                      onClick={submitAnswer}
                      disabled={!userAnswer.trim() || isLoading}
                      className="flex items-center gap-2"
                    >
                      {isLoading ? (
                        <>
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                          Evaluating...
                        </>
                      ) : (
                        <>
                          <CheckCircle className="h-4 w-4" />
                          Submit Answer
                        </>
                      )}
                    </Button>

                    <Button
                      onClick={resetSession}
                      variant="outline"
                      className="flex items-center gap-2"
                    >
                      <RotateCcw className="h-4 w-4" />
                      End Session
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Results Display */}
          {showResults && (
            <Card className="border-green-200 bg-green-50">
              <CardContent className="pt-6">
                <div className="flex items-center gap-3 text-green-800">
                  <CheckCircle className="h-5 w-5" />
                  <div>
                    <p className="font-medium">Answer submitted successfully!</p>
                    <p className="text-sm">Moving to next question...</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    )
  }

  if (currentSession && !currentSession.isActive) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card className="max-w-2xl mx-auto text-center">
          <CardHeader>
            <div className="mx-auto w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
              <Trophy className="h-8 w-8 text-green-600" />
            </div>
            <CardTitle className="text-2xl">Practice Session Complete!</CardTitle>
            <p className="text-muted-foreground">
              Great job completing your practice session
            </p>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <p className="font-medium">Questions Answered</p>
                <p className="text-2xl font-bold text-blue-600">{currentSession.questionsAnswered}</p>
              </div>
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <p className="font-medium">Correct Answers</p>
                <p className="text-2xl font-bold text-green-600">{currentSession.correctAnswers}</p>
              </div>
            </div>

            <div className="text-center">
              <p className="text-sm font-medium text-muted-foreground">Final Score</p>
              <p className="text-4xl font-bold text-green-600">{currentSession.totalScore}</p>
              <p className="text-sm text-muted-foreground">
                Accuracy: {Math.round((currentSession.correctAnswers / currentSession.questionsAnswered) * 100)}%
              </p>
            </div>

            <div className="flex gap-3">
              <Button onClick={resetSession} className="flex-1">
                Practice Again
              </Button>
              <Button onClick={resetSession} variant="outline" className="flex-1">
                Back to Practice Hub
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold">Practice Hub</h1>
          <p className="text-xl text-muted-foreground">
            Sharpen your skills with targeted practice sessions
          </p>
        </div>

        {/* Practice Configuration */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="h-5 w-5" />
              Start Practice Session
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label className="text-sm font-medium">Select Topic</label>
                <Select value={selectedTopic} onValueChange={setSelectedTopic}>
                  <SelectTrigger>
                    <SelectValue placeholder="Choose a topic to practice" />
                  </SelectTrigger>
                  <SelectContent>
                    {PRACTICE_TOPICS.map((topic) => (
                      <SelectItem key={topic.id} value={topic.id}>
                        <div className="flex items-center gap-2">
                          <topic.icon className="h-4 w-4" />
                          {topic.name}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Difficulty Level</label>
                <Select value={selectedDifficulty} onValueChange={setSelectedDifficulty}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {DIFFICULTY_LEVELS.map((level) => (
                      <SelectItem key={level.value} value={level.value}>
                        {level.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="pt-4">
              <Button
                onClick={startPracticeSession}
                disabled={!selectedTopic || isLoading}
                size="lg"
                className="w-full md:w-auto"
              >
                {isLoading ? 'Starting Session...' : 'Start Practice Session'}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Topic Overview */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {PRACTICE_TOPICS.map((topic) => {
            const progress = topicProgress.find(p => p.topic === topic.id)
            const Icon = topic.icon

            return (
              <Card key={topic.id} className="hover:shadow-lg transition-shadow cursor-pointer">
                <CardHeader>
                  <div className="flex items-center gap-3">
                    <div className={`w-12 h-12 ${topic.bgColor} rounded-lg flex items-center justify-center`}>
                      <Icon className={`h-6 w-6 ${topic.color}`} />
                    </div>
                    <div>
                      <CardTitle className="text-lg">{topic.name}</CardTitle>
                      <p className="text-sm text-muted-foreground">{topic.description}</p>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {progress && (
                    <>
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span>Progress</span>
                          <span>{Math.round((progress.correctAnswers / progress.totalQuestions) * 100)}%</span>
                        </div>
                        <Progress value={(progress.correctAnswers / progress.totalQuestions) * 100} />
                      </div>

                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <p className="text-muted-foreground">Questions</p>
                          <p className="font-medium">{progress.totalQuestions}</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Score</p>
                          <p className="font-medium">{progress.averageScore}%</p>
                        </div>
                      </div>

                      <div className="text-xs text-muted-foreground">
                        Last practiced: {new Date(progress.lastPracticed).toLocaleDateString()}
                      </div>
                    </>
                  )}

                  <Button
                    variant="outline"
                    className="w-full"
                    onClick={() => {
                      setSelectedTopic(topic.id)
                      setSelectedDifficulty(topic.difficulty)
                    }}
                  >
                    Practice {topic.name}
                  </Button>
                </CardContent>
              </Card>
            )
          })}
        </div>

        {/* Progress Overview */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Overall Progress
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="text-center">
                <p className="text-sm font-medium text-muted-foreground">Total Questions</p>
                <p className="text-2xl font-bold">
                  {topicProgress.reduce((sum, topic) => sum + topic.totalQuestions, 0)}
                </p>
              </div>
              <div className="text-center">
                <p className="text-sm font-medium text-muted-foreground">Correct Answers</p>
                <p className="text-2xl font-bold text-green-600">
                  {topicProgress.reduce((sum, topic) => sum + topic.correctAnswers, 0)}
                </p>
              </div>
              <div className="text-center">
                <p className="text-sm font-medium text-muted-foreground">Average Score</p>
                <p className="text-2xl font-bold text-blue-600">
                  {Math.round(topicProgress.reduce((sum, topic) => sum + topic.averageScore, 0) / topicProgress.length)}%
                </p>
              </div>
              <div className="text-center">
                <p className="text-sm font-medium text-muted-foreground">Time Spent</p>
                <p className="text-2xl font-bold text-purple-600">
                  {Math.round(topicProgress.reduce((sum, topic) => sum + topic.timeSpent, 0) / 60)}m
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
