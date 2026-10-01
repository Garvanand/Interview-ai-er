"use client"

import { useState, useEffect, Suspense } from "react"
import { useSearchParams, useRouter } from "next/navigation"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { InterviewWorkspace } from "@/components/interview/interview-workspace"
import { apiClient } from "@/lib/api-client"
import { useAuth } from "@/hooks/use-auth"
import { Brain, ArrowLeft, Loader2, AlertCircle, Compass, Play } from "lucide-react"

function LiveSessionContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const { userId, isLoading: authLoading, isAuthenticated } = useAuth({ redirectIfUnauthenticated: true })

  const [sessionId, setSessionId] = useState<string | null>(null)
  const [isChecking, setIsChecking] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const paramSessionId = searchParams.get("session_id")
    if (paramSessionId) {
      setSessionId(paramSessionId)
      localStorage.setItem("active_interview_session_id", paramSessionId)
      setIsChecking(false)
      return
    }

    const cachedId = localStorage.getItem("active_interview_session_id")
    if (cachedId) {
      apiClient
        .getSessionState(cachedId)
        .then((state) => {
          if (state && !state.is_completed) {
            setSessionId(cachedId)
          } else {
            localStorage.removeItem("active_interview_session_id")
          }
        })
        .catch(() => {
          localStorage.removeItem("active_interview_session_id")
        })
        .finally(() => {
          setIsChecking(false)
        })
    } else {
      setIsChecking(false)
    }
  }, [searchParams])

  if (authLoading || isChecking) {
    return (
      <div className="flex min-h-[80vh] items-center justify-center">
        <div className="flex flex-col items-center space-y-3 font-mono text-xs text-slate-500">
          <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
          <span>INITIALIZING SECURE WORKSPACE...</span>
        </div>
      </div>
    )
  }

  // If no active session, provide a clear link to configure one
  if (!sessionId) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-20 text-center">
        <div className="w-12 h-12 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f] flex items-center justify-center mx-auto mb-4 text-slate-700 dark:text-slate-300">
          <Compass className="h-6 w-6 text-blue-600" />
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 mb-2">
          No Active Interview Session
        </h1>
        <p className="text-sm text-slate-600 dark:text-slate-400 mb-6 max-w-md mx-auto">
          You are not currently in an active interview session. Configure a new session with your target role and difficulty benchmark to enter the live workspace.
        </p>
        <Link href="/interview">
          <Button className="h-10 px-5 text-xs font-mono bg-slate-900 text-white hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900">
            <Play className="h-3.5 w-3.5 mr-2" />
            Configure New Interview
          </Button>
        </Link>
      </div>
    )
  }

  return (
    <div className="w-full">
      <InterviewWorkspace
        sessionId={sessionId}
        onSessionEnd={() => {
          localStorage.removeItem("active_interview_session_id")
        }}
      />
    </div>
  )
}

export default function SessionPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[80vh] items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
        </div>
      }
    >
      <LiveSessionContent />
    </Suspense>
  )
}
