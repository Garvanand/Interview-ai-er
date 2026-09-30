"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { Button } from "@/components/ui/button"
import {
  Home,
  Brain,
  Code2,
  BarChart3,
  BookOpen,
  Clock,
  Menu,
  X,
  LogOut,
  LogIn,
  User,
  Activity,
} from "lucide-react"
import { useState } from "react"
import { useAuth } from "@/hooks/use-auth"

const PROTECTED_NAV = [
  { name: "Interview", href: "/interview", icon: Brain },
  { name: "Dashboard", href: "/dashboard", icon: BarChart3 },
  { name: "Analytics", href: "/analytics", icon: Activity },
  { name: "History", href: "/history", icon: Clock },
  { name: "Practice", href: "/practice", icon: BookOpen },
  { name: "IDE", href: "/ide", icon: Code2 },
]

const PUBLIC_NAV = [
  { name: "Home", href: "/", icon: Home },
]

export function Navigation() {
  const pathname = usePathname()
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const { user, isLoading, isAuthenticated, signOut } = useAuth()

  const navItems = isAuthenticated ? [...PUBLIC_NAV, ...PROTECTED_NAV] : PUBLIC_NAV

  return (
    <nav className="bg-white border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          {/* Logo and Desktop Navigation */}
          <div className="flex items-center">
            <Link href="/" className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <Brain className="h-5 w-5 text-white" />
              </div>
              <span className="text-xl font-bold text-gray-900">InterviewAI</span>
            </Link>

            {/* Desktop Navigation */}
            <div className="hidden md:ml-10 md:flex md:space-x-8">
              {navItems.map((item) => {
                const isActive = pathname === item.href
                const Icon = item.icon

                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors ${
                      isActive
                        ? "border-blue-500 text-gray-900"
                        : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
                    }`}
                  >
                    <Icon className="h-4 w-4 mr-2" />
                    {item.name}
                  </Link>
                )
              })}
            </div>
          </div>

          {/* Right side — auth actions */}
          <div className="hidden md:flex md:items-center md:space-x-3">
            {isLoading ? (
              <div className="h-8 w-24 animate-pulse rounded bg-gray-100" />
            ) : isAuthenticated ? (
              <>
                <span className="text-sm text-gray-500 flex items-center gap-1.5">
                  <User className="h-3.5 w-3.5" />
                  {user?.email}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={signOut}
                  className="flex items-center gap-1.5"
                >
                  <LogOut className="h-4 w-4" />
                  Sign out
                </Button>
              </>
            ) : (
              <>
                <Button variant="ghost" size="sm" asChild>
                  <Link href="/login">
                    <LogIn className="h-4 w-4 mr-1.5" />
                    Sign in
                  </Link>
                </Button>
                <Button size="sm" asChild>
                  <Link href="/signup">Get Started</Link>
                </Button>
              </>
            )}
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden flex items-center">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="p-2"
            >
              {isMobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </Button>
          </div>
        </div>
      </div>

      {/* Mobile Navigation */}
      {isMobileMenuOpen && (
        <div className="md:hidden">
          <div className="px-2 pt-2 pb-3 space-y-1 sm:px-3 bg-white border-t border-gray-200">
            {navItems.map((item) => {
              const isActive = pathname === item.href
              const Icon = item.icon

              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`block px-3 py-2 rounded-md text-base font-medium transition-colors ${
                    isActive
                      ? "bg-blue-50 text-blue-700 border-l-4 border-blue-500"
                      : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                  }`}
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  <div className="flex items-center">
                    <Icon className="h-5 w-5 mr-3" />
                    {item.name}
                  </div>
                </Link>
              )
            })}

            {/* Mobile Auth Actions */}
            <div className="pt-4 border-t border-gray-100 space-y-2">
              {isLoading ? null : isAuthenticated ? (
                <>
                  <p className="px-3 text-xs text-gray-500 truncate">{user?.email}</p>
                  <Button
                    variant="outline"
                    className="w-full justify-start"
                    onClick={() => { setIsMobileMenuOpen(false); signOut() }}
                  >
                    <LogOut className="h-4 w-4 mr-2" />
                    Sign out
                  </Button>
                </>
              ) : (
                <>
                  <Button variant="outline" className="w-full justify-start" asChild>
                    <Link href="/login" onClick={() => setIsMobileMenuOpen(false)}>
                      <LogIn className="h-4 w-4 mr-2" />
                      Sign in
                    </Link>
                  </Button>
                  <Button className="w-full" asChild>
                    <Link href="/signup" onClick={() => setIsMobileMenuOpen(false)}>
                      Get Started
                    </Link>
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </nav>
  )
}
