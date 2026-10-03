"use client"

import { useState, useEffect, Suspense } from "react"
import Link from "next/link"
import { apiClient, CandidateSkillProfile, Recommendation } from "@/lib/api-client"
import { useAuth } from "@/hooks/use-auth"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
import {
  BookOpen,
  Target,
  Brain,
  Code2,
  CheckCircle2,
  AlertCircle,
  Play,
  ArrowRight,
  Loader2,
  RefreshCw,
  Sparkles,
  Layers,
  Terminal,
  Clock,
  Compass,
} from "lucide-react"
import {
  MLDetectedFocus,
  MLConceptCoverageResult,
  MLAdaptiveExplanation,
} from "@/components/ui/ml-explanation"

const DEFAULT_PRACTICE_TOPICS = [
  { id: "algorithms", title: "Algorithms & Complexity", focus: "Dynamic Programming, Trees, Binary Search" },
  { id: "system_design", title: "System Design Tradeoffs", focus: "Partitioning, Raft/Paxos, Caching, CAP" },
  { id: "concurrency", title: "Concurrency & Multithreading", focus: "Race Conditions, Deadlocks, Mutexes, Async" },
  { id: "database", title: "Database Systems & SQL", focus: "Indexing, B-Trees, Isolation Levels, Sharding" },
  { id: "behavioral", title: "Technical Communication", focus: "STAR Framework, Conflict Negotiation, Delivery" },
]

