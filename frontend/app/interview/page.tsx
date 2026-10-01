"use client"

import { useState, useEffect, Suspense } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { apiClient } from "@/lib/api-client"
import { useAuth } from "@/hooks/use-auth"
import {
  Brain,
  Terminal,
  BarChart2,
  Layers,
  Server,
  Compass,
  ArrowRight,
  ShieldCheck,
  Clock,
  Sparkles,
  Loader2,
  CheckCircle2,
  AlertCircle,
  FileCode,
  Sliders,
} from "lucide-react"

const ASSESSMENT_TRACKS = [
  {
    id: "Software Engineer",
    title: "Software Engineering",
    desc: "Data structures, algorithms, runtime complexity, concurrency, and clean modular code.",
    icon: Terminal,
    skills: ["Algorithms", "Data Structures", "System Fundamentals", "Complexity Analysis"],
    format: "Coding & Algorithmic Analysis",
    defaultDifficulty: "intermediate",
  },
  {
    id: "system_design",
    title: "System Design & Architecture",
    desc: "Distributed consensus, caching topologies, partition tolerance, and high-availability patterns.",
    icon: Layers,
    skills: ["Distributed Systems", "Database Partitioning", "CAP Theorem", "Availability"],
    format: "Architecture Breakdown",
    defaultDifficulty: "advanced",
  },
  {
    id: "Data Scientist",
    title: "Data Science & Machine Learning",
    desc: "Statistical inference, loss functions, ML model evaluation, feature engineering, and data pipelines.",
    icon: BarChart2,
    skills: ["Machine Learning", "Statistical Analysis", "Data Modeling", "Model Validation"],
    format: "Technical Case Analysis",
    defaultDifficulty: "intermediate",
  },
  {
    id: "DevOps Engineer",
    title: "Cloud & Reliability Engineering",
    desc: "Container orchestration, incident mitigation, CI/CD pipelines, and infrastructure observability.",
    icon: Server,
    skills: ["Kubernetes", "Observability", "Failover Strategies", "CI/CD Architecture"],
    format: "Scenario Troubleshooting",
    defaultDifficulty: "intermediate",
  },
  {
    id: "behavioral",
    title: "Technical Leadership & Behavioral",
    desc: "Tradeoff negotiation, cross-team conflict resolution, engineering velocity, and mentorship.",
    icon: Compass,
    skills: ["Communication", "Decision Making", "Engineering Values", "Cross-Functional Alignment"],
    format: "Structured STAR Dialogue",
    defaultDifficulty: "intermediate",
  },
]

const DIFFICULTY_LEVELS = [
  { id: "beginner", label: "Entry Level (L3)", desc: "Foundational concepts, clean syntax, core algorithms" },
  { id: "intermediate", label: "Mid / Senior (L4/L5)", desc: "Production tradeoffs, edge-case coverage, optimal complexity" },
  { id: "advanced", label: "Staff / Principal (L6+)", desc: "Deep architectural guarantees, distributed failure modes, scale constraints" },
]

