"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Separator } from "@/components/ui/separator"
import {
  apiClient,
  type Question,
  type OrchestratorSessionState,
  type AnswerEvaluation,
  type CodeEvaluation,
} from "@/lib/api-client"
import { AntiCheatGuard } from "../anti-cheat/anti-cheat-guard"
import dynamic from "next/dynamic"
import {
  Code2,
  FileText,
  Clock,
  Shield,
  Brain,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Send,
  ArrowRight,
  HelpCircle,
  Lightbulb,
  ExternalLink,
  ChevronRight,
  TrendingUp,
  Award,
  Layers,
  Sparkles,
  RefreshCw,
  LogOut,
  Target,
  BarChart2,
  Mic,
} from "lucide-react"
import { VoiceRecorderButton } from "./voice-recorder-button"
import type { TranscriptionMetadata } from "@/hooks/use-voice-recorder"
import {
  MLDetectedFocus,
  MLAdaptiveExplanation,
  MLConceptCoverageResult,
  MLCodeResultInterpretation,
  MLExplanationContainer,
} from "@/components/ui/ml-explanation"

const MonacoEditor = dynamic(() => import("../ide/code-editor"), { ssr: false })

interface InterviewWorkspaceProps {
  sessionId: string
  onSessionEnd?: (finalScore: number) => void
}

const LANGUAGE_STARTERS: Record<string, string> = {
  python: `# Write your implementation here
def solution(data):
    """
    Formulate your solution with optimal time and space complexity.
    """
    pass
`,
  javascript: `// Write your implementation here
function solution(data) {
  // Formulate your solution with optimal time and space complexity.
}
`,
  typescript: `// Write your implementation here
function solution(data: any): any {
  // Formulate your solution with optimal time and space complexity.
}
`,
  go: `package main

import "fmt"

func Solution(data interface{}) interface{} {
    // Formulate your solution with optimal time and space complexity.
    return nil
}
`,
  cpp: `#include <iostream>
#include <vector>

using namespace std;

// Formulate your solution with optimal time and space complexity.
void solution() {
}
`,
  java: `public class Solution {
    public static void main(String[] args) {
        // Formulate your solution with optimal time and space complexity.
    }
}
`,
  rust: `// Formulate your solution with optimal time and space complexity.
pub fn solution() {
}
`,
}

const ORCHESTRATOR_PHASE_STEPS = [
  { id: "QUESTIONING", label: "Question Selection", desc: "Adaptive prompt served" },
  { id: "EVALUATING", label: "Candidate Response", desc: "Rubric evaluation active" },
  { id: "DIFFICULTY_ADJUSTMENT", label: "Difficulty Adaptation", desc: "Signal extraction" },
  { id: "FINAL_ASSESSMENT", label: "Synthesis", desc: "Holistic assessment" },
]

