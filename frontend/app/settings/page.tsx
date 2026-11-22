"use client"

import { Suspense } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { useEffect } from "react"
import { ArrowLeft } from "lucide-react"
import useSWR from "swr"
import { Button } from "@/components/ui/button"
import { ThemeToggle } from "@/components/settings/theme-toggle"
import { ConnectionCard } from "@/components/settings/connection-card"
import { MemoryItem } from "@/components/settings/memory-item"
import { useAuth } from "@/hooks/use-auth"
import { apiFetch } from "@/lib/api"

interface Memory {
  id: string
  content: string
  category: string
  created_at: string
}

interface Connection {
  provider: string
  connected: boolean
}

function SettingsContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { session } = useAuth()

  const { data: memories, mutate: mutateMemories } = useSWR(
    session ? "/api/memories" : null,
    () => apiFetch<{ memories: Memory[] }>("/api/memories", session!.access_token),
  )

  const { data: connections, mutate: mutateConnections } = useSWR(
    session ? "/api/auth/connections" : null,
    () => apiFetch<{ connections: Connection[] }>("/api/auth/connections", session!.access_token),
  )

  useEffect(() => {
    if (searchParams.get("connected") || searchParams.get("error")) {
      mutateConnections()
      router.replace("/settings", { scroll: false })
    }
  }, [searchParams, mutateConnections, router])

  const handleDeleteMemory = async (id: string) => {
    if (!session) return
    await apiFetch(`/api/memories/${id}`, session.access_token, { method: "DELETE" })
    mutateMemories()
  }

  const handleConnect = async (provider: string) => {
    if (!session) return
    const data = await apiFetch<{ redirect_url: string }>(
      `/api/auth/connect/${provider}`,
      session.access_token,
    )
    window.location.href = data.redirect_url
  }

  const handleDisconnect = async (provider: string) => {
    if (!session) return
    await apiFetch(`/api/auth/disconnect/${provider}`, session.access_token, { method: "DELETE" })
    mutateConnections()
  }

  return (
    <div className="mx-auto max-w-2xl space-y-8 px-4 py-8">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={() => router.back()}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <h1 className="text-2xl font-semibold">Settings</h1>
      </div>

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Appearance</h2>
        <ThemeToggle />
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Connections</h2>
        <p className="text-sm text-muted-foreground">
          Connect external services to enhance SAM AI capabilities.
        </p>
        {connections?.connections.map((conn) => (
          <ConnectionCard
            key={conn.provider}
            provider={conn.provider}
            connected={conn.connected}
            onConnect={() => handleConnect(conn.provider)}
            onDisconnect={() => handleDisconnect(conn.provider)}
          />
        ))}
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Memories</h2>
        <p className="text-sm text-muted-foreground">
          SAM AI remembers facts about you across conversations.
        </p>
        {memories?.memories.length === 0 && (
          <p className="text-sm text-muted-foreground italic">No memories stored yet.</p>
        )}
        {memories?.memories.map((memory) => (
          <MemoryItem
            key={memory.id}
            id={memory.id}
            content={memory.content}
            category={memory.category}
            createdAt={memory.created_at}
            onDelete={handleDeleteMemory}
          />
        ))}
      </section>
    </div>
  )
}

export default function SettingsPage() {
  return (
    <Suspense>
      <SettingsContent />
    </Suspense>
  )
}
