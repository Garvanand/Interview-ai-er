"use client"

import Link from "next/link"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { getBrowserSupabaseClient } from "@/lib/supabase"
import { useRouter } from "next/navigation"

const navItems = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/interview", label: "Interview Hub" },
  { href: "/ide", label: "IDE" },
  { href: "/chat", label: "Chat" },
  { href: "/history", label: "History" },
  { href: "/practice", label: "Practice" },
  { href: "/analytics", label: "Analytics" },
]

export function Navbar({ userEmail }: { userEmail?: string }) {
  const [open, setOpen] = useState(false)
  const supabase = getBrowserSupabaseClient()
  const router = useRouter()

  async function signOut() {
    if (supabase) {
      await supabase.auth.signOut()
    }
    router.replace("/")
  }

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <div className="flex items-center gap-3">
          <Link href="/" className="inline-flex items-center gap-2">
            <span className="sr-only">Mock Interview Platform</span>
            <div aria-hidden className="h-5 w-5 rounded-sm bg-primary" />
            <span className="font-semibold">MockInterview</span>
          </Link>
        </div>

        <button
          aria-label="Toggle navigation menu"
          className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border md:hidden"
          onClick={() => setOpen((v) => !v)}
        >
          <span aria-hidden className="block h-0.5 w-5 bg-foreground" />
        </button>

        <div className="hidden md:flex md:items-center md:gap-6">
          <ul className="flex items-center gap-4">
            {navItems.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={cn("text-sm text-foreground/80 transition-colors hover:text-foreground")}
                >
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
          <div className="ml-2 flex items-center gap-2">
            {!userEmail ? (
              <>
                <Link href="/login" className="text-sm text-foreground/80 hover:text-foreground">
                  Sign in
                </Link>
                <Button asChild>
                  <Link href="/signup">Sign up</Link>
                </Button>
              </>
            ) : (
              <>
                <span className="text-sm text-foreground/70" aria-live="polite">
                  {userEmail}
                </span>
                <Button variant="secondary" onClick={signOut}>
                  Sign out
                </Button>
              </>
            )}
          </div>
        </div>
      </nav>

      {/* Mobile drawer */}
      <div
        className={cn(
          "md:hidden border-t border-border transition-[max-height,opacity] ease-in-out",
          open ? "max-h-96 opacity-100" : "max-h-0 opacity-0",
        )}
      >
        <ul className="space-y-2 px-4 py-3">
          {navItems.map((item) => (
            <li key={item.href}>
              <Link
                href={item.href}
                className="block rounded-md px-2 py-2 text-foreground/90 hover:bg-muted hover:text-foreground"
                onClick={() => setOpen(false)}
              >
                {item.label}
              </Link>
            </li>
          ))}
          <li className="flex items-center gap-2 pt-1">
            {!userEmail ? (
              <>
                <Link
                  href="/login"
                  className="rounded-md px-2 py-2 text-foreground/90 hover:bg-muted hover:text-foreground"
                  onClick={() => setOpen(false)}
                >
                  Sign in
                </Link>
                <Button asChild className="w-full">
                  <Link href="/signup" onClick={() => setOpen(false)}>
                    Sign up
                  </Link>
                </Button>
              </>
            ) : (
              <>
                <span className="flex-1 rounded-md px-2 py-2 text-sm text-foreground/70">{userEmail}</span>
                <Button className="w-full" variant="secondary" onClick={signOut}>
                  Sign out
                </Button>
              </>
            )}
          </li>
        </ul>
      </div>
    </header>
  )
}
