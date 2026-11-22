"use client"

import { useState, useRef, useEffect } from "react"
import useSWR from "swr"
import { useRouter } from "next/navigation"
import {
  MessageSquare,
  MoreHorizontal,
  Pencil,
  Trash2,
  Bookmark,
  BookmarkCheck,
  Check,
  X,
} from "lucide-react"
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

  const [menuOpen, setMenuOpen] = useState<string | null>(null)
  const [renaming, setRenaming] = useState<string | null>(null)
  const [renameValue, setRenameValue] = useState("")
  const [bookmarked, setBookmarked] = useState<Set<string>>(() => {
    if (typeof window === "undefined") return new Set()
    try {
      const saved = localStorage.getItem("sam-bookmarked-threads")
      return saved ? new Set(JSON.parse(saved)) : new Set()
    } catch {
      return new Set()
    }
  })
  const menuRef = useRef<HTMLDivElement>(null)
  const renameInputRef = useRef<HTMLInputElement>(null)

  const { data, mutate } = useSWR(
    session ? "/api/threads" : null,
    () => apiFetch<{ threads: Thread[] }>("/api/threads", session!.access_token),
    { revalidateOnFocus: false },
  )

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(null)
      }
    }
    if (menuOpen) {
      document.addEventListener("mousedown", handleClickOutside)
      return () => document.removeEventListener("mousedown", handleClickOutside)
    }
  }, [menuOpen])

  useEffect(() => {
    if (renaming && renameInputRef.current) {
      renameInputRef.current.focus()
      renameInputRef.current.select()
    }
  }, [renaming])

  const handleDelete = async (threadId: string) => {
    if (!session) return
    setMenuOpen(null)
    await apiFetch(`/api/threads/${threadId}`, session.access_token, { method: "DELETE" })
    mutate()
    if (threadId === currentThreadId) {
      router.push("/")
    }
  }

  const handleRenameStart = (thread: Thread) => {
    setMenuOpen(null)
    setRenaming(thread.thread_id)
    setRenameValue(thread.title)
  }

  const handleRenameSubmit = async (threadId: string) => {
    if (!session || !renameValue.trim()) {
      setRenaming(null)
      return
    }
    await apiFetch(`/api/threads/${threadId}`, session.access_token, {
      method: "PATCH",
      body: JSON.stringify({ title: renameValue.trim() }),
    })
    setRenaming(null)
    mutate()
  }

  const toggleBookmark = (threadId: string) => {
    setMenuOpen(null)
    setBookmarked((prev) => {
      const next = new Set(prev)
      if (next.has(threadId)) {
        next.delete(threadId)
      } else {
        next.add(threadId)
      }
      try {
        localStorage.setItem("sam-bookmarked-threads", JSON.stringify(Array.from(next)))
      } catch { /* ignore */ }
      return next
    })
  }

  if (!data) {
    return (
      <div className="space-y-2 px-3 py-2">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-9 animate-pulse rounded-lg bg-muted" />
        ))}
      </div>
    )
  }

  if (data.threads.length === 0) {
    return (
      <div className="px-4 py-8 text-center text-sm text-muted-foreground">
        No conversations yet.
        <br />
        Start a new chat to begin.
      </div>
    )
  }

  const bookmarkedThreads = data.threads.filter((t) => bookmarked.has(t.thread_id))
  const regularThreads = data.threads.filter((t) => !bookmarked.has(t.thread_id))

  const renderThread = (thread: Thread) => {
    const isActive = thread.thread_id === currentThreadId
    const isRenaming = renaming === thread.thread_id

    return (
      <div
        key={thread.thread_id}
        className={cn(
          "group relative flex cursor-pointer items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors",
          isActive
            ? "bg-accent text-accent-foreground"
            : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
        )}
        onClick={() => {
          if (!isRenaming) {
            router.push(`/${thread.thread_id}`)
            onSelect?.()
          }
        }}
      >
        {bookmarked.has(thread.thread_id) ? (
          <BookmarkCheck className="h-4 w-4 shrink-0 text-primary" />
        ) : (
          <MessageSquare className="h-4 w-4 shrink-0" />
        )}

        {isRenaming ? (
          <div className="flex flex-1 items-center gap-1" onClick={(e) => e.stopPropagation()}>
            <input
              ref={renameInputRef}
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleRenameSubmit(thread.thread_id)
                if (e.key === "Escape") setRenaming(null)
              }}
              className="flex-1 rounded border border-input bg-background px-2 py-0.5 text-sm outline-none focus:ring-1 focus:ring-ring"
            />
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => handleRenameSubmit(thread.thread_id)}
            >
              <Check className="h-3 w-3" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => setRenaming(null)}
            >
              <X className="h-3 w-3" />
            </Button>
          </div>
        ) : (
          <>
            <span className="flex-1 truncate">{thread.title}</span>
            <div className="relative" ref={menuOpen === thread.thread_id ? menuRef : undefined}>
              <Button
                variant="ghost"
                size="icon"
                className={cn(
                  "h-7 w-7 shrink-0",
                  menuOpen === thread.thread_id
                    ? "opacity-100"
                    : "opacity-0 group-hover:opacity-100",
                )}
                onClick={(e) => {
                  e.stopPropagation()
                  setMenuOpen(menuOpen === thread.thread_id ? null : thread.thread_id)
                }}
                aria-label="Thread options"
              >
                <MoreHorizontal className="h-4 w-4" />
              </Button>

              {menuOpen === thread.thread_id && (
                <div className="absolute right-0 top-full z-50 mt-1 w-44 rounded-lg border bg-card py-1 shadow-lg">
                  <button
                    className="flex w-full items-center gap-2 px-3 py-2 text-sm hover:bg-accent"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleRenameStart(thread)
                    }}
                  >
                    <Pencil className="h-4 w-4" />
                    Rename
                  </button>
                  <button
                    className="flex w-full items-center gap-2 px-3 py-2 text-sm hover:bg-accent"
                    onClick={(e) => {
                      e.stopPropagation()
                      toggleBookmark(thread.thread_id)
                    }}
                  >
                    {bookmarked.has(thread.thread_id) ? (
                      <>
                        <BookmarkCheck className="h-4 w-4" />
                        Unbookmark
                      </>
                    ) : (
                      <>
                        <Bookmark className="h-4 w-4" />
                        Bookmark
                      </>
                    )}
                  </button>
                  <div className="my-1 border-t" />
                  <button
                    className="flex w-full items-center gap-2 px-3 py-2 text-sm text-destructive hover:bg-destructive/10"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleDelete(thread.thread_id)
                    }}
                  >
                    <Trash2 className="h-4 w-4" />
                    Delete
                  </button>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-1 px-2">
      {bookmarkedThreads.length > 0 && (
        <>
          <div className="px-3 pb-1 pt-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Bookmarked
          </div>
          {bookmarkedThreads.map(renderThread)}
          {regularThreads.length > 0 && (
            <div className="px-3 pb-1 pt-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Recent
            </div>
          )}
        </>
      )}
      {regularThreads.map(renderThread)}
    </div>
  )
}
