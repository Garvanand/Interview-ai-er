"use client"

import { useState, useEffect, useMemo } from 'react'
import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { 
  Brain, 
  Target, 
  TrendingUp, 
  TrendingDown, 
  Minus,
  AlertTriangle, 
  CheckCircle2, 
  Clock, 
  Sparkles, 
  Code2, 
  Terminal, 
  Layers, 
  Activity, 
  RefreshCw, 
  Play, 
  Check, 
  Info, 
  ArrowUpRight,
  ArrowDownRight,
  ShieldAlert,
  Flame,
  FileCheck2,
  Compass,
  AlertCircle
} from 'lucide-react'
import { 
  ResponsiveContainer, 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  Tooltip as RechartsTooltip, 
  CartesianGrid 
} from 'recharts'
import { apiClient, InterviewSession, CandidateSkillProfile, Recommendation } from '@/lib/api-client'
import { useAuth } from '@/hooks/use-auth'

export default function RedesignedDashboardPage() {
  const { userId, isLoading: authLoading } = useAuth({ redirectIfUnauthenticated: true })
  const [sessions, setSessions] = useState<InterviewSession[]>([])
  const [skillProfiles, setSkillProfiles] = useState<CandidateSkillProfile[]>([])
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  const [latestSessionDetails, setLatestSessionDetails] = useState<any | null>(null)
  const [previousSessionDetails, setPreviousSessionDetails] = useState<any | null>(null)

  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [currentUserId, setCurrentUserId] = useState<string | null>(null)

  useEffect(() => {
    if (!authLoading && userId) {
      loadDashboardData()
    } else if (!authLoading && !userId) {
      setIsLoading(false)
    }
  }, [authLoading, userId])

  const loadDashboardData = async (refreshOnly = false) => {
    if (refreshOnly) {
      setIsRefreshing(true)
    } else {
      setIsLoading(true)
    }
    setError(null)

    try {
      // 1. Use verified user identity from useAuth — never a hardcoded fallback
      if (!userId) {
        setError('You must be signed in to view your dashboard.')
        setIsLoading(false)
        setIsRefreshing(false)
        return
      }
      setCurrentUserId(userId)

      // 2. Fetch Sessions, Skills, and Recommendations concurrently
      const [sessionsRes, skillsRes, recsRes] = await Promise.allSettled([
        apiClient.getUserSessions(userId, 50),
        apiClient.getCandidateSkills(userId),
        apiClient.getRecommendations(userId)
      ])

      const fetchedSessions: InterviewSession[] = 
        sessionsRes.status === 'fulfilled' && sessionsRes.value?.sessions 
          ? sessionsRes.value.sessions 
          : []
      setSessions(fetchedSessions)

      let fetchedSkills: CandidateSkillProfile[] = 
        skillsRes.status === 'fulfilled' && skillsRes.value?.profiles 
          ? skillsRes.value.profiles 
          : []
      setSkillProfiles(fetchedSkills)

      let fetchedRecs: Recommendation[] = 
        recsRes.status === 'fulfilled' && recsRes.value?.recommendations 
          ? recsRes.value.recommendations 
          : []

      // If recommendations are empty and candidate has sessions or skills, trigger recommendation generation
      if (fetchedRecs.length === 0 && (fetchedSessions.length > 0 || fetchedSkills.length > 0)) {
        try {
          const latestId = fetchedSessions[0]?.id
          const genRes = await apiClient.generateRecommendations(userId, latestId)
          if (genRes?.recommendations) {
            fetchedRecs = genRes.recommendations
          }
        } catch {
          // Non-fatal
        }
      }
      setRecommendations(fetchedRecs)

      // 3. Fetch latest session details for Question-Level Evidence and Delta
      if (fetchedSessions.length > 0) {
        const latestId = fetchedSessions[0].id
        try {
          const details = await apiClient.getSessionDetails(latestId)
          setLatestSessionDetails(details?.data || details)
        } catch {
          setLatestSessionDetails(null)
        }

        // Fetch preceding session for delta comparison if available
        if (fetchedSessions.length > 1) {
          const prevId = fetchedSessions[1].id
          try {
            const prevDetails = await apiClient.getSessionDetails(prevId)
            setPreviousSessionDetails(prevDetails?.data || prevDetails)
          } catch {
            setPreviousSessionDetails(null)
          }
        } else {
          setPreviousSessionDetails(null)
        }
      } else {
        setLatestSessionDetails(null)
        setPreviousSessionDetails(null)
      }

    } catch (err: any) {
      setError(err?.message || "Failed to load candidate intelligence signals.")
    } finally {
      setIsLoading(false)
      setIsRefreshing(false)
    }
  }

  // Handle recommendation status changes
  const handleUpdateRecStatus = async (recId: string, newStatus: string) => {
    try {
      await apiClient.updateRecommendationStatus(recId, newStatus)
      setRecommendations(prev => 
        prev.map(r => r.id === recId ? { ...r, status: newStatus as any } : r)
      )
    } catch (err: any) {
      console.error("Failed to update recommendation status:", err)
    }
  }

  // ---------------------------------------------------------------------------
  // Derived Intelligence Computations
  // ---------------------------------------------------------------------------

  // 1. Overall Estimated Readiness
  const readinessMetrics = useMemo(() => {
    const completedSessions = sessions.filter(s => s.status === 'completed')
    
    // Calculate composite proficiency from longitudinal profiles if available
    let compositeScore = 0
    if (skillProfiles.length > 0) {
      const sum = skillProfiles.reduce((acc, p) => acc + (p.estimated_proficiency || 0), 0)
      compositeScore = Math.round(sum / skillProfiles.length)
    } else if (completedSessions.length > 0) {
      const sum = completedSessions.reduce((acc, s) => acc + (s.score || 0), 0)
      compositeScore = Math.round(sum / completedSessions.length)
    }

    // Reliability signal coverage: % of skills with medium or high confidence
    const highConfCount = skillProfiles.filter(p => 
      p.confidence === 'high confidence' || p.confidence === 'medium confidence'
    ).length
    const reliabilityPct = skillProfiles.length > 0 
      ? Math.round((highConfCount / skillProfiles.length) * 100) 
      : (completedSessions.length > 0 ? 60 : 0)

    // Readiness Band definition
    let readinessBand = "Calibration Required"
    let readinessColor = "text-muted-foreground"
    if (compositeScore >= 82) {
      readinessBand = "Production Ready (L5/Senior)"
      readinessColor = "text-emerald-500"
    } else if (compositeScore >= 68) {
      readinessBand = "Mid-Level Competency (L4)"
      readinessColor = "text-blue-500"
    } else if (compositeScore >= 50) {
      readinessBand = "Foundational Alignment (L3)"
      readinessColor = "text-amber-500"
    } else if (compositeScore > 0) {
      readinessBand = "Targeted Remediation Required"
      readinessColor = "text-rose-500"
    }

    const totalEvidenceCount = skillProfiles.reduce((acc, p) => acc + (p.evidence_count || 0), 0)

    return {
      compositeScore,
      readinessBand,
      readinessColor,
      reliabilityPct,
      totalEvidenceCount,
      completedSessionsCount: completedSessions.length
    }
  }, [sessions, skillProfiles])

  // 2. Strongest Skills & Areas Needing Attention
  const { strongestSkills, attentionSkills, weakSignalSkills } = useMemo(() => {
    const sorted = [...skillProfiles].sort((a, b) => b.estimated_proficiency - a.estimated_proficiency)
    
    const strongest = sorted.filter(p => p.estimated_proficiency >= 70 && p.evidence_count >= 1)
    const attention = sorted.filter(p => p.estimated_proficiency < 65 || p.improvement_trend === 'declining')
    const weakSignals = sorted.filter(p => 
      p.confidence === 'insufficient evidence' || p.confidence === 'low confidence' || p.evidence_count <= 2
    )

    return {
      strongestSkills: strongest,
      attentionSkills: attention,
      weakSignalSkills: weakSignals
    }
  }, [skillProfiles])

  // 3. Longitudinal Score Trend Data
  const scoreTrendData = useMemo(() => {
    const completed = [...sessions]
      .filter(s => s.status === 'completed' && s.start_time)
      .sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime())

    return completed.map((s, idx) => ({
      index: idx + 1,
      name: `Session ${idx + 1}`,
      date: new Date(s.start_time).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      score: Math.round(s.score || 0),
      type: s.interview_type
    }))
  }, [sessions])

  // 4. Delta: What Changed Since Previous Interview?
  const deltaComparison = useMemo(() => {
    if (sessions.length < 2) return null
    const latest = sessions[0]
    const previous = sessions[1]

    const scoreDelta = (latest.score || 0) - (previous.score || 0)
    
    return {
      latestScore: latest.score || 0,
      previousScore: previous.score || 0,
      scoreDelta: Math.round(scoreDelta),
      latestType: latest.interview_type,
      previousType: previous.interview_type,
      latestDate: new Date(latest.start_time).toLocaleDateString(),
      previousDate: new Date(previous.start_time).toLocaleDateString()
    }
  }, [sessions])

  // ---------------------------------------------------------------------------
  // Render: Loading State
  // ---------------------------------------------------------------------------
  if (isLoading) {
    return (
      <div className="container max-w-7xl mx-auto py-8 px-4 space-y-8">
        <div className="flex items-center justify-between pb-6 border-b border-border/40">
          <div className="space-y-2">
            <div className="h-8 w-64 bg-muted animate-pulse rounded" />
            <div className="h-4 w-96 bg-muted/60 animate-pulse rounded" />
          </div>
          <div className="h-10 w-36 bg-muted animate-pulse rounded" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="h-44 bg-muted/40 animate-pulse rounded-xl" />
          <div className="h-44 bg-muted/40 animate-pulse rounded-xl" />
          <div className="h-44 bg-muted/40 animate-pulse rounded-xl" />
        </div>
        <div className="h-96 bg-muted/30 animate-pulse rounded-xl" />
      </div>
    )
  }

  // ---------------------------------------------------------------------------
  // Render: Error State
  // ---------------------------------------------------------------------------
  if (error && sessions.length === 0 && skillProfiles.length === 0) {
    return (
      <div className="container max-w-4xl mx-auto py-16 px-4">
        <Card className="border-rose-500/30 bg-rose-500/5">
          <CardHeader>
            <div className="flex items-center gap-3 text-rose-500">
              <AlertCircle className="h-6 w-6" />
              <CardTitle>Unable to Load Candidate Intelligence</CardTitle>
            </div>
            <CardDescription className="text-muted-foreground mt-2">
              {error}
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-2 space-y-4">
            <p className="text-sm text-foreground/80">
              Ensure the Python backend service is active and the Supabase database connection is configured.
            </p>
            <div className="flex gap-3">
              <Button onClick={() => loadDashboardData()} variant="outline" className="gap-2">
                <RefreshCw className="h-4 w-4" /> Retry Query
              </Button>
              <Link href="/interview">
                <Button className="gap-2">
                  <Play className="h-4 w-4" /> Start Interview Session
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  // ---------------------------------------------------------------------------
  // Render: Empty State (Brand New Candidate)
  // ---------------------------------------------------------------------------
  const hasNoData = sessions.length === 0 && skillProfiles.length === 0

  return (
    <div className="min-h-screen bg-background text-foreground py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* =================================================================== */}
        {/* Telemetry Header & Architecture Indicator Bar                      */}
        {/* =================================================================== */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-border/60">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
                Candidate Skill Intelligence
              </h1>
              <Badge variant="outline" className="text-xs font-mono uppercase bg-muted/40 border-border">
                Telemetry v2.4
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground flex items-center gap-2">
              <span>Authoritative assessment engine</span>
              <span className="text-border">•</span>
              <span className="font-mono text-xs text-muted-foreground/80">
                Evaluation Model: Groq / openai/gpt-oss-120b Structured
              </span>
              <span className="text-border">•</span>
              <span className="font-mono text-xs text-muted-foreground/80">
                Orchestrator: Adaptive State Machine
              </span>
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link href="/analytics">
              <Button variant="outline" size="sm" className="gap-2 font-mono text-xs">
                <Activity className="h-3.5 w-3.5 text-primary" />
                Longitudinal Analytics
              </Button>
            </Link>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => loadDashboardData(true)} 
              disabled={isRefreshing}
              className="gap-2 font-mono text-xs"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
              {isRefreshing ? 'Syncing...' : 'Sync Evidence'}
            </Button>
            <Link href="/interview">
              <Button size="sm" className="gap-2 font-medium">
                <Play className="h-4 w-4 fill-current" />
                Launch Interview
              </Button>
            </Link>
          </div>
        </div>

        {/* =================================================================== */}
        {/* Empty State Banner                                                 */}
        {/* =================================================================== */}
        {hasNoData && (
          <Card className="border-dashed border-2 border-border bg-card/50 p-8 text-center space-y-4">
            <div className="mx-auto w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center text-primary">
              <Compass className="h-6 w-6" />
            </div>
            <div className="max-w-md mx-auto space-y-2">
              <h3 className="text-lg font-semibold">No Empirical Signals Recorded Yet</h3>
              <p className="text-sm text-muted-foreground">
                The AI assessment engine requires at least one evaluated interview to calibrate your longitudinal 
                skill proficiencies, baseline reliability intervals, and generate targeted practice drills.
              </p>
            </div>
            <div className="pt-2">
              <Link href="/interview">
                <Button className="gap-2">
                  <Play className="h-4 w-4" /> Start Baseline Diagnostic Interview
                </Button>
              </Link>
            </div>
          </Card>
        )}

        {/* =================================================================== */}
        {/* 1. "HOW AM I PERFORMING?" — Current Readiness Overview              */}
        {/* =================================================================== */}
        {!hasNoData && (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            
            {/* Primary Readiness Indicator */}
            <Card className="lg:col-span-2 border-border/80 bg-card shadow-sm flex flex-col justify-between">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono uppercase tracking-wider text-muted-foreground">
                    Estimated Production Readiness
                  </span>
                  <Badge variant="secondary" className="font-mono text-xs">
                    Confidence: {readinessMetrics.reliabilityPct}%
                  </Badge>
                </div>
                <div className="flex items-baseline gap-3 mt-2">
                  <span className="text-4xl font-extrabold tracking-tight">
                    {readinessMetrics.compositeScore}
                    <span className="text-lg font-normal text-muted-foreground">/100</span>
                  </span>
                  <span className={`text-sm font-semibold ${readinessMetrics.readinessColor}`}>
                    {readinessMetrics.readinessBand}
                  </span>
                </div>
              </CardHeader>

              <CardContent className="space-y-4 pt-1">
                <div>
                  <div className="flex justify-between text-xs text-muted-foreground mb-1.5 font-mono">
                    <span>Signal Calibration</span>
                    <span>{readinessMetrics.reliabilityPct}% High-Confidence Nodes</span>
                  </div>
                  <Progress value={readinessMetrics.reliabilityPct} className="h-2" />
                </div>

                <div className="grid grid-cols-2 gap-4 pt-2 border-t border-border/60 text-xs">
                  <div>
                    <span className="text-muted-foreground block">Completed Interviews</span>
                    <span className="text-base font-bold text-foreground">
                      {readinessMetrics.completedSessionsCount}
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground block">Empirical Evidence Points</span>
                    <span className="text-base font-bold text-foreground">
                      {readinessMetrics.totalEvidenceCount} Questions Evaluated
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Quick Readiness Breakdown Metric Cards */}
            <Card className="border-border/80 bg-card shadow-sm">
              <CardHeader className="pb-2">
                <span className="text-xs font-mono uppercase tracking-wider text-muted-foreground">
                  Verified Strength Count
                </span>
                <CardTitle className="text-2xl font-bold flex items-center gap-2 mt-1">
                  <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                  {strongestSkills.length} Skills
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-xs text-muted-foreground">
                <p>
                  Competencies meeting or exceeding the 70% production benchmark with active evidence backing.
                </p>
                {strongestSkills.length > 0 && (
                  <div className="pt-2 flex flex-wrap gap-1.5">
                    {strongestSkills.slice(0, 3).map(s => (
                      <Badge key={s.skill_name} variant="outline" className="text-[11px] border-emerald-500/30 text-emerald-400">
                        {s.skill_name}
                      </Badge>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="border-border/80 bg-card shadow-sm">
              <CardHeader className="pb-2">
                <span className="text-xs font-mono uppercase tracking-wider text-muted-foreground">
                  Attention Required
                </span>
                <CardTitle className="text-2xl font-bold flex items-center gap-2 mt-1">
                  <AlertTriangle className="h-5 w-5 text-amber-500" />
                  {attentionSkills.length} Skills
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-xs text-muted-foreground">
                <p>
                  Domains displaying performance below 65% or showing stagnant or declining trajectories.
                </p>
                {attentionSkills.length > 0 && (
                  <div className="pt-2 flex flex-wrap gap-1.5">
                    {attentionSkills.slice(0, 3).map(s => (
                      <Badge key={s.skill_name} variant="outline" className="text-[11px] border-amber-500/30 text-amber-400">
                        {s.skill_name}
                      </Badge>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

          </div>
        )}

        {/* =================================================================== */}
        {/* Core Tabbed Intelligence Views                                      */}
        {/* =================================================================== */}
        {!hasNoData && (
          <Tabs defaultValue="overview" className="w-full space-y-6">
            <TabsList className="bg-muted/40 p-1 border border-border/80 rounded-lg">
              <TabsTrigger value="overview" className="gap-2 font-medium">
                <Brain className="h-4 w-4" /> Intelligence Overview
              </TabsTrigger>
              <TabsTrigger value="progression" className="gap-2 font-medium">
                <TrendingUp className="h-4 w-4" /> Progression & Score Trend
              </TabsTrigger>
              <TabsTrigger value="recommendations" className="gap-2 font-medium">
                <Flame className="h-4 w-4" /> Recommended Actions ({recommendations.filter(r => r.status === 'PENDING').length})
              </TabsTrigger>
              <TabsTrigger value="evidence" className="gap-2 font-medium">
                <FileCheck2 className="h-4 w-4" /> Latest Session Delta & Evidence
              </TabsTrigger>
            </TabsList>

            {/* ------------------------------------------------------------- */}
            {/* TAB 1: Intelligence Overview                                  */}
            {/* ------------------------------------------------------------- */}
            <TabsContent value="overview" className="space-y-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

                {/* 2. "WHAT SKILLS ARE STRONGEST?" */}
                <Card className="border-border/80 bg-card">
                  <CardHeader className="pb-3 border-b border-border/40">
                    <div className="flex items-center justify-between">
                      <div>
                        <CardTitle className="text-base font-semibold flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                          Top Verified Proficiencies
                        </CardTitle>
                        <CardDescription className="text-xs">
                          Empirically validated high competency signals (&ge; 70%)
                        </CardDescription>
                      </div>
                      <Badge variant="outline" className="font-mono text-xs">
                        {strongestSkills.length} Verified
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="pt-4 divide-y divide-border/40">
                    {strongestSkills.length === 0 ? (
                      <p className="text-sm text-muted-foreground py-4 text-center">
                        No skills have crossed the 70% threshold yet. Continue practicing to establish verified strengths.
                      </p>
                    ) : (
                      strongestSkills.map(skill => (
                        <div key={skill.skill_name} className="py-3 first:pt-0 last:pb-0 space-y-2">
                          <div className="flex items-center justify-between text-sm">
                            <span className="font-semibold text-foreground">{skill.skill_name}</span>
                            <div className="flex items-center gap-2">
                              <Badge variant="secondary" className="font-mono text-xs">
                                {skill.confidence}
                              </Badge>
                              <span className="font-bold text-emerald-500 font-mono">
                                {skill.estimated_proficiency}%
                              </span>
                            </div>
                          </div>
                          <Progress value={skill.estimated_proficiency} className="h-1.5" />
                          <div className="flex justify-between text-[11px] text-muted-foreground font-mono">
                            <span>Evidence: {skill.evidence_count} interactions</span>
                            <span>Recent Avg: {skill.recent_performance}%</span>
                          </div>
                        </div>
                      ))
                    )}
                  </CardContent>
                </Card>

                {/* 3. "WHAT SKILLS NEED ATTENTION & WEAK-SIGNAL ALERTS?" */}
                <Card className="border-border/80 bg-card">
                  <CardHeader className="pb-3 border-b border-border/40">
                    <div className="flex items-center justify-between">
                      <div>
                        <CardTitle className="text-base font-semibold flex items-center gap-2">
                          <AlertTriangle className="h-4 w-4 text-amber-500" />
                          Areas Requiring Attention
                        </CardTitle>
                        <CardDescription className="text-xs">
                          Skills below target readiness threshold (&lt; 65%)
                        </CardDescription>
                      </div>
                      <Badge variant="outline" className="font-mono text-xs border-amber-500/40 text-amber-400">
                        {attentionSkills.length} Deficiencies
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="pt-4 divide-y divide-border/40">
                    {attentionSkills.length === 0 ? (
                      <p className="text-sm text-muted-foreground py-4 text-center">
                        No critical deficiencies detected across evaluated competencies.
                      </p>
                    ) : (
                      attentionSkills.map(skill => (
                        <div key={skill.skill_name} className="py-3 first:pt-0 last:pb-0 space-y-2">
                          <div className="flex items-center justify-between text-sm">
                            <span className="font-semibold text-foreground">{skill.skill_name}</span>
                            <div className="flex items-center gap-2">
                              {skill.improvement_trend === 'declining' && (
                                <span className="flex items-center text-xs text-rose-500 font-mono">
                                  <TrendingDown className="h-3.5 w-3.5 mr-0.5" /> Declining
                                </span>
                              )}
                              <span className="font-bold text-amber-500 font-mono">
                                {skill.estimated_proficiency}%
                              </span>
                            </div>
                          </div>
                          <Progress value={skill.estimated_proficiency} className="h-1.5" />
                          <div className="flex justify-between text-[11px] text-muted-foreground font-mono">
                            <span>Evaluated: {skill.evidence_count} times</span>
                            <span>Historical: {skill.historical_performance}%</span>
                          </div>
                        </div>
                      ))
                    )}
                  </CardContent>
                </Card>

              </div>

              {/* Weak-Signal Warnings Panel */}
              {weakSignalSkills.length > 0 && (
                <Card className="border-border/80 bg-muted/20 border-l-4 border-l-amber-500">
                  <CardHeader className="pb-2">
                    <div className="flex items-center gap-2 text-amber-500 font-semibold text-sm">
                      <ShieldAlert className="h-4 w-4" />
                      Weak-Signal Calibration Alert
                    </div>
                    <CardDescription className="text-xs">
                      The AI model has collected sparse interaction evidence for the following domains. Estimated proficiencies carry high uncertainty intervals.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="pt-2">
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                      {weakSignalSkills.map(ws => (
                        <div key={ws.skill_name} className="bg-card p-3 rounded-lg border border-border/60 space-y-1">
                          <div className="flex items-center justify-between text-xs">
                            <span className="font-semibold">{ws.skill_name}</span>
                            <span className="font-mono text-muted-foreground">{ws.evidence_count} items</span>
                          </div>
                          <p className="text-[11px] text-muted-foreground font-mono">
                            Model Confidence: <span className="text-amber-400">{ws.confidence}</span>
                          </p>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            {/* ------------------------------------------------------------- */}
            {/* TAB 2: "AM I IMPROVING?" — Progression & Score Trend         */}
            {/* ------------------------------------------------------------- */}
            <TabsContent value="progression" className="space-y-6">
              
              {/* Longitudinal Score Chart */}
              <Card className="border-border/80 bg-card">
                <CardHeader className="pb-3 border-b border-border/40">
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-base font-semibold flex items-center gap-2">
                        <TrendingUp className="h-4 w-4 text-primary" />
                        Session Score Trajectory
                      </CardTitle>
                      <CardDescription className="text-xs">
                        Empirical scoring evolution over time across full interview sessions
                      </CardDescription>
                    </div>
                    {deltaComparison && (
                      <Badge variant="outline" className={`font-mono text-xs ${deltaComparison.scoreDelta >= 0 ? 'text-emerald-400 border-emerald-500/30' : 'text-rose-400 border-rose-500/30'}`}>
                        {deltaComparison.scoreDelta >= 0 ? `+${deltaComparison.scoreDelta}` : deltaComparison.scoreDelta}% vs Prev Session
                      </Badge>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="pt-6">
                  {scoreTrendData.length < 2 ? (
                    <div className="h-64 flex flex-col items-center justify-center text-center p-6 space-y-2 text-muted-foreground">
                      <Clock className="h-8 w-8 text-muted-foreground/60" />
                      <p className="text-sm font-medium">Insufficient Timeline Data</p>
                      <p className="text-xs max-w-sm">
                        Complete at least two full interview sessions to unlock trajectory curvature and regression analysis.
                      </p>
                    </div>
                  ) : (
                    <div className="h-64 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={scoreTrendData} margin={{ top: 10, right: 20, left: -20, bottom: 0 }}>
                          <defs>
                            <linearGradient id="scoreGradient" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#1e3a8a" stopOpacity={0.8}/>
                              <stop offset="95%" stopColor="#1e3a8a" stopOpacity={0}/>
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="#262626" opacity={0.3} />
                          <XAxis dataKey="date" stroke="#737373" fontSize={11} tickLine={false} />
                          <YAxis stroke="#737373" fontSize={11} tickLine={false} domain={[0, 100]} />
                          <RechartsTooltip 
                            contentStyle={{ 
                              backgroundColor: '#171717', 
                              borderColor: '#404040', 
                              borderRadius: '8px', 
                              fontSize: '12px' 
                            }} 
                          />
                          <Area 
                            type="monotone" 
                            dataKey="score" 
                            stroke="#3b82f6" 
                            strokeWidth={2} 
                            fillOpacity={1} 
                            fill="url(#scoreGradient)" 
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Comprehensive Skill Progression Matrix */}
              <Card className="border-border/80 bg-card">
                <CardHeader className="pb-3 border-b border-border/40">
                  <CardTitle className="text-base font-semibold">
                    Longitudinal Skill Progression Matrix
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Rigorous mathematical aggregation of recent vs historical performances
                  </CardDescription>
                </CardHeader>
                <CardContent className="pt-4 p-0">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-muted/30 text-muted-foreground uppercase font-mono text-[10px] border-b border-border/40">
                        <tr>
                          <th className="py-3 px-4">Skill Domain</th>
                          <th className="py-3 px-4">Estimated Proficiency</th>
                          <th className="py-3 px-4">Confidence Level</th>
                          <th className="py-3 px-4">Evidence Count</th>
                          <th className="py-3 px-4">Recent vs Historical</th>
                          <th className="py-3 px-4">Trajectory Trend</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/40 font-mono">
                        {skillProfiles.map(sp => {
                          const delta = sp.historical_performance > 0 
                            ? Math.round(sp.recent_performance - sp.historical_performance)
                            : 0

                          return (
                            <tr key={sp.skill_name} className="hover:bg-muted/20 transition-colors">
                              <td className="py-3 px-4 font-sans font-medium text-foreground">
                                {sp.skill_name}
                              </td>
                              <td className="py-3 px-4">
                                <span className="font-bold text-foreground">
                                  {sp.estimated_proficiency}%
                                </span>
                              </td>
                              <td className="py-3 px-4">
                                <Badge variant="outline" className="text-[10px] uppercase">
                                  {sp.confidence}
                                </Badge>
                              </td>
                              <td className="py-3 px-4 text-muted-foreground">
                                {sp.evidence_count} signals
                              </td>
                              <td className="py-3 px-4 text-muted-foreground">
                                {sp.recent_performance}% / {sp.historical_performance}%
                              </td>
                              <td className="py-3 px-4">
                                {sp.improvement_trend === 'improving' && (
                                  <span className="text-emerald-400 flex items-center gap-1 font-semibold">
                                    <TrendingUp className="h-3.5 w-3.5" /> Improving (+{delta}%)
                                  </span>
                                )}
                                {sp.improvement_trend === 'declining' && (
                                  <span className="text-rose-400 flex items-center gap-1 font-semibold">
                                    <TrendingDown className="h-3.5 w-3.5" /> Declining ({delta}%)
                                  </span>
                                )}
                                {sp.improvement_trend === 'stable' && (
                                  <span className="text-blue-400 flex items-center gap-1">
                                    <Minus className="h-3.5 w-3.5" /> Stable
                                  </span>
                                )}
                                {sp.improvement_trend === 'neutral' && (
                                  <span className="text-muted-foreground flex items-center gap-1">
                                    <Minus className="h-3.5 w-3.5" /> Neutral
                                  </span>
                                )}
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>

            </TabsContent>

            {/* ------------------------------------------------------------- */}
            {/* TAB 3: "WHAT SHOULD I PRACTICE NEXT?" — Recommendations       */}
            {/* ------------------------------------------------------------- */}
            <TabsContent value="recommendations" className="space-y-6">
              <div className="flex items-center justify-between pb-2">
                <div>
                  <h3 className="text-lg font-bold text-foreground flex items-center gap-2">
                    <Sparkles className="h-5 w-5 text-primary" />
                    Personalized Next Actions from Evidence
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    Deterministic pedagogical interventions derived from observed candidate evaluations.
                  </p>
                </div>
                <Badge variant="outline" className="font-mono text-xs">
                  {recommendations.length} Active Directives
                </Badge>
              </div>

              {recommendations.length === 0 ? (
                <Card className="p-8 text-center space-y-3 bg-card/60">
                  <Target className="h-8 w-8 mx-auto text-muted-foreground" />
                  <h4 className="font-semibold text-sm">No Pending Recommendations</h4>
                  <p className="text-xs text-muted-foreground max-w-md mx-auto">
                    All current directives have been accepted or completed. Run another interview session to synthesize new candidate interventions.
                  </p>
                </Card>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {recommendations.map(rec => {
                    const isPending = rec.status === 'PENDING'
                    const isAccepted = rec.status === 'ACCEPTED'
                    const isCompleted = rec.status === 'COMPLETED'

                    let priorityBadgeColor = "border-border text-muted-foreground"
                    if (rec.priority === 'CRITICAL') priorityBadgeColor = "border-rose-500/40 text-rose-400 bg-rose-500/10"
                    if (rec.priority === 'HIGH') priorityBadgeColor = "border-amber-500/40 text-amber-400 bg-amber-500/10"
                    if (rec.priority === 'MEDIUM') priorityBadgeColor = "border-blue-500/40 text-blue-400 bg-blue-500/10"

                    return (
                      <Card key={rec.id} className="border-border/80 bg-card flex flex-col justify-between shadow-sm">
                        <CardHeader className="pb-3 border-b border-border/40">
                          <div className="flex items-center justify-between gap-2 mb-1.5">
                            <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                              {rec.strategy.replace('_', ' ')}
                            </span>
                            <div className="flex items-center gap-2">
                              <Badge variant="outline" className={`font-mono text-[10px] uppercase ${priorityBadgeColor}`}>
                                {rec.priority}
                              </Badge>
                              <Badge variant="secondary" className="font-mono text-[10px] uppercase">
                                {rec.status}
                              </Badge>
                            </div>
                          </div>
                          <CardTitle className="text-base font-bold text-foreground">
                            {rec.recommended_activity?.title || `${rec.target_skill} Practice`}
                          </CardTitle>
                          <CardDescription className="text-xs text-foreground/80 font-medium">
                            Target Skill: <span className="text-primary font-semibold">{rec.target_skill}</span>
                          </CardDescription>
                        </CardHeader>

                        <CardContent className="pt-4 space-y-4 text-xs">
                          {/* Reason */}
                          <div className="space-y-1">
                            <span className="font-mono uppercase text-[10px] text-muted-foreground tracking-wider block">
                              Explainable Rationale
                            </span>
                            <p className="text-muted-foreground leading-relaxed">
                              {rec.reason}
                            </p>
                          </div>

                          {/* Learning Objective */}
                          <div className="bg-muted/30 p-2.5 rounded-lg border border-border/60 space-y-1">
                            <span className="font-mono uppercase text-[10px] text-muted-foreground tracking-wider block">
                              Expected Learning Objective
                            </span>
                            <p className="text-foreground/90 font-medium leading-normal">
                              {rec.expected_learning_objective}
                            </p>
                          </div>

                          {/* Progression Stages or Remediation Steps if present */}
                          {rec.recommended_activity?.progression_stages && (
                            <div className="space-y-1.5">
                              <span className="font-mono uppercase text-[10px] text-muted-foreground tracking-wider block">
                                Recommended Stages
                              </span>
                              <ul className="list-disc list-inside text-muted-foreground space-y-0.5">
                                {rec.recommended_activity.progression_stages.map((st: string, idx: number) => (
                                  <li key={idx}>{st}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {rec.recommended_activity?.remediation_steps && (
                            <div className="space-y-1.5">
                              <span className="font-mono uppercase text-[10px] text-muted-foreground tracking-wider block">
                                Remediation Steps
                              </span>
                              <ul className="list-disc list-inside text-muted-foreground space-y-0.5">
                                {rec.recommended_activity.remediation_steps.map((st: string, idx: number) => (
                                  <li key={idx}>{st}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {/* Interactive Status Actions */}
                          <div className="pt-2 flex items-center justify-between border-t border-border/40">
                            <span className="font-mono text-[10px] text-muted-foreground">
                              Baseline: {rec.baseline_proficiency}%
                            </span>
                            <div className="flex gap-2">
                              {isPending && (
                                <Button 
                                  size="sm" 
                                  variant="outline" 
                                  onClick={() => handleUpdateRecStatus(rec.id, 'ACCEPTED')}
                                  className="h-7 text-xs font-mono"
                                >
                                  Accept Action
                                </Button>
                              )}
                              {(isPending || isAccepted) && (
                                <Button 
                                  size="sm" 
                                  onClick={() => handleUpdateRecStatus(rec.id, 'COMPLETED')}
                                  className="h-7 text-xs font-mono gap-1"
                                >
                                  <Check className="h-3.5 w-3.5" /> Mark Done
                                </Button>
                              )}
                              {isCompleted && (
                                <span className="font-mono text-emerald-400 text-xs flex items-center gap-1">
                                  <CheckCircle2 className="h-3.5 w-3.5" /> Action Logged
                                </span>
                              )}
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    )
                  })}
                </div>
              )}
            </TabsContent>

            {/* ------------------------------------------------------------- */}
            {/* TAB 4: "WHAT CHANGED SINCE MY PREVIOUS INTERVIEW?"             */}
            {/* ------------------------------------------------------------- */}
            <TabsContent value="evidence" className="space-y-6">
              
              {/* Comparative Delta Summary */}
              {deltaComparison ? (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <Card className="border-border/80 bg-card">
                    <CardHeader className="pb-2">
                      <span className="text-xs font-mono uppercase tracking-wider text-muted-foreground">
                        Overall Score Delta
                      </span>
                      <CardTitle className="text-2xl font-bold flex items-center gap-2 mt-1">
                        {deltaComparison.scoreDelta >= 0 ? (
                          <ArrowUpRight className="h-6 w-6 text-emerald-500" />
                        ) : (
                          <ArrowDownRight className="h-6 w-6 text-rose-500" />
                        )}
                        {deltaComparison.scoreDelta >= 0 ? `+${deltaComparison.scoreDelta}` : deltaComparison.scoreDelta}%
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="text-xs text-muted-foreground font-mono">
                      <span>Latest: {deltaComparison.latestScore}%</span>
                      <span className="mx-2">•</span>
                      <span>Prev: {deltaComparison.previousScore}%</span>
                    </CardContent>
                  </Card>

                  <Card className="border-border/80 bg-card">
                    <CardHeader className="pb-2">
                      <span className="text-xs font-mono uppercase tracking-wider text-muted-foreground">
                        Interview Domain Progression
                      </span>
                      <CardTitle className="text-lg font-bold mt-1 truncate">
                        {deltaComparison.latestType}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="text-xs text-muted-foreground font-mono">
                      <span>Preceded by {deltaComparison.previousType}</span>
                    </CardContent>
                  </Card>

                  <Card className="border-border/80 bg-card">
                    <CardHeader className="pb-2">
                      <span className="text-xs font-mono uppercase tracking-wider text-muted-foreground">
                        Recency Interval
                      </span>
                      <CardTitle className="text-lg font-bold mt-1">
                        {deltaComparison.latestDate}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="text-xs text-muted-foreground font-mono">
                      <span>Previous: {deltaComparison.previousDate}</span>
                    </CardContent>
                  </Card>
                </div>
              ) : (
                <Card className="p-4 bg-muted/20 border-border text-xs text-muted-foreground font-mono text-center">
                  Only one interview session recorded so far. A comparative delta will automatically populate once your second interview concludes.
                </Card>
              )}

              {/* Latest Interview Synthesis Card */}
              {latestSessionDetails && latestSessionDetails.session && (
                <Card className="border-border/80 bg-card">
                  <CardHeader className="pb-3 border-b border-border/40">
                    <div className="flex items-center justify-between">
                      <div>
                        <CardTitle className="text-base font-semibold flex items-center gap-2">
                          <Activity className="h-4 w-4 text-primary" />
                          Latest Session Synthesis
                        </CardTitle>
                        <CardDescription className="text-xs font-mono">
                          Session ID: {latestSessionDetails.session.id} • Score: {latestSessionDetails.session.score}%
                        </CardDescription>
                      </div>
                      <Badge variant="outline" className="font-mono text-xs">
                        {latestSessionDetails.statistics?.answered_questions || 0} Questions Answered
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="pt-4 space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
                      <div className="bg-muted/30 p-3 rounded-lg border border-border/60">
                        <span className="text-muted-foreground block mb-1">Completion Rate</span>
                        <span className="text-base font-bold text-foreground">
                          {Math.round(latestSessionDetails.statistics?.completion_rate || 100)}%
                        </span>
                      </div>
                      <div className="bg-muted/30 p-3 rounded-lg border border-border/60">
                        <span className="text-muted-foreground block mb-1">Total Questions Analyzed</span>
                        <span className="text-base font-bold text-foreground">
                          {latestSessionDetails.questions?.length || 0}
                        </span>
                      </div>
                      <div className="bg-muted/30 p-3 rounded-lg border border-border/60">
                        <span className="text-muted-foreground block mb-1">Security / Integrity Score</span>
                        <span className="text-base font-bold text-emerald-400">
                          {latestSessionDetails.session.security_score || 100}% Clean
                        </span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Question-Level Evidence Accordion */}
              {latestSessionDetails && latestSessionDetails.questions && latestSessionDetails.questions.length > 0 && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-bold text-foreground flex items-center gap-2">
                      <Terminal className="h-4 w-4 text-primary" />
                      Granular Question-Level Evidence
                    </h4>
                    <span className="text-xs text-muted-foreground font-mono">
                      {latestSessionDetails.questions.length} interaction artifacts
                    </span>
                  </div>

                  <Accordion type="single" collapsible className="w-full space-y-3">
                    {latestSessionDetails.questions.map((q: any, index: number) => {
                      const evalScore = q.evaluation_score || q.code_evaluation_score || 0
                      const evalDetails = q.evaluation_details || q.code_evaluation_details || {}
                      const isCode = Boolean(q.code_text || q.programming_language)

                      return (
                        <AccordionItem 
                          key={q.id || index} 
                          value={`q-${index}`} 
                          className="bg-card border border-border/80 rounded-lg px-4 overflow-hidden"
                        >
                          <AccordionTrigger className="hover:no-underline py-3">
                            <div className="flex items-center justify-between w-full pr-4 text-left">
                              <div className="flex items-center gap-3">
                                <span className="font-mono text-xs font-bold text-muted-foreground">
                                  Q{index + 1}
                                </span>
                                <span className="text-sm font-semibold text-foreground line-clamp-1 max-w-md">
                                  {q.question_text}
                                </span>
                              </div>
                              <div className="flex items-center gap-2">
                                {isCode && (
                                  <Badge variant="outline" className="font-mono text-[10px]">
                                    {q.programming_language || 'code'}
                                  </Badge>
                                )}
                                <span className={`font-mono text-xs font-bold ${evalScore >= 75 ? 'text-emerald-400' : evalScore >= 55 ? 'text-amber-400' : 'text-rose-400'}`}>
                                  {evalScore}/100
                                </span>
                              </div>
                            </div>
                          </AccordionTrigger>

                          <AccordionContent className="pt-2 pb-4 space-y-3 text-xs border-t border-border/40">
                            {/* Question prompt */}
                            <div>
                              <span className="font-mono uppercase text-[10px] text-muted-foreground block mb-1">
                                Full Question Prompt
                              </span>
                              <p className="text-foreground/90 font-medium">
                                {q.question_text}
                              </p>
                            </div>

                            {/* Candidate Submitted Response / Code */}
                            {q.answer_text && (
                              <div>
                                <span className="font-mono uppercase text-[10px] text-muted-foreground block mb-1">
                                  Candidate Articulated Answer
                                </span>
                                <div className="bg-muted/30 p-3 rounded border border-border/60 text-muted-foreground font-mono text-xs leading-relaxed whitespace-pre-wrap">
                                  {q.answer_text}
                                </div>
                              </div>
                            )}

                            {q.code_text && (
                              <div>
                                <span className="font-mono uppercase text-[10px] text-muted-foreground block mb-1">
                                  Candidate Submitted Code ({q.programming_language || 'code'})
                                </span>
                                <pre className="bg-black/40 text-emerald-300 p-3 rounded border border-border/60 font-mono text-xs overflow-x-auto">
                                  {q.code_text}
                                </pre>
                              </div>
                            )}

                            {/* Granular Model Evaluation Breakdown */}
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2">
                              {evalDetails.correctness !== undefined && (
                                <div className="bg-muted/20 p-2 rounded border border-border/40">
                                  <span className="text-[10px] text-muted-foreground block font-mono">Correctness</span>
                                  <span className="font-bold text-foreground font-mono">{evalDetails.correctness}/100</span>
                                </div>
                              )}
                              {evalDetails.algorithm_quality !== undefined && (
                                <div className="bg-muted/20 p-2 rounded border border-border/40">
                                  <span className="text-[10px] text-muted-foreground block font-mono">Algorithm Quality</span>
                                  <span className="font-bold text-foreground font-mono">{evalDetails.algorithm_quality}/100</span>
                                </div>
                              )}
                              {evalDetails.readability !== undefined && (
                                <div className="bg-muted/20 p-2 rounded border border-border/40">
                                  <span className="text-[10px] text-muted-foreground block font-mono">Readability</span>
                                  <span className="font-bold text-foreground font-mono">{evalDetails.readability}/100</span>
                                </div>
                              )}
                              {evalDetails.technical_accuracy !== undefined && (
                                <div className="bg-muted/20 p-2 rounded border border-border/40">
                                  <span className="text-[10px] text-muted-foreground block font-mono">Technical Accuracy</span>
                                  <span className="font-bold text-foreground font-mono">{evalDetails.technical_accuracy}/100</span>
                                </div>
                              )}
                              {evalDetails.communication !== undefined && (
                                <div className="bg-muted/20 p-2 rounded border border-border/40">
                                  <span className="text-[10px] text-muted-foreground block font-mono">Communication</span>
                                  <span className="font-bold text-foreground font-mono">{evalDetails.communication}/100</span>
                                </div>
                              )}
                            </div>

                            {/* Evaluation Summary & Evidence */}
                            {(q.evaluation_feedback || evalDetails.evidence) && (
                              <div className="bg-primary/5 p-3 rounded border border-primary/20 space-y-1">
                                <span className="font-mono text-[10px] uppercase text-primary tracking-wider font-semibold block">
                                  AI Model Feedback & Evidence
                                </span>
                                <p className="text-foreground/80 leading-relaxed">
                                  {q.evaluation_feedback || evalDetails.evidence}
                                </p>
                              </div>
                            )}
                          </AccordionContent>
                        </AccordionItem>
                      )
                    })}
                  </Accordion>
                </div>
              )}

            </TabsContent>
          </Tabs>
        )}

      </div>
    </div>
  )
}
