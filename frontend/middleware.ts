import { NextResponse, type NextRequest } from "next/server"

/**
 * Next.js Edge Middleware — route-level authentication guard.
 *
 * Protected paths:  /dashboard, /interview, /ide, /chat, /history, /practice, /analytics
 * Auth paths:       /login, /signup  (redirect authenticated users away)
 *
 * Design:
 * - Uses Supabase SSR client to verify the session server-side (reads cookies).
 * - If Supabase is not configured, protected routes are blocked with a 307 to /login.
 *   (We do NOT silently pass unauthenticated users through when auth is misconfigured.)
 * - Authenticated users who visit /login or /signup are redirected to /dashboard.
 */
export async function middleware(req: NextRequest) {
  const res = NextResponse.next()

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  const path = req.nextUrl.pathname

  const isProtected =
    path.startsWith("/dashboard") ||
    path.startsWith("/interview") ||
    path.startsWith("/ide") ||
    path.startsWith("/chat") ||
    path.startsWith("/history") ||
    path.startsWith("/practice") ||
    path.startsWith("/analytics")

  const isAuthPage = path === "/login" || path === "/signup"

  // If Supabase is not configured, block protected routes unconditionally.
  // Do NOT allow unauthenticated access when the auth system is misconfigured.
  if (!supabaseUrl || !supabaseAnonKey) {
    if (isProtected) {
      const url = req.nextUrl.clone()
      url.pathname = "/login"
      url.searchParams.set("reason", "auth_not_configured")
      return NextResponse.redirect(url)
    }
    return res
  }

  try {
    const { createServerClient } = await import("@supabase/ssr")

    const supabase = createServerClient(supabaseUrl, supabaseAnonKey, {
      cookies: {
        getAll() {
          return req.cookies.getAll()
        },
        setAll(cookies) {
          cookies.forEach(({ name, value, options }) => res.cookies.set(name, value, options))
        },
      },
    })

    // getUser() verifies the JWT with the Supabase Auth server.
    // This is more reliable than getSession() which only reads the local cookie.
    const { data: { user }, error } = await supabase.auth.getUser()

    // Protect routes: redirect unauthenticated users to /login
    if (isProtected && (!user || error)) {
      const url = req.nextUrl.clone()
      url.pathname = "/login"
      // Preserve the intended destination so login can redirect back after auth
      url.searchParams.set("redirectTo", path)
      return NextResponse.redirect(url)
    }

    // Auth pages: redirect authenticated users to /dashboard
    if (isAuthPage && user && !error) {
      const url = req.nextUrl.clone()
      url.pathname = "/dashboard"
      return NextResponse.redirect(url)
    }

  } catch (error) {
    // On middleware error, block protected routes (fail-secure, not fail-open).
    console.error("Auth middleware error:", error)
    if (isProtected) {
      const url = req.nextUrl.clone()
      url.pathname = "/login"
      url.searchParams.set("reason", "auth_error")
      return NextResponse.redirect(url)
    }
  }

  return res
}

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/interview/:path*",
    "/ide/:path*",
    "/chat/:path*",
    "/history/:path*",
    "/practice/:path*",
    "/analytics/:path*",
    "/login",
    "/signup",
  ],
}