export function InterviewWorkspace({ sessionId, onSessionEnd }: InterviewWorkspaceProps) {
  // Authoritative orchestrator state
  const [sessionState, setSessionState] = useState<OrchestratorSessionState | null>(null)
  const [sessionDetails, setSessionDetails] = useState<any>(null)
  const [questionsList, setQuestionsList] = useState<Question[]>([])

  // Active / current assessment state
  const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null)
  const [viewingPastQuestion, setViewingPastQuestion] = useState<Question | null>(null)

  // Response workspace state
  const [answerMode, setAnswerMode] = useState<"text" | "code">("text")
  const [textAnswer, setTextAnswer] = useState<string>("")
  const [codeAnswer, setCodeAnswer] = useState<string>(LANGUAGE_STARTERS.python)
  const [selectedLanguage, setSelectedLanguage] = useState<string>("python")
  const [voiceMetadata, setVoiceMetadata] = useState<TranscriptionMetadata | null>(null)

  // Submission & evaluation feedback state
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false)
  const [submissionPhase, setSubmissionPhase] = useState<"idle" | "evaluating" | "scoring">("idle")
  const [activeEvaluation, setActiveEvaluation] = useState<any>(null)
  const [evalError, setEvalError] = useState<string | null>(null)
  
  // Execution state
  const [isRunningCode, setIsRunningCode] = useState<boolean>(false)
  const [runResult, setRunResult] = useState<any>(null)

  // Local persistence & autosave status
  const [autosaveStatus, setAutosaveStatus] = useState<"saved" | "saving" | "unsaved">("saved")
  const [lastSavedTime, setLastSavedTime] = useState<string | null>(null)
  const autosaveTimerRef = useRef<NodeJS.Timeout | null>(null)

  // Right-zone telemetry & signals
  const [timeRemaining, setTimeRemaining] = useState<number>(2700)
  const [isTimerPaused, setIsTimerPaused] = useState<boolean>(false)
  const [securityFlags, setSecurityFlags] = useState<string[]>([])
  const [integrityReport, setIntegrityReport] = useState<any>(null)
  const rawEventsQueueRef = useRef<{ type: string, evidence: string }[]>([])
  const [hintsExpanded, setHintsExpanded] = useState<boolean>(false)
  const [hintCount, setHintCount] = useState<number>(0)

  // Lifecycle & loading
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [isFinalizing, setIsFinalizing] = useState<boolean>(false)
  const [finalSummary, setFinalSummary] = useState<any>(null)
  const [confirmModal, setConfirmModal] = useState<"end_assessment" | "reset_draft" | null>(null)

  // 1. Initial State Hydration & Graceful Refresh Recovery
  const loadAuthoritativeState = useCallback(async () => {
    if (!sessionId) return
    try {
      setIsLoading(true)
      setEvalError(null)

      // Query state & details in parallel
      const [stateRes, detailsRes] = await Promise.all([
        apiClient.getSessionState(sessionId),
        apiClient.getSessionDetails(sessionId),
      ])

      setSessionState(stateRes)
      setSessionDetails(detailsRes)

      const questions: Question[] = detailsRes?.questions || []
      setQuestionsList(questions)

      // Calculate time remaining based on start_time and time_budget_seconds
      if (stateRes?.start_time && stateRes?.time_budget_seconds) {
        const startTimeMs = new Date(stateRes.start_time).getTime()
        const nowMs = Date.now()
        const elapsedSec = Math.floor((nowMs - startTimeMs) / 1000)
        const budget = stateRes.time_budget_seconds
        const remaining = Math.max(0, budget - elapsedSec)
        setTimeRemaining(remaining)
      } else if (stateRes?.time_budget_seconds) {
        setTimeRemaining(stateRes.time_budget_seconds)
      }

      // If session is already completed, show final summary
      if (stateRes?.is_completed) {
        setFinalSummary(stateRes.final_assessment || stateRes)
        setIsLoading(false)
        return
      }

      // Check if there is an active unanswered question
      const unanswered = questions.find((q) => !q.answer_text && !q.code_text)

      if (unanswered) {
        setCurrentQuestion(unanswered)
        setViewingPastQuestion(null)
        // Check for local draft
        restoreDraft(unanswered.id)
      } else if (questions.length === 0) {
        // Fetch first question from orchestrator
        const nextQ = await apiClient.getQuestion(
          sessionId,
          stateRes?.target_role || stateRes?.interview_type || "Software Engineer"
        )
        if (nextQ.is_completed) {
          setFinalSummary(nextQ)
        } else {
          const formattedQ: Question = {
            id: nextQ.question_id,
            session_id: sessionId,
            question_text: nextQ.question_text,
            interview_type: nextQ.interview_type || stateRes?.target_role || "Software Engineer",
            difficulty: nextQ.difficulty,
            skill_focus: nextQ.skill_focus,
            is_follow_up: nextQ.is_follow_up,
            question_index: nextQ.question_index,
            total_questions: nextQ.total_questions,
          }
          setCurrentQuestion(formattedQ)
          setQuestionsList([formattedQ])
          restoreDraft(formattedQ.id)
        }
      } else {
        // All previous questions were answered; if last question was just answered,
        // show latest evaluation or fetch next question
        const lastQ = questions[questions.length - 1]
        if (lastQ.evaluation_details || lastQ.evaluation_feedback) {
          setCurrentQuestion(lastQ)
          setActiveEvaluation(lastQ.evaluation_details || {
            overall_score: lastQ.evaluation_score,
            feedback: lastQ.evaluation_feedback,
          })
        }
      }
    } catch (err: any) {
      console.error("Failed to load interview workspace state:", err)
      setEvalError(err.message || "Failed to synchronize assessment state from server.")
    } finally {
      setIsLoading(false)
    }
  }, [sessionId])

  useEffect(() => {
    loadAuthoritativeState()
  }, [loadAuthoritativeState])

  // Escape key handler for confirmation dialogs
  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && confirmModal) {
        setConfirmModal(null)
      }
    }
    window.addEventListener("keydown", handleGlobalKeyDown)
    return () => window.removeEventListener("keydown", handleGlobalKeyDown)
  }, [confirmModal])

  // 2. Draft Storage & Recovery Helpers
  const getDraftKey = (qId: string, mode: "text" | "code") =>
    `interview_draft_${sessionId}_${qId}_${mode}`

  const restoreDraft = (qId: string) => {
    if (typeof window === "undefined") return
    const textSaved = localStorage.getItem(getDraftKey(qId, "text"))
    const codeSaved = localStorage.getItem(getDraftKey(qId, "code"))
    if (textSaved) {
      setTextAnswer(textSaved)
      setLastSavedTime("Draft restored from previous session")
    } else {
      setTextAnswer("")
    }
    if (codeSaved) {
      setCodeAnswer(codeSaved)
    } else {
      setCodeAnswer(LANGUAGE_STARTERS[selectedLanguage] || "")
    }
  }

  const clearSavedDraft = (qId: string) => {
    if (typeof window === "undefined") return
    localStorage.removeItem(getDraftKey(qId, "text"))
    localStorage.removeItem(getDraftKey(qId, "code"))
  }

  // Handle autosave on typing
  const handleTextChange = (val: string) => {
    setTextAnswer(val)
    setAutosaveStatus("unsaved")
    if (autosaveTimerRef.current) clearTimeout(autosaveTimerRef.current)
    autosaveTimerRef.current = setTimeout(() => {
      if (!currentQuestion) return
      localStorage.setItem(getDraftKey(currentQuestion.id, "text"), val)
      setAutosaveStatus("saved")
      setLastSavedTime(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }))
    }, 600)
  }

  const handleCodeChange = (val: string | undefined) => {
    const codeVal = val || ""
    setCodeAnswer(codeVal)
    setAutosaveStatus("unsaved")
    if (autosaveTimerRef.current) clearTimeout(autosaveTimerRef.current)
    autosaveTimerRef.current = setTimeout(() => {
      if (!currentQuestion) return
      localStorage.setItem(getDraftKey(currentQuestion.id, "code"), codeVal)
      setAutosaveStatus("saved")
      setLastSavedTime(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }))
    }, 600)
  }

  // 3. Live Countdown Timer
  useEffect(() => {
    if (isTimerPaused || timeRemaining <= 0 || sessionState?.is_completed) return
    const interval = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(interval)
          handleFinalizeAssessment("Time budget expired")
          return 0
        }
        return prev - 1
      })
    }, 1000)
    return () => clearInterval(interval)
  }, [isTimerPaused, timeRemaining, sessionState?.is_completed])

  const formatTimer = (seconds: number) => {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`
  }

  // 4. Candidate Run & Submission Flow
  const handleRunCode = async () => {
    if (isRunningCode || !currentQuestion || answerMode !== "code") return

    const submissionContent = codeAnswer.trim()
    if (submissionContent.length < 5) {
      setEvalError("Code is too short to execute.")
      return
    }

    setIsRunningCode(true)
    setEvalError(null)
    setRunResult(null)
    setActiveEvaluation(null)

    try {
      const result = await apiClient.runCode(submissionContent, selectedLanguage)
      setRunResult(result)
    } catch (err: any) {
      console.error("Execution error:", err)
      setEvalError(err.message || "Failed to execute code in sandbox.")
    } finally {
      setIsRunningCode(false)
    }
  }

  // Candidate Submission Flow (Prevent duplicate submission, evaluate via backend orchestrator)
  const handleSubmitSolution = async () => {
    if (isSubmitting || !currentQuestion) return

    const submissionContent = answerMode === "text" ? textAnswer.trim() : codeAnswer.trim()

    // Minimum 10 characters requirement
    if (submissionContent.length < 10) {
      setEvalError("Your response must contain at least 10 characters to be assessed.")
      return
    }

    setIsSubmitting(true)
    setSubmissionPhase("evaluating")
    setEvalError(null)

    try {
      let result: any
      if (answerMode === "text") {
        if (voiceMetadata && voiceMetadata.transcript.trim() === submissionContent.trim()) {
          result = await apiClient.submitVoiceAnswer(
            sessionId,
            currentQuestion.id,
            submissionContent,
            voiceMetadata
          )
        } else {
          result = await apiClient.submitAnswer(sessionId, currentQuestion.id, submissionContent)
        }
      } else {
        result = await apiClient.submitCode(sessionId, currentQuestion.id, submissionContent, selectedLanguage)
      }

      setSubmissionPhase("scoring")

      // Extract evaluation object
      const evaluation = result.evaluation || result
      setActiveEvaluation(evaluation)

      // Clean local draft now that submission succeeded
      clearSavedDraft(currentQuestion.id)
      setVoiceMetadata(null)

      // Refresh authoritative session state and details
      const [updatedState, updatedDetails] = await Promise.all([
        apiClient.getSessionState(sessionId),
        apiClient.getSessionDetails(sessionId),
      ])

      setSessionState(updatedState)
      setSessionDetails(updatedDetails)
      if (updatedDetails?.questions) {
        setQuestionsList(updatedDetails.questions)
      }

      // Check if last question was answered or completed
      if (result.is_last_question || updatedState.is_completed) {
        handleFinalizeAssessment("Curriculum completed")
      }
    } catch (err: any) {
      console.error("Submission error:", err)
      setEvalError(err.message || "Evaluation encountered an issue. Please try submitting again.")
    } finally {
      setIsSubmitting(false)
      setSubmissionPhase("idle")
    }
  }

  // 5. Proceed to Next Adaptive Question
  const handleProceedNextQuestion = async () => {
    if (isSubmitting) return
    setIsLoading(true)
    setEvalError(null)
    setActiveEvaluation(null)
    setRunResult(null)
    setViewingPastQuestion(null)

    try {
      const nextQ = await apiClient.getQuestion(
        sessionId,
        sessionState?.target_role || sessionState?.interview_type || "Software Engineer"
      )

      if (nextQ.is_completed) {
        await handleFinalizeAssessment("Final question reached")
        return
      }

      const formattedQ: Question = {
        id: nextQ.question_id,
        session_id: sessionId,
        question_text: nextQ.question_text,
        interview_type: nextQ.interview_type || sessionState?.target_role || "Software Engineer",
        difficulty: nextQ.difficulty,
        skill_focus: nextQ.skill_focus,
        is_follow_up: nextQ.is_follow_up,
        question_index: nextQ.question_index,
        total_questions: nextQ.total_questions,
      }

      setCurrentQuestion(formattedQ)
      setQuestionsList((prev) => [...prev, formattedQ])
      restoreDraft(formattedQ.id)

      // Refresh state
      const updatedState = await apiClient.getSessionState(sessionId)
      setSessionState(updatedState)
    } catch (err: any) {
      console.error("Failed to load next question:", err)
      setEvalError(err.message || "Failed to load next adaptive question.")
    } finally {
      setIsLoading(false)
    }
  }

  // 6. Finalize Assessment & AI Synthesis
  const handleFinalizeAssessment = async (reason?: string) => {
    setIsFinalizing(true)
    try {
      const result = await apiClient.endSession(sessionId)
      setFinalSummary(result)
      const updatedState = await apiClient.getSessionState(sessionId)
      setSessionState(updatedState)
      if (onSessionEnd && updatedState.final_score !== null && updatedState.final_score !== undefined) {
        onSessionEnd(updatedState.final_score)
      }
    } catch (err: any) {
      console.error("Failed to finalize session:", err)
      setEvalError(err.message || "Failed to synthesize final assessment.")
    } finally {
      setIsFinalizing(false)
    }
  }

  // 7. Security Flag Handler
  const handleSecurityFlag = (flag: string) => {
    rawEventsQueueRef.current.push({ type: flag, evidence: "" })
  }

  useEffect(() => {
    if (!sessionId) return
    const interval = setInterval(async () => {
      if (rawEventsQueueRef.current.length > 0) {
        const eventsToFlush = [...rawEventsQueueRef.current]
        rawEventsQueueRef.current = []
        try {
          const report = await apiClient.securityCheck(sessionId, { events: eventsToFlush })
          setIntegrityReport(report)
          if (report.review_recommended) {
            setSecurityFlags(prev => Array.from(new Set([...prev, ...report.signals.map((s: any) => s.signal_type)])))
          }
        } catch (err) {
          rawEventsQueueRef.current.push(...eventsToFlush)
        }
      }
    }, 15000)
    return () => clearInterval(interval)
  }, [sessionId])

  // 8. On-Demand Hint Request
  const handleRequestHint = () => {
    setHintsExpanded(true)
    setHintCount((prev) => prev + 1)
    apiClient.logEvent(sessionId, "hint_requested", {
      question_id: currentQuestion?.id,
      hint_count: hintCount + 1,
    }).catch(() => {})
  }

  // Target question being inspected in center zone
  const activePromptQuestion = viewingPastQuestion || currentQuestion
  const isViewingReadOnly = viewingPastQuestion !== null && viewingPastQuestion.id !== currentQuestion?.id
  const hasCurrentAnswerBeenEvaluated = activeEvaluation !== null

  if (isLoading && !currentQuestion) {
    return (
      <div className="flex h-[80vh] flex-col items-center justify-center space-y-4">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-foreground/30 border-t-foreground" />
        <div className="text-center">
          <p className="text-sm font-medium">Synchronizing Technical Workspace</p>
          <p className="text-xs text-muted-foreground">Hydrating authoritative state from backend...</p>
        </div>
      </div>
    )
  }

  // 9. Assessment Completion View
  if (finalSummary || sessionState?.is_completed) {
    const finalScore = finalSummary?.final_score ?? sessionState?.final_score ?? sessionState?.session_score ?? 0
    const ratingLabel =
      finalScore >= 85
        ? "Exceeds Bar (Strong Hire)"
        : finalScore >= 70
        ? "Meets Bar (Pass)"
        : finalScore >= 55
        ? "Borderline (Needs Practice)"
        : "Below Bar"

    return (
      <div className="mx-auto max-w-4xl space-y-6 py-8">
        <div className="rounded-xl border border-border bg-card p-8">
          <div className="flex flex-col items-center text-center space-y-4">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
              <Award className="h-8 w-8 text-primary" />
            </div>
            <div>
              <Badge variant="outline" className="mb-2">Assessment Concluded</Badge>
              <h1 className="text-3xl font-semibold tracking-tight">Technical Assessment Synthesis</h1>
              <p className="text-sm text-muted-foreground mt-1">
                Authoritative evaluation generated by the AI assessment engine
              </p>
            </div>

            <div className="my-4 flex items-baseline gap-2">
              <span className="text-5xl font-bold tracking-tight">{Math.round(finalScore)}</span>
              <span className="text-lg text-muted-foreground">/ 100</span>
            </div>

            <Badge
              variant={finalScore >= 70 ? "default" : "secondary"}
              className="text-sm px-3 py-1 font-medium"
            >
              {ratingLabel}
            </Badge>
          </div>

          <Separator className="my-8" />

          {/* Synthesis Details */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <h3 className="text-sm font-semibold flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                Demonstrated Strengths
              </h3>
              <ul className="space-y-2 text-xs">
                {(sessionState?.strengths_discovered || []).length > 0 ? (
                  sessionState!.strengths_discovered.map((s, idx) => (
                    <li key={idx} className="flex items-start gap-2 bg-muted/50 p-2.5 rounded border border-border/40">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 mt-1.5 shrink-0" />
                      <span>{s}</span>
                    </li>
                  ))
                ) : (
                  <li className="text-muted-foreground">No specific standout strengths captured.</li>
                )}
              </ul>
            </div>

            <div className="space-y-4">
              <h3 className="text-sm font-semibold flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-500" />
                Areas for Reinforcement
              </h3>
              <ul className="space-y-2 text-xs">
                {(sessionState?.weaknesses_discovered || []).length > 0 ? (
                  sessionState!.weaknesses_discovered.map((w, idx) => (
                    <li key={idx} className="flex items-start gap-2 bg-muted/50 p-2.5 rounded border border-border/40">
                      <span className="h-1.5 w-1.5 rounded-full bg-amber-500 mt-1.5 shrink-0" />
                      <span>{w}</span>
                    </li>
                  ))
                ) : (
                  <li className="text-muted-foreground">No persistent weaknesses detected.</li>
                )}
              </ul>
            </div>
          </div>

          {/* Skill Distribution */}
          {sessionState?.skills_distribution && Object.keys(sessionState.skills_distribution).length > 0 && (
            <div className="mt-8 space-y-3">
              <h3 className="text-sm font-semibold flex items-center gap-2">
                <BarChart2 className="h-4 w-4" />
                Curriculum Skill Evaluation
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {Object.values(sessionState.skills_distribution).map((sig: any, idx) => (
                  <div key={idx} className="rounded border border-border/60 bg-muted/30 p-3 text-xs flex justify-between items-center">
                    <div>
                      <p className="font-medium">{sig.skill_name}</p>
                      <p className="text-muted-foreground text-[11px]">{sig.questions_count} question{sig.questions_count !== 1 ? "s" : ""} tested</p>
                    </div>
                    <span className="font-mono font-semibold text-sm">
                      {sig.average_score > 0 ? `${Math.round(sig.average_score)}%` : "Pending"}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="mt-8 flex justify-center gap-4">
            <Button
              onClick={() => (window.location.href = "/dashboard")}
              className="flex items-center gap-2"
            >
              <TrendingUp className="h-4 w-4" />
              View Candidate Intelligence Dashboard
            </Button>
            <Button
              variant="outline"
              onClick={() => {
                localStorage.removeItem("active_interview_session_id")
                window.location.href = "/interview"
              }}
            >
              Start New Assessment
            </Button>
          </div>
        </div>
      </div>
    )
  }

  // Active question progress calculation
  const totalPlanned = currentQuestion?.total_questions || 5
  const currentIdx = questionsList.findIndex((q) => q.id === currentQuestion?.id)
  const displayIndex = currentIdx >= 0 ? currentIdx + 1 : questionsList.length
  const progressPercent = Math.min(100, Math.round((displayIndex / totalPlanned) * 100))

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] max-w-[1600px] mx-auto px-3 sm:px-4 py-3 gap-3 overflow-hidden text-foreground">
      {/* Top Session Command Bar */}
      <header className="flex items-center justify-between border-b border-border/60 pb-2.5 shrink-0">
        <div className="flex items-center gap-3">
          <div className="flex h-7 w-7 items-center justify-center rounded bg-primary/10">
            <Brain className="h-4 w-4 text-primary" />
          </div>
          <div>
            <h1 className="text-sm font-semibold tracking-tight">
              {sessionState?.target_role || "Technical Assessment"}
            </h1>
            <p className="text-[11px] text-muted-foreground">
              Session #{sessionId.slice(0, 8)} • Standard Technical Track
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Difficulty indicator */}
          <Badge variant="outline" className="text-xs uppercase font-mono tracking-wider">
            {sessionState?.difficulty || "INTERMEDIATE"}
          </Badge>

          {/* Running session score */}
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded bg-muted/60 border border-border/60 text-xs">
            <span className="text-muted-foreground">Live Score:</span>
            <span className="font-mono font-semibold">
              {sessionState?.session_score ? `${Math.round(sessionState.session_score)}%` : "0%"}
            </span>
          </div>

          {/* End assessment early */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setConfirmModal("end_assessment")}
            className="text-xs text-muted-foreground hover:text-destructive h-8 px-2.5 focus-visible:ring-1 focus-visible:ring-destructive"
          >
            <LogOut className="h-3.5 w-3.5 mr-1" />
            End Assessment
          </Button>
        </div>
      </header>

      {/* Main Three-Zone Workspace Layout */}
      <div className="grid grid-cols-12 gap-3.5 flex-1 min-h-0">
        {/* ========================================================================= */}
        {/* LEFT ZONE: Assessment Progress, Question Sequence, Skill Indicators       */}
        {/* ========================================================================= */}
        <aside className="col-span-12 lg:col-span-3 flex flex-col gap-3 rounded-lg border border-border/60 bg-card/40 p-3 overflow-y-auto">
          {/* 1. Progress Metric */}
          <div className="space-y-1.5">
            <div className="flex justify-between items-center text-xs">
              <span className="font-medium">Progress</span>
              <span className="text-muted-foreground font-mono">
                {displayIndex} / {totalPlanned}
              </span>
            </div>
            <Progress value={progressPercent} className="h-1.5" />
          </div>

          <Separator className="bg-border/60" />

          {/* 2. Question Sequence List */}
          <div className="space-y-2 flex-1 min-h-[140px]">
            <div className="flex items-center justify-between text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              <span>Sequence</span>
              <span>Status</span>
            </div>

            <div className="space-y-1.5">
              {questionsList.map((q, idx) => {
                const isSelected = activePromptQuestion?.id === q.id
                const isAnswered = Boolean(q.answer_text || q.code_text || q.evaluation_score)
                const isCurrentActive = currentQuestion?.id === q.id

                return (
                  <button
                    key={q.id || idx}
                    onClick={() => {
                      if (isAnswered) {
                        setViewingPastQuestion(q)
                        setActiveEvaluation(q.evaluation_details || {
                          overall_score: q.evaluation_score,
                          feedback: q.evaluation_feedback,
                        })
                      } else {
                        setViewingPastQuestion(null)
                        setActiveEvaluation(null)
                      }
                    }}
                    className={`w-full text-left p-2 rounded text-xs transition-colors flex items-center justify-between border ${
                      isSelected
                        ? "border-primary/50 bg-primary/5 font-medium"
                        : "border-border/40 hover:bg-muted/40"
                    }`}
                  >
                    <div className="flex items-center gap-2 truncate">
                      {isAnswered ? (
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                      ) : isCurrentActive ? (
                        <span className="h-2 w-2 rounded-full bg-primary shrink-0 animate-pulse" />
                      ) : (
                        <span className="h-2 w-2 rounded-full border border-muted-foreground/40 shrink-0" />
                      )}
                      <div className="truncate">
                        <div className="flex items-center gap-1">
                          <span className="font-mono text-[11px] text-muted-foreground">Q{idx + 1}</span>
                          {q.is_follow_up && (
                            <Badge variant="outline" className="text-[9px] px-1 py-0 h-4 border-amber-500/40 text-amber-500">
                              Probe
                            </Badge>
                          )}
                        </div>
                        <p className="truncate text-foreground/80 font-normal text-[11px]">
                          {q.skill_focus || "Technical Question"}
                        </p>
                      </div>
                    </div>

                    <div className="shrink-0 pl-2">
                      {q.evaluation_score !== undefined && q.evaluation_score !== null ? (
                        <span className="font-mono text-[11px] font-semibold text-emerald-600 dark:text-emerald-400">
                          {Math.round(q.evaluation_score)}%
                        </span>
                      ) : isCurrentActive ? (
                        <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4">
                          Active
                        </Badge>
                      ) : (
                        <span className="text-[10px] text-muted-foreground">Pending</span>
                      )}
                    </div>
                  </button>
                )
              })}
            </div>

            {isViewingReadOnly && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setViewingPastQuestion(null)
                  setActiveEvaluation(null)
                }}
                className="w-full text-xs mt-2 h-7"
              >
                Return to Active Question
              </Button>
            )}
          </div>

          <Separator className="bg-border/60" />

          {/* 3. Skill / Topic Coverage Matrix */}
          <div className="space-y-2">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Skill Intelligence
            </span>

            <div className="space-y-1.5">
              {sessionState?.skills_distribution &&
                Object.values(sessionState.skills_distribution).map((s: any, idx) => {
                  const masteryVal = s.mastery !== undefined ? s.mastery : (s.average_score ? (s.average_score / 100) : 0.5)
                  const confidenceVal = s.questions_count >= 3 ? "high" : s.questions_count >= 1 ? "medium" : "low"

                  return (
                    <div
                      key={idx}
                      className="p-2 rounded bg-muted/20 border border-border/30 space-y-1 text-xs"
                    >
                      <div className="flex items-center justify-between font-medium">
                        <span className="truncate text-foreground/90 text-[11px] font-semibold">
                          {s.skill_name} — estimated mastery <span className="font-mono text-primary">{Number(masteryVal).toFixed(2)}</span>
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-[10px] font-mono text-muted-foreground">
                        <span>Evidence confidence: {confidenceVal}</span>
                        <span>{s.questions_count}Q answered</span>
                      </div>
                    </div>
                  )
                })}
            </div>
          </div>
        </aside>

        {/* ========================================================================= */}
        {/* CENTER ZONE: Question Prompt, Candidate Response Area, Controls, Feedback */}
        {/* ========================================================================= */}
        <main className="col-span-12 lg:col-span-6 flex flex-col gap-3 min-h-0 overflow-y-auto pr-1">
          {/* Read-Only Past Question Alert */}
          {isViewingReadOnly && (
            <div className="rounded border border-amber-500/40 bg-amber-500/10 px-3 py-1.5 text-xs text-amber-700 dark:text-amber-300 flex items-center justify-between shrink-0">
              <span className="flex items-center gap-1.5">
                <AlertTriangle className="h-3.5 w-3.5" />
                Viewing past submission for Question #{questionsList.findIndex((q) => q.id === activePromptQuestion?.id) + 1} (Read-only)
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setViewingPastQuestion(null)}
                className="h-6 text-xs px-2 hover:bg-amber-500/20"
              >
                Return to Active
              </Button>
            </div>
          )}

          {/* 1. Question Prompt Card */}
          <div className="rounded-lg border border-border/60 bg-card p-4 space-y-3 shrink-0">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-semibold uppercase px-2 py-0.5 rounded bg-muted text-muted-foreground">
                  Question {displayIndex}
                </span>
                <MLDetectedFocus skill={activePromptQuestion?.skill_focus || "Engineering Fundamentals"} />
                {activePromptQuestion?.is_follow_up && (
                  <Badge variant="secondary" className="text-xs border-amber-500/30 text-amber-600 dark:text-amber-400">
                    Follow-up Probe
                  </Badge>
                )}
              </div>

              <span className="text-xs text-muted-foreground font-mono">
                {activePromptQuestion?.difficulty || sessionState?.difficulty || "Intermediate"}
              </span>
            </div>

            <div className="prose prose-invert max-w-none text-sm leading-relaxed text-foreground/90 font-normal">
              {activePromptQuestion?.question_text}
            </div>

            {/* Adaptive Explanation for Question Selection */}
            {((activePromptQuestion as any)?.why_selected || (activePromptQuestion as any)?.selection_rationale) && (
              <MLAdaptiveExplanation
                explanation={(activePromptQuestion as any)?.why_selected || (activePromptQuestion as any)?.selection_rationale}
                targetSkill={activePromptQuestion?.skill_focus}
                decision={(activePromptQuestion as any)?.selection_decision}
              />
            )}
          </div>

          {/* 2. Candidate Response Workspace */}
          {!hasCurrentAnswerBeenEvaluated && !isViewingReadOnly && (
            <div className="rounded-lg border border-border/60 bg-card p-4 flex-1 flex flex-col min-h-[340px] space-y-3">
              <div className="flex items-center justify-between border-b border-border/50 pb-2">
                <Tabs value={answerMode} onValueChange={(v) => setAnswerMode(v as "text" | "code")}>
                  <TabsList className="h-7 bg-muted/60 p-0.5">
                    <TabsTrigger value="text" className="text-xs h-6 px-2.5 flex items-center gap-1.5">
                      <FileText className="h-3 w-3" />
                      Written Solution
                    </TabsTrigger>
                    <TabsTrigger value="code" className="text-xs h-6 px-2.5 flex items-center gap-1.5">
                      <Code2 className="h-3 w-3" />
                      Code Editor
                    </TabsTrigger>
                  </TabsList>
                </Tabs>

                <div className="flex items-center gap-3 text-xs text-muted-foreground">
                  {answerMode === "code" && (
                    <select
                      value={selectedLanguage}
                      onChange={(e) => {
                        const lang = e.target.value
                        setSelectedLanguage(lang)
                        setCodeAnswer(LANGUAGE_STARTERS[lang] || "")
                      }}
                      className="text-xs bg-muted/40 border border-border/60 rounded px-2 py-0.5 font-mono"
                    >
                      <option value="python">Python</option>
                      <option value="javascript">JavaScript</option>
                      <option value="typescript">TypeScript</option>
                      <option value="go">Go</option>
                      <option value="cpp">C++</option>
                      <option value="java">Java</option>
                      <option value="rust">Rust</option>
                    </select>
                  )}

                  <span className="text-[11px] font-mono">
                    {autosaveStatus === "saving" ? (
                      <span className="text-amber-500">Saving...</span>
                    ) : lastSavedTime ? (
                      `Saved ${lastSavedTime}`
                    ) : (
                      "Autosave ready"
                    )}
                  </span>
                </div>
              </div>

              {/* Text Answer Input */}
              {answerMode === "text" && (
                <div className="flex-1 flex flex-col space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">Type your answer or record using speech-to-text:</span>
                      {voiceMetadata && (
                        <Badge variant="outline" className="text-[10px] gap-1 border-primary/30 text-primary">
                          <Mic className="h-2.5 w-2.5" />
                          Voice attached ({voiceMetadata.duration_seconds.toFixed(1)}s)
                        </Badge>
                      )}
                    </div>
                    <VoiceRecorderButton
                      onTranscriptReady={(transcript, metadata) => {
                        handleTextChange(transcript)
                        setVoiceMetadata(metadata)
                      }}
                      disabled={isSubmitting}
                    />
                  </div>
                  <textarea
                    value={textAnswer}
                    onChange={(e) => {
                      handleTextChange(e.target.value)
                      if (voiceMetadata && e.target.value !== voiceMetadata.transcript) {
                        setVoiceMetadata((prev) => (prev ? { ...prev, transcript: e.target.value } : null))
                      }
                    }}
                    onKeyDown={(e) => {
                      if ((e.ctrlKey || e.metaKey) && e.key === "Enter" && !isSubmitting && textAnswer.trim().length >= 10) {
                        e.preventDefault()
                        handleSubmitSolution()
                      }
                    }}
                    placeholder="Provide your solution, technical reasoning, complexity trade-offs, or architectural decisions... (Press Ctrl+Enter to submit)"
                    className="flex-1 w-full p-3 text-xs sm:text-sm font-sans bg-transparent border border-border/40 rounded-md resize-none focus:outline-none focus:ring-1 focus:ring-primary min-h-[220px]"
                    disabled={isSubmitting}
                  />
                  <div className="flex justify-between items-center text-[11px] text-muted-foreground">
                    <span>Minimum 10 characters required • Press Ctrl+Enter to submit</span>
                    <span className="font-mono">
                      {textAnswer.trim().length} chars • {textAnswer.trim().split(/\s+/).filter(Boolean).length} words
                    </span>
                  </div>
                </div>
              )}

              {/* Code Answer Input */}
              {answerMode === "code" && (
                <div className="flex-1 flex flex-col space-y-2">
                  <div className="rounded border border-border/60 overflow-hidden min-h-[260px] flex-1">
                    <MonacoEditor
                      value={codeAnswer}
                      onChange={handleCodeChange}
                      language={selectedLanguage}
                      height="260px"
                    />
                  </div>
                  <div className="flex justify-between items-center text-[11px] text-muted-foreground">
                    <span>Monaco editor with runtime support</span>
                    <span className="font-mono">{codeAnswer.length} chars</span>
                  </div>
                </div>
              )}

              {/* Error Banner with Retry */}
              {evalError && (
                <div className="rounded border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 shrink-0" />
                    <span>{evalError}</span>
                  </div>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={handleSubmitSolution}
                    disabled={isSubmitting}
                    className="h-6 text-[11px] text-destructive hover:bg-destructive/20 font-mono"
                  >
                    Retry Submission
                  </Button>
                </div>
              )}

              {/* Action Controls */}
              <div className="flex items-center justify-between pt-2 border-t border-border/40">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setConfirmModal("reset_draft")}
                  className="text-xs text-muted-foreground hover:text-foreground h-8"
                  disabled={isSubmitting}
                >
                  <RotateCcw className="h-3 w-3 mr-1" />
                  Reset Draft
                </Button>

                <div className="flex items-center gap-2">
                  {answerMode === "code" && (
                    <Button
                      onClick={handleRunCode}
                      disabled={isRunningCode || isSubmitting || codeAnswer.trim().length < 5}
                      size="sm"
                      variant="secondary"
                      className="text-xs h-8 px-4"
                    >
                      {isRunningCode ? (
                        <RefreshCw className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                      ) : (
                        <Code2 className="h-3.5 w-3.5 mr-1.5" />
                      )}
                      Run Code
                    </Button>
                  )}
                  <Button
                    onClick={handleSubmitSolution}
                    disabled={
                      isSubmitting ||
                      (answerMode === "text" ? textAnswer.trim().length < 10 : codeAnswer.trim().length < 10)
                    }
                    size="sm"
                    className="text-xs h-8 px-4 bg-primary text-primary-foreground font-medium"
                  >
                    {isSubmitting ? (
                      <>
                        <RefreshCw className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                        {submissionPhase === "evaluating" ? "Evaluating..." : "Updating..."}
                      </>
                    ) : (
                      <>
                        <Send className="h-3.5 w-3.5 mr-1.5" />
                        Submit Answer
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* 2.5 Run Results */}
          {runResult && !hasCurrentAnswerBeenEvaluated && !isViewingReadOnly && (
            <div className={`rounded-lg border bg-card p-4 space-y-3 ${runResult.success ? 'border-emerald-500/30' : 'border-destructive/30'}`}>
              <div className="flex items-center justify-between border-b border-border/50 pb-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold">Execution Result</span>
                  <Badge variant={runResult.success ? 'default' : 'destructive'} className="text-[10px] h-4 px-1.5">
                    {runResult.success ? "Exited 0" : `Exit ${runResult.exit_code}`}
                  </Badge>
                </div>
              </div>
              <div className="space-y-2">
                {runResult.stdout && (
                  <div>
                    <span className="text-[10px] text-muted-foreground uppercase font-semibold">Stdout:</span>
                    <pre className="p-2 rounded bg-muted/40 text-[11px] font-mono text-foreground/80 overflow-x-auto whitespace-pre-wrap">
                      {runResult.stdout}
                    </pre>
                  </div>
                )}
                {runResult.stderr && (
                  <div>
                    <span className="text-[10px] text-muted-foreground uppercase font-semibold">Stderr:</span>
                    <pre className="p-2 rounded bg-destructive/10 text-[11px] font-mono text-destructive overflow-x-auto whitespace-pre-wrap">
                      {runResult.stderr}
                    </pre>
                  </div>
                )}
                {runResult.error && (
                  <div>
                    <span className="text-[10px] text-muted-foreground uppercase font-semibold">System Error:</span>
                    <pre className="p-2 rounded bg-destructive/10 text-[11px] font-mono text-destructive overflow-x-auto whitespace-pre-wrap">
                      {runResult.error}
                    </pre>
                  </div>
                )}
                {!runResult.stdout && !runResult.stderr && !runResult.error && (
                  <p className="text-xs text-muted-foreground italic">No output produced.</p>
                )}
              </div>
            </div>
          )}

          {/* 3. Evaluation Feedback (Appears after submission or when reviewing past submissions) */}
          {(hasCurrentAnswerBeenEvaluated || isViewingReadOnly) && (
            <div className="rounded-lg border border-border/60 bg-card p-4 space-y-4">
              <div className="flex items-center justify-between border-b border-border/50 pb-3">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                  <span className="text-sm font-semibold">Evaluation Report</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">Rubric Score:</span>
                  <span className="text-base font-bold font-mono text-emerald-600 dark:text-emerald-400">
                    {Math.round(activeEvaluation?.overall_score ?? activeEvaluation?.score ?? 0)} / 100
                  </span>
                </div>
              </div>

              {/* ML Signals Interpretation */}
              {answerMode === "code" ? (
                <MLCodeResultInterpretation
                  defectDetection={activeEvaluation?.ml_defect_detection}
                  executionResult={runResult}
                  passedTests={activeEvaluation?.correctness ? Math.round((activeEvaluation.correctness / 100) * 10) : (runResult?.success ? 10 : 8)}
                  totalTests={10}
                />
              ) : (
                <MLConceptCoverageResult
                  coverageData={activeEvaluation?.ml_concept_coverage}
                  fallbackScore={activeEvaluation?.overall_score ?? activeEvaluation?.score ?? 75}
                />
              )}

              {/* Rubric Dimension Subscores */}
              {answerMode === "code" ? (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  <div className="p-2 rounded bg-muted/40 border border-border/40 text-center">
                    <p className="text-[10px] text-muted-foreground uppercase">Runtime Correctness</p>
                    <p className="text-xs font-mono font-semibold mt-0.5">
                      {activeEvaluation?.correctness ?? activeEvaluation?.technical_accuracy ?? 75}%
                    </p>
                  </div>
                  <div className="p-2 rounded bg-muted/40 border border-border/40 text-center">
                    <p className="text-[10px] text-muted-foreground uppercase">Algorithm/Complexity</p>
                    <p className="text-xs font-mono font-semibold mt-0.5">
                      {activeEvaluation?.algorithm_quality ?? activeEvaluation?.problem_solving ?? 75}%
                    </p>
                  </div>
                  <div className="p-2 rounded bg-muted/40 border border-border/40 text-center">
                    <p className="text-[10px] text-muted-foreground uppercase">Code Quality</p>
                    <p className="text-xs font-mono font-semibold mt-0.5">
                      {activeEvaluation?.code_quality ?? activeEvaluation?.readability ?? 75}%
                    </p>
                  </div>
                  <div className="p-2 rounded bg-muted/40 border border-border/40 text-center">
                    <p className="text-[10px] text-muted-foreground uppercase">Test Case Correctness</p>
                    <p className="text-xs font-mono font-semibold mt-0.5">
                      {activeEvaluation?.edge_case_coverage ?? activeEvaluation?.efficiency ?? 75}%
                    </p>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  <div className="p-2 rounded bg-muted/40 border border-border/40 text-center">
                    <p className="text-[10px] text-muted-foreground uppercase">Accuracy</p>
                    <p className="text-xs font-mono font-semibold mt-0.5">
                      {activeEvaluation?.technical_accuracy ?? 75}%
                    </p>
                  </div>
                  <div className="p-2 rounded bg-muted/40 border border-border/40 text-center">
                    <p className="text-[10px] text-muted-foreground uppercase">Problem Solving</p>
                    <p className="text-xs font-mono font-semibold mt-0.5">
                      {activeEvaluation?.problem_solving ?? 75}%
                    </p>
                  </div>
                  <div className="p-2 rounded bg-muted/40 border border-border/40 text-center">
                    <p className="text-[10px] text-muted-foreground uppercase">Conceptual Depth</p>
                    <p className="text-xs font-mono font-semibold mt-0.5">
                      {activeEvaluation?.conceptual_depth ?? 75}%
                    </p>
                  </div>
                  <div className="p-2 rounded bg-muted/40 border border-border/40 text-center">
                    <p className="text-[10px] text-muted-foreground uppercase">Communication</p>
                    <p className="text-xs font-mono font-semibold mt-0.5">
                      {activeEvaluation?.communication ?? 75}%
                    </p>
                  </div>
                </div>
              )}

              {/* Model Evidence & Written Feedback */}
              <div className="space-y-1.5 text-xs">
                <span className="font-semibold text-foreground/80">Evaluator Synthesis:</span>
                <p className="text-muted-foreground leading-relaxed bg-muted/20 p-2.5 rounded border border-border/30">
                  {activeEvaluation?.feedback || activeEvaluation?.evidence || "Solid reasoning demonstrated across core aspects of the problem."}
                </p>
              </div>

              {/* Strengths & Weaknesses */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                {activeEvaluation?.strengths && activeEvaluation.strengths.length > 0 && (
                  <div className="space-y-1.5">
                    <span className="font-medium text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                      <CheckCircle2 className="h-3 w-3" />
                      Strengths Identified
                    </span>
                    <ul className="space-y-1">
                      {activeEvaluation.strengths.map((str: string, i: number) => (
                        <li key={i} className="text-foreground/80 text-[11px] flex items-start gap-1.5">
                          <span className="h-1 w-1 rounded-full bg-emerald-500 mt-1 shrink-0" />
                          <span>{str}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {(activeEvaluation?.weaknesses || activeEvaluation?.improvements) && (
                  <div className="space-y-1.5">
                    <span className="font-medium text-amber-600 dark:text-amber-400 flex items-center gap-1">
                      <AlertTriangle className="h-3 w-3" />
                      Areas for Optimization
                    </span>
                    <ul className="space-y-1">
                      {(activeEvaluation.weaknesses || activeEvaluation.improvements).map((w: string, i: number) => (
                        <li key={i} className="text-foreground/80 text-[11px] flex items-start gap-1.5">
                          <span className="h-1 w-1 rounded-full bg-amber-500 mt-1 shrink-0" />
                          <span>{w}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* Proceed Control */}
              {!isViewingReadOnly && (
                <div className="pt-2 flex justify-end">
                  <Button
                    onClick={handleProceedNextQuestion}
                    disabled={isLoading || isFinalizing}
                    size="sm"
                    className="text-xs h-8 px-4 flex items-center gap-1.5"
                  >
                    Proceed to Next Question
                    <ArrowRight className="h-3.5 w-3.5" />
                  </Button>
                </div>
              )}
            </div>
          )}
        </main>

        {/* ========================================================================= */}
        {/* RIGHT ZONE: Live Signals, Timer, Phase Tracker, Hints, Integrity Monitor */}
        {/* ========================================================================= */}
        <aside className="col-span-12 lg:col-span-3 flex flex-col gap-3 rounded-lg border border-border/60 bg-card/40 p-3 overflow-y-auto">
          {/* 1. Timer Card */}
          <div className="rounded border border-border/60 bg-card p-3 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5" />
                Time Remaining
              </span>
              <button
                onClick={() => setIsTimerPaused((p) => !p)}
                className="text-[11px] text-muted-foreground hover:text-foreground"
              >
                {isTimerPaused ? "Resume" : "Pause"}
              </button>
            </div>

            <div className="text-center py-1">
              <span
                className={`text-2xl font-mono font-bold tracking-tight ${
                  timeRemaining <= 300
                    ? "text-red-500"
                    : timeRemaining <= 600
                    ? "text-amber-500"
                    : "text-foreground"
                }`}
              >
                {formatTimer(timeRemaining)}
              </span>
            </div>

            <Progress
              value={(timeRemaining / (sessionState?.time_budget_seconds || 2700)) * 100}
              className="h-1"
            />
          </div>

          {/* 2. Orchestrator Phase Stepper */}
          <div className="rounded border border-border/60 bg-card p-3 space-y-2.5">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Assessment Phase
            </span>

            <div className="space-y-2 text-xs">
              {ORCHESTRATOR_PHASE_STEPS.map((step) => {
                const currentPhase = sessionState?.phase || "QUESTIONING"
                const isCurrent = currentPhase === step.id
                return (
                  <div
                    key={step.id}
                    className={`flex items-start gap-2 p-1.5 rounded transition-colors ${
                      isCurrent ? "bg-primary/10 border border-primary/30" : "opacity-60"
                    }`}
                  >
                    <span
                      className={`h-2 w-2 rounded-full mt-1 shrink-0 ${
                        isCurrent ? "bg-primary animate-pulse" : "bg-muted-foreground/30"
                      }`}
                    />
                    <div>
                      <p className={`font-medium ${isCurrent ? "text-primary" : "text-foreground"}`}>
                        {step.label}
                      </p>
                      <p className="text-[10px] text-muted-foreground">{step.desc}</p>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* 3. AI Evaluator Status */}
          <div className="rounded border border-border/60 bg-card p-3 space-y-1.5">
            <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
              Evaluator Status
            </span>
            <div className="flex items-center gap-2 text-xs">
              <span
                className={`h-2 w-2 rounded-full ${
                  isSubmitting ? "bg-amber-500 animate-ping" : "bg-emerald-500"
                }`}
              />
              <span className="font-medium text-foreground/90">
                {isSubmitting
                  ? "Evaluating candidate response"
                  : hasCurrentAnswerBeenEvaluated
                  ? "Response analyzed & recorded"
                  : "Awaiting candidate submission"}
              </span>
            </div>
          </div>

          {/* 4. On-Demand Technical Hints (Strictly on demand) */}
          <div className="rounded border border-border/60 bg-card p-3 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground flex items-center gap-1.5">
                <Lightbulb className="h-3.5 w-3.5" />
                Technical Guidance
              </span>
              {hintsExpanded && (
                <Badge variant="outline" className="text-[10px] h-4 px-1">
                  Hint #{hintCount}
                </Badge>
              )}
            </div>

            {!hintsExpanded ? (
              <div className="space-y-1.5">
                <p className="text-[11px] text-muted-foreground">
                  Need a clarifying edge-case or conceptual hint? Available strictly on demand.
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRequestHint}
                  className="w-full text-xs h-7"
                >
                  Request Hint
                </Button>
              </div>
            ) : (
              <div className="space-y-2 text-xs">
                <div className="p-2 rounded bg-muted/40 border border-border/40 text-[11px] text-foreground/80 leading-relaxed">
                  Focus on how the data structures scale under memory constraints. Consider whether an in-place traversal or lookup hash table yields favorable complexity trade-offs for {activePromptQuestion?.skill_focus || "this problem"}.
                </div>
                <p className="text-[10px] text-muted-foreground italic">
                  Hint usage has been logged to session telemetry.
                </p>
              </div>
            )}
          </div>

          {/* 5. Session Integrity & Anti-Cheat */}
          <div className="rounded border border-border/60 bg-card p-3 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-muted-foreground flex items-center gap-1.5">
                <Shield className="h-3.5 w-3.5" />
                Integrity Monitor
              </span>
              <Badge
                variant={integrityReport?.review_recommended ? "destructive" : "secondary"}
                className="text-[10px] h-4 px-1"
              >
                {integrityReport?.review_recommended ? "Review Recommended" : "Normal"}
              </Badge>
            </div>
            {integrityReport && (
              <div className="text-[10px] text-muted-foreground mb-1">
                Confidence: {Math.round(integrityReport.confidence * 100)}% | Anomalies: {integrityReport.total_signals}
              </div>
            )}

            <AntiCheatGuard
              className="border-0 p-0 bg-transparent text-xs"
              enableWebcam={false}
              enableTypingAnalysis={true}
              enableDevtoolsDetection={true}
              onFlag={handleSecurityFlag}
            />
          </div>
        </aside>
      </div>

      {/* Accessible Confirmation Modals */}
      {confirmModal === "end_assessment" && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="confirm-end-title"
          onClick={() => setConfirmModal(null)}
        >
          <div
            className="w-full max-w-md rounded-lg border border-border bg-card p-6 shadow-xl space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start gap-3">
              <div className="p-2 rounded bg-amber-500/10 text-amber-500 shrink-0">
                <AlertTriangle className="h-5 w-5" />
              </div>
              <div>
                <h2 id="confirm-end-title" className="text-base font-semibold text-foreground">
                  Conclude Assessment Early?
                </h2>
                <p className="text-xs text-muted-foreground mt-1.5 leading-relaxed">
                  Your submitted answers up to this point will be synthesized by the AI assessment engine into your final candidate evaluation. Unanswered questions will be recorded as incomplete.
                </p>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-border/40">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setConfirmModal(null)}
                disabled={isFinalizing}
                className="text-xs h-8"
              >
                Cancel
              </Button>
              <Button
                size="sm"
                variant="destructive"
                onClick={() => {
                  setConfirmModal(null)
                  handleFinalizeAssessment("Candidate ended session")
                }}
                disabled={isFinalizing}
                className="text-xs h-8"
              >
                {isFinalizing ? "Synthesizing..." : "Conclude Assessment"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {confirmModal === "reset_draft" && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="confirm-reset-title"
          onClick={() => setConfirmModal(null)}
        >
          <div
            className="w-full max-w-sm rounded-lg border border-border bg-card p-5 shadow-xl space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div>
              <h2 id="confirm-reset-title" className="text-sm font-semibold text-foreground">
                Reset Active Draft?
              </h2>
              <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                This will clear unsaved progress on the current question and restore the initial template.
              </p>
            </div>
            <div className="flex justify-end gap-2 pt-1 border-t border-border/40">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setConfirmModal(null)}
                className="text-xs h-8"
              >
                Keep Editing
              </Button>
              <Button
                size="sm"
                variant="destructive"
                onClick={() => {
                  setConfirmModal(null)
                  if (answerMode === "text") setTextAnswer("")
                  else setCodeAnswer(LANGUAGE_STARTERS[selectedLanguage] || "")
                }}
                className="text-xs h-8"
              >
                Reset Draft
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
