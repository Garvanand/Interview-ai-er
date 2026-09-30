"use client"

import React, { useState, useEffect, useMemo, useCallback } from "react"
import Link from "next/link"
import {
  TrendingUp,
  TrendingDown,
  Target,
  Brain,
  ShieldAlert,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  ArrowRight,
  Filter,
  RotateCcw,
  Sparkles,
  Calendar,
  Layers,
  Activity,
  Code2,
  Compass,
  BarChart3,
  Award,
  Clock,
  ChevronDown,
  ChevronUp,
  Info,
  Check,
  Search
} from "lucide-react"
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  BarChart,
  Bar,
  Cell
} from "recharts"

import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select"
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from "@/components/ui/accordion"
import { Skeleton } from "@/components/ui/skeleton"
import { apiClient, LongitudinalAnalyticsResponse, AnalyticsFilterOptions, AnalyticsFilterParams, NextPracticeRecommendation, SkillTrendSummary, RepeatedWeakness } from "@/lib/api-client"
import { useAuth } from "@/hooks/use-auth"

export default function LongitudinalAnalyticsPage() {
  const { userId, isLoading: authLoading } = useAuth({ redirectIfUnauthenticated: true })
  const [data, setData] = useState<LongitudinalAnalyticsResponse | null>(null)
  const [filterOptions, setFilterOptions] = useState<AnalyticsFilterOptions | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Filter States
  const [timePreset, setTimePreset] = useState<string>("all")
  const [startDate, setStartDate] = useState<string>("")
  const [endDate, setEndDate] = useState<string>("")
  const [selectedInterviewType, setSelectedInterviewType] = useState<string>("all")
  const [selectedSkill, setSelectedSkill] = useState<string>("all")
  const [selectedDifficulty, setSelectedDifficulty] = useState<string>("all")
  const [selectedQuestionType, setSelectedQuestionType] = useState<string>("all")

  // Load filter options once user is resolved
  useEffect(() => {
    if (authLoading || !userId) return
    async function loadOptions() {
      try {
        const res = await apiClient.getAnalyticsFilterOptions(userId!)
        if (res?.success && res.data) {
          setFilterOptions(res.data)
        }
      } catch (err) {
        console.error("Failed to load filter options:", err)
      }
    }
    loadOptions()
  }, [authLoading, userId])

  // Compute effective filter payload
  const currentFilterPayload = useMemo<AnalyticsFilterParams>(() => {
    const payload: AnalyticsFilterParams = {}

    // Date range
    if (timePreset === "7d") {
      const d = new Date()
      d.setDate(d.getDate() - 7)
      payload.start_date = d.toISOString()
    } else if (timePreset === "30d") {
      const d = new Date()
      d.setDate(d.getDate() - 30)
      payload.start_date = d.toISOString()
    } else if (timePreset === "90d") {
      const d = new Date()
      d.setDate(d.getDate() - 90)
      payload.start_date = d.toISOString()
    } else if (timePreset === "custom") {
      if (startDate) payload.start_date = new Date(startDate).toISOString()
      if (endDate) payload.end_date = new Date(endDate).toISOString()
    }

    if (selectedInterviewType !== "all") payload.interview_type = selectedInterviewType
    if (selectedSkill !== "all") payload.skill = selectedSkill
    if (selectedDifficulty !== "all") payload.difficulty = selectedDifficulty
    if (selectedQuestionType !== "all") payload.question_type = selectedQuestionType

    return payload
  }, [timePreset, startDate, endDate, selectedInterviewType, selectedSkill, selectedDifficulty, selectedQuestionType])

  // Fetch analytics data from backend
  const fetchAnalytics = useCallback(async (refresh = false) => {
    if (authLoading || !userId) return
    if (refresh) setIsRefreshing(true)
    else setIsLoading(true)
    setError(null)

    try {
      const res = await apiClient.getLongitudinalAnalytics(userId, currentFilterPayload)
      if (res?.success && res.data) {
        setData(res.data)
      } else {
        throw new Error("Unable to retrieve longitudinal analytics data.")
      }
    } catch (err: any) {
      console.error("Analytics fetch error:", err)
      setError(err?.message || "An unexpected error occurred while compiling analytics.")
    } finally {
      setIsLoading(false)
      setIsRefreshing(false)
    }
  }, [authLoading, userId, currentFilterPayload])

  useEffect(() => {
    fetchAnalytics()
  }, [fetchAnalytics])

  // Reset filters
  const handleResetFilters = () => {
    setTimePreset("all")
    setStartDate("")
    setEndDate("")
    setSelectedInterviewType("all")
    setSelectedSkill("all")
    setSelectedDifficulty("all")
    setSelectedQuestionType("all")
  }

  const hasActiveFilters = timePreset !== "all" ||
    selectedInterviewType !== "all" ||
    selectedSkill !== "all" ||
    selectedDifficulty !== "all" ||
    selectedQuestionType !== "all"

  return (
    <div className="mx-auto min-h-screen max-w-7xl px-4 py-8 sm:px-6 lg:px-8 space-y-8">
      {/* 1. Header Section */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between border-b pb-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center rounded-md bg-primary/10 px-2.5 py-0.5 text-xs font-semibold text-primary">
              <Sparkles className="mr-1 h-3.5 w-3.5" />
              Longitudinal Candidate Intelligence
            </span>
            <span className="text-xs text-muted-foreground font-mono">
              Persisted Evidence Engine v2.4
            </span>
          </div>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
            Performance Analytics
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            Strictly derived from persisted session logs, evaluations, and code submissions.
            Avoids naive point-to-point comparisons through statistical regressions, difficulty weighting, and recurrent error clustering.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchAnalytics(true)}
            disabled={isRefreshing || isLoading}
            className="h-9 gap-1.5"
          >
            <RotateCcw className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} />
            <span>{isRefreshing ? "Recomputing..." : "Refresh Signals"}</span>
          </Button>
          <Link href="/interview">
            <Button size="sm" className="h-9 gap-1.5 font-medium shadow-sm">
              <Compass className="h-4 w-4" />
              <span>Launch Assessment</span>
            </Button>
          </Link>
        </div>
      </div>

      {/* 2. Multi-Dimensional Interactive Filter Bar */}
      <Card className="border shadow-sm bg-card/60 backdrop-blur-sm">
        <CardContent className="p-4 sm:p-5">
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between border-b pb-3">
              <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
                <Filter className="h-4 w-4 text-primary" />
                <span>Multi-Dimensional Filtering</span>
              </div>
              {hasActiveFilters && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleResetFilters}
                  className="h-7 text-xs text-muted-foreground hover:text-foreground"
                >
                  <RotateCcw className="mr-1 h-3 w-3" />
                  Reset Filters
                </Button>
              )}
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
              {/* Filter 1: Time Horizon */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                  <Calendar className="h-3 w-3" /> Time Range
                </label>
                <Select value={timePreset} onValueChange={setTimePreset}>
                  <SelectTrigger className="h-9 text-xs">
                    <SelectValue placeholder="All Time" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Available Records</SelectItem>
                    <SelectItem value="7d">Last 7 Days</SelectItem>
                    <SelectItem value="30d">Last 30 Days</SelectItem>
                    <SelectItem value="90d">Last 90 Days</SelectItem>
                    <SelectItem value="custom">Custom Date Range</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Filter 2: Interview Type */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                  <Layers className="h-3 w-3" /> Interview Type
                </label>
                <Select value={selectedInterviewType} onValueChange={setSelectedInterviewType}>
                  <SelectTrigger className="h-9 text-xs">
                    <SelectValue placeholder="All Interview Types" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Track Types</SelectItem>
                    {filterOptions?.interview_types.map((type) => (
                      <SelectItem key={type} value={type}>
                        {type}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Filter 3: Target Skill Focus */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                  <Brain className="h-3 w-3" /> Skill Domain
                </label>
                <Select value={selectedSkill} onValueChange={setSelectedSkill}>
                  <SelectTrigger className="h-9 text-xs">
                    <SelectValue placeholder="All Skills" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Skill Domains</SelectItem>
                    {filterOptions?.skills.map((skill) => (
                      <SelectItem key={skill} value={skill}>
                        {skill}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Filter 4: Difficulty Tier */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                  <BarChart3 className="h-3 w-3" /> Difficulty
                </label>
                <Select value={selectedDifficulty} onValueChange={setSelectedDifficulty}>
                  <SelectTrigger className="h-9 text-xs">
                    <SelectValue placeholder="All Difficulties" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Difficulties</SelectItem>
                    <SelectItem value="beginner">Beginner (0.85x)</SelectItem>
                    <SelectItem value="intermediate">Intermediate (1.00x)</SelectItem>
                    <SelectItem value="advanced">Advanced (1.25x)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Filter 5: Question Type / Modality */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                  <Code2 className="h-3 w-3" /> Question Modality
                </label>
                <Select value={selectedQuestionType} onValueChange={setSelectedQuestionType}>
                  <SelectTrigger className="h-9 text-xs">
                    <SelectValue placeholder="All Modalities" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Modalities</SelectItem>
                    <SelectItem value="coding">Coding Implementations</SelectItem>
                    <SelectItem value="system_design">System Design & Arch</SelectItem>
                    <SelectItem value="algorithmic">Algorithmic Reasoning</SelectItem>
                    <SelectItem value="conceptual">Conceptual & Behavioral</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Custom Date Inputs if custom selected */}
            {timePreset === "custom" && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t">
                <div className="space-y-1">
                  <span className="text-xs text-muted-foreground">Start Date:</span>
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="w-full text-xs p-2 rounded border bg-background text-foreground"
                  />
                </div>
                <div className="space-y-1">
                  <span className="text-xs text-muted-foreground">End Date:</span>
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="w-full text-xs p-2 rounded border bg-background text-foreground"
                  />
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Loading Skeleton */}
      {isLoading && (
        <div className="space-y-6">
          <Skeleton className="h-44 w-full rounded-xl" />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Skeleton className="h-64 rounded-xl" />
            <Skeleton className="h-64 rounded-xl" />
            <Skeleton className="h-64 rounded-xl" />
          </div>
          <Skeleton className="h-96 w-full rounded-xl" />
        </div>
      )}

      {/* Error Banner */}
      {error && !isLoading && (
        <Card className="border-destructive/50 bg-destructive/5">
          <CardContent className="p-6 flex items-start gap-4">
            <AlertCircle className="h-6 w-6 text-destructive shrink-0 mt-0.5" />
            <div className="space-y-1">
              <h3 className="font-semibold text-destructive">Failed to Load Performance Analytics</h3>
              <p className="text-sm text-destructive/90">{error}</p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => fetchAnalytics()}
                className="mt-3 border-destructive/30 hover:bg-destructive/10"
              >
                Retry Calculation
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Empty State */}
      {!isLoading && !error && data && data.score_trends.total_sessions_analyzed === 0 && (
        <Card className="border-dashed p-10 text-center">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-muted">
            <Search className="h-8 w-8 text-muted-foreground" />
          </div>
          <h2 className="mt-4 text-lg font-semibold text-foreground">No Evaluated Sessions Found</h2>
          <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
            No interview records matched the currently selected filters. Clear your filters or complete an assessment to populate longitudinal evidence.
          </p>
          <div className="mt-6 flex justify-center gap-3">
            {hasActiveFilters && (
              <Button variant="outline" size="sm" onClick={handleResetFilters}>
                Clear All Filters
              </Button>
            )}
            <Link href="/interview">
              <Button size="sm">Start an Interview</Button>
            </Link>
          </div>
        </Card>
      )}

      {/* Populated Analytics Dashboard */}
      {!isLoading && !error && data && data.score_trends.total_sessions_analyzed > 0 && (
        <div className="space-y-8">
          {/* 3. Hero Section: WHAT TO PRACTICE NEXT (Actionability Decision Engine) */}
          <section className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
                  <Target className="h-5 w-5 text-primary" />
                  What to Practice Next
                </h2>
                <p className="text-xs text-muted-foreground">
                  Prescriptive recommendations synthesized from persistent weakness blockers, frontier thresholds, and volatility signals.
                </p>
              </div>
              <Badge variant="outline" className="text-xs font-mono">
                {data.next_practice_recommendations.length} Prioritized Targets
              </Badge>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {data.next_practice_recommendations.map((rec) => (
                <Card
                  key={rec.priority}
                  className={`border-l-4 transition-all hover:shadow-md ${
                    rec.priority === 1
                      ? "border-l-rose-500 bg-rose-500/5 dark:bg-rose-950/10"
                      : rec.priority === 2
                      ? "border-l-amber-500 bg-amber-500/5 dark:bg-amber-950/10"
                      : "border-l-primary bg-primary/5 dark:bg-primary/10"
                  }`}
                >
                  <CardHeader className="p-4 pb-2">
                    <div className="flex items-center justify-between">
                      <Badge
                        variant="secondary"
                        className={`text-[10px] font-bold tracking-wider ${
                          rec.priority === 1
                            ? "bg-rose-500/20 text-rose-700 dark:text-rose-300"
                            : rec.priority === 2
                            ? "bg-amber-500/20 text-amber-700 dark:text-amber-300"
                            : "bg-primary/20 text-primary"
                        }`}
                      >
                        PRIORITY {rec.priority}
                      </Badge>
                      <Badge variant="outline" className="text-[11px] capitalize font-mono">
                        {rec.recommended_difficulty} • {rec.question_type.replace('_', ' ')}
                      </Badge>
                    </div>
                    <CardTitle className="text-base font-semibold mt-2 text-foreground">
                      {rec.target_skill}
                    </CardTitle>
                    <CardDescription className="text-xs text-foreground/80 font-medium">
                      {rec.learning_objective}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-4 pt-1 space-y-3">
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      {rec.rationale}
                    </p>
                    <div className="rounded-md bg-muted/60 p-2 text-[11px] text-muted-foreground font-mono">
                      <span className="font-semibold text-foreground">Evidence: </span>
                      {rec.evidence_context}
                    </div>
                    <div className="pt-1">
                      <Link
                        href={`/practice?topic=${encodeURIComponent(rec.target_skill)}&difficulty=${rec.recommended_difficulty}&type=${rec.question_type}`}
                      >
                        <Button size="sm" variant="default" className="w-full text-xs h-8 gap-1 font-medium">
                          <span>Practice This Topic</span>
                          <ArrowRight className="h-3.5 w-3.5" />
                        </Button>
                      </Link>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </section>

          {/* 4. Score Trajectory & Difficulty-Normalized Trends */}
          <section className="space-y-4">
            <Card className="border shadow-sm">
              <CardHeader className="pb-2">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                  <div>
                    <CardTitle className="text-lg font-bold flex items-center gap-2">
                      <TrendingUp className="h-5 w-5 text-primary" />
                      Longitudinal Score Trajectory & Difficulty Adjustment
                    </CardTitle>
                    <CardDescription className="text-xs">
                      Difficulty-weighted normalization (Beginner 0.85x, Intermediate 1.00x, Advanced 1.25x) with 3-session SMA and OLS linear regression slope.
                    </CardDescription>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge
                      className={`text-xs font-semibold ${
                        data.score_trends.trajectory_classification === "significant_improvement"
                          ? "bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border-emerald-500/30"
                          : data.score_trends.trajectory_classification === "moderate_improvement"
                          ? "bg-blue-500/20 text-blue-700 dark:text-blue-300 border-blue-500/30"
                          : data.score_trends.trajectory_classification === "concerning_decline"
                          ? "bg-rose-500/20 text-rose-700 dark:text-rose-300 border-rose-500/30"
                          : "bg-muted text-muted-foreground"
                      }`}
                    >
                      {data.score_trends.trajectory_classification.replace('_', ' ').toUpperCase()}
                      {data.score_trends.linear_regression_slope !== 0 && (
                        ` (${data.score_trends.linear_regression_slope > 0 ? "+" : ""}${data.score_trends.linear_regression_slope} pts/sess)`
                      )}
                    </Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Stats Bar */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3 bg-muted/40 rounded-lg text-xs">
                  <div>
                    <span className="text-muted-foreground block">Sessions Analyzed</span>
                    <span className="text-base font-bold text-foreground font-mono">
                      {data.score_trends.total_sessions_analyzed}
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground block">Current 3-Period SMA</span>
                    <span className="text-base font-bold text-primary font-mono">
                      {data.score_trends.current_moving_average}%
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground block">Difficulty-Adjusted Score</span>
                    <span className="text-base font-bold text-emerald-600 dark:text-emerald-400 font-mono">
                      {data.score_trends.difficulty_adjusted_current}%
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground block">Trajectory Fit (R²)</span>
                    <span className="text-base font-bold text-foreground font-mono">
                      {data.score_trends.r_squared}
                    </span>
                  </div>
                </div>

                {/* Trajectory Area Chart */}
                <div className="h-72 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart
                      data={data.score_trends.data_points}
                      margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                    >
                      <defs>
                        <linearGradient id="diffAdjGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="var(--color-primary, #6366f1)" stopOpacity={0.4} />
                          <stop offset="95%" stopColor="var(--color-primary, #6366f1)" stopOpacity={0.0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="opacity-15" />
                      <XAxis dataKey="date" stroke="currentColor" fontSize={11} tickLine={false} />
                      <YAxis domain={[0, 100]} stroke="currentColor" fontSize={11} tickLine={false} />
                      <RechartsTooltip
                        content={({ active, payload }) => {
                          if (active && payload && payload.length) {
                            const p = payload[0].payload
                            return (
                              <div className="rounded-lg border bg-popover p-3 text-xs shadow-md space-y-1">
                                <p className="font-semibold text-foreground">{p.date} • {p.interview_type}</p>
                                <div className="space-y-0.5">
                                  <p className="text-muted-foreground">
                                    Raw Score: <span className="font-bold text-foreground font-mono">{p.raw_score}</span>
                                  </p>
                                  <p className="text-primary">
                                    Difficulty-Adjusted: <span className="font-bold font-mono">{p.difficulty_adjusted_score}</span> ({p.difficulty_level})
                                  </p>
                                  <p className="text-emerald-600 dark:text-emerald-400">
                                    3-Session SMA: <span className="font-bold font-mono">{p.sma_3}</span>
                                  </p>
                                </div>
                              </div>
                            )
                          }
                          return null
                        }}
                      />
                      <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: 12 }} />
                      <Area
                        type="monotone"
                        dataKey="difficulty_adjusted_score"
                        name="Difficulty-Adjusted Score"
                        stroke="#6366f1"
                        strokeWidth={2.5}
                        fill="url(#diffAdjGradient)"
                      />
                      <Line
                        type="monotone"
                        dataKey="raw_score"
                        name="Raw Score"
                        stroke="#94a3b8"
                        strokeWidth={1.5}
                        strokeDasharray="4 4"
                        dot={{ r: 3 }}
                      />
                      <Line
                        type="monotone"
                        dataKey="sma_3"
                        name="3-Session SMA Trend"
                        stroke="#10b981"
                        strokeWidth={2}
                        dot={false}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </section>

          {/* 5. Two-Column Analytical Insights: Adaptive Frontier & Consistency */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Adaptive Difficulty Progression */}
            <Card className="border shadow-sm">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base font-bold flex items-center gap-2">
                    <BarChart3 className="h-4 w-4 text-primary" />
                    Adaptive Difficulty Progression
                  </CardTitle>
                  <Badge variant="outline" className="text-xs uppercase font-mono bg-primary/10 text-primary border-primary/30">
                    Frontier: {data.difficulty_progression.current_performance_frontier}
                  </Badge>
                </div>
                <CardDescription className="text-xs">
                  Evaluates candidate pass rates and sustained mastery across difficulty tier promotions.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4 text-xs">
                <div className="space-y-3">
                  {(["beginner", "intermediate", "advanced"] as const).map((lvl) => {
                    const stats = data.difficulty_progression.levels[lvl] || { total_attempted: 0, average_score: 0, pass_rate: 0 }
                    return (
                      <div key={lvl} className="space-y-1">
                        <div className="flex justify-between font-medium">
                          <span className="capitalize">{lvl} Tier</span>
                          <span className="font-mono text-muted-foreground">
                            {stats.average_score}% avg • {stats.pass_rate}% pass ({stats.total_attempted} Qs)
                          </span>
                        </div>
                        <Progress value={stats.average_score} className="h-2" />
                      </div>
                    )
                  })}
                </div>

                <div className="rounded-lg bg-muted/40 p-3 flex items-center justify-between">
                  <div>
                    <span className="font-medium text-foreground block">Promotion Step-Up Retention</span>
                    <span className="text-[11px] text-muted-foreground">
                      Maintained ≥ 70 when promoted to higher difficulty
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="text-lg font-bold font-mono text-primary">
                      {data.difficulty_progression.promotion_sustained_rate}%
                    </span>
                    <span className="text-[10px] text-muted-foreground block">
                      ({data.difficulty_progression.promotion_transitions_attempted} promotions)
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Consistency & Dispersion Analysis */}
            <Card className="border shadow-sm">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base font-bold flex items-center gap-2">
                    <Activity className="h-4 w-4 text-primary" />
                    Consistency & Dispersion Metrics
                  </CardTitle>
                  <Badge
                    variant="outline"
                    className={`text-xs font-semibold ${
                      data.consistency.consistency_category === "Highly Consistent"
                        ? "bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border-emerald-500/30"
                        : data.consistency.consistency_category === "Moderately Consistent"
                        ? "bg-blue-500/20 text-blue-700 dark:text-blue-300 border-blue-500/30"
                        : "bg-amber-500/20 text-amber-700 dark:text-amber-300 border-amber-500/30"
                    }`}
                  >
                    {data.consistency.consistency_category}
                  </Badge>
                </div>
                <CardDescription className="text-xs">
                  Coefficient of Variation (CV = σ / μ) and Interquartile Range (IQR) measuring performance stability.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4 text-xs">
                <div className="grid grid-cols-3 gap-2 text-center p-3 bg-muted/40 rounded-lg">
                  <div>
                    <span className="text-muted-foreground block text-[11px]">Consistency Index</span>
                    <span className="text-lg font-bold font-mono text-primary">
                      {data.consistency.consistency_index} / 100
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground block text-[11px]">Coeff. of Variation</span>
                    <span className="text-lg font-bold font-mono text-foreground">
                      {data.consistency.coefficient_of_variation}%
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground block text-[11px]">Std Deviation (σ)</span>
                    <span className="text-lg font-bold font-mono text-foreground">
                      ±{data.consistency.standard_deviation}
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-4 gap-2 text-center text-xs">
                  <div className="p-2 border rounded">
                    <span className="text-muted-foreground block text-[10px]">Median</span>
                    <span className="font-semibold font-mono">{data.consistency.median_score}%</span>
                  </div>
                  <div className="p-2 border rounded">
                    <span className="text-muted-foreground block text-[10px]">Min Score</span>
                    <span className="font-semibold font-mono">{data.consistency.min_score}%</span>
                  </div>
                  <div className="p-2 border rounded">
                    <span className="text-muted-foreground block text-[10px]">Max Score</span>
                    <span className="font-semibold font-mono">{data.consistency.max_score}%</span>
                  </div>
                  <div className="p-2 border rounded">
                    <span className="text-muted-foreground block text-[10px]">Score Spread</span>
                    <span className="font-semibold font-mono">{data.consistency.score_range} pts</span>
                  </div>
                </div>

                <p className="text-[11px] text-muted-foreground leading-relaxed">
                  {data.consistency.coefficient_of_variation < 15
                    ? "Your low variance proves consistent technical readiness regardless of problem variety or timing."
                    : "Moderate variance detected. Candidate performance fluctuates depending on problem modality."}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* 6. Skill Intelligence & Longitudinal Progression */}
          <section className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
                  <Brain className="h-5 w-5 text-primary" />
                  Longitudinal Skill Progression
                </h2>
                <p className="text-xs text-muted-foreground">
                  Time-decayed proficiency, statistical confidence levels, and net delta comparing recent vs historical windows.
                </p>
              </div>
              <Badge variant="outline" className="text-xs font-mono">
                {data.skill_trends.length} Evaluated Domains
              </Badge>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {data.skill_trends.map((skill) => (
                <Card key={skill.skill_name} className="border shadow-sm">
                  <CardHeader className="p-4 pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm font-bold text-foreground">
                        {skill.skill_name}
                      </CardTitle>
                      <Badge
                        variant="secondary"
                        className={`text-[10px] font-semibold ${
                          skill.confidence === "high confidence"
                            ? "bg-emerald-500/20 text-emerald-700 dark:text-emerald-300"
                            : skill.confidence === "medium confidence"
                            ? "bg-blue-500/20 text-blue-700 dark:text-blue-300"
                            : "bg-muted text-muted-foreground"
                        }`}
                      >
                        {skill.confidence}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="p-4 pt-1 space-y-3 text-xs">
                    <div className="flex items-baseline justify-between">
                      <div>
                        <span className="text-2xl font-bold font-mono text-primary">
                          {skill.decayed_proficiency}%
                        </span>
                        <span className="text-[11px] text-muted-foreground ml-1.5">
                          decayed proficiency
                        </span>
                      </div>
                      <Badge
                        variant="outline"
                        className={`text-[10px] font-semibold ${
                          skill.trend_status === "demonstrated_growth"
                            ? "border-emerald-500/30 text-emerald-600 dark:text-emerald-400"
                            : skill.trend_status === "skill_regression"
                            ? "border-rose-500/30 text-rose-600 dark:text-rose-400"
                            : "text-muted-foreground"
                        }`}
                      >
                        {skill.trend_status === "demonstrated_growth" && <TrendingUp className="mr-1 h-3 w-3 inline" />}
                        {skill.trend_status === "skill_regression" && <TrendingDown className="mr-1 h-3 w-3 inline" />}
                        {skill.net_delta > 0 ? `+${skill.net_delta}` : skill.net_delta} pts
                      </Badge>
                    </div>

                    <div className="grid grid-cols-3 gap-1 bg-muted/40 p-2 rounded text-[11px] text-center">
                      <div>
                        <span className="text-muted-foreground block text-[10px]">Recent Avg</span>
                        <span className="font-semibold font-mono">{skill.recent_average}%</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground block text-[10px]">Hist Avg</span>
                        <span className="font-semibold font-mono">{skill.historical_average}%</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground block text-[10px]">Volatility (σ)</span>
                        <span className="font-semibold font-mono">±{skill.volatility_sd}</span>
                      </div>
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-muted-foreground pt-1 border-t">
                      <span>{skill.evidence_count} evaluated evidence samples</span>
                      {skill.last_evaluated && (
                        <span>
                          {new Date(skill.last_evaluated).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </section>

          {/* 7. Repeated Weaknesses & Blocker Detection */}
          <section className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
                  <ShieldAlert className="h-5 w-5 text-rose-500" />
                  Repeated Weaknesses & Critical Error Patterns
                </h2>
                <p className="text-xs text-muted-foreground">
                  Algorithmic recurrence analysis tracking systemic blind spots across multiple distinct interview sessions.
                </p>
              </div>
              <Badge variant="outline" className="text-xs font-mono">
                {data.repeated_weaknesses.length} Weakness Clusters
              </Badge>
            </div>

            {data.repeated_weaknesses.length === 0 ? (
              <Card className="p-6 text-center text-xs text-muted-foreground">
                No repeated error clusters identified in the filtered evaluation window.
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {data.repeated_weaknesses.map((weakness) => (
                  <Card
                    key={weakness.weakness_cluster}
                    className={`border shadow-sm ${
                      weakness.persistence_status === "persistent_blocker"
                        ? "border-rose-500/40 bg-rose-500/5 dark:bg-rose-950/10"
                        : "border-border"
                    }`}
                  >
                    <CardHeader className="p-4 pb-2">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-sm font-bold text-foreground">
                          {weakness.canonical_label}
                        </CardTitle>
                        <Badge
                          className={`text-[10px] uppercase font-mono ${
                            weakness.persistence_status === "persistent_blocker"
                              ? "bg-rose-500/20 text-rose-700 dark:text-rose-300 border-rose-500/30"
                              : weakness.persistence_status === "emerging_issue"
                              ? "bg-amber-500/20 text-amber-700 dark:text-amber-300 border-amber-500/30"
                              : "bg-muted text-muted-foreground"
                          }`}
                        >
                          {weakness.persistence_status.replace('_', ' ')}
                        </Badge>
                      </div>
                      <CardDescription className="text-xs">
                        Recurred in {weakness.distinct_sessions_count} sessions ({weakness.session_percentage}% recurrence rate) • {weakness.total_occurrences} total instances
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="p-4 pt-1 space-y-2 text-xs">
                      {weakness.evidence_snippets.length > 0 && (
                        <div className="space-y-1.5">
                          <span className="text-[11px] font-medium text-muted-foreground">Real Evaluator Citations:</span>
                          {weakness.evidence_snippets.map((snip, idx) => (
                            <div key={idx} className="rounded bg-muted/60 p-2 text-[11px] text-foreground font-mono">
                              "{snip}"
                            </div>
                          ))}
                        </div>
                      )}
                      <div className="flex items-center justify-between text-[11px] pt-1 border-t text-muted-foreground">
                        <span>Target Domain: {weakness.target_skill || "General"}</span>
                        <span>{weakness.recency_flag ? "Appeared in latest session" : "Absorbed in prior sessions"}</span>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </section>

          {/* 8. Intervention Effectiveness & Completion Behavior */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Recommendation Outcomes */}
            <Card className="border shadow-sm">
              <CardHeader className="pb-3">
                <CardTitle className="text-base font-bold flex items-center gap-2">
                  <Award className="h-4 w-4 text-primary" />
                  Intervention Impact (Post-Recommendation Growth)
                </CardTitle>
                <CardDescription className="text-xs">
                  Tracks measured proficiency delta after completing recommended practice actions.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-xs">
                {data.recommendation_impact.length === 0 ? (
                  <p className="text-muted-foreground text-center py-6">
                    No completed recommendations evaluated in subsequent sessions yet. Complete recommended actions to track intervention lift.
                  </p>
                ) : (
                  data.recommendation_impact.map((imp) => (
                    <div key={imp.recommendation_id} className="border rounded p-3 space-y-1.5 bg-card">
                      <div className="flex items-center justify-between font-semibold">
                        <span>{imp.target_skill}</span>
                        <Badge
                          variant="outline"
                          className={`text-[10px] ${
                            imp.outcome_status === "verified_improvement"
                              ? "bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border-emerald-500/30"
                              : "bg-muted text-muted-foreground"
                          }`}
                        >
                          {imp.outcome_status.replace('_', ' ')}
                          {imp.delta !== null && ` (${imp.delta > 0 ? "+" : ""}${imp.delta} pts)`}
                        </Badge>
                      </div>
                      <p className="text-muted-foreground text-[11px]">{imp.reason}</p>
                      <div className="flex justify-between text-[10px] text-muted-foreground pt-1 border-t font-mono">
                        <span>Baseline: {imp.baseline_proficiency}%</span>
                        <span>Post-Intervention: {imp.post_proficiency !== null ? `${imp.post_proficiency}%` : "Awaiting sample"}</span>
                        <span>{imp.post_questions_evaluated} Qs evaluated</span>
                      </div>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>

            {/* Session Completion & Engagement Behavior */}
            <Card className="border shadow-sm">
              <CardHeader className="pb-3">
                <CardTitle className="text-base font-bold flex items-center gap-2">
                  <Clock className="h-4 w-4 text-primary" />
                  Session Completion & Engagement Behavior
                </CardTitle>
                <CardDescription className="text-xs">
                  Reliability metrics comparing fully completed interviews vs abandoned sessions.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4 text-xs">
                <div className="grid grid-cols-3 gap-2 text-center p-3 bg-muted/40 rounded-lg">
                  <div>
                    <span className="text-muted-foreground block text-[11px]">Completion Rate</span>
                    <span className="text-lg font-bold font-mono text-primary">
                      {data.completion_behavior.completion_rate}%
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground block text-[11px]">Avg Duration</span>
                    <span className="text-lg font-bold font-mono text-foreground">
                      {data.completion_behavior.avg_duration_minutes} min
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground block text-[11px]">Avg Qs / Sess</span>
                    <span className="text-lg font-bold font-mono text-foreground">
                      {data.completion_behavior.avg_questions_per_session}
                    </span>
                  </div>
                </div>

                <div className="space-y-2 border-t pt-2">
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">Completed Sessions Average Score:</span>
                    <span className="font-bold font-mono text-emerald-600 dark:text-emerald-400">
                      {data.completion_behavior.completed_avg_score}% ({data.completion_behavior.completed_sessions} sessions)
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">Abandoned / Incomplete Sessions Score:</span>
                    <span className="font-bold font-mono text-muted-foreground">
                      {data.completion_behavior.abandoned_avg_score}% ({data.completion_behavior.abandoned_sessions} sessions)
                    </span>
                  </div>
                </div>

                <div className="rounded bg-muted/60 p-2.5 text-[11px] text-muted-foreground">
                  <span className="font-semibold text-foreground">Recent vs Historical Baseline: </span>
                  {data.recent_vs_historical.verdict} ({data.recent_vs_historical.recent_average_score}% recent vs {data.recent_vs_historical.historical_average_score}% historical).
                </div>
              </CardContent>
            </Card>
          </div>

          {/* 9. Session-Level Evidence Audit Trail */}
          <section className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-foreground flex items-center gap-2">
                  <Search className="h-5 w-5 text-primary" />
                  Granular Evidence Audit Log
                </h2>
                <p className="text-xs text-muted-foreground">
                  Inspect the underlying database questions, difficulty adjustments, and evaluator feedback backing these metrics.
                </p>
              </div>
            </div>

            <Accordion type="single" collapsible className="space-y-2">
              {data.session_evidence.map((sess, idx) => (
                <AccordionItem key={sess.session_id} value={sess.session_id} className="border rounded-lg bg-card px-4">
                  <AccordionTrigger className="text-xs font-medium py-3 hover:no-underline">
                    <div className="flex items-center justify-between w-full pr-4">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="font-mono text-[10px]">
                          Session {idx + 1}
                        </Badge>
                        <span className="font-semibold text-foreground">{sess.interview_type}</span>
                        <span className="text-muted-foreground">
                          • {new Date(sess.start_time).toLocaleDateString()}
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        <Badge className="font-mono text-[11px]">
                          Score: {sess.score}%
                        </Badge>
                        <span className="text-[11px] text-muted-foreground">
                          {sess.questions.length} Questions
                        </span>
                      </div>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent className="pt-2 pb-4 space-y-3 text-xs border-t">
                    {sess.questions.map((q, qIdx) => (
                      <div key={q.question_id || qIdx} className="p-3 bg-muted/40 rounded-lg space-y-1.5 font-mono">
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="font-semibold text-foreground">
                            Q{qIdx + 1} ({q.difficulty}) • {q.skill_focus}
                          </span>
                          <span className="font-bold text-primary">Score: {q.score}%</span>
                        </div>
                        <p className="text-muted-foreground font-sans text-xs">
                          {q.question_text}
                        </p>
                        {q.feedback && (
                          <div className="text-[11px] text-foreground/80 bg-background/80 p-2 rounded border font-sans">
                            <span className="font-semibold text-foreground">Feedback: </span>
                            {q.feedback}
                          </div>
                        )}
                      </div>
                    ))}
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </section>
        </div>
      )}
    </div>
  )
}
