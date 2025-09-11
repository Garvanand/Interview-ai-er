"use client"

import type React from "react"
import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react"

type PresenceContextValue = {
  connected: boolean
  transport: "socket.io" | "broadcast" | "none"
  onlineCount: number
  peers: string[]
}

const PresenceContext = createContext<PresenceContextValue>({
  connected: false,
  transport: "none",
  onlineCount: 0,
  peers: [],
})

function useSocketIO(url?: string) {
  const [connected, setConnected] = useState(false)
  const [peers, setPeers] = useState<string[]>([])
  const socketRef = useRef<any>(null)

  useEffect(() => {
    if (!url) return
    let cancelled = false
    ;(async () => {
      try {
        const { io } = await import("socket.io-client")
        if (cancelled) return
        const id = crypto.randomUUID()
        const socket = io(url, { transports: ["websocket"], autoConnect: true })
        socketRef.current = socket

        socket.on("connect", () => {
          setConnected(true)
          socket.emit("presence:join", { id })
        })
        socket.on("disconnect", () => setConnected(false))

        socket.on("presence:update", (list: string[]) => {
          setPeers(list)
        })

        const onBeforeUnload = () => {
          socket.emit("presence:leave", { id })
        }
        window.addEventListener("beforeunload", onBeforeUnload)

        return () => {
          window.removeEventListener("beforeunload", onBeforeUnload)
          socket.disconnect()
        }
      } catch {
        // socket.io not available
      }
    })()

    return () => {
      cancelled = true
      if (socketRef.current) {
        socketRef.current.disconnect()
        socketRef.current = null
      }
    }
  }, [url])

  return { connected, peers }
}

function useBroadcastChannelPresence() {
  const channelRef = useRef<BroadcastChannel | null>(null)
  const [peers, setPeers] = useState<string[]>([])
  const [connected, setConnected] = useState(false)
  const idRef = useRef<string>(crypto.randomUUID())
  const timerRef = useRef<number | null>(null)

  useEffect(() => {
    if (!("BroadcastChannel" in window)) return
    const channel = new BroadcastChannel("realtime-presence")
    channelRef.current = channel
    setConnected(true)

    const id = idRef.current
    const peersSet = new Set<string>([id])

    const broadcast = (type: "join" | "leave" | "ping") => {
      channel.postMessage({ type, id, ts: Date.now() })
    }

    const handle = (e: MessageEvent) => {
      const { type, id: peerId } = e.data || {}
      if (!peerId || peerId === id) return
      if (type === "join" || type === "ping") peersSet.add(peerId)
      if (type === "leave") peersSet.delete(peerId)
      setPeers(Array.from(peersSet))
    }

    channel.addEventListener("message", handle)
    broadcast("join")

    // Keep-alive pings to maintain presence
    timerRef.current = window.setInterval(() => broadcast("ping"), 3000)

    const onUnload = () => broadcast("leave")
    window.addEventListener("beforeunload", onUnload)

    // Ask others to announce themselves
    channel.postMessage({ type: "ping", id, ts: Date.now() })

    return () => {
      onUnload()
      window.removeEventListener("beforeunload", onUnload)
      if (timerRef.current) window.clearInterval(timerRef.current)
      channel.removeEventListener("message", handle)
      channel.close()
      setConnected(false)
    }
  }, [])

  return { connected, peers }
}

export function RealtimeProvider({ children }: { children: React.ReactNode }) {
  const socketUrl = typeof window !== "undefined" ? process.env.NEXT_PUBLIC_SOCKET_URL || "" : ""
  const useSocket = Boolean(socketUrl)

  const { connected: sockConnected, peers: sockPeers } = useSocketIO(useSocket ? socketUrl : undefined)
  const { connected: bcConnected, peers: bcPeers } = useBroadcastChannelPresence()

  const value = useMemo<PresenceContextValue>(() => {
    if (useSocket && sockConnected) {
      return {
        connected: true,
        transport: "socket.io",
        onlineCount: Math.max(1, sockPeers.length),
        peers: sockPeers,
      }
    }
    if (bcConnected) {
      return {
        connected: true,
        transport: "broadcast",
        onlineCount: Math.max(1, bcPeers.length),
        peers: bcPeers,
      }
    }
    return { connected: false, transport: "none", onlineCount: 0, peers: [] }
  }, [useSocket, sockConnected, sockPeers, bcConnected, bcPeers])

  return <PresenceContext.Provider value={value}>{children}</PresenceContext.Provider>
}

export function usePresence() {
  return useContext(PresenceContext)
}
