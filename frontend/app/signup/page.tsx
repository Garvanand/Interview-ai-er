"use client"

import type React from "react"
import { useState, useEffect } from "react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { getBrowserSupabaseClient } from "@/lib/supabase"
import { useRouter } from "next/navigation"
import { AlertCircle, Loader2, CheckCircle2, UserPlus, ArrowRight } from "lucide-react"

const MIN_PASSWORD_LEN = 8

export default function SignUpPage() {
  const router = useRouter()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
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

    if (password.length < MIN_PASSWORD_LEN) {
      setError(`Password must be at least ${MIN_PASSWORD_LEN} characters.`)
      return
    }

    setLoading(true)
    setMessage(null)
    setError(null)

    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: `${window.location.origin}/dashboard`,
      },
    })

    setLoading(false)
    if (error) {
      setError(error.message)
    } else {
      setMessage("Account created. Please check your email inbox to confirm your account before logging in.")
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
            <UserPlus className="h-3 w-3" />
            <span>CANDIDATE ONBOARDING</span>
          </div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            Create Account
          </h1>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            Begin calibrated mock interviews and skill profile tracking
          </p>
        </div>

        {/* Message Callout or Success Card */}
        {message ? (
          <div className="space-y-4">
            <div className="rounded border border-emerald-200 dark:border-emerald-900/50 bg-emerald-50 dark:bg-emerald-950/30 p-4 text-xs text-emerald-800 dark:text-emerald-300 flex items-start space-x-2.5">
              <CheckCircle2 className="h-4 w-4 mt-0.5 shrink-0 text-emerald-600 dark:text-emerald-400" />
              <div className="space-y-1">
                <p className="font-semibold text-emerald-900 dark:text-emerald-200">Account Created Successfully</p>
                <p className="leading-relaxed">{message}</p>
              </div>
            </div>
            <Link href="/login" className="block">
              <Button className="w-full h-9 bg-slate-900 hover:bg-slate-800 text-white dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200 text-xs font-medium rounded transition-colors">
                <span>Proceed to Sign In</span>
                <ArrowRight className="h-3.5 w-3.5 ml-1.5" />
              </Button>
            </Link>
          </div>
        ) : (
          <>
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
                <label htmlFor="password" className="block text-xs font-mono text-slate-600 dark:text-slate-400 mb-1">
                  PASSWORD (MIN 8 CHARACTERS)
                </label>
                <Input
                  id="password"
                  type="password"
                  required
                  autoComplete="new-password"
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
                    <span>Registering Profile...</span>
                  </span>
                ) : (
                  <span className="flex items-center justify-center space-x-1.5">
                    <span>Create Candidate Profile</span>
                    <ArrowRight className="h-3.5 w-3.5" />
                  </span>
                )}
              </Button>
            </form>
          </>
        )}

        {/* Footer */}
        <div className="mt-6 pt-4 border-t border-slate-100 dark:border-slate-800 text-center text-xs text-slate-500">
          <span>Already registered? </span>
          <Link href="/login" className="font-semibold text-blue-600 dark:text-blue-400 hover:underline">
            Sign In
          </Link>
        </div>
      </div>
    </div>
  )
}
