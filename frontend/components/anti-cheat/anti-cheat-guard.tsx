"use client"

import { useEffect, useRef, useState } from "react"
import { cn } from "@/lib/utils"

type Props = {
  className?: string
  onFlag?: (flag: string) => void
  enableWebcam?: boolean
  enableTypingAnalysis?: boolean
  enableDevtoolsDetection?: boolean
}

export function AntiCheatGuard({
  className,
  onFlag,
  enableWebcam,
  enableTypingAnalysis,
  enableDevtoolsDetection,
}: Props) {
  const [active, setActive] = useState(true)
  const keystrokesRef = useRef<number[]>([])
  const videoRef = useRef<HTMLVideoElement | null>(null)

  useEffect(() => {
    function handleBlur() {
      if (!active) return
      onFlag?.("Window blur/tab switch detected")
    }
    function handleVisibility() {
      if (!active) return
      if (document.hidden) onFlag?.("Page hidden detected")
    }
    window.addEventListener("blur", handleBlur)
    document.addEventListener("visibilitychange", handleVisibility)
    return () => {
      window.removeEventListener("blur", handleBlur)
      document.removeEventListener("visibilitychange", handleVisibility)
    }
  }, [onFlag, active])

  useEffect(() => {
    if (!enableDevtoolsDetection) return
    if (!active) return
    let prev = 0
    const interval = setInterval(() => {
      const widthDiff = window.outerWidth - window.innerWidth
      const heightDiff = window.outerHeight - window.innerHeight
      const open = widthDiff > 160 || heightDiff > 160
      if (Number(open) !== prev) {
        prev = Number(open)
        if (open) onFlag?.("Devtools suspected open")
      }
    }, 1000)
    return () => clearInterval(interval)
  }, [enableDevtoolsDetection, onFlag, active])

  useEffect(() => {
    if (!enableTypingAnalysis) return
    if (!active) return
    function onKeydown(e: KeyboardEvent) {
      keystrokesRef.current.push(Date.now())
      const arr = keystrokesRef.current.slice(-10)
      if (arr.length >= 5) {
        const deltas = arr.slice(1).map((t, i) => t - arr[i])
        const avg = deltas.reduce((a, b) => a + b, 0) / deltas.length
        if (avg < 40) onFlag?.("Suspicious rapid typing cadence")
      }
      const k = e.key?.toLowerCase()
      const devtoolsCombo =
        k === "f12" || ((e.ctrlKey || e.metaKey) && e.shiftKey && (k === "i" || k === "j" || k === "c"))
      if (devtoolsCombo) onFlag?.("Devtools hotkey detected")
    }
    function onPaste(e: ClipboardEvent) {
      const text = e.clipboardData?.getData("text") || ""
      if (text && text.length > 50) onFlag?.("Large paste detected")
    }
    window.addEventListener("keydown", onKeydown)
    window.addEventListener("paste", onPaste as any)
    return () => {
      window.removeEventListener("keydown", onKeydown)
      window.removeEventListener("paste", onPaste as any)
    }
  }, [enableTypingAnalysis, onFlag, active])

  useEffect(() => {
    if (!enableWebcam) return
    let stream: MediaStream | null = null
    let stopped = false
    async function start() {
      try {
        if (!active) return
        stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false })
        if (videoRef.current && !stopped) {
          videoRef.current.srcObject = stream
          await videoRef.current.play().catch(() => {})
        }
      } catch {
        onFlag?.("Webcam denied or unavailable")
      }
    }
    if (active) start()
    return () => {
      stopped = true
      stream?.getTracks().forEach((t) => t.stop())
      if (videoRef.current) videoRef.current.srcObject = null
    }
  }, [enableWebcam, onFlag, active])

  return (
    <section className={cn("rounded-lg border border-border bg-card p-4", className)}>
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Monitoring</h2>
        <button
          onClick={() => setActive((v) => !v)}
          className="text-xs text-foreground/70 underline underline-offset-4"
          aria-pressed={active}
        >
          {active ? "Pause" : "Resume"}
        </button>
      </div>
      <p className="mt-1 text-xs text-foreground/70">
        Running: tab visibility, devtools heuristic, typing cadence{enableWebcam ? ", webcam" : ""}.
      </p>
      {enableWebcam && (
        <div className="mt-3">
          <video
            ref={videoRef}
            className="h-28 w-full rounded-md bg-muted object-cover"
            playsInline
            muted
            aria-label="Webcam preview"
          />
        </div>
      )}
    </section>
  )
}