function InterviewConfigContent() {
  const router = useRouter()
  const { userId, isLoading: authLoading, isAuthenticated } = useAuth({ redirectIfUnauthenticated: true })

  const [selectedTrack, setSelectedTrack] = useState<string>("Software Engineer")
  const [selectedDifficulty, setSelectedDifficulty] = useState<string>("intermediate")
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [showDiscardConfirm, setShowDiscardConfirm] = useState<boolean>(false)
  const [isStarting, setIsStarting] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  // Check if an ongoing uncompleted session exists
  useEffect(() => {
    const cachedId = localStorage.getItem("active_interview_session_id")
    if (cachedId) {
      apiClient
        .getSessionState(cachedId)
        .then((state) => {
          if (state && !state.is_completed) {
            setActiveSessionId(cachedId)
          } else {
            localStorage.removeItem("active_interview_session_id")
          }
        })
        .catch(() => {
          localStorage.removeItem("active_interview_session_id")
        })
    }
  }, [])

  // Listen for Escape key to close modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && showDiscardConfirm) {
        setShowDiscardConfirm(false)
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [showDiscardConfirm])

  const handleStartSession = async () => {
    if (!userId) {
      setError("Authentication verified session required.")
      return
    }

    setIsStarting(true)
    setError(null)

    try {
      const result = await apiClient.startSession(userId, selectedTrack)
      const newSessionId = result?.id || result?.session_id
      if (!newSessionId) {
        throw new Error("Session initialization did not return a valid session ID.")
      }

      localStorage.setItem("active_interview_session_id", newSessionId)
      router.push(`/interview/session?session_id=${newSessionId}`)
    } catch (err: any) {
      setError(err?.message || "Failed to initialize interview session.")
      setIsStarting(false)
    }
  }

  if (authLoading) {
    return (
      <div className="flex min-h-[80vh] items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
      </div>
    )
  }

  const currentTrack = ASSESSMENT_TRACKS.find((t) => t.id === selectedTrack) || ASSESSMENT_TRACKS[0]

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Top Banner for Active Session if present */}
      {activeSessionId && (
        <div className="mb-8 rounded-lg border border-blue-300 dark:border-blue-800 bg-blue-50/70 dark:bg-blue-950/40 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center space-x-3">
            <span className="w-2 h-2 rounded-full bg-blue-500 animate-ping" />
            <div>
              <div className="text-xs font-mono font-semibold text-blue-900 dark:text-blue-200">
                ACTIVE SESSION DETECTED
              </div>
              <div className="text-xs text-blue-700 dark:text-blue-300">
                You have an uncompleted interview session ({activeSessionId.slice(0, 8)}...).
              </div>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowDiscardConfirm(true)}
              className="h-8 text-xs font-mono"
            >
              Discard
            </Button>
            <Link href={`/interview/session?session_id=${activeSessionId}`}>
              <Button size="sm" className="h-8 text-xs font-mono bg-blue-600 hover:bg-blue-700 text-white">
                Resume Session →
              </Button>
            </Link>
          </div>
        </div>
      )}

      {/* Page Header */}
      <div className="mb-8">
        <div className="inline-flex items-center space-x-1.5 px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-[10px] font-mono text-slate-600 dark:text-slate-400 mb-2">
          <Sliders className="h-3 w-3" />
          <span>SESSION PRE-FLIGHT</span>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
          Interview Configuration
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Select your target role track and baseline difficulty. The engine dynamically adapts follow-up probing and evaluation criteria to your responses.
        </p>
      </div>

      {error && (
        <div className="mb-6 rounded border border-rose-200 dark:border-rose-900/50 bg-rose-50 dark:bg-rose-950/30 p-3.5 text-xs text-rose-700 dark:text-rose-300 flex items-start space-x-2">
          <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Track & Difficulty Selection */}
        <div className="lg:col-span-8 space-y-6">
          {/* Track Selection */}
          <div>
            <label className="block text-xs font-mono text-slate-500 uppercase tracking-wider mb-3">
              1. Target Competency Track
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {ASSESSMENT_TRACKS.map((track) => {
                const isSelected = selectedTrack === track.id
                const Icon = track.icon
                return (
                  <button
                    key={track.id}
                    type="button"
                    onClick={() => {
                      setSelectedTrack(track.id)
                      setSelectedDifficulty(track.defaultDifficulty)
                    }}
                    className={`p-4 rounded-lg border text-left transition-all ${
                      isSelected
                        ? "border-blue-600 bg-blue-50/30 dark:bg-blue-950/20 shadow-xs"
                        : "border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f] hover:border-slate-300 dark:hover:border-slate-700"
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className={`p-1.5 rounded ${isSelected ? "bg-blue-600 text-white" : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400"}`}>
                        <Icon className="h-4 w-4" />
                      </div>
                      {isSelected && (
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-blue-600 text-white font-semibold">
                          SELECTED
                        </span>
                      )}
                    </div>
                    <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">{track.title}</div>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 leading-snug">{track.desc}</p>
                    <div className="mt-3 pt-2.5 border-t border-slate-100 dark:border-slate-800/80 flex flex-wrap gap-1">
                      {track.skills.slice(0, 2).map((sk) => (
                        <span key={sk} className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                          {sk}
                        </span>
                      ))}
                    </div>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Difficulty Level Selection */}
          <div>
            <label className="block text-xs font-mono text-slate-500 uppercase tracking-wider mb-3">
              2. Baseline Calibration Level
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {DIFFICULTY_LEVELS.map((lvl) => {
                const isSelected = selectedDifficulty === lvl.id
                return (
                  <button
                    key={lvl.id}
                    type="button"
                    onClick={() => setSelectedDifficulty(lvl.id)}
                    className={`p-3.5 rounded-lg border text-left transition-all ${
                      isSelected
                        ? "border-blue-600 bg-blue-50/30 dark:bg-blue-950/20"
                        : "border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f] hover:border-slate-300 dark:hover:border-slate-700"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-bold text-slate-900 dark:text-slate-100">{lvl.label}</span>
                      {isSelected && <span className="w-1.5 h-1.5 rounded-full bg-blue-600" />}
                    </div>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-snug">{lvl.desc}</p>
                  </button>
                )
              })}
            </div>
          </div>
        </div>

        {/* Right Column: Pre-Flight Summary & Launch Button */}
        <div className="lg:col-span-4">
          <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f] p-5 space-y-5 sticky top-20">
            <div>
              <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Session Blueprint</div>
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100 mt-0.5">
                {currentTrack.title}
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{currentTrack.format}</p>
            </div>

            <div className="space-y-2.5 pt-3 border-t border-slate-100 dark:border-slate-800 text-xs font-mono">
              <div className="flex justify-between text-slate-600 dark:text-slate-400">
                <span>STARTING DIFFICULTY</span>
                <span className="font-semibold text-slate-900 dark:text-slate-200 uppercase">{selectedDifficulty}</span>
              </div>
              <div className="flex justify-between text-slate-600 dark:text-slate-400">
                <span>ESTIMATED DURATION</span>
                <span className="text-slate-900 dark:text-slate-200">~45 minutes</span>
              </div>
              <div className="flex justify-between text-slate-600 dark:text-slate-400">
                <span>ADAPTIVE QUESTIONING</span>
                <span className="text-emerald-600 dark:text-emerald-400 font-semibold">ENABLED</span>
              </div>
              <div className="flex justify-between text-slate-600 dark:text-slate-400">
                <span>CODE SANDBOX RUNNER</span>
                <span className="text-slate-900 dark:text-slate-200">Python 3 / Node</span>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-100 dark:border-slate-800 space-y-2">
              <div className="text-[11px] font-mono text-slate-500 uppercase">Assessment Rubric Breakdown</div>
              <div className="grid grid-cols-2 gap-1.5 text-[11px] font-mono text-slate-600 dark:text-slate-400">
                <span className="px-2 py-1 rounded bg-slate-50 dark:bg-slate-900">Accuracy (30%)</span>
                <span className="px-2 py-1 rounded bg-slate-50 dark:bg-slate-900">Depth (25%)</span>
                <span className="px-2 py-1 rounded bg-slate-50 dark:bg-slate-900">Solving (20%)</span>
                <span className="px-2 py-1 rounded bg-slate-50 dark:bg-slate-900">Clarity (15%)</span>
              </div>
            </div>

            <Button
              onClick={handleStartSession}
              disabled={isStarting}
              className="w-full h-10 bg-slate-900 hover:bg-slate-800 text-white dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200 font-mono text-xs font-semibold rounded"
            >
              {isStarting ? (
                <span className="flex items-center space-x-2">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  <span>INITIALIZING WORKSPACE...</span>
                </span>
              ) : (
                <span className="flex items-center justify-center space-x-2">
                  <span>LAUNCH ASSESSMENT SESSION</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </span>
              )}
            </Button>
          </div>
        </div>
      </div>

      {/* Destructive Discard Confirmation Modal */}
      {showDiscardConfirm && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="discard-title"
          onClick={() => setShowDiscardConfirm(false)}
        >
          <div
            className="w-full max-w-sm rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f] p-5 shadow-xl space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start gap-3">
              <div className="p-2 rounded bg-rose-500/10 text-rose-500 shrink-0">
                <AlertCircle className="h-5 w-5" />
              </div>
              <div>
                <h2 id="discard-title" className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                  Discard Active Session?
                </h2>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
                  This will detach session {activeSessionId?.slice(0, 8)}... from your active workspace. You will need to start a new interview session.
                </p>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-1 border-t border-slate-100 dark:border-slate-800/80">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowDiscardConfirm(false)}
                className="text-xs h-8"
              >
                Cancel
              </Button>
              <Button
                size="sm"
                variant="destructive"
                onClick={() => {
                  localStorage.removeItem("active_interview_session_id")
                  setActiveSessionId(null)
                  setShowDiscardConfirm(false)
                }}
                className="text-xs h-8"
              >
                Discard Session
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default function InterviewConfigPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[80vh] items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
        </div>
      }
    >
      <InterviewConfigContent />
    </Suspense>
  )
}
