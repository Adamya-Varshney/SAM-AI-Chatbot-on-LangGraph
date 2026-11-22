"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Plus, Settings, LogOut, Search, X, PanelLeftClose } from "lucide-react"
import { Button } from "@/components/ui/button"
import { ThreadList } from "@/components/sidebar/thread-list"
import { useAuth } from "@/hooks/use-auth"
import { useMediaQuery } from "@/hooks/use-media-query"
import { cn } from "@/lib/utils"

interface SidebarProps {
  open: boolean
  onClose?: () => void
  currentThreadId?: string
}

export function Sidebar({ open, onClose, currentThreadId }: SidebarProps) {
  const router = useRouter()
  const { user, signOut } = useAuth()
  const [searchOpen, setSearchOpen] = useState(false)
  const isDesktop = useMediaQuery("(min-width: 768px)")

  const handleNewChat = () => {
    const id = crypto.randomUUID()
    router.push(`/${id}`)
    onClose?.()
  }

  return (
    <aside
      className={cn(
        "flex h-full w-[280px] flex-col bg-card transition-transform duration-200",
        "border-r border-border/50",
        !open && "-translate-x-full md:translate-x-0",
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-3 sm:px-4">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold text-sm">
            S
          </div>
          <span className="text-base font-semibold truncate">SAM AI</span>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 shrink-0"
          onClick={() => setSearchOpen(!searchOpen)}
          aria-label="Search conversations"
        >
          <Search className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 shrink-0"
          onClick={handleNewChat}
          aria-label="New chat"
        >
          <Plus className="h-4 w-4" />
        </Button>
        {!isDesktop && (
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 shrink-0"
            onClick={onClose}
            aria-label="Close sidebar"
          >
            <PanelLeftClose className="h-4 w-4" />
          </Button>
        )}
      </div>

      {/* Search bar (collapsible) */}
      {searchOpen && (
        <div className="px-3 pb-2">
          <div className="flex items-center gap-1 rounded-lg border bg-background px-2">
            <Search className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
            <input
              autoFocus
              placeholder="Search conversations..."
              className="flex-1 bg-transparent py-1.5 text-sm outline-none placeholder:text-muted-foreground"
            />
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => setSearchOpen(false)}
            >
              <X className="h-3 w-3" />
            </Button>
          </div>
        </div>
      )}

      {/* Thread list */}
      <div className="flex-1 overflow-y-auto scrollbar-thin">
        <ThreadList currentThreadId={currentThreadId} onSelect={onClose} />
      </div>

      {/* Footer */}
      <div className="border-t border-border/50 p-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] space-y-1">
        <Button
          variant="ghost"
          className="w-full justify-start gap-2 h-9 px-3 text-sm"
          onClick={() => { router.push("/settings"); onClose?.() }}
        >
          <Settings className="h-4 w-4" />
          Settings
        </Button>
        <div className="flex items-center gap-2 px-3 py-1">
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-medium">
            {user?.email?.charAt(0).toUpperCase() || "?"}
          </div>
          <span className="flex-1 truncate text-sm text-muted-foreground">{user?.email}</span>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 shrink-0"
            onClick={signOut}
            aria-label="Sign out"
          >
            <LogOut className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
    </aside>
  )
}
