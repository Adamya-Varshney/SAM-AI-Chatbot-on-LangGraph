"use client"

import useSWR from "swr"
import { useRouter } from "next/navigation"
import { MessageSquare, Trash2 } from "lucide-react"
import { useAuth } from "@/hooks/use-auth"
import { apiFetch } from "@/lib/api"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"

interface Thread {
  thread_id: string
  title: string
  updated_at: string
}

interface ThreadListProps {
  currentThreadId?: string
  onSelect?: () => void
}

export function ThreadList({ currentThreadId, onSelect }: ThreadListProps) {
  const router = useRouter()
  const { session } = useAuth()

  const { data, mutate } = useSWR(
    session ? "/api/threads" : null,
    () => apiFetch<{ threads: Thread[] }>("/api/threads", session!.access_token),
    { revalidateOnFocus: false },
  )

  const handleDelete = async (e: React.MouseEvent, threadId: string) => {
    e.stopPropagation()
    if (!session) return

    await apiFetch(`/api/threads/${threadId}`, session.access_token, { method: "DELETE" })
    mutate()

    if (threadId === currentThreadId) {
      router.push("/")
    }
  }

  if (!data) {
    return <div className="p-4 text-sm text-muted-foreground">Loading...</div>
  }

  if (data.threads.length === 0) {
    return <div className="p-4 text-sm text-muted-foreground">No conversations yet</div>
  }

  return (
    <div className="space-y-1 px-2">
      {data.threads.map((thread) => (
        <div
          key={thread.thread_id}
          className={cn(
            "group flex cursor-pointer items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-accent",
            thread.thread_id === currentThreadId && "bg-accent",
          )}
          onClick={() => { router.push(`/${thread.thread_id}`); onSelect?.() }}
        >
          <MessageSquare className="h-4 w-4 shrink-0 text-muted-foreground" />
          <span className="flex-1 truncate">{thread.title}</span>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 opacity-0 group-hover:opacity-100"
            onClick={(e) => handleDelete(e, thread.thread_id)}
            aria-label="Delete thread"
          >
            <Trash2 className="h-3 w-3" />
          </Button>
        </div>
      ))}
    </div>
  )
}
