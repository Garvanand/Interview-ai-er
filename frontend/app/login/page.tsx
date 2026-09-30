"use client"

import type React from "react"
import { useState, useEffect } from "react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { getBrowserSupabaseClient } from "@/lib/supabase"
import { useRouter, useSearchParams } from "next/navigation"
import { Brain, AlertCircle, Loader2 } from "lucide-react"

export default function LoginPage() {
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
    } else {
      router.replace(redirectTo)
    }
  }

  if (notConfigured) {
    return (
      <div className="flex min-h-[80vh] items-center justify-center px-4">
        <div className="max-w-sm w-full rounded-lg border border-amber-200 bg-amber-50 p-6 text-sm text-amber-800">
          <AlertCircle className="h-5 w-5 mb-2" />
          <p className="font-medium">Supabase not configured</p>
          <p className="mt-1 text-amber-700">
            Set <code className="font-mono text-xs bg-amber-100 px-1 rounded">NEXT_PUBLIC_SUPABASE_URL</code> and{" "}
            <code className="font-mono text-xs bg-amber-100 px-1 rounded">NEXT_PUBLIC_SUPABASE_ANON_KEY</code> to enable authentication.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-[80vh] items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Header */}
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-blue-600">
            <Brain className="h-7 w-7 text-white" />
          </div>
          <h1 className="text-2xl font-semibold text-gray-900">Sign in to InterviewAI</h1>
          <p className="mt-1.5 text-sm text-gray-500">
            Don&apos;t have an account?{" "}
            <Link href="/signup" className="font-medium text-blue-600 hover:text-blue-500 underline underline-offset-2">
              Sign up
            </Link>
          </p>
        </div>

        {/* Form */}
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
              Email address
            </label>
            <Input
              id="email"
              type="email"
              required
              autoComplete="email"
              autoFocus
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              disabled={loading}
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                Password
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
            />
          </div>

          {error && (
            <div className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-700">
              <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <Button type="submit" disabled={loading} className="w-full">
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Signing in…
              </>
            ) : (
              "Sign in"
            )}
          </Button>
        </form>
      </div>
    </div>
  )
}
