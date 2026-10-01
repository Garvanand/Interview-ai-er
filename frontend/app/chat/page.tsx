"use client"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import {
  MessageSquare,
  Send,
  Loader2,
  Terminal,
  Brain,
  Sparkles,
  Bot,
  User,
  ArrowRight,
  ShieldCheck,
  Compass,
} from "lucide-react"

type ChatMsg = { role: "user" | "assistant"; content: string }

const PROMPT_SUGGESTIONS = [
  "Explain Raft leader election vs Paxos consensus guarantees",
  "How should I structure a STAR response on negotiating scope cuts?",
  "What are common edge cases in distributed database sharding?",
  "Analyze trade-offs between B-Trees and LSM-Trees for high-write workloads",
]

export default function ChatPage() {
  const defaultIntro: ChatMsg = {
    role: "assistant",
    content:
      "Welcome to the Interview Intelligence Advisor. I assist with technical concept formulation, algorithmic trade-off analysis, system design architectures, and behavioral STAR framing. How can I assist your interview preparation today?",
  }

  const [input, setInput] = useState("")
  const [messages, setMessages] = useState<ChatMsg[]>([defaultIntro])
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const clearChat = () => {
    if (!loading) {
      setMessages([defaultIntro])
    }
  }

  async function send(textToSend?: string) {
    const text = (textToSend || input).trim()
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
        throw new Error(data.error || "No stream body returned")
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
      setMessages((m) => [
        ...m.slice(0, -1),
        {
          role: "assistant",
          content:
            "Advisor communication error: " +
            (e?.message || "Unable to stream response from AI model. Please verify your connection."),
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col h-[calc(100vh-4rem)]">
      {/* Header */}
      <div className="pb-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
        <div>
          <div className="inline-flex items-center space-x-1.5 px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-[10px] font-mono text-slate-600 dark:text-slate-400 mb-1">
            <MessageSquare className="h-3 w-3" />
            <span>AI TECHNICAL ADVISOR</span>
          </div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            Interview & Architecture Advisor
          </h1>
        </div>

        <div className="flex items-center space-x-3">
          <div className="text-[11px] font-mono text-slate-400 flex items-center space-x-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            <span>LLM ACTIVE</span>
          </div>
          {messages.length > 1 && (
            <Button
              variant="outline"
              size="sm"
              onClick={clearChat}
              disabled={loading}
              className="h-7 px-2 text-[10px] font-mono text-slate-500 hover:text-slate-900 dark:hover:text-slate-100"
            >
              Reset Chat
            </Button>
          )}
        </div>
      </div>

      {/* Suggested Chips */}
      <div className="py-3 flex flex-wrap gap-1.5 border-b border-slate-100 dark:border-slate-800/80">
        {PROMPT_SUGGESTIONS.map((sug) => (
          <button
            key={sug}
            onClick={() => send(sug)}
            disabled={loading}
            className="text-[11px] font-mono px-2.5 py-1 rounded border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f] text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-700 hover:text-slate-900 dark:hover:text-slate-200 transition-colors disabled:opacity-50"
          >
            {sug}
          </button>
        ))}
      </div>

      {/* Message Stream */}
      <div className="flex-1 overflow-y-auto py-6 space-y-5">
        {messages.map((msg, idx) => {
          const isUser = msg.role === "user"
          return (
            <div
              key={idx}
              className={`flex items-start space-x-3 ${isUser ? "justify-end" : "justify-start"}`}
            >
              {!isUser && (
                <div className="w-7 h-7 rounded bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 flex items-center justify-center shrink-0 mt-0.5">
                  <Brain className="h-4 w-4" />
                </div>
              )}

              <div
                className={`max-w-2xl rounded-lg p-4 text-xs leading-relaxed ${
                  isUser
                    ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 font-mono"
                    : "border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f] text-slate-800 dark:text-slate-200"
                }`}
              >
                {!isUser && (
                  <div className="text-[10px] font-mono text-slate-400 uppercase tracking-wider mb-1.5 font-semibold">
                    Advisor Output
                  </div>
                )}
                {msg.content ? (
                  <div className="whitespace-pre-wrap font-sans text-xs">{msg.content}</div>
                ) : (
                  <div className="flex items-center space-x-1.5 py-1 text-slate-400">
                    <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-pulse" />
                    <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-pulse delay-150" />
                    <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-pulse delay-300" />
                    <span className="text-[11px] font-mono ml-2">Synthesizing response...</span>
                  </div>
                )}
              </div>

              {isUser && (
                <div className="w-7 h-7 rounded bg-blue-600 text-white flex items-center justify-center shrink-0 mt-0.5">
                  <User className="h-4 w-4" />
                </div>
              )}
            </div>
          )
        })}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Bar */}
      <div className="pt-3 border-t border-slate-200 dark:border-slate-800">
        <form
          onSubmit={(e) => {
            e.preventDefault()
            send()
          }}
          className="space-y-1.5"
        >
          <div className="flex items-center space-x-2">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault()
                  send()
                }
              }}
              placeholder="Ask technical question, drill on a trade-off, or formulate an answer..."
              rows={1}
              disabled={loading}
              className="resize-none min-h-[42px] max-h-32 text-xs font-mono rounded border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f]"
            />
            <Button
              type="submit"
              disabled={loading || !input.trim()}
              aria-label="Send technical prompt"
              className="h-[42px] px-4 bg-slate-900 text-white hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900 shrink-0 text-xs font-mono"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </Button>
          </div>
          <div className="flex justify-between items-center text-[10px] font-mono text-slate-400 px-1">
            <span>Enter to send • Shift+Enter for new line</span>
            <span>Groq LLM Accelerated</span>
          </div>
        </form>
      </div>
    </div>
  )
}
