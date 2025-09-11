"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { usePresence } from "@/components/realtime/realtime-provider"
import { VoiceControls } from "@/components/chat/voice-controls"
import { MessageList } from "@/components/chat/message-list"

type ChatMsg = { role: "user" | "assistant"; content: string }

export default function ChatPage() {
  const [input, setInput] = useState("")
  const [messages, setMessages] = useState<ChatMsg[]>([])
  const [loading, setLoading] = useState(false)
  const [ttsEnabled, setTtsEnabled] = useState(false)
  const { onlineCount, transport, connected } = usePresence()

  function speak(text: string) {
    if (!ttsEnabled) return
    if (typeof window === "undefined") return
    if (!("speechSynthesis" in window)) return
    const utter = new SpeechSynthesisUtterance(text)
    utter.rate = 1
    utter.pitch = 1
    utter.lang = "en-US"
    window.speechSynthesis.cancel()
    window.speechSynthesis.speak(utter)
  }

  async function send() {
    const text = input.trim()
    if (!text || loading) return
    setInput("")
    setLoading(true)
    setMessages((m) => [...m, { role: "user", content: text }, { role: "assistant", content: "" }])

    let assistantBuffer = ""

    try {
      const res = await fetch("/api/ai/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: text }),
      })
      if (!res.body) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.error || "No stream body")
      }
      const reader = res.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value, { stream: true })
        if (!chunk) continue
        assistantBuffer += chunk
        setMessages((m) => {
          const next = [...m]
          const last = next[next.length - 1]
          if (last?.role === "assistant") last.content += chunk
          return next
        })
      }
    } catch (e: any) {
      setMessages((m) => [...m, { role: "assistant", content: e?.message || "AI error" }])
    } finally {
      setLoading(false)
      if (assistantBuffer) speak(assistantBuffer)
    }
  }

  function handleTranscript(text: string) {
    // Append transcript to input; user can edit or press Send
    setInput((v) => (v ? `${v} ${text}` : text))
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="text-2xl font-semibold">Chat</h1>
      <div className="mt-1 flex flex-col items-start justify-between gap-2 sm:flex-row sm:items-center">
        <p className="text-xs text-foreground/60" aria-live="polite">
          {connected ? `Online: ${onlineCount} (${transport})` : "Connecting…"}
        </p>
        <VoiceControls onTranscript={handleTranscript} onTtsChange={setTtsEnabled} />
      </div>

      <div className="mt-4 space-y-3 rounded-lg border border-border bg-card p-4">
        <div className="space-y-2">
          {messages.length === 0 && (
            <p className="text-sm text-foreground/70">Ask interview-style questions or request feedback.</p>
          )}
          <MessageList messages={messages} />
        </div>
        <div className="flex flex-col gap-2">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question..."
            aria-label="Chat input"
          />
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs text-foreground/60">{loading ? "Generating..." : "Ready"}</span>
            <Button onClick={send} disabled={loading}>
              Send
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