function PracticeContent() {
  const { userId, isLoading: authLoading } = useAuth({ redirectIfUnauthenticated: true })

  const [skills, setSkills] = useState<CandidateSkillProfile[]>([])
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  const [selectedTopic, setSelectedTopic] = useState<string>("algorithms")
  const [difficulty, setDifficulty] = useState<string>("intermediate")

  // Practice session state
  const [activeQuestion, setActiveQuestion] = useState<any | null>(null)
  const [userAnswer, setUserAnswer] = useState<string>("")
  const [evaluation, setEvaluation] = useState<any | null>(null)
  const [isGenerating, setIsGenerating] = useState<boolean>(false)
  const [isEvaluating, setIsEvaluating] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  // Restore drill and draft from sessionStorage on mount (browser refresh recovery)
  useEffect(() => {
    try {
      const saved = sessionStorage.getItem("practice_active_drill")
      if (saved) {
        const parsed = JSON.parse(saved)
        if (parsed.question) setActiveQuestion(parsed.question)
        if (parsed.answer) setUserAnswer(parsed.answer)
        if (parsed.evaluation) setEvaluation(parsed.evaluation)
      }
    } catch (e) {}
  }, [])

  // Persist drill and draft to sessionStorage
  useEffect(() => {
    try {
      if (activeQuestion) {
        sessionStorage.setItem(
          "practice_active_drill",
          JSON.stringify({
            question: activeQuestion,
            answer: userAnswer,
            evaluation,
          })
        )
      } else {
        sessionStorage.removeItem("practice_active_drill")
      }
    } catch (e) {}
  }, [activeQuestion, userAnswer, evaluation])

  // Load skills & recommendations to personalize drills
  useEffect(() => {
    if (authLoading || !userId) return
    async function loadCandidateProfile() {
      try {
        const [skillsRes, recsRes] = await Promise.allSettled([
          apiClient.getCandidateSkills(userId!),
          apiClient.getRecommendations(userId!),
        ])
        if (skillsRes.status === "fulfilled" && skillsRes.value?.profiles) {
          setSkills(skillsRes.value.profiles)
        }
        if (recsRes.status === "fulfilled" && recsRes.value?.recommendations) {
          setRecommendations(recsRes.value.recommendations)
        }
      } catch (e) {
        console.error("Failed to load candidate intelligence for practice:", e)
      }
    }
    loadCandidateProfile()
  }, [authLoading, userId])

  const handleGenerateDrill = async () => {
    setIsGenerating(true)
    setError(null)
    setActiveQuestion(null)
    setUserAnswer("")
    setEvaluation(null)

    try {
      const res: any = await apiClient.generatePracticeQuestion("technical", difficulty, selectedTopic)
      const questionText = res?.question || res?.data?.question || res?.question_text
      if (questionText) {
        setActiveQuestion({
          question_text: questionText,
          topic: res?.topic || res?.data?.topic || selectedTopic,
          difficulty: res?.difficulty || res?.data?.difficulty || difficulty,
        })
      } else {
        throw new Error("Unable to generate drill question.")
      }
    } catch (err: any) {
      setError(err?.message || "Failed to generate targeted practice question.")
    } finally {
      setIsGenerating(false)
    }
  }

  const handleSubmitAnswer = async () => {
    if (!activeQuestion || !userAnswer.trim()) return

    if (userAnswer.trim().length < 10) {
      setError("Please provide a more detailed answer (minimum 10 characters) for assessment.")
      return
    }

    setIsEvaluating(true)
    setError(null)

    try {
      const [evalRes, followUpRes] = await Promise.allSettled([
        apiClient.evaluatePracticeAnswer(activeQuestion.question_text, userAnswer),
        apiClient.getFollowUpQuestion(activeQuestion.question_text, userAnswer, "technical"),
      ])

      const evalData = evalRes.status === "fulfilled" ? evalRes.value : null
      const followUpData = followUpRes.status === "fulfilled" ? followUpRes.value : null

      if (!evalData && evalRes.status === "rejected") {
        throw new Error(evalRes.reason?.message || "Evaluation request failed.")
      }

      setEvaluation({
        score: evalData?.overall_score ?? evalData?.score ?? 75,
        feedback: evalData?.feedback || "Response successfully evaluated against target skill criteria.",
        strengths: evalData?.strengths || [],
        weaknesses: evalData?.weaknesses || [],
        dimensions: {
          accuracy: evalData?.technical_accuracy,
          problemSolving: evalData?.problem_solving,
          depth: evalData?.conceptual_depth,
          communication: evalData?.communication,
        },
        follow_up: followUpData?.follow_up_question || (followUpData as any)?.data?.follow_up_question || null,
      })
    } catch (err: any) {
      setError(err?.message || "Evaluation failed. Please verify your connection and try again.")
    } finally {
      setIsEvaluating(false)
    }
  }

  if (authLoading) {
    return (
      <div className="flex min-h-[80vh] items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
      </div>
    )
  }

  // Find weakness areas from real recommendations
  const recommendedWeaknesses = recommendations.filter(
    (r) => r.priority === "CRITICAL" || r.priority === "HIGH"
  )

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-slate-200 dark:border-slate-800 gap-4">
        <div>
          <div className="inline-flex items-center space-x-1.5 px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-[10px] font-mono text-slate-600 dark:text-slate-400 mb-2">
            <Target className="h-3 w-3" />
            <span>ADAPTIVE DRILL ENGINE</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            Targeted Skill Practice
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            Reinforce specific competency gaps identified by your interview evaluations with targeted drill questions.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <Link href="/interview">
            <Button variant="outline" size="sm" className="h-9 px-4 text-xs font-mono">
              Live Mock Interview →
            </Button>
          </Link>
        </div>
      </div>

      {/* Recommended Weakness Alerts from Real Intelligence */}
      {recommendedWeaknesses.length > 0 && (
        <div className="mt-6 p-4 rounded-lg border border-amber-300 dark:border-amber-800/80 bg-amber-50/50 dark:bg-amber-950/20 text-xs font-mono space-y-2">
          <div className="flex items-center text-amber-800 dark:text-amber-300 font-semibold">
            <AlertCircle className="h-4 w-4 mr-2" />
            IDENTIFIED SKILL REMEDIATION PRIORITIES
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-slate-700 dark:text-slate-300">
            {recommendedWeaknesses.slice(0, 2).map((rec) => (
              <div
                key={rec.id}
                className="p-2.5 rounded border border-amber-200 dark:border-amber-900/40 bg-white/80 dark:bg-[#0d121f] flex justify-between items-center"
              >
                <div>
                  <span className="font-bold text-amber-700 dark:text-amber-400">[{rec.target_skill}]</span>{" "}
                  <span className="text-[11px] text-slate-500">{rec.reason}</span>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    setSelectedTopic(rec.target_skill.toLowerCase())
                    handleGenerateDrill()
                  }}
                  className="h-6 text-[10px] font-mono px-2"
                >
                  Drill →
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Main Practice Workspace Grid */}
      <div className="mt-8 grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Topic & Calibration Controls */}
        <div className="lg:col-span-4 space-y-6">
          <div>
            <label className="block text-xs font-mono text-slate-500 uppercase tracking-wider mb-2.5">
              Select Practice Topic
            </label>
            <div className="space-y-2">
              {DEFAULT_PRACTICE_TOPICS.map((topic) => {
                const isSelected = selectedTopic === topic.id
                return (
                  <button
                    key={topic.id}
                    onClick={() => setSelectedTopic(topic.id)}
                    className={`w-full p-3 rounded-lg border text-left transition-all ${
                      isSelected
                        ? "border-blue-600 bg-blue-50/30 dark:bg-blue-950/20 shadow-xs"
                        : "border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f] hover:border-slate-300 dark:hover:border-slate-700"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-900 dark:text-slate-100">{topic.title}</span>
                      {isSelected && <span className="w-1.5 h-1.5 rounded-full bg-blue-600" />}
                    </div>
                    <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">{topic.focus}</div>
                  </button>
                )
              })}
            </div>
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-500 uppercase tracking-wider mb-2">
              Difficulty Tier
            </label>
            <div className="grid grid-cols-3 gap-2">
              {["beginner", "intermediate", "advanced"].map((lvl) => (
                <button
                  key={lvl}
                  onClick={() => setDifficulty(lvl)}
                  className={`py-1.5 px-2 rounded text-xs font-mono uppercase transition-colors ${
                    difficulty === lvl
                      ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 font-semibold"
                      : "border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f] text-slate-600 dark:text-slate-400"
                  }`}
                >
                  {lvl}
                </button>
              ))}
            </div>
          </div>

          <Button
            onClick={handleGenerateDrill}
            disabled={isGenerating}
            className="w-full h-10 text-xs font-mono bg-slate-900 text-white hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900 font-semibold rounded"
          >
            {isGenerating ? (
              <span className="flex items-center space-x-2">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                <span>GENERATING QUESTION...</span>
              </span>
            ) : (
              <span className="flex items-center justify-center space-x-2">
                <Play className="h-3.5 w-3.5" />
                <span>GENERATE DRILL QUESTION</span>
              </span>
            )}
          </Button>
        </div>

        {/* Right Column: Live Drill & Evaluation View */}
        <div className="lg:col-span-8">
          {error && (
            <div className="mb-4 rounded border border-rose-200 dark:border-rose-900/50 bg-rose-50 dark:bg-rose-950/30 p-3 text-xs text-rose-700 dark:text-rose-300">
              {error}
            </div>
          )}

          {activeQuestion ? (
            <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f] p-6 space-y-5">
              {/* Question Header */}
              <div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <MLDetectedFocus skill={activeQuestion.topic || "Algorithmic Reasoning"} />
                  <span className="text-[10px] font-mono uppercase text-slate-400">
                    Tier: {activeQuestion.difficulty}
                  </span>
                </div>
                <h3 className="text-base font-bold text-slate-900 dark:text-slate-100 leading-snug">
                  {activeQuestion.question_text}
                </h3>
              </div>

              {/* Response Input */}
              <div className="space-y-2">
                <label className="block text-xs font-mono text-slate-500 uppercase">
                  Your Technical Formulation
                </label>
                <Textarea
                  value={userAnswer}
                  onChange={(e) => setUserAnswer(e.target.value)}
                  onKeyDown={(e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === "Enter" && !isEvaluating && userAnswer.trim()) {
                      e.preventDefault()
                      handleSubmitAnswer()
                    }
                  }}
                  placeholder="Outline your approach, time/space complexity, and architecture tradeoffs... (Press Ctrl+Enter to submit)"
                  rows={8}
                  className="text-xs font-mono rounded border-slate-200 dark:border-slate-800 leading-relaxed focus-visible:ring-1 focus-visible:ring-blue-500"
                />
                <div className="flex justify-between items-center text-[11px] font-mono text-slate-500">
                  <span>Press Ctrl+Enter to submit</span>
                  <span>{userAnswer.trim().length} chars • {userAnswer.trim().split(/\s+/).filter(Boolean).length} words</span>
                </div>
              </div>

              {/* Error Callout with Retry */}
              {error && (
                <div className="rounded border border-rose-300 dark:border-rose-900/60 bg-rose-50 dark:bg-rose-950/30 p-3 text-xs font-mono text-rose-700 dark:text-rose-300 flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <AlertCircle className="h-4 w-4 shrink-0 text-rose-500" />
                    <span>{error}</span>
                  </div>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={handleSubmitAnswer}
                    disabled={isEvaluating}
                    className="h-6 text-[10px] text-rose-700 dark:text-rose-300 hover:bg-rose-100 dark:hover:bg-rose-900/40"
                  >
                    Retry
                  </Button>
                </div>
              )}

              <div className="flex justify-between items-center pt-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleGenerateDrill}
                  disabled={isGenerating || isEvaluating}
                  className="text-xs font-mono"
                >
                  <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
                  Skip / Next Drill
                </Button>

                <Button
                  size="sm"
                  onClick={handleSubmitAnswer}
                  disabled={isEvaluating || !userAnswer.trim()}
                  className="text-xs font-mono bg-slate-900 hover:bg-slate-800 text-white dark:bg-slate-100 dark:text-slate-900"
                >
                  {isEvaluating ? (
                    <span className="flex items-center space-x-1.5">
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      <span>EVALUATING...</span>
                    </span>
                  ) : (
                    <span>SUBMIT DRILL (Ctrl+↵)</span>
                  )}
                </Button>
              </div>

              {/* Evaluation Output */}
              {evaluation && (
                <div className="mt-6 pt-5 border-t border-slate-200 dark:border-slate-800 space-y-4 font-mono text-xs">
                  <div className="flex items-baseline justify-between">
                    <span className="font-bold text-slate-900 dark:text-slate-100">DRILL EVALUATION</span>
                    <span className="text-sm font-extrabold text-emerald-600 dark:text-emerald-400">
                      {evaluation.score} / 100
                    </span>
                  </div>

                  {/* ML Concept Coverage Result */}
                  <MLConceptCoverageResult
                    coverageData={evaluation.ml_concept_coverage}
                    fallbackScore={evaluation.score}
                  />

                  {/* Dimension Cards */}
                  {evaluation.dimensions && evaluation.dimensions.accuracy && (
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                      <div className="p-2 rounded bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-center">
                        <span className="text-[10px] text-slate-500 uppercase block">Accuracy</span>
                        <span className="font-bold text-slate-900 dark:text-slate-100">{evaluation.dimensions.accuracy}%</span>
                      </div>
                      <div className="p-2 rounded bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-center">
                        <span className="text-[10px] text-slate-500 uppercase block">Depth</span>
                        <span className="font-bold text-slate-900 dark:text-slate-100">{evaluation.dimensions.depth}%</span>
                      </div>
                      <div className="p-2 rounded bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-center">
                        <span className="text-[10px] text-slate-500 uppercase block">Logic</span>
                        <span className="font-bold text-slate-900 dark:text-slate-100">{evaluation.dimensions.problemSolving}%</span>
                      </div>
                      <div className="p-2 rounded bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-center">
                        <span className="text-[10px] text-slate-500 uppercase block">Clarity</span>
                        <span className="font-bold text-slate-900 dark:text-slate-100">{evaluation.dimensions.communication}%</span>
                      </div>
                    </div>
                  )}

                  <p className="text-slate-700 dark:text-slate-300 font-sans leading-relaxed">
                    {evaluation.feedback}
                  </p>

                  {/* Strengths & Weaknesses */}
                  {((evaluation.strengths && evaluation.strengths.length > 0) || (evaluation.weaknesses && evaluation.weaknesses.length > 0)) && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                      {evaluation.strengths && evaluation.strengths.length > 0 && (
                        <div className="p-2.5 rounded bg-emerald-50/20 dark:bg-emerald-950/10 border border-emerald-200 dark:border-emerald-900/40">
                          <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-bold block mb-1">STRENGTHS</span>
                          <ul className="space-y-1 text-slate-700 dark:text-slate-300">
                            {evaluation.strengths.map((str: string, i: number) => (
                              <li key={i} className="flex items-start gap-1.5 font-sans text-xs">
                                <span className="h-1 w-1 rounded-full bg-emerald-500 mt-1.5 shrink-0" />
                                <span>{str}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {evaluation.weaknesses && evaluation.weaknesses.length > 0 && (
                        <div className="p-2.5 rounded bg-amber-50/20 dark:bg-amber-950/10 border border-amber-200 dark:border-amber-900/40">
                          <span className="text-[10px] text-amber-600 dark:text-amber-400 font-bold block mb-1">REMEDIATION TARGETS</span>
                          <ul className="space-y-1 text-slate-700 dark:text-slate-300">
                            {evaluation.weaknesses.map((w: string, i: number) => (
                              <li key={i} className="flex items-start gap-1.5 font-sans text-xs">
                                <span className="h-1 w-1 rounded-full bg-amber-500 mt-1.5 shrink-0" />
                                <span>{w}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}

                  {evaluation.follow_up && (
                    <div className="p-3 rounded bg-blue-50/50 dark:bg-blue-950/20 border-l-2 border-blue-600 text-slate-800 dark:text-slate-200">
                      <span className="text-[10px] text-blue-600 dark:text-blue-400 font-bold uppercase block mb-1">
                        Adaptive Follow-Up Probe
                      </span>
                      {evaluation.follow_up}
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="rounded-lg border border-dashed border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-[#0d121f]/50 p-12 text-center">
              <BookOpen className="h-8 w-8 text-slate-400 mx-auto mb-3" />
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                Ready to Initiate Targeted Practice
              </h3>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto mb-4">
                Select a topic from the left or choose one of your identified skill gaps, then click Generate to begin.
              </p>
              <Button
                size="sm"
                onClick={handleGenerateDrill}
                disabled={isGenerating}
                className="text-xs font-mono bg-slate-900 text-white hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900"
              >
                Start Drill Now
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function PracticePage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[80vh] items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
        </div>
      }
    >
      <PracticeContent />
    </Suspense>
  )
}
