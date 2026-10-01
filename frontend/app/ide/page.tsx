"use client"

import { EnhancedCodeEditor } from "@/components/ide/enhanced-code-editor"
import { Code2, Terminal, Cpu, Play, CheckCircle2, ShieldCheck, Layers } from "lucide-react"

export default function IDEPage() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-slate-200 dark:border-slate-800 gap-4 mb-8">
        <div>
          <div className="inline-flex items-center space-x-1.5 px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-[10px] font-mono text-slate-600 dark:text-slate-400 mb-2">
            <Terminal className="h-3 w-3" />
            <span>SUBPROCESS RUNTIME</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            Technical Coding Workspace
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            Write, execute, and evaluate algorithmic implementations in an isolated process sandbox with sub-second feedback.
          </p>
        </div>

        {/* Runtime Spec Pills */}
        <div className="flex flex-wrap items-center gap-2 text-[11px] font-mono">
          <span className="px-2 py-1 rounded border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f] text-slate-600 dark:text-slate-400 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            Python 3.12 Engine
          </span>
          <span className="px-2 py-1 rounded border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f] text-slate-600 dark:text-slate-400 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
            Node.js Runtime
          </span>
          <span className="px-2 py-1 rounded border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f] text-slate-600 dark:text-slate-400">
            Timeout: 5.0s
          </span>
        </div>
      </div>

      {/* Main IDE Workspace */}
      <div className="space-y-6">
        <EnhancedCodeEditor />
      </div>
    </div>
  )
}
