"use client"

import { useState, useEffect, Suspense } from "react"
import Link from "next/link"
import {
  apiClient,
  CandidateSkillProfile,
  Recommendation,
  PracticePlan,
  PracticeSequenceItem,
} from "@/lib/api-client"
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
  Zap,
  TrendingUp,
  ShieldCheck,
  ChevronRight,
  ListOrdered,
} from "lucide-react"
import {
  MLDetectedFocus,
  MLConceptCoverageResult,
  MLAdaptiveExplanation,
} from "@/components/ui/ml-explanation"

const TARGET_ROLES = [
  { id: "Software Engineer", label: "Software Engineer (Full-Stack / Core)" },
  { id: "Frontend Engineer", label: "Frontend Engineer (React / Web)" },
  { id: "Backend Engineer", label: "Backend Engineer (Distributed Systems / DB)" },
]

function PracticeContent() {
  const { userId, isLoading: authLoading } = useAuth({ redirectIfUnauthenticated: true })

  const [skills, setSkills] = useState<CandidateSkillProfile[]>([])
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  const [selectedRole, setSelectedRole] = useState<string>("Software Engineer")
  const [practiceMode, setPracticeMode] = useState<"weakest_skills" | "role_prep">("weakest_skills")

  // Practice sequence state
  const [practicePlan, setPracticePlan] = useState<PracticePlan | null>(null)
  const [currentStepIndex, setCurrentStepIndex] = useState<number>(0)
  const [completedSteps, setCompletedSteps] = useState<Record<number, boolean>>({})

  // Active question state
  const [userAnswer, setUserAnswer] = useState<string>("")
  const [evaluation, setEvaluation] = useState<any | null>(null)
  const [isGenerating, setIsGenerating] = useState<boolean>(false)
  const [isEvaluating, setIsEvaluating] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  // Restore drill and draft from sessionStorage on mount (browser refresh recovery)
  useEffect(() => {
    try {
      const saved = sessionStorage.getItem("adaptive_practice_plan_state")
      if (saved) {
        const parsed = JSON.parse(saved)
        if (parsed.practicePlan) setPracticePlan(parsed.practicePlan)
        if (parsed.currentStepIndex !== undefined) setCurrentStepIndex(parsed.currentStepIndex)
        if (parsed.userAnswer) setUserAnswer(parsed.userAnswer)
        if (parsed.evaluation) setEvaluation(parsed.evaluation)
        if (parsed.completedSteps) setCompletedSteps(parsed.completedSteps)
        if (parsed.practiceMode) setPracticeMode(parsed.practiceMode)
      }
    } catch (e) {}
  }, [])

  // Persist drill and draft to sessionStorage
  useEffect(() => {
    try {
      if (practicePlan) {
        sessionStorage.setItem(
          "adaptive_practice_plan_state",
          JSON.stringify({
            practicePlan,
            currentStepIndex,
            userAnswer,
            evaluation,
            completedSteps,
            practiceMode,
          })
        )
      }
    } catch (e) {}
  }, [practicePlan, currentStepIndex, userAnswer, evaluation, completedSteps, practiceMode])

  // Load skills & recommendations to personalize practice
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

  const handleCreateSequence = async (mode: "weakest_skills" | "role_prep", role: string = selectedRole) => {
    setIsGenerating(true)
    setError(null)
    setUserAnswer("")
    setEvaluation(null)
    setPracticeMode(mode)
    setCurrentStepIndex(0)
    setCompletedSteps({})

    try {
      const plan = await apiClient.generatePracticeSequence(mode, role, 4)
      if (plan && plan.sequence && plan.sequence.length > 0) {
        setPracticePlan(plan)
      } else {
        throw new Error("Unable to create practice sequence from candidate profile.")
      }
    } catch (err: any) {
      setError(err?.message || "Failed to generate adaptive practice sequence.")
    } finally {
      setIsGenerating(false)
    }
  }

  const handleSelectStep = (index: number) => {
    if (!practicePlan || index < 0 || index >= practicePlan.sequence.length) return
    setCurrentStepIndex(index)
    setUserAnswer("")
    setEvaluation(null)
    setError(null)
  }

  const activeItem: PracticeSequenceItem | null =
    practicePlan && practicePlan.sequence && practicePlan.sequence[currentStepIndex]
      ? practicePlan.sequence[currentStepIndex]
      : null

  const handleSubmitAnswer = async () => {
    if (!activeItem || !userAnswer.trim()) return

    if (userAnswer.trim().length < 10) {
      setError("Please provide a more detailed technical explanation (minimum 10 characters) for assessment.")
      return
    }

    setIsEvaluating(true)
    setError(null)

    try {
      const [evalRes, followUpRes] = await Promise.allSettled([
        apiClient.evaluatePracticeAnswer(
          activeItem.question_text,
          userAnswer,
          activeItem.question_id,
          activeItem.skill_focus,
          activeItem.difficulty
        ),
        apiClient.getFollowUpQuestion(activeItem.question_text, userAnswer, activeItem.interview_type),
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

      // Mark current step completed
      setCompletedSteps((prev) => ({ ...prev, [currentStepIndex]: true }))
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
          <div className="inline-flex items-center space-x-1.5 px-2 py-0.5 rounded bg-blue-50 dark:bg-blue-950/40 text-[10px] font-mono text-blue-700 dark:text-blue-300 mb-2 border border-blue-200 dark:border-blue-900">
            <Sparkles className="h-3 w-3" />
            <span>ADAPTIVE PRACTICE ENGINE</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            Adaptive Skill Practice & Curriculum
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            Personalized practice sequences powered by candidate skill profiles, difficulty progression, and spaced repetition.
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

      {/* Two Primary Mode Selectors */}
      <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Mode 1: Practice my weakest skills */}
        <div
          onClick={() => handleCreateSequence("weakest_skills")}
          className={`cursor-pointer p-5 rounded-xl border transition-all relative overflow-hidden group ${
            practiceMode === "weakest_skills" && practicePlan
              ? "border-amber-500 bg-amber-50/20 dark:bg-amber-950/20 shadow-sm"
              : "border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f] hover:border-amber-400 dark:hover:border-amber-700"
          }`}
        >
          <div className="flex items-start justify-between">
            <div className="flex items-center space-x-2.5">
              <div className="p-2 rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400">
                <Target className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                  Practice my weakest skills
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Adaptive weakness reinforcement, recent error remediation & spaced review
                </p>
              </div>
            </div>
          </div>

          <div className="mt-4 flex items-center justify-between">
            <div className="flex flex-wrap gap-1.5">
              {recommendedWeaknesses.length > 0 ? (
                recommendedWeaknesses.slice(0, 2).map((r) => (
                  <span
                    key={r.id}
                    className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300"
                  >
                    {r.target_skill}
                  </span>
                ))
              ) : (
                <span className="text-[11px] font-mono text-slate-400">
                  Auto-targets lowest mastery signals
                </span>
              )}
            </div>

            <Button
              size="sm"
              disabled={isGenerating}
              onClick={(e) => {
                e.stopPropagation()
                handleCreateSequence("weakest_skills")
              }}
              className="h-8 text-xs font-mono bg-amber-600 hover:bg-amber-500 text-white font-semibold"
            >
              {isGenerating && practiceMode === "weakest_skills" ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <span className="flex items-center space-x-1">
                  <span>Generate Sequence</span>
                  <ArrowRight className="h-3 w-3 ml-1" />
                </span>
              )}
            </Button>
          </div>
        </div>

        {/* Mode 2: Prepare me for Software Engineer interviews */}
        <div
          onClick={() => handleCreateSequence("role_prep")}
          className={`cursor-pointer p-5 rounded-xl border transition-all relative overflow-hidden group ${
            practiceMode === "role_prep" && practicePlan
              ? "border-blue-500 bg-blue-50/20 dark:bg-blue-950/20 shadow-sm"
              : "border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f] hover:border-blue-400 dark:hover:border-blue-700"
          }`}
        >
          <div className="flex items-start justify-between">
            <div className="flex items-center space-x-2.5">
              <div className="p-2 rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400">
                <Compass className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                  Prepare me for {selectedRole} interviews
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Full curriculum ladder: DSA, System Architecture & Communication
                </p>
              </div>
            </div>
          </div>

          <div className="mt-4 flex items-center justify-between">
            <select
              value={selectedRole}
              onClick={(e) => e.stopPropagation()}
              onChange={(e) => {
                setSelectedRole(e.target.value)
              }}
              className="text-[11px] font-mono rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 py-1 px-2 text-slate-700 dark:text-slate-300"
            >
              {TARGET_ROLES.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.label}
                </option>
              ))}
            </select>

            <Button
              size="sm"
              disabled={isGenerating}
              onClick={(e) => {
                e.stopPropagation()
                handleCreateSequence("role_prep", selectedRole)
              }}
              className="h-8 text-xs font-mono bg-blue-600 hover:bg-blue-500 text-white font-semibold"
            >
              {isGenerating && practiceMode === "role_prep" ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <span className="flex items-center space-x-1">
                  <span>Generate Curriculum</span>
                  <ArrowRight className="h-3 w-3 ml-1" />
                </span>
              )}
            </Button>
          </div>
        </div>
      </div>

      {/* Main Practice Workspace Grid */}
      <div className="mt-8 grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Adaptive Practice Sequence Roadmap */}
        <div className="lg:col-span-4 space-y-4">
          <div className="flex items-center justify-between">
            <label className="block text-xs font-mono text-slate-500 uppercase tracking-wider">
              Practice Sequence ({practicePlan?.sequence.length || 0} Steps)
            </label>
            {practicePlan && (
              <span className="text-[10px] font-mono text-slate-400">
                ~{practicePlan.total_estimated_minutes} mins total
              </span>
            )}
          </div>

          {practicePlan ? (
            <div className="space-y-2.5">
              {practicePlan.sequence.map((item, idx) => {
                const isActive = idx === currentStepIndex
                const isCompleted = completedSteps[idx]

                return (
                  <div
                    key={item.question_id + idx}
                    onClick={() => handleSelectStep(idx)}
                    className={`cursor-pointer p-3 rounded-lg border text-left transition-all ${
                      isActive
                        ? "border-blue-600 bg-blue-50/40 dark:bg-blue-950/30 shadow-xs"
                        : "border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f] hover:border-slate-300 dark:hover:border-slate-700"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <span
                          className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-mono font-bold ${
                            isCompleted
                              ? "bg-emerald-500 text-white"
                              : isActive
                              ? "bg-blue-600 text-white"
                              : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400"
                          }`}
                        >
                          {isCompleted ? "✓" : idx + 1}
                        </span>
                        <span className="text-xs font-bold text-slate-900 dark:text-slate-100 line-clamp-1">
                          {item.title}
                        </span>
                      </div>
                      <span
                        className={`text-[9px] font-mono uppercase px-1.5 py-0.5 rounded ${
                          item.difficulty === "advanced"
                            ? "bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300"
                            : item.difficulty === "intermediate"
                            ? "bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300"
                            : "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300"
                        }`}
                      >
                        {item.difficulty}
                      </span>
                    </div>

                    <div className="mt-1.5 flex items-center justify-between text-[11px] font-mono text-slate-500 dark:text-slate-400">
                      <span>{item.skill_focus}</span>
                      <span className="text-[10px] text-slate-400">{item.expected_time_minutes}m</span>
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="rounded-lg border border-dashed border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-[#0d121f]/50 p-6 text-center text-xs font-mono text-slate-500">
              Select one of the practice modes above to generate your tailored practice sequence.
            </div>
          )}

          {practicePlan?.summary_explanation && (
            <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50 text-[11px] font-mono text-slate-600 dark:text-slate-400 leading-relaxed">
              <span className="font-bold text-slate-800 dark:text-slate-200 block mb-1">
                ENGINE CURRICULUM SUMMARY:
              </span>
              {practicePlan.summary_explanation}
            </div>
          )}
        </div>

        {/* Right Column: Live Drill & Evaluation View */}
        <div className="lg:col-span-8">
          {error && (
            <div className="mb-4 rounded border border-rose-200 dark:border-rose-900/50 bg-rose-50 dark:bg-rose-950/30 p-3 text-xs text-rose-700 dark:text-rose-300">
              {error}
            </div>
          )}

          {activeItem ? (
            <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f] p-6 space-y-5">
              {/* Question Header & Stage */}
              <div>
                <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                  <div className="flex items-center space-x-2">
                    <MLDetectedFocus skill={activeItem.skill_focus} />
                    <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                      Step {currentStepIndex + 1} of {practicePlan?.sequence.length || 1}
                    </span>
                  </div>
                  <span className="text-[10px] font-mono uppercase font-bold text-slate-500">
                    Tier: {activeItem.difficulty}
                  </span>
                </div>

                <h3 className="text-base font-bold text-slate-900 dark:text-slate-100 leading-snug">
                  {activeItem.question_text}
                </h3>
              </div>

              {/* Explainable Selection Reason Callout */}
              <div className="p-3.5 rounded-lg border border-blue-200 dark:border-blue-900/60 bg-blue-50/50 dark:bg-blue-950/20 text-xs leading-relaxed space-y-1">
                <div className="flex items-center text-[10px] font-mono font-bold text-blue-700 dark:text-blue-300">
                  <Brain className="h-3.5 w-3.5 mr-1.5 text-blue-600" />
                  WHY THIS QUESTION WAS SELECTED
                </div>
                <p className="text-slate-700 dark:text-slate-300 font-mono text-[11px]">
                  {activeItem.selection_reason}
                </p>
                {activeItem.remediation_objective && (
                  <p className="text-[10px] font-mono text-blue-600 dark:text-blue-400 pt-0.5">
                    Objective: {activeItem.remediation_objective}
                  </p>
                )}
              </div>

              {/* Response Input */}
              <div className="space-y-2">
                <label className="block text-xs font-mono text-slate-500 uppercase">
                  Your Technical Formulation & Implementation
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
                  placeholder="Outline your algorithm approach, time/space complexity tradeoffs, and code solution... (Press Ctrl+Enter to submit)"
                  rows={8}
                  className="text-xs font-mono rounded border-slate-200 dark:border-slate-800 leading-relaxed focus-visible:ring-1 focus-visible:ring-blue-500"
                />
                <div className="flex justify-between items-center text-[11px] font-mono text-slate-500">
                  <span>Press Ctrl+Enter to submit response</span>
                  <span>
                    {userAnswer.trim().length} chars • {userAnswer.trim().split(/\s+/).filter(Boolean).length} words
                  </span>
                </div>
              </div>

              {/* Navigation & Submission Controls */}
              <div className="flex justify-between items-center pt-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    if (practicePlan && currentStepIndex < practicePlan.sequence.length - 1) {
                      handleSelectStep(currentStepIndex + 1)
                    }
                  }}
                  disabled={!practicePlan || currentStepIndex >= practicePlan.sequence.length - 1 || isEvaluating}
                  className="text-xs font-mono"
                >
                  <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
                  Skip to Next Step
                </Button>

                <Button
                  size="sm"
                  onClick={handleSubmitAnswer}
                  disabled={isEvaluating || !userAnswer.trim()}
                  className="text-xs font-mono bg-slate-900 hover:bg-slate-800 text-white dark:bg-slate-100 dark:text-slate-900 font-semibold"
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
                  {evaluation.dimensions && evaluation.dimensions.accuracy !== undefined && (
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                      <div className="p-2 rounded bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-center">
                        <span className="text-[10px] text-slate-500 uppercase block">Accuracy</span>
                        <span className="font-bold text-slate-900 dark:text-slate-100">
                          {evaluation.dimensions.accuracy}%
                        </span>
                      </div>
                      <div className="p-2 rounded bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-center">
                        <span className="text-[10px] text-slate-500 uppercase block">Depth</span>
                        <span className="font-bold text-slate-900 dark:text-slate-100">
                          {evaluation.dimensions.depth}%
                        </span>
                      </div>
                      <div className="p-2 rounded bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-center">
                        <span className="text-[10px] text-slate-500 uppercase block">Logic</span>
                        <span className="font-bold text-slate-900 dark:text-slate-100">
                          {evaluation.dimensions.problemSolving}%
                        </span>
                      </div>
                      <div className="p-2 rounded bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-center">
                        <span className="text-[10px] text-slate-500 uppercase block">Clarity</span>
                        <span className="font-bold text-slate-900 dark:text-slate-100">
                          {evaluation.dimensions.communication}%
                        </span>
                      </div>
                    </div>
                  )}

                  <p className="text-slate-700 dark:text-slate-300 font-sans leading-relaxed">
                    {evaluation.feedback}
                  </p>

                  {/* Strengths & Weaknesses */}
                  {((evaluation.strengths && evaluation.strengths.length > 0) ||
                    (evaluation.weaknesses && evaluation.weaknesses.length > 0)) && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                      {evaluation.strengths && evaluation.strengths.length > 0 && (
                        <div className="p-2.5 rounded bg-emerald-50/20 dark:bg-emerald-950/10 border border-emerald-200 dark:border-emerald-900/40">
                          <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-bold block mb-1">
                            STRENGTHS
                          </span>
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
                          <span className="text-[10px] text-amber-600 dark:text-amber-400 font-bold block mb-1">
                            REMEDIATION TARGETS
                          </span>
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

                  {/* Advance to next step CTA */}
                  {practicePlan && currentStepIndex < practicePlan.sequence.length - 1 && (
                    <div className="pt-2 flex justify-end">
                      <Button
                        size="sm"
                        onClick={() => handleSelectStep(currentStepIndex + 1)}
                        className="text-xs font-mono bg-blue-600 hover:bg-blue-500 text-white font-semibold"
                      >
                        Advance to Step {currentStepIndex + 2} →
                      </Button>
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="rounded-lg border border-dashed border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-[#0d121f]/50 p-12 text-center">
              <BookOpen className="h-8 w-8 text-slate-400 mx-auto mb-3" />
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                Ready to Initiate Adaptive Practice
              </h3>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto mb-4">
                Choose <span className="font-semibold text-slate-700 dark:text-slate-300">&quot;Practice my weakest skills&quot;</span> or <span className="font-semibold text-slate-700 dark:text-slate-300">&quot;Prepare me for Software Engineer interviews&quot;</span> above to generate an evidence-based sequence.
              </p>
              <div className="flex justify-center gap-3">
                <Button
                  size="sm"
                  onClick={() => handleCreateSequence("weakest_skills")}
                  disabled={isGenerating}
                  className="text-xs font-mono bg-amber-600 hover:bg-amber-500 text-white"
                >
                  Practice Weakest Skills
                </Button>
                <Button
                  size="sm"
                  onClick={() => handleCreateSequence("role_prep")}
                  disabled={isGenerating}
                  className="text-xs font-mono bg-blue-600 hover:bg-blue-500 text-white"
                >
                  Prepare for Role
                </Button>
              </div>
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
