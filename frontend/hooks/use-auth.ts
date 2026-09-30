"use client"

/**
 * useAuth — centralized authentication hook for the frontend.
 *
 * Provides:
 *   user        — the authenticated Supabase User object (null if unauthenticated)
 *   userId      — convenience string (user.id | null)
 *   isLoading   — true while the session is being resolved on mount
 *   isAuthenticated — derived boolean, false while loading
 *   signOut     — calls supabase.auth.signOut and redirects to /login
 *
 * Design constraints:
 *   - Never falls back to a hardcoded demo/guest ID. If unauthenticated, userId is null.
 *   - Subscribes to onAuthStateChange so the state stays consistent across tab focus.
 *   - Redirects unauthenticated users to /login when redirectIfUnauthenticated=true.
 */

import { useState, useEffect, useCallback } from "react"
import { useRouter } from "next/navigation"
import type { User } from "@supabase/supabase-js"
import { getBrowserSupabaseClient } from "@/lib/supabase"

interface UseAuthOptions {
  /** If true, redirects to /login when auth resolves to unauthenticated. */
  redirectIfUnauthenticated?: boolean
}

interface UseAuthReturn {
  user: User | null
  userId: string | null
  isLoading: boolean
  isAuthenticated: boolean
  signOut: () => Promise<void>
}

export function useAuth(options: UseAuthOptions = {}): UseAuthReturn {
  const { redirectIfUnauthenticated = false } = options
  const router = useRouter()

  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const supabase = getBrowserSupabaseClient()
    if (!supabase) {
      // Supabase not configured — treat as unauthenticated
      setUser(null)
      setIsLoading(false)
      if (redirectIfUnauthenticated) {
        router.replace("/login")
      }
      return
    }

    // Resolve the current session immediately
    supabase.auth.getUser().then(({ data: { user } }) => {
      setUser(user ?? null)
      setIsLoading(false)
      if (!user && redirectIfUnauthenticated) {
        router.replace("/login")
      }
    }).catch(() => {
      setUser(null)
      setIsLoading(false)
      if (redirectIfUnauthenticated) {
        router.replace("/login")
      }
    })

    // Keep state in sync with auth events (sign-in, sign-out, token refresh)
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      const nextUser = session?.user ?? null
      setUser(nextUser)
      setIsLoading(false)
      if (!nextUser && redirectIfUnauthenticated) {
        router.replace("/login")
      }
    })

    return () => subscription.unsubscribe()
  }, [redirectIfUnauthenticated, router])

  const signOut = useCallback(async () => {
    const supabase = getBrowserSupabaseClient()
    if (supabase) {
      await supabase.auth.signOut()
    }
    // Always redirect to /login, even if signOut fails
    router.replace("/login")
  }, [router])

  return {
    user,
    userId: user?.id ?? null,
    isLoading,
    isAuthenticated: !isLoading && user !== null,
    signOut,
  }
}
