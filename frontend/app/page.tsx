import Link from "next/link"
import { Button } from "@/components/ui/button"

export default function Page() {
  return (
    <main className="mx-auto max-w-6xl px-4 py-14 sm:py-20">
      <section className="mx-auto max-w-3xl text-center">
        <h1 className="text-balance text-4xl font-bold tracking-tight sm:text-5xl">
          Ace your next interview with AI-powered practice
        </h1>
        <p className="text-pretty mt-4 text-base text-foreground/80 sm:text-lg">
          Simulate real interviews with live feedback, code execution, voice chat, and secure proctoring. Built for
          serious candidates and teams.
        </p>
        <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Button asChild>
            <Link href="/interview">Start mock interview</Link>
          </Button>
          <Button asChild variant="secondary">
            <Link href="/dashboard">View dashboard</Link>
          </Button>
        </div>
        <p className="mt-3 text-xs text-foreground/60">WCAG AA compliant. Keyboard navigable. No gradients.</p>
      </section>

      <section className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {[
          { title: "AI Questions", desc: "Context-aware questions and follow-ups." },
          { title: "Real-time Evaluation", desc: "Live scoring and targeted feedback." },
          { title: "Webcam Monitoring", desc: "Face presence and gaze tracking stubs." },
          { title: "Code Execution", desc: "Run code in a Monaco-powered IDE." },
          { title: "Voice Chat", desc: "Low-latency voice with transcripts." },
          { title: "Anti-cheat", desc: "Tab/devtools detection and typing analysis." },
        ].map((f) => (
          <article key={f.title} className="rounded-lg border border-border bg-card p-5 transition-colors">
            <h3 className="text-sm font-semibold">{f.title}</h3>
            <p className="mt-1 text-sm text-foreground/80">{f.desc}</p>
          </article>
        ))}
      </section>
    </main>
  )
}
