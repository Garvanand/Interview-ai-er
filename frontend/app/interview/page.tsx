"use client"

import { useState, useEffect, Suspense } from "react"
import { useSearchParams, useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { InterviewWorkspace } from "@/components/interview/interview-workspace"
import { apiClient } from "@/lib/api-client"
import { getBrowserSupabaseClient } from "@/lib/supabase"
import {
  Brain,
  Shield,
  Clock,
  Code2,
  Database,
  Server,
  Layers,
  Sparkles,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  Cpu,
  BarChart2,
  Terminal,
} from "lucide-react"

const ASSESSMENT_TRACKS = [
  {
    id: "Software Engineer",
    title: "Software Engineering",
    desc: "Algorithms, system architecture, programming fundamentals, and complexity analysis.",
    icon: Terminal,
    skills: ["Data Structures & Algorithms", "System Design", "Problem Solving", "Programming Fundamentals"],
    targetDuration: "45 minutes",
    difficulty: "Adaptive (Intermediate to Expert)",
  },
  {
    id: "Data Scientist",
    title: "Data Science & Machine Learning",
    desc: "Applied statistics, predictive modeling, data pipelines, and quantitative reasoning.",
    icon: BarChart2,
    skills: ["Statistics", "Machine Learning", "Database Concepts", "Problem Solving"],
    targetDuration: "45 minutes",
    difficulty: "Adaptive (Intermediate to Expert)",
  },
  {
    id: "Product Manager",
    title: "Technical Product Management",
    desc: "System trade-offs, technical feasibility, product reasoning, and behavioral judgment.",
    icon: Layers,
    skills: ["Problem Solving", "System Design", "Communication", "Behavioral Reasoning"],
    targetDuration: "40 minutes",
    difficulty: "Adaptive (Intermediate to Expert)",
  },
  {
    id: "DevOps Engineer",
    title: "Cloud & DevOps Engineering",
    desc: "Distributed systems, infrastructure reliability, debugging, and database architecture.",
    icon: Server,
    skills: ["System Design", "Database Concepts", "Debugging", "Problem Solving"],
    targetDuration: "45 minutes",
    difficulty: "Adaptive (Intermediate to Expert)",
  },
]

function InterviewContent() {
  const searchParams = useSearchParams()
  const router = useRouter()

  const [sessionId, setSessionId] = useState<string | null>(null)
  const [selectedTrack, setSelectedTrack] = useState<string>("Software Engineer")
  const [isStarting, setIsStarting] = useState<boolean>(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isCheckingActiveSession, setIsCheckingActiveSession] = useState<boolean>(true)

  // Check for active session in URL or localStorage
  useEffect(() => {
    const urlSessionId = searchParams.get("session_id")
    if (urlSessionId) {
      setSessionId(urlSessionId)
      localStorage.setItem("active_interview_session_id", urlSessionId)
      setIsCheckingActiveSession(false)
      return
    }

    const cachedSessionId = localStorage.getItem("active_interview_session_id")
    if (cachedSessionId) {
      // Validate session state with backend before restoring
      apiClient
        .getSessionState(cachedSessionId)
        .then((state) => {
          if (state && !state.is_completed) {
            setSessionId(cachedSessionId)
          } else {
            localStorage.removeItem("active_interview_session_id")
          }
        })
        .catch(() => {
          localStorage.removeItem("active_interview_session_id")
        })
        .finally(() => {
          setIsCheckingActiveSession(false)
        })
    } else {
      setIsCheckingActiveSession(false)
    }
  }, [searchParams])

  const handleStartAssessment = async () => {
    setIsStarting(true)
    setErrorMessage(null)

    try {
      let userId = "guest_candidate"

      // Attempt to get authenticated user if available
      try {
        const supabase = getBrowserSupabaseClient()
        if (supabase) {
          const { data: { user } } = await supabase.auth.getUser()
          if (user?.id) userId = user.id
        }
      } catch (authErr) {
        console.warn("Supabase auth skipped, using candidate session:", authErr)
      }

      const response = await apiClient.startSession(userId, selectedTrack)
      const actualSessionId = response?.session_id || response?.data?.session_id

      if (!actualSessionId) {
        throw new Error("Assessment orchestrator failed to return a valid session ID.")
      }

      setSessionId(actualSessionId)
      localStorage.setItem("active_interview_session_id", actualSessionId)

      // Update URL search query
      router.push(`/interview?session_id=${actualSessionId}`)
    } catch (err: any) {
      console.error("Failed to start assessment:", err)
      setErrorMessage(err.message || "Failed to initialize assessment workspace. Ensure backend API is online.")
    } finally {
      setIsStarting(false)
    }
  }

  const handleSessionEnd = (finalScore: number) => {
    localStorage.removeItem("active_interview_session_id")
  }

  if (isCheckingActiveSession) {
    return (
      <div className="flex h-[80vh] flex-col items-center justify-center space-y-4">
        <div className="h-7 w-7 animate-spin rounded-full border-2 border-foreground/30 border-t-foreground" />
        <p className="text-xs text-muted-foreground font-mono">Checking active assessment telemetry...</p>
      </div>
    )
  }

  // Active Live Three-Zone Workspace
  if (sessionId) {
    return <InterviewWorkspace sessionId={sessionId} onSessionEnd={handleSessionEnd} />
  }

  // Pre-Interview Track Selection & Configuration Launcher
  const currentTrackDetails = ASSESSMENT_TRACKS.find((t) => t.id === selectedTrack) || ASSESSMENT_TRACKS[0]

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 space-y-8">
      {/* Assessment Header */}
      <div className="space-y-2 border-b border-border/60 pb-6">
        <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground uppercase tracking-wider">
          <Terminal className="h-3.5 w-3.5" />
          <span>Technical Assessment Environment</span>
        </div>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground">
          Adaptive Technical Interview
        </h1>
        <p className="text-sm text-muted-foreground max-w-2xl leading-relaxed">
          Stateful assessment driven by an adaptive evaluation engine. Evaluates algorithmic depth, system architecture, code quality, and communication rigor in real time.
        </p>
      </div>

      {/* Error Alert */}
      {errorMessage && (
        <div className="rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive flex items-start gap-2">
          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Track Selection Cards */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Select Track
          </h2>
          <span className="text-xs text-muted-foreground font-mono">4 Curricula Available</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {ASSESSMENT_TRACKS.map((track) => {
            const isSelected = selectedTrack === track.id
            const Icon = track.icon
            return (
              <button
                key={track.id}
                onClick={() => setSelectedTrack(track.id)}
                className={`text-left p-4 rounded-lg border transition-all ${
                  isSelected
                    ? "border-primary bg-primary/5 shadow-sm"
                    : "border-border/60 bg-card/60 hover:bg-card hover:border-border"
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2.5">
                    <div
                      className={`flex h-8 w-8 items-center justify-center rounded ${
                        isSelected ? "bg-primary text-primary-foreground" : "bg-muted text-foreground/80"
                      }`}
                    >
                      <Icon className="h-4 w-4" />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold">{track.title}</h3>
                      <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{track.desc}</p>
                    </div>
                  </div>
                  {isSelected && <CheckCircle2 className="h-4 w-4 text-primary shrink-0" />}
                </div>

                <div className="mt-3 flex flex-wrap gap-1">
                  {track.skills.map((skill, idx) => (
                    <span
                      key={idx}
                      className="text-[10px] px-1.5 py-0.5 rounded bg-muted/60 border border-border/40 text-muted-foreground"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </button>
            )
          })}
        </div>
      </div>

      {/* Track Specification & Protocol Checklist */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
        <div className="rounded-lg border border-border/60 bg-card/40 p-4 space-y-2">
          <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase">
            <Clock className="h-3.5 w-3.5 text-primary" />
            <span>Time Budget</span>
          </div>
          <p className="text-xl font-bold font-mono">{currentTrackDetails.targetDuration}</p>
          <p className="text-xs text-muted-foreground">
            Strict timer synchronized with backend orchestrator. Auto-synthesizes on timeout.
          </p>
        </div>

        <div className="rounded-lg border border-border/60 bg-card/40 p-4 space-y-2">
          <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase">
            <Brain className="h-3.5 w-3.5 text-primary" />
            <span>Evaluation Protocol</span>
          </div>
          <p className="text-xl font-bold font-mono">Dynamic Rubric</p>
          <p className="text-xs text-muted-foreground">
            Multi-dimensional evaluation: accuracy, problem solving, depth, and communication.
          </p>
        </div>

        <div className="rounded-lg border border-border/60 bg-card/40 p-4 space-y-2">
          <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase">
            <Shield className="h-3.5 w-3.5 text-primary" />
            <span>Integrity Guard</span>
          </div>
          <p className="text-xl font-bold font-mono">Active Proctoring</p>
          <p className="text-xs text-muted-foreground">
            Tab switch, copy-paste heuristics, and typing telemetry recorded to audit logs.
          </p>
        </div>
      </div>

      {/* Launch Action */}
      <div className="flex flex-col sm:flex-row items-center justify-between border-t border-border/60 pt-6 gap-4">
        <div className="text-xs text-muted-foreground space-y-0.5">
          <p className="font-medium text-foreground">Ready to begin assessment?</p>
          <p>Answers are continuously autosaved locally and authoritative state is backed by Supabase.</p>
        </div>

        <Button
          onClick={handleStartAssessment}
          disabled={isStarting}
          size="lg"
          className="w-full sm:w-auto h-10 px-6 font-medium text-xs flex items-center gap-2"
        >
          {isStarting ? (
            <>
              <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-primary-foreground/30 border-t-primary-foreground" />
              Initializing Orchestrator...
            </>
          ) : (
            <>
              Launch Assessment Workspace
              <ArrowRight className="h-4 w-4" />
            </>
          )}
        </Button>
      </div>
    </div>
  )
}

export default function InterviewPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-[80vh] flex-col items-center justify-center space-y-4">
          <div className="h-7 w-7 animate-spin rounded-full border-2 border-foreground/30 border-t-foreground" />
          <p className="text-xs text-muted-foreground font-mono">Loading technical assessment environment...</p>
        </div>
      }
    >
      <InterviewContent />
    </Suspense>
  )
}
