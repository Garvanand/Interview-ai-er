import { Navbar } from "@/components/navbar"
import { getServerSupabaseClient } from "@/lib/supabase"

export async function NavbarServer() {
  const supabase = getServerSupabaseClient()
  if (!supabase) {
    return <Navbar />
  }
  const {
    data: { user },
  } = await supabase.auth.getUser()

  return <Navbar userEmail={user?.email ?? undefined} />
}
