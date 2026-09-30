"use client"

import { useEffect, useState } from 'react'
import { apiClient } from '@/lib/api-client'
import { getBrowserSupabaseClient } from '@/lib/supabase'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface InterviewSession {
  id: string
  interview_type: string
  start_time: string
  score?: number
  status: string
}

export default function HistoryPage() {
  const [sessions, setSessions] = useState<InterviewSession[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    async function fetchHistory() {
      try {
        const supabase = getBrowserSupabaseClient()
        if (!supabase) throw new Error("No database connection")
        const { data: { user } } = await supabase.auth.getUser()
        if (!user) throw new Error("Not logged in")
        const res = await apiClient.getUserSessions(user.id, 50)
        if (res.sessions) {
          setSessions(res.sessions)
        }
      } catch (err) {
        console.error(err)
      } finally {
        setIsLoading(false)
      }
    }
    fetchHistory()
  }, [])

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <h1 className="text-2xl font-semibold">History</h1>
      <p className="mt-1 text-sm text-foreground/70">Your past interviews will appear here.</p>
      
      {isLoading ? (
        <div className="mt-4 rounded-lg border border-border bg-card p-6 text-sm text-foreground/70">Loading...</div>
      ) : sessions.length === 0 ? (
        <div className="mt-4 rounded-lg border border-border bg-card p-6 text-sm text-foreground/70">No history yet.</div>
      ) : (
        <div className="mt-4 space-y-4">
          {sessions.map(session => (
            <Card key={session.id}>
              <CardContent className="p-4 flex justify-between items-center">
                <div>
                  <p className="font-semibold">{session.interview_type} Interview</p>
                  <p className="text-sm text-muted-foreground">{new Date(session.start_time).toLocaleString()}</p>
                </div>
                <div className="flex gap-4 items-center">
                  <Badge variant={session.status === 'completed' ? 'default' : 'secondary'}>{session.status}</Badge>
                  {session.score !== undefined && session.score !== null && (
                    <div className="font-bold text-lg">{Math.round(session.score)}/100</div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
