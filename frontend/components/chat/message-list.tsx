"use client"

type Message = { role: "user" | "assistant"; content: string }

export function MessageList({ messages }: { messages: Message[] }) {
  return (
    <ul className="space-y-3" role="list" aria-label="Chat transcript">
      {messages.map((m, i) => (
        <li
          key={i}
          className={m.role === "user" ? "text-foreground" : "text-foreground/90"}
          aria-live={m.role === "assistant" ? "polite" : undefined}
        >
          <span className="text-xs uppercase tracking-wide text-foreground/60">{m.role}</span>
          <p className="mt-1 text-sm leading-relaxed">{m.content}</p>
        </li>
      ))}
    </ul>
  )
}
