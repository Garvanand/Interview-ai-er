"use client"

import type React from "react"
import { useState, useEffect, Suspense } from "react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { getBrowserSupabaseClient } from "@/lib/supabase"
import { useRouter, useSearchParams } from "next/navigation"
import { Brain, AlertCircle, Loader2, ArrowRight, ShieldCheck, KeyRound } from "lucide-react"

function LoginForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const redirectTo = searchParams.get("redirectTo") ?? "/dashboard"
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notConfigured, setNotConfigured] = useState(false)

  useEffect(() => {
    const supabase = getBrowserSupabaseClient()
    if (!supabase) {
      setNotConfigured(true)
      return
    }
    // Redirect already-authenticated users
    supabase.auth.getUser().then(({ data: { user } }) => {
      if (user) router.replace("/dashboard")
    })
  }, [router])

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    const supabase = getBrowserSupabaseClient()
    if (!supabase) return
    setLoading(true)
    setError(null)
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    setLoading(false)
    if (error) {
      setError(error.message)
      setPassword("")
    } else {
      router.replace(redirectTo)
    }
  }

  if (notConfigured) {
    return (
      <div className="flex min-h-[80vh] items-center justify-center px-4">
        <div className="max-w-md w-full rounded border border-amber-300 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30 p-6 text-xs font-mono text-amber-800 dark:text-amber-300">
          <AlertCircle className="h-5 w-5 mb-2" />
          <p className="font-semibold text-sm mb-1">Supabase Client Unconfigured</p>
          <p className="leading-relaxed">
            Please configure <code className="bg-amber-100 dark:bg-amber-900/50 px-1 py-0.5 rounded">NEXT_PUBLIC_SUPABASE_URL</code> and{" "}
            <code className="bg-amber-100 dark:bg-amber-900/50 px-1 py-0.5 rounded">NEXT_PUBLIC_SUPABASE_ANON_KEY</code> in your environment.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-[80vh] items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f] p-8 shadow-sm">
        {/* Header */}
        <div className="mb-6">
          <div className="inline-flex items-center space-x-1.5 px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-[10px] font-mono text-slate-600 dark:text-slate-400 mb-3">
            <KeyRound className="h-3 w-3" />
            <span>SESSION GATEWAY</span>
          </div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            Sign In
          </h1>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            Access your interview sessions and skill profile
          </p>
        </div>

        {/* Error Callout */}
        {error && (
          <div className="mb-4 rounded border border-rose-200 dark:border-rose-900/50 bg-rose-50 dark:bg-rose-950/30 p-3 text-xs text-rose-700 dark:text-rose-300 flex items-start space-x-2">
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-xs font-mono text-slate-600 dark:text-slate-400 mb-1">
              EMAIL ADDRESS
            </label>
            <Input
              id="email"
              type="email"
              required
              autoComplete="email"
              autoFocus
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="candidate@example.com"
              disabled={loading}
              className="h-9 text-xs rounded border-slate-200 dark:border-slate-800 font-mono"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label htmlFor="password" className="block text-xs font-mono text-slate-600 dark:text-slate-400">
                PASSWORD
              </label>
            </div>
            <Input
              id="password"
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              disabled={loading}
              className="h-9 text-xs rounded border-slate-200 dark:border-slate-800 font-mono"
            />
          </div>

          <Button
            type="submit"
            disabled={loading}
            className="w-full h-9 bg-slate-900 hover:bg-slate-800 text-white dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200 text-xs font-medium rounded transition-colors"
          >
            {loading ? (
              <span className="flex items-center space-x-2">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                <span>Authenticating...</span>
              </span>
            ) : (
              <span className="flex items-center justify-center space-x-1.5">
                <span>Sign In to Platform</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </span>
            )}
          </Button>
        </form>

        {/* Footer */}
        <div className="mt-6 pt-4 border-t border-slate-100 dark:border-slate-800 text-center text-xs text-slate-500">
          <span>New candidate? </span>
          <Link href="/signup" className="font-semibold text-blue-600 dark:text-blue-400 hover:underline">
            Register Account
          </Link>
        </div>
      </div>
    </div>
  )
}

export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-[80vh] items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
      </div>
    }>
      <LoginForm />
    </Suspense>
  )
}
