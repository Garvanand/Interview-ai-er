import { NextResponse, type NextRequest } from "next/server"

export async function middleware(req: NextRequest) {
  const res = NextResponse.next()
  
  // Check if Supabase environment variables are available
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  
  // If Supabase is not configured, allow all routes (temporary for development)
  if (!supabaseUrl || !supabaseAnonKey) {
    console.warn("Supabase environment variables not found. Authentication disabled.")
    return res
  }
  
  try {
    // Only import Supabase if environment variables are available
    const { createServerClient } = await import("@supabase/ssr")
    
    const supabase = createServerClient(
      supabaseUrl,
      supabaseAnonKey,
      {
        cookies: {
          getAll() {
            return req.cookies.getAll()
          },
          setAll(cookies) {
            cookies.forEach(({ name, value, options }) => res.cookies.set(name, value, options))
          },
        },
      },
    )
    
    // Touch the session to refresh cookies when needed
    const {
      data: { user },
    } = await supabase.auth.getUser()

    // If not authenticated and trying to access protected routes, redirect to /login
    const path = req.nextUrl.pathname
    const isProtected =
      path.startsWith("/dashboard") ||
      path.startsWith("/interview") ||
      path.startsWith("/ide") ||
      path.startsWith("/chat") ||
      path.startsWith("/history") ||
      path.startsWith("/practice") ||
      path.startsWith("/analytics")

    if (isProtected && !user && !path.startsWith("/login") && !path.startsWith("/auth") && !path.startsWith("/signup")) {
      const url = req.nextUrl.clone()
      url.pathname = "/login"
      return NextResponse.redirect(url)
    }
  } catch (error) {
    console.error("Supabase middleware error:", error)
    // On error, allow access (temporary for development)
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
