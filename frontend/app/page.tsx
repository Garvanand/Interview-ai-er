import Link from "next/link"
import { Button } from "@/components/ui/button"
import {
  Brain,
  Code2,
  BarChart3,
  Target,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  Terminal,
  Activity,
  Layers,
  Sparkles,
  GitCommit,
  Clock,
  Compass,
} from "lucide-react"

export default function Page() {
  return (
    <div className="min-h-screen bg-slate-50/50 dark:bg-[#090d16] text-slate-900 dark:text-slate-100 technical-grid">
      {/* Top Banner / System Metadata */}
      <div className="border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f] text-xs font-mono text-slate-500 dark:text-slate-400 py-1.5 px-4 sm:px-8">
        <div className="max-w-7xl mx-auto flex flex-wrap justify-between items-center gap-2">
          <div className="flex items-center space-x-3">
            <span className="flex items-center text-slate-700 dark:text-slate-300 font-semibold">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-2" />
              SYSTEM PROTOCOL 2.4
            </span>
            <span>•</span>
            <span>STRUCTURED RUBRIC EVALUATION</span>
            <span>•</span>
            <span>ADAPTIVE IRT DIFFICULTY</span>
          </div>
          <div className="hidden sm:flex items-center space-x-4">
            <span>ISOLATED SUBPROCESS SANDBOX</span>
            <span>•</span>
            <span>BAYESIAN SKILL UPDATES</span>
          </div>
        </div>
      </div>

      {/* Hero Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-16 pb-14 sm:pt-24 sm:pb-20">
        <div className="max-w-4xl">
          {/* Badge */}
          <div className="inline-flex items-center space-x-2 px-2.5 py-1 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs font-mono text-slate-700 dark:text-slate-300 mb-6">
            <span className="text-blue-600 dark:text-blue-400 font-bold">ASSESSMENT ENGINE</span>
            <span>/</span>
            <span>ENGINEERING & TECHNICAL INTELLIGENCE</span>
          </div>

          {/* Three Core Value Statements */}
          <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-slate-950 dark:text-slate-50 leading-[1.1] mb-6">
            <span className="block text-slate-950 dark:text-slate-100">Practice an interview.</span>
            <span className="block text-blue-600 dark:text-blue-500">Measure what you actually know.</span>
            <span className="block text-slate-500 dark:text-slate-400 font-medium">Understand where you improve.</span>
          </h1>

          <p className="text-lg sm:text-xl text-slate-600 dark:text-slate-400 leading-relaxed max-w-3xl mb-8">
            An intelligence platform designed for serious engineering candidates and technical hiring teams. 
            Replaces generic interview prep with calibrated adaptive questioning, multi-dimensional rubric assessment, 
            sandboxed code execution, and longitudinal skill modeling.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-wrap items-center gap-3">
            <Link href="/interview">
              <Button className="h-11 px-6 bg-slate-900 hover:bg-slate-800 text-white dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200 font-medium text-sm rounded shadow-sm">
                Configure Interview Session
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </Link>
            <Link href="/dashboard">
              <Button variant="outline" className="h-11 px-5 border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 text-sm font-medium rounded">
                Candidate Intelligence
              </Button>
            </Link>
            <Link href="/practice">
              <Button variant="ghost" className="h-11 px-4 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 text-sm font-medium">
                Targeted Practice
              </Button>
            </Link>
          </div>
        </div>

        {/* Real Assessment Telemetry Live Preview (Information-Dense Technical Card) */}
        <div className="mt-14 rounded-lg border border-slate-300 dark:border-slate-800 bg-white dark:bg-[#0d121f] shadow-sm overflow-hidden">
          <div className="bg-slate-100 dark:bg-slate-900/80 px-4 py-2.5 border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between text-xs font-mono">
            <div className="flex items-center space-x-2 text-slate-700 dark:text-slate-300">
              <Terminal className="h-3.5 w-3.5 text-blue-500" />
              <span className="font-semibold">EVALUATION TELEMETRY SAMPLE</span>
              <span className="text-slate-400">|</span>
              <span className="text-slate-500">ID: sess_94f8e21a</span>
            </div>
            <div className="flex items-center space-x-3 text-slate-500">
              <span>LATENCY: 1.18s</span>
              <span>•</span>
              <span className="text-emerald-600 dark:text-emerald-400 font-semibold">STATUS: EVALUATED</span>
            </div>
          </div>

          <div className="p-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left: Question & Evaluated Response */}
            <div className="lg:col-span-7 space-y-4">
              <div>
                <div className="flex items-center space-x-2 mb-1.5">
                  <span className="text-[11px] font-mono uppercase px-2 py-0.5 rounded bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300 font-semibold">
                    System Design
                  </span>
                  <span className="text-[11px] font-mono text-slate-500">Difficulty: Intermediate (L5)</span>
                  <span className="text-[11px] font-mono text-slate-500">• Skill: Distributed Consensus</span>
                </div>
                <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">
                  How does Raft handle network partitions where the leader is isolated in a minority partition?
                </h3>
              </div>

              <div className="rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/40 p-3.5 text-xs font-mono text-slate-700 dark:text-slate-300 leading-relaxed">
                <span className="text-slate-400 block mb-1 text-[10px] uppercase font-bold tracking-wider">Candidate Transcript Excerpt</span>
                "When the current leader is partitioned into a minority partition, it continues receiving write requests but cannot achieve majority quorum. Meanwhile, the majority partition elects a new leader with a higher term number. Once healed, the old leader receives an AppendEntries RPC with a higher term, steps down to follower, and uncommitted log entries are truncated."
              </div>

              <div className="border-t border-slate-200 dark:border-slate-800 pt-3">
                <div className="text-[11px] font-mono uppercase text-slate-500 font-semibold mb-1">
                  Targeted Adaptive Follow-Up Probe
                </div>
                <p className="text-xs text-slate-800 dark:text-slate-200 italic bg-amber-500/5 border-l-2 border-amber-500 px-3 py-2">
                  "What occurs if clients read state from the partitioned old leader before the new leader commits entries? How does Raft guarantee linearizable reads?"
                </p>
              </div>
            </div>

            {/* Right: Multi-Dimensional Rubric Score Breakdown */}
            <div className="lg:col-span-5 border-t lg:border-t-0 lg:border-l border-slate-200 dark:border-slate-800 lg:pl-6 space-y-3.5">
              <div className="flex items-baseline justify-between">
                <div>
                  <div className="text-xs font-mono text-slate-500 uppercase">Composite Score</div>
                  <div className="text-3xl font-extrabold text-slate-900 dark:text-slate-100 font-mono">
                    88<span className="text-sm font-normal text-slate-400"> / 100</span>
                  </div>
                </div>
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-semibold border border-emerald-500/20">
                  PASSING BENCHMARK
                </span>
              </div>

              {/* 5-Axis Rubric Bars */}
              <div className="space-y-2 text-xs">
                {[
                  { name: "Technical Accuracy", score: 92, weight: "30%" },
                  { name: "Conceptual Depth", score: 85, weight: "25%" },
                  { name: "Problem Solving", score: 88, weight: "20%" },
                  { name: "Communication Clarity", score: 90, weight: "15%" },
                  { name: "Answer Completeness", score: 80, weight: "10%" },
                ].map((axis) => (
                  <div key={axis.name}>
                    <div className="flex justify-between text-[11px] font-mono text-slate-600 dark:text-slate-400 mb-0.5">
                      <span>{axis.name}</span>
                      <span className="font-semibold text-slate-900 dark:text-slate-200">{axis.score}%</span>
                    </div>
                    <div className="h-1.5 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-600 dark:bg-blue-500 rounded-full"
                        style={{ width: `${axis.score}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>

              <div className="pt-2 border-t border-slate-200 dark:border-slate-800 text-[11px] font-mono text-slate-500 space-y-1">
                <div><strong className="text-emerald-600 dark:text-emerald-400">STRENGTH:</strong> Correct log convergence & term stepdown mechanics.</div>
                <div><strong className="text-amber-600 dark:text-amber-400">GAP:</strong> Omitted read-index and lease-read linearizability.</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 5 Core Technical Pillars */}
      <section className="border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f]/60 py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-2xl mb-12">
            <span className="text-xs font-mono uppercase tracking-wider text-blue-600 dark:text-blue-400 font-semibold block mb-2">
              Architecture & Methodologies
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              Engineered for objective measurement
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-400 mt-2">
              Every score, recommendation, and question is tied to empirical data and structured schemas.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Pillar 1: Adaptive Questioning */}
            <div className="p-6 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f] flex flex-col justify-between">
              <div>
                <div className="w-9 h-9 rounded bg-blue-50 dark:bg-blue-950/50 text-blue-600 dark:text-blue-400 flex items-center justify-center mb-4">
                  <Compass className="h-5 w-5" />
                </div>
                <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100 mb-2">
                  Adaptive Questioning Engine
                </h3>
                <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed mb-4">
                  Instead of static question lists, questions calibrate in real time. Dynamic difficulty adjusts from 
                  baseline to senior frontiers based on response depth, while targeted follow-ups probe discovered omissions.
                </p>
              </div>
              <div className="text-[11px] font-mono text-slate-500 pt-3 border-t border-slate-100 dark:border-slate-800">
                Item Response Theory (IRT) Inspired
              </div>
            </div>

            {/* Pillar 2: Evidence-Backed Evaluation */}
            <div className="p-6 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f] flex flex-col justify-between">
              <div>
                <div className="w-9 h-9 rounded bg-emerald-50 dark:bg-emerald-950/50 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mb-4">
                  <CheckCircle2 className="h-5 w-5" />
                </div>
                <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100 mb-2">
                  Evidence-Backed Evaluation
                </h3>
                <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed mb-4">
                  Every score is validated against a 5-dimension rubric (Accuracy, Depth, Problem Solving, Communication, Completeness). 
                  AI models never invent raw scores; evaluations require textual citation evidence.
                </p>
              </div>
              <div className="text-[11px] font-mono text-slate-500 pt-3 border-t border-slate-100 dark:border-slate-800">
                Multi-Dimensional Rubric Grounding
              </div>
            </div>

            {/* Pillar 3: Skill Intelligence */}
            <div className="p-6 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f] flex flex-col justify-between">
              <div>
                <div className="w-9 h-9 rounded bg-purple-50 dark:bg-purple-950/50 text-purple-600 dark:text-purple-400 flex items-center justify-center mb-4">
                  <Layers className="h-5 w-5" />
                </div>
                <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100 mb-2">
                  Longitudinal Skill Modeling
                </h3>
                <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed mb-4">
                  Persistent candidate skill profiles maintain Bayesian proficiency estimates across sessions. 
                  Confidence bounds narrow as evidence accumulates, factoring in recency weighting and topic volatility.
                </p>
              </div>
              <div className="text-[11px] font-mono text-slate-500 pt-3 border-t border-slate-100 dark:border-slate-800">
                Cross-Session Competency Graph
              </div>
            </div>

            {/* Pillar 4: Sandboxed Code Assessment */}
            <div className="p-6 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f] flex flex-col justify-between">
              <div>
                <div className="w-9 h-9 rounded bg-amber-50 dark:bg-amber-950/50 text-amber-600 dark:text-amber-400 flex items-center justify-center mb-4">
                  <Code2 className="h-5 w-5" />
                </div>
                <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100 mb-2">
                  Deterministic Code Execution
                </h3>
                <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed mb-4">
                  Real subprocess code runner with strict execution timeouts. Measures test case pass rates, exit codes, 
                  stdout/stderr, and runtime complexity before sending code to LLMs for idiomatic code review.
                </p>
              </div>
              <div className="text-[11px] font-mono text-slate-500 pt-3 border-t border-slate-100 dark:border-slate-800">
                Subprocess Sandboxing • Python & Node.js
              </div>
            </div>

            {/* Pillar 5: Longitudinal Analytics */}
            <div className="p-6 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f] flex flex-col justify-between">
              <div>
                <div className="w-9 h-9 rounded bg-cyan-50 dark:bg-cyan-950/50 text-cyan-600 dark:text-cyan-400 flex items-center justify-center mb-4">
                  <Activity className="h-5 w-5" />
                </div>
                <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100 mb-2">
                  Growth & Persistence Analytics
                </h3>
                <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed mb-4">
                  Computes linear regression growth slopes, score dispersion (MAD), repeated weakness clustering, 
                  and frontier success rates. Proves measurable skill gains over time.
                </p>
              </div>
              <div className="text-[11px] font-mono text-slate-500 pt-3 border-t border-slate-100 dark:border-slate-800">
                Statistical Trend & Clustering Engine
              </div>
            </div>

            {/* Pillar 6: Actionable Recommendations */}
            <div className="p-6 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f] flex flex-col justify-between">
              <div>
                <div className="w-9 h-9 rounded bg-rose-50 dark:bg-rose-950/50 text-rose-600 dark:text-rose-400 flex items-center justify-center mb-4">
                  <Target className="h-5 w-5" />
                </div>
                <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100 mb-2">
                  Remediation Recommendations
                </h3>
                <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed mb-4">
                  Generates prioritized remediation activities mapped directly to repeated weakness clusters. 
                  Measures empirical lift by tracking post-outcome proficiency after completed drills.
                </p>
              </div>
              <div className="text-[11px] font-mono text-slate-500 pt-3 border-t border-slate-100 dark:border-slate-800">
                Targeted Intervention & Lift Tracking
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Role Coverage Matrix */}
      <section className="py-16 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-8 gap-4">
          <div>
            <span className="text-xs font-mono uppercase tracking-wider text-slate-500 font-semibold block mb-1">
              Assessment Blueprints
            </span>
            <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
              Evaluated Tracks & Role Competencies
            </h2>
          </div>
          <Link href="/interview">
            <Button variant="outline" size="sm" className="text-xs font-mono">
              View All Configurations →
            </Button>
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            {
              role: "Software Engineer",
              focus: "Algorithms, Concurrency, Clean Code",
              format: "Code + Technical Discussion",
              tier: "L3 to Staff",
            },
            {
              role: "System Design",
              focus: "Scalability, Partitioning, CAP Tradeoffs",
              format: "Architecture Walkthrough",
              tier: "L5 to Principal",
            },
            {
              role: "Data Scientist",
              focus: "Model Validation, SQL, Feature Engineering",
              format: "Case Study + Code",
              tier: "L4 to Lead",
            },
            {
              role: "DevOps Engineer",
              focus: "CI/CD, Kubernetes, Observability, Failover",
              format: "Scenario Troubleshooting",
              tier: "L4 to Senior",
            },
          ].map((track) => (
            <div
              key={track.role}
              className="p-4 rounded border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f] space-y-2"
            >
              <div className="text-xs font-mono text-blue-600 dark:text-blue-400 font-semibold">{track.tier}</div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">{track.role}</h3>
              <p className="text-xs text-slate-600 dark:text-slate-400">{track.focus}</p>
              <div className="pt-2 border-t border-slate-100 dark:border-slate-800 text-[11px] font-mono text-slate-500">
                {track.format}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Footer / System Status */}
      <footer className="border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f] py-8 text-xs text-slate-500 font-mono">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row justify-between items-center gap-4">
          <div>
            <span className="font-semibold text-slate-700 dark:text-slate-300">INTERVIEW INTELLIGENCE PLATFORM</span>
            <span className="mx-2">•</span>
            <span>MEASURABLE COMPETENCY ASSESSMENT</span>
          </div>
          <div className="flex items-center space-x-4">
            <Link href="/interview" className="hover:text-slate-800 dark:hover:text-slate-200">Interview</Link>
            <Link href="/dashboard" className="hover:text-slate-800 dark:hover:text-slate-200">Dashboard</Link>
            <Link href="/analytics" className="hover:text-slate-800 dark:hover:text-slate-200">Analytics</Link>
            <Link href="/practice" className="hover:text-slate-800 dark:hover:text-slate-200">Practice</Link>
            <Link href="/ide" className="hover:text-slate-800 dark:hover:text-slate-200">IDE</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
