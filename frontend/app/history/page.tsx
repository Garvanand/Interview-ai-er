"use client"

import { useEffect, useState, useMemo, Suspense } from "react"
import Link from "next/link"
import { apiClient, InterviewSession } from "@/lib/api-client"
import { useAuth } from "@/hooks/use-auth"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import {
  Clock,
  Search,
  Filter,
  CheckCircle2,
  AlertCircle,
  Play,
  RotateCcw,
  ChevronRight,
  ExternalLink,
  Layers,
  Terminal,
  Activity,
  Calendar,
  X,
  FileText,
  Loader2,
} from "lucide-react"

export default function HistoryPage() {
  const { userId, isLoading: authLoading } = useAuth({ redirectIfUnauthenticated: true })
  const [sessions, setSessions] = useState<InterviewSession[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState("")
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [selectedSession, setSelectedSession] = useState<any | null>(null)
  const [isLoadingDetails, setIsLoadingDetails] = useState(false)

  useEffect(() => {
    if (authLoading || !userId) return
    async function fetchHistory() {
      try {
        const res = await apiClient.getUserSessions(userId!, 50)
        if (res?.sessions) {
          setSessions(res.sessions)
        }
      } catch (err) {
        console.error("Failed to fetch session history:", err)
      } finally {
        setIsLoading(false)
      }
    }
    fetchHistory()
  }, [authLoading, userId])

  const filteredSessions = useMemo(() => {
    return sessions.filter((s) => {
      const matchesSearch =
        s.interview_type?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.id.toLowerCase().includes(searchQuery.toLowerCase())
      const matchesStatus =
        statusFilter === "all" || s.status?.toLowerCase() === statusFilter.toLowerCase()
      return matchesSearch && matchesStatus
    })
  }, [sessions, searchQuery, statusFilter])

  const handleInspectSession = async (sessionId: string) => {
    setIsLoadingDetails(true)
    try {
      const details = await apiClient.getSessionDetails(sessionId)
      setSelectedSession(details?.data || details)
    } catch (err) {
      console.error("Failed to load session details:", err)
    } finally {
      setIsLoadingDetails(false)
    }
  }

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setSelectedSession(null)
      }
    }
    if (selectedSession) {
      window.addEventListener("keydown", handleKeyDown)
    }
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [selectedSession])

  if (authLoading) {
    return (
      <div className="flex min-h-[80vh] items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-slate-200 dark:border-slate-800 gap-4">
        <div>
          <div className="inline-flex items-center space-x-1.5 px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-[10px] font-mono text-slate-600 dark:text-slate-400 mb-2">
            <Clock className="h-3 w-3" />
            <span>SESSION LEDGER</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            Interview History & Audit Trail
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            Complete record of your past evaluated interview sessions, questions answered, and rubric breakdowns.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <Link href="/interview">
            <Button size="sm" className="h-9 px-4 text-xs font-mono bg-slate-900 text-white hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900">
              <Play className="h-3.5 w-3.5 mr-1.5" />
              New Interview
            </Button>
          </Link>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="mt-6 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-80">
          <Search className="h-4 w-4 absolute left-3 top-2.5 text-slate-400" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by role or session ID..."
            className="pl-9 h-9 text-xs font-mono rounded border-slate-200 dark:border-slate-800"
          />
        </div>

        <div className="flex items-center space-x-2 w-full sm:w-auto">
          {["all", "completed", "active"].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded text-xs font-mono transition-colors ${
                statusFilter === st
                  ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 font-semibold"
                  : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700"
              }`}
            >
              {st.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Sessions Table */}
      <div className="mt-6 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f] overflow-hidden shadow-xs">
        {isLoading ? (
          <div className="p-12 text-center text-xs font-mono text-slate-500 flex flex-col items-center space-y-2">
            <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
            <span>FETCHING PERSISTED SESSIONS...</span>
          </div>
        ) : filteredSessions.length === 0 ? (
          <div className="p-12 text-center">
            <Clock className="h-8 w-8 text-slate-400 mx-auto mb-2" />
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">No Interview Records Found</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              {searchQuery || statusFilter !== "all"
                ? "No sessions match your filter criteria. Try adjusting your search query."
                : "Complete your first diagnostic interview to populate your historical records and rubric evaluations."}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-50 dark:bg-slate-900/60 border-b border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400 uppercase text-[11px]">
                <tr>
                  <th className="py-3 px-4">Session ID / Role</th>
                  <th className="py-3 px-4">Started At</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Composite Score</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/80">
                {filteredSessions.map((session) => {
                  const isCompleted = session.status?.toLowerCase() === "completed"
                  const score = session.score != null ? Math.round(session.score) : null
                  return (
                    <tr
                      key={session.id}
                      className="hover:bg-slate-50/60 dark:hover:bg-slate-800/30 transition-colors"
                    >
                      <td className="py-3 px-4">
                        <div className="font-sans font-semibold text-slate-900 dark:text-slate-100">
                          {session.interview_type}
                        </div>
                        <div className="text-[10px] text-slate-400 font-mono">
                          ID: {session.id.slice(0, 13)}...
                        </div>
                      </td>
                      <td className="py-3 px-4 text-slate-600 dark:text-slate-400">
                        {session.start_time
                          ? new Date(session.start_time).toLocaleString("en-US", {
                              month: "short",
                              day: "numeric",
                              year: "numeric",
                              hour: "2-digit",
                              minute: "2-digit",
                            })
                          : "—"}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold ${
                            isCompleted
                              ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"
                              : "bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20"
                          }`}
                        >
                          {session.status?.toUpperCase() || "UNKNOWN"}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right font-bold text-sm">
                        {score !== null ? (
                          <span
                            className={
                              score >= 80
                                ? "text-emerald-600 dark:text-emerald-400"
                                : score >= 65
                                ? "text-blue-600 dark:text-blue-400"
                                : "text-amber-600 dark:text-amber-400"
                            }
                          >
                            {score}
                            <span className="text-xs font-normal text-slate-400"> / 100</span>
                          </span>
                        ) : (
                          <span className="text-slate-400 text-xs font-normal">Pending</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right space-x-2">
                        {isCompleted ? (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleInspectSession(session.id)}
                            className="h-7 px-2.5 text-xs font-mono"
                          >
                            Inspect
                          </Button>
                        ) : (
                          <Link href={`/interview/session?session_id=${session.id}`}>
                            <Button size="sm" className="h-7 px-2.5 text-xs font-mono bg-blue-600 hover:bg-blue-700 text-white">
                              Resume →
                            </Button>
                          </Link>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Session Deep-Dive Inspection Drawer / Modal */}
      {selectedSession && (
        <div
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="audit-modal-title"
          onClick={() => setSelectedSession(null)}
        >
          <div
            className="bg-white dark:bg-[#0d121f] rounded-lg border border-slate-200 dark:border-slate-800 max-w-3xl w-full max-h-[85vh] overflow-hidden flex flex-col shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
              <div>
                <span className="text-[10px] font-mono text-slate-400 uppercase">SESSION DETAIL AUDIT</span>
                <h3 id="audit-modal-title" className="text-base font-bold text-slate-900 dark:text-slate-100">
                  {selectedSession.session?.interview_type || "Technical"} Interview
                </h3>
              </div>
              <button
                onClick={() => setSelectedSession(null)}
                className="p-1 rounded text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-6 overflow-y-auto space-y-6 text-xs font-mono">
              {/* Score & Timing Telemetry */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 rounded bg-slate-50 dark:bg-slate-900 border border-slate-100 dark:border-slate-800">
                  <div className="text-[10px] text-slate-400">FINAL SCORE</div>
                  <div className="text-xl font-bold text-slate-900 dark:text-slate-100">
                    {Math.round(selectedSession.session?.score || 0)} / 100
                  </div>
                </div>
                <div className="p-3 rounded bg-slate-50 dark:bg-slate-900 border border-slate-100 dark:border-slate-800">
                  <div className="text-[10px] text-slate-400">QUESTIONS</div>
                  <div className="text-xl font-bold text-slate-900 dark:text-slate-100">
                    {selectedSession.questions?.length || 0}
                  </div>
                </div>
                <div className="p-3 rounded bg-slate-50 dark:bg-slate-900 border border-slate-100 dark:border-slate-800">
                  <div className="text-[10px] text-slate-400">STATUS</div>
                  <div className="text-sm font-bold text-emerald-600 dark:text-emerald-400 uppercase mt-1">
                    {selectedSession.session?.status || "COMPLETED"}
                  </div>
                </div>
                <div className="p-3 rounded bg-slate-50 dark:bg-slate-900 border border-slate-100 dark:border-slate-800">
                  <div className="text-[10px] text-slate-400">SESSION ID</div>
                  <div className="text-[10px] text-slate-600 dark:text-slate-400 truncate mt-1">
                    {selectedSession.session?.id}
                  </div>
                </div>
              </div>

              {/* Questions & Evaluations Accordion */}
              <div>
                <h4 className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase mb-3">
                  Evaluated Questions & Rubrics ({selectedSession.questions?.length || 0})
                </h4>
                <div className="space-y-3">
                  {selectedSession.questions?.map((q: any, idx: number) => (
                    <div
                      key={q.id || idx}
                      className="p-4 rounded border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/40 space-y-3"
                    >
                      <div className="flex items-start justify-between">
                        <span className="text-blue-600 dark:text-blue-400 font-bold">
                          Q{idx + 1}. {q.skill_focus ? `[${q.skill_focus}]` : ""}
                        </span>
                        {q.evaluation_score != null && (
                          <span className="px-2 py-0.5 rounded bg-slate-200 dark:bg-slate-800 font-bold text-slate-900 dark:text-slate-100">
                            {Math.round(q.evaluation_score)} pts
                          </span>
                        )}
                      </div>
                      <p className="text-xs font-sans text-slate-800 dark:text-slate-200 leading-relaxed">
                        {q.question_text}
                      </p>

                      {q.answer_text && (
                        <div className="rounded border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f] p-3 text-[11px] text-slate-600 dark:text-slate-300">
                          <span className="text-[10px] text-slate-400 uppercase block mb-1">Your Answer:</span>
                          {q.answer_text}
                        </div>
                      )}

                      {q.evaluation_feedback && (
                        <div className="text-[11px] text-slate-700 dark:text-slate-300 bg-emerald-500/5 border-l-2 border-emerald-500 pl-3 py-1">
                          <span className="font-semibold text-emerald-600 dark:text-emerald-400 block mb-0.5">
                            Evaluator Feedback:
                          </span>
                          {q.evaluation_feedback}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-3 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50 flex justify-end">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSelectedSession(null)}
                className="text-xs font-mono"
              >
                Close Audit
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
