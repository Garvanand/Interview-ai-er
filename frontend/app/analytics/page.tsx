"use client"

import { useEffect, useState } from "react"
import { apiClient } from "@/lib/api-client"
import { getBrowserSupabaseClient } from "@/lib/supabase"

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  BarChart,
  Bar,
} from "recharts"

export default function AnalyticsPage() {
  const [scoreTrend, setScoreTrend] = useState<{ date: string, score: number }[]>([])
  const [categoryPerf, setCategoryPerf] = useState<{ skill: string, score: number }[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    async function loadData() {
      try {
        const supabase = getBrowserSupabaseClient()
        if (!supabase) return
        const { data: { user } } = await supabase.auth.getUser()
        if (!user) return
        const res = await apiClient.getUserSessions(user.id, 50)
        
        const sessions = res.sessions || []
        
        const sortedSessions = [...sessions].filter(s => s.status === 'completed' && s.score).sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime())
        
        const trendData = sortedSessions.map((s, idx) => ({
          date: `S${idx + 1}`,
          score: Math.round(s.score || 0)
        }))
        setScoreTrend(trendData)

        const categoryMap = {} as Record<string, { total: number, count: number }>
        sortedSessions.forEach(s => {
          if (!categoryMap[s.interview_type]) {
            categoryMap[s.interview_type] = { total: 0, count: 0 }
          }
          categoryMap[s.interview_type].total += s.score || 0
          categoryMap[s.interview_type].count += 1
        })
        const catData = Object.keys(categoryMap).map(k => ({
          skill: k,
          score: Math.round(categoryMap[k].total / categoryMap[k].count)
        }))
        setCategoryPerf(catData)

      } catch (err) {
        console.error(err)
      } finally {
        setIsLoading(false)
      }
    }
    loadData()
  }, [])

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <h1 className="text-2xl font-semibold">Analytics</h1>
      <p className="mt-1 text-sm text-foreground/70">Visualize performance and improvement over time.</p>
      {isLoading ? (
        <div className="mt-4 p-4 text-sm text-foreground/70">Loading analytics...</div>
      ) : scoreTrend.length === 0 ? (
        <div className="mt-4 p-4 text-sm text-foreground/70">No completed interviews to analyze yet.</div>
      ) : (
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <div className="rounded-lg border border-border bg-card p-4" role="region" aria-label="Score trend over time">
            <h2 className="text-sm font-semibold">Score Trend</h2>
            <div className="mt-2 h-56">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={scoreTrend} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="date" stroke="currentColor" fontSize={12} />
                  <YAxis domain={[0, 100]} stroke="currentColor" fontSize={12} />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="score" stroke="var(--color-primary)" strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="rounded-lg border border-border bg-card p-4" role="region" aria-label="Scores by category">
            <h2 className="text-sm font-semibold">Scores by Category</h2>
            <div className="mt-2 h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={categoryPerf} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="skill" stroke="currentColor" fontSize={12} />
                  <YAxis domain={[0, 100]} stroke="currentColor" fontSize={12} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="score" fill="var(--color-accent)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
