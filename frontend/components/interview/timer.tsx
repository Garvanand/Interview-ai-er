"use client"

import { useEffect, useRef, useState } from "react"
import { Button } from "@/components/ui/button"

export function InterviewTimer({ seconds = 900 }: { seconds?: number }) {
  const [remaining, setRemaining] = useState(seconds)
  const [running, setRunning] = useState(false)
  const intervalRef = useRef<number | null>(null)

  useEffect(() => {
    if (!running) return
    intervalRef.current = window.setInterval(() => {
      setRemaining((r) => Math.max(0, r - 1))
    }, 1000)
    return () => {
      if (intervalRef.current) window.clearInterval(intervalRef.current)
    }
  }, [running])

  useEffect(() => {
    if (remaining === 0) setRunning(false)
  }, [remaining])

  const mm = String(Math.floor(remaining / 60)).padStart(2, "0")
  const ss = String(remaining % 60).padStart(2, "0")

  return (
    <div className="flex items-center gap-3" aria-live="polite">
      <div className="rounded-md border border-border bg-muted px-3 py-2 font-mono">
        {mm}:{ss}
      </div>
      <Button size="sm" onClick={() => setRunning((v) => !v)}>
        {running ? "Pause" : "Start"}
      </Button>
      <Button size="sm" variant="secondary" onClick={() => setRemaining(seconds)}>
        Reset
      </Button>
    </div>
  )
}
